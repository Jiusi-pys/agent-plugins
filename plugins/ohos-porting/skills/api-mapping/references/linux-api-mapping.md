# Linux API 到 OHOS API 完整映射表

## 事件机制

### epoll → poll

**Linux 代码:**
```c
#include <sys/epoll.h>

int epfd = epoll_create1(0);
struct epoll_event ev = {.events = EPOLLIN, .data.fd = fd};
epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &ev);

struct epoll_event events[10];
int n = epoll_wait(epfd, events, 10, timeout_ms);
for (int i = 0; i < n; i++) {
    if (events[i].events & EPOLLIN) {
        // handle read
    }
}
close(epfd);
```

**OHOS 适配:**
```c
#include <poll.h>

struct pollfd fds[MAX_FDS];
int nfds = 0;

// 添加文件描述符
fds[nfds].fd = fd;
fds[nfds].events = POLLIN;
nfds++;

// 等待事件
int n = poll(fds, nfds, timeout_ms);
for (int i = 0; i < nfds; i++) {
    if (fds[i].revents & POLLIN) {
        // handle read
    }
}
```

**条件编译包装:**
```c
#ifdef __OHOS__
    #include "pal_poll.h"
    #define pal_event_init() poll_init()
    #define pal_event_add(fd, events) poll_add(fd, events)
    #define pal_event_wait(timeout) poll_wait(timeout)
#else
    #include "pal_epoll.h"
    #define pal_event_init() epoll_init()
    #define pal_event_add(fd, events) epoll_add(fd, events)
    #define pal_event_wait(timeout) epoll_wait_wrapper(timeout)
#endif
```

---

### inotify → FileWatcher

**Linux 代码:**
```c
#include <sys/inotify.h>

int ifd = inotify_init1(IN_NONBLOCK);
int wd = inotify_add_watch(ifd, "/path/to/watch", IN_MODIFY | IN_CREATE);

char buf[4096];
ssize_t len = read(ifd, buf, sizeof(buf));
for (char *ptr = buf; ptr < buf + len; ) {
    struct inotify_event *event = (struct inotify_event *)ptr;
    if (event->mask & IN_MODIFY) {
        printf("File modified: %s\n", event->name);
    }
    ptr += sizeof(struct inotify_event) + event->len;
}
```

**OHOS 适配 (简化版 - 轮询):**
```c
#include <sys/stat.h>
#include <dirent.h>
#include <time.h>

typedef struct {
    char path[PATH_MAX];
    time_t last_mtime;
} file_watch_t;

int file_watch_check(file_watch_t *watch) {
    struct stat st;
    if (stat(watch->path, &st) != 0) return -1;
    
    if (st.st_mtime != watch->last_mtime) {
        watch->last_mtime = st.st_mtime;
        return 1;  // modified
    }
    return 0;
}
```

---

### eventfd → pipe

**Linux 代码:**
```c
#include <sys/eventfd.h>

int efd = eventfd(0, EFD_NONBLOCK);
uint64_t val = 1;
write(efd, &val, sizeof(val));  // signal
read(efd, &val, sizeof(val));   // wait
```

**OHOS 适配:**
```c
int pipefd[2];
pipe(pipefd);
fcntl(pipefd[0], F_SETFL, O_NONBLOCK);
fcntl(pipefd[1], F_SETFL, O_NONBLOCK);

char dummy = 1;
write(pipefd[1], &dummy, 1);  // signal
read(pipefd[0], &dummy, 1);   // wait
```

---

### signalfd → signal handler

**Linux 代码:**
```c
#include <sys/signalfd.h>

sigset_t mask;
sigemptyset(&mask);
sigaddset(&mask, SIGINT);
sigprocmask(SIG_BLOCK, &mask, NULL);

int sfd = signalfd(-1, &mask, SFD_NONBLOCK);
struct signalfd_siginfo fdsi;
read(sfd, &fdsi, sizeof(fdsi));
if (fdsi.ssi_signo == SIGINT) {
    // handle SIGINT
}
```

**OHOS 适配:**
```c
#include <signal.h>

volatile sig_atomic_t got_sigint = 0;

void sigint_handler(int sig) {
    got_sigint = 1;
}

// 设置
struct sigaction sa = {.sa_handler = sigint_handler};
sigaction(SIGINT, &sa, NULL);

// 检查
if (got_sigint) {
    got_sigint = 0;
    // handle SIGINT
}
```

---

### timerfd → timer_create

**Linux 代码:**
```c
#include <sys/timerfd.h>

int tfd = timerfd_create(CLOCK_MONOTONIC, TFD_NONBLOCK);
struct itimerspec ts = {
    .it_value = {.tv_sec = 1, .tv_nsec = 0},
    .it_interval = {.tv_sec = 1, .tv_nsec = 0}
};
timerfd_settime(tfd, 0, &ts, NULL);

uint64_t expirations;
read(tfd, &expirations, sizeof(expirations));
```

**OHOS 适配:**
```c
#include <signal.h>
#include <time.h>

volatile sig_atomic_t timer_expired = 0;

void timer_handler(int sig, siginfo_t *si, void *uc) {
    timer_expired = 1;
}

timer_t timerid;
struct sigevent sev = {
    .sigev_notify = SIGEV_SIGNAL,
    .sigev_signo = SIGRTMIN,
};
timer_create(CLOCK_MONOTONIC, &sev, &timerid);

struct sigaction sa = {
    .sa_flags = SA_SIGINFO,
    .sa_sigaction = timer_handler,
};
sigaction(SIGRTMIN, &sa, NULL);

struct itimerspec ts = {
    .it_value = {.tv_sec = 1, .tv_nsec = 0},
    .it_interval = {.tv_sec = 1, .tv_nsec = 0}
};
timer_settime(timerid, 0, &ts, NULL);
```

---

## 进程/线程

### getauxval

**Linux 代码:**
```c
#include <sys/auxv.h>
unsigned long page_size = getauxval(AT_PAGESZ);
```

**OHOS 适配:**
```c
#include <unistd.h>
long page_size = sysconf(_SC_PAGESIZE);
```

---

### prctl

**Linux 代码:**
```c
#include <sys/prctl.h>
prctl(PR_SET_NAME, "mythread");
```

**OHOS 适配:**
```c
#include <pthread.h>
pthread_setname_np(pthread_self(), "mythread");
```

---

## 文件系统

### /proc/self/exe

**Linux 代码:**
```c
char path[PATH_MAX];
readlink("/proc/self/exe", path, sizeof(path));
```

**OHOS 适配:**
```c
// OHOS 上 /proc/self/exe 可能受限
// 替代方案: 在 main() 中保存 argv[0] 的绝对路径
extern char *g_exe_path;  // 全局变量
```

---

### /proc/self/fd

**Linux 代码:**
```c
char link[PATH_MAX];
snprintf(link, sizeof(link), "/proc/self/fd/%d", fd);
readlink(link, path, sizeof(path));
```

**OHOS 适配:**
```c
// 使用 fcntl 获取部分信息
int flags = fcntl(fd, F_GETFL);
// 或记录文件描述符与路径的映射关系
```

---

## 网络

### socket options

大部分 socket 选项兼容，以下需注意：

| 选项 | 状态 |
|-----|------|
| SO_REUSEADDR | ✓ 支持 |
| SO_REUSEPORT | ✓ 支持 |
| SO_KEEPALIVE | ✓ 支持 |
| TCP_NODELAY | ✓ 支持 |
| TCP_CORK | ⚠ 使用 TCP_NODELAY 替代 |
| SO_BINDTODEVICE | ✗ 不支持 |

---

## 内存

### mmap flags

| Flag | 状态 |
|------|------|
| MAP_ANONYMOUS | ✓ 支持 |
| MAP_PRIVATE | ✓ 支持 |
| MAP_SHARED | ✓ 支持 |
| MAP_FIXED | ⚠ 谨慎使用 |
| MAP_HUGETLB | ✗ 不支持 |
| MAP_POPULATE | ✗ 不支持 |

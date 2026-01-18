/**
 * stub_write.c - LD_PRELOAD 运行时打桩：拦截 write() 系统调用
 * 
 * 功能：
 * - 记录所有 write() 调用（fd、长度、内容预览）
 * - 日志固定从 fd=2 (stderr) 输出
 * - 支持额外写入日志文件
 * - 避免递归（使用 syscall 直接写）
 * 
 * 编译：
 *   gcc -shared -fPIC -O2 -o libstub_write.so stub_write.c -ldl -pthread
 * 
 * 使用：
 *   LD_PRELOAD=./libstub_write.so ./target
 * 
 * 环境变量：
 *   STUB_LOG_FD=2        日志输出 fd（默认 stderr）
 *   STUB_LOG_FILE=path   额外写入日志文件
 *   STUB_PREVIEW=80      内容预览字节数
 *   STUB_HEX=1           输出 hex 编码
 *   STUB_FILTER_FD=1,2   只记录指定 fd
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

/* 真实函数指针 */
static ssize_t (*real_write)(int, const void*, size_t) = NULL;

/* 配置 */
static int g_log_fd = 2;           /* 日志输出 fd，默认 stderr */
static int g_log_file_fd = -1;     /* 额外日志文件 fd */
static size_t g_preview = 80;      /* 预览字节数 */
static int g_hex = 0;              /* 是否 hex 编码 */
static char g_filter_fds[64] = ""; /* 过滤 fd 列表 */
static int g_initialized = 0;

/* 线程安全锁 */
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

/* 直接系统调用写，避免递归 */
static void raw_write(int fd, const char* buf, size_t len) {
    if (fd >= 0 && buf && len > 0) {
        syscall(SYS_write, fd, buf, len);
    }
}

/* 写日志（同时写 log_fd 和 log_file） */
static void log_output(const char* buf, size_t len) {
    raw_write(g_log_fd, buf, len);
    if (g_log_file_fd >= 0) {
        raw_write(g_log_file_fd, buf, len);
    }
}

/* 格式化日志 */
static void log_fmt(const char* fmt, ...) {
    char buf[1024];
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    if (n > 0) {
        log_output(buf, (size_t)n);
    }
}

/* 检查 fd 是否在过滤列表中 */
static int should_log_fd(int fd) {
    if (g_filter_fds[0] == '\0') {
        return 1; /* 无过滤，全部记录 */
    }
    char needle[16];
    snprintf(needle, sizeof(needle), "%d", fd);
    return strstr(g_filter_fds, needle) != NULL;
}

/* 输出 hex 编码 */
static void log_hex(const void* data, size_t len) {
    const unsigned char* p = (const unsigned char*)data;
    char hex[4];
    for (size_t i = 0; i < len; i++) {
        snprintf(hex, sizeof(hex), "%02x ", p[i]);
        log_output(hex, 3);
    }
}

/* 初始化 */
__attribute__((constructor))
static void init_stub(void) {
    if (g_initialized) return;
    
    /* 获取真实 write */
    real_write = (ssize_t(*)(int,const void*,size_t))dlsym(RTLD_NEXT, "write");
    if (!real_write) {
        raw_write(2, "[STUB] FATAL: dlsym(write) failed\n", 35);
        return;
    }
    
    /* 读取配置 */
    const char* env;
    
    if ((env = getenv("STUB_LOG_FD"))) {
        g_log_fd = atoi(env);
    }
    
    if ((env = getenv("STUB_LOG_FILE"))) {
        g_log_file_fd = syscall(SYS_openat, AT_FDCWD, env, 
                                O_WRONLY | O_CREAT | O_APPEND, 0644);
    }
    
    if ((env = getenv("STUB_PREVIEW"))) {
        g_preview = (size_t)atoi(env);
    }
    
    if ((env = getenv("STUB_HEX"))) {
        g_hex = atoi(env);
    }
    
    if ((env = getenv("STUB_FILTER_FD"))) {
        strncpy(g_filter_fds, env, sizeof(g_filter_fds) - 1);
    }
    
    g_initialized = 1;
    
    log_fmt("[STUB] write-logger initialized (log_fd=%d, preview=%zu, hex=%d)\n",
            g_log_fd, g_preview, g_hex);
}

/* 清理 */
__attribute__((destructor))
static void fini_stub(void) {
    if (g_log_file_fd >= 0) {
        syscall(SYS_close, g_log_file_fd);
        g_log_file_fd = -1;
    }
    log_fmt("[STUB] write-logger finalized\n");
}

/* 拦截 write() */
ssize_t write(int fd, const void* buf, size_t count) {
    if (!real_write) {
        errno = ENOSYS;
        return -1;
    }
    
    /* 检查是否需要记录 */
    if (should_log_fd(fd)) {
        pthread_mutex_lock(&g_lock);
        
        /* 时间戳 */
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        
        /* 日志头 */
        log_fmt("[STUB write] ts=%ld.%09ld pid=%d tid=%ld fd=%d count=%zu ",
                (long)ts.tv_sec, ts.tv_nsec,
                (int)getpid(), (long)syscall(SYS_gettid),
                fd, count);
        
        /* 内容预览 */
        if (buf && count > 0) {
            size_t preview_len = (count > g_preview) ? g_preview : count;
            
            if (g_hex) {
                log_output("hex=", 4);
                log_hex(buf, preview_len);
            } else {
                log_output("preview=\"", 9);
                /* 过滤非打印字符 */
                const char* p = (const char*)buf;
                for (size_t i = 0; i < preview_len; i++) {
                    char c = p[i];
                    if (c >= 32 && c < 127) {
                        log_output(&c, 1);
                    } else if (c == '\n') {
                        log_output("\\n", 2);
                    } else if (c == '\r') {
                        log_output("\\r", 2);
                    } else if (c == '\t') {
                        log_output("\\t", 2);
                    } else {
                        char esc[5];
                        snprintf(esc, sizeof(esc), "\\x%02x", (unsigned char)c);
                        log_output(esc, 4);
                    }
                }
                log_output("\"", 1);
            }
            
            if (count > preview_len) {
                log_output(" ...", 4);
            }
        }
        
        log_output("\n", 1);
        
        pthread_mutex_unlock(&g_lock);
    }
    
    /* 调用真实 write */
    return real_write(fd, buf, count);
}

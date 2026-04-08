/**
 * stub_net.c - LD_PRELOAD 网络调用打桩
 * 
 * 拦截: connect, send, recv, socket, bind, listen, accept
 * 
 * 编译:
 *   gcc -shared -fPIC -O2 -o libstub_net.so stub_net.c -ldl -pthread
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

/* 真实函数指针 */
static int (*real_socket)(int, int, int) = NULL;
static int (*real_connect)(int, const struct sockaddr*, socklen_t) = NULL;
static ssize_t (*real_send)(int, const void*, size_t, int) = NULL;
static ssize_t (*real_recv)(int, void*, size_t, int) = NULL;
static int (*real_bind)(int, const struct sockaddr*, socklen_t) = NULL;

static int g_log_fd = 2;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

/* 直接系统调用写日志 */
static void log_fmt(const char* fmt, ...) {
    char buf[1024];
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    if (n > 0) {
        syscall(SYS_write, g_log_fd, buf, (size_t)n);
    }
}

/* 格式化地址 */
static void format_addr(const struct sockaddr* addr, char* buf, size_t len) {
    if (!addr) {
        snprintf(buf, len, "NULL");
        return;
    }
    
    if (addr->sa_family == AF_INET) {
        struct sockaddr_in* in = (struct sockaddr_in*)addr;
        char ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &in->sin_addr, ip, sizeof(ip));
        snprintf(buf, len, "%s:%d", ip, ntohs(in->sin_port));
    } else if (addr->sa_family == AF_INET6) {
        struct sockaddr_in6* in6 = (struct sockaddr_in6*)addr;
        char ip[INET6_ADDRSTRLEN];
        inet_ntop(AF_INET6, &in6->sin6_addr, ip, sizeof(ip));
        snprintf(buf, len, "[%s]:%d", ip, ntohs(in6->sin6_port));
    } else {
        snprintf(buf, len, "family=%d", addr->sa_family);
    }
}

__attribute__((constructor))
static void init_stub(void) {
    real_socket = dlsym(RTLD_NEXT, "socket");
    real_connect = dlsym(RTLD_NEXT, "connect");
    real_send = dlsym(RTLD_NEXT, "send");
    real_recv = dlsym(RTLD_NEXT, "recv");
    real_bind = dlsym(RTLD_NEXT, "bind");
    
    const char* env = getenv("STUB_LOG_FD");
    if (env) g_log_fd = atoi(env);
    
    log_fmt("[STUB] net-logger initialized\n");
}

int socket(int domain, int type, int protocol) {
    if (!real_socket) { errno = ENOSYS; return -1; }
    
    int fd = real_socket(domain, type, protocol);
    
    pthread_mutex_lock(&g_lock);
    log_fmt("[STUB socket] domain=%d type=%d proto=%d -> fd=%d\n",
            domain, type, protocol, fd);
    pthread_mutex_unlock(&g_lock);
    
    return fd;
}

int connect(int sockfd, const struct sockaddr* addr, socklen_t addrlen) {
    if (!real_connect) { errno = ENOSYS; return -1; }
    
    char addr_str[128];
    format_addr(addr, addr_str, sizeof(addr_str));
    
    int ret = real_connect(sockfd, addr, addrlen);
    
    pthread_mutex_lock(&g_lock);
    log_fmt("[STUB connect] fd=%d addr=%s -> ret=%d (errno=%d)\n",
            sockfd, addr_str, ret, ret < 0 ? errno : 0);
    pthread_mutex_unlock(&g_lock);
    
    return ret;
}

ssize_t send(int sockfd, const void* buf, size_t len, int flags) {
    if (!real_send) { errno = ENOSYS; return -1; }
    
    ssize_t ret = real_send(sockfd, buf, len, flags);
    
    pthread_mutex_lock(&g_lock);
    log_fmt("[STUB send] fd=%d len=%zu flags=%d -> sent=%zd\n",
            sockfd, len, flags, ret);
    pthread_mutex_unlock(&g_lock);
    
    return ret;
}

ssize_t recv(int sockfd, void* buf, size_t len, int flags) {
    if (!real_recv) { errno = ENOSYS; return -1; }
    
    ssize_t ret = real_recv(sockfd, buf, len, flags);
    
    pthread_mutex_lock(&g_lock);
    log_fmt("[STUB recv] fd=%d len=%zu flags=%d -> recv=%zd\n",
            sockfd, len, flags, ret);
    pthread_mutex_unlock(&g_lock);
    
    return ret;
}

int bind(int sockfd, const struct sockaddr* addr, socklen_t addrlen) {
    if (!real_bind) { errno = ENOSYS; return -1; }
    
    char addr_str[128];
    format_addr(addr, addr_str, sizeof(addr_str));
    
    int ret = real_bind(sockfd, addr, addrlen);
    
    pthread_mutex_lock(&g_lock);
    log_fmt("[STUB bind] fd=%d addr=%s -> ret=%d\n", sockfd, addr_str, ret);
    pthread_mutex_unlock(&g_lock);
    
    return ret;
}

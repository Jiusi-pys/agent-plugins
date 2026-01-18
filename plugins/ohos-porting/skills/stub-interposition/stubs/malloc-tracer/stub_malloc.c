/**
 * stub_malloc.c - LD_PRELOAD 内存分配打桩
 * 
 * 拦截: malloc, free, realloc, calloc
 * 
 * 注意: 内存函数打桩需要特别小心递归和初始化顺序问题
 * 
 * 编译:
 *   gcc -shared -fPIC -O2 -o libstub_malloc.so stub_malloc.c -ldl -pthread
 */

#define _GNU_SOURCE
#include <dlfcn.h>
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
static void* (*real_malloc)(size_t) = NULL;
static void (*real_free)(void*) = NULL;
static void* (*real_realloc)(void*, size_t) = NULL;
static void* (*real_calloc)(size_t, size_t) = NULL;

static int g_log_fd = 2;
static int g_initialized = 0;
static int g_in_init = 0;
static __thread int t_in_hook = 0; /* 防止递归 */

/* 统计 */
static size_t g_total_alloc = 0;
static size_t g_total_free = 0;
static size_t g_alloc_count = 0;
static size_t g_free_count = 0;

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

/* 临时分配器（初始化前使用） */
static char g_temp_buf[65536];
static size_t g_temp_pos = 0;

static void* temp_malloc(size_t size) {
    size = (size + 15) & ~15; /* 16 字节对齐 */
    if (g_temp_pos + size > sizeof(g_temp_buf)) {
        return NULL;
    }
    void* p = &g_temp_buf[g_temp_pos];
    g_temp_pos += size;
    return p;
}

/* 直接系统调用写日志 */
static void log_fmt(const char* fmt, ...) {
    if (t_in_hook) return; /* 防止递归 */
    
    char buf[512];
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    if (n > 0) {
        syscall(SYS_write, g_log_fd, buf, (size_t)n);
    }
}

__attribute__((constructor))
static void init_stub(void) {
    if (g_initialized || g_in_init) return;
    g_in_init = 1;
    
    real_malloc = dlsym(RTLD_NEXT, "malloc");
    real_free = dlsym(RTLD_NEXT, "free");
    real_realloc = dlsym(RTLD_NEXT, "realloc");
    real_calloc = dlsym(RTLD_NEXT, "calloc");
    
    const char* env = getenv("STUB_LOG_FD");
    if (env) g_log_fd = atoi(env);
    
    g_initialized = 1;
    g_in_init = 0;
    
    log_fmt("[STUB] malloc-tracer initialized\n");
}

__attribute__((destructor))
static void fini_stub(void) {
    log_fmt("[STUB] malloc-tracer stats: alloc=%zu bytes (%zu calls), "
            "free=%zu bytes (%zu calls)\n",
            g_total_alloc, g_alloc_count, g_total_free, g_free_count);
}

void* malloc(size_t size) {
    /* 初始化前使用临时分配器 */
    if (!g_initialized) {
        if (!g_in_init) init_stub();
        if (!real_malloc) return temp_malloc(size);
    }
    
    if (t_in_hook) return real_malloc(size);
    t_in_hook = 1;
    
    void* p = real_malloc(size);
    
    pthread_mutex_lock(&g_lock);
    g_total_alloc += size;
    g_alloc_count++;
    log_fmt("[STUB malloc] size=%zu -> ptr=%p\n", size, p);
    pthread_mutex_unlock(&g_lock);
    
    t_in_hook = 0;
    return p;
}

void free(void* ptr) {
    /* 临时缓冲区内的指针不释放 */
    if (ptr >= (void*)g_temp_buf && 
        ptr < (void*)(g_temp_buf + sizeof(g_temp_buf))) {
        return;
    }
    
    if (!g_initialized || !real_free) return;
    if (t_in_hook) { real_free(ptr); return; }
    
    t_in_hook = 1;
    
    pthread_mutex_lock(&g_lock);
    g_free_count++;
    log_fmt("[STUB free] ptr=%p\n", ptr);
    pthread_mutex_unlock(&g_lock);
    
    real_free(ptr);
    t_in_hook = 0;
}

void* realloc(void* ptr, size_t size) {
    if (!g_initialized) {
        if (!g_in_init) init_stub();
        if (!real_realloc) {
            void* new_ptr = temp_malloc(size);
            if (ptr && new_ptr) memcpy(new_ptr, ptr, size);
            return new_ptr;
        }
    }
    
    if (t_in_hook) return real_realloc(ptr, size);
    t_in_hook = 1;
    
    void* new_ptr = real_realloc(ptr, size);
    
    pthread_mutex_lock(&g_lock);
    g_total_alloc += size;
    g_alloc_count++;
    log_fmt("[STUB realloc] ptr=%p size=%zu -> new_ptr=%p\n", ptr, size, new_ptr);
    pthread_mutex_unlock(&g_lock);
    
    t_in_hook = 0;
    return new_ptr;
}

void* calloc(size_t nmemb, size_t size) {
    if (!g_initialized) {
        if (!g_in_init) init_stub();
        if (!real_calloc) {
            size_t total = nmemb * size;
            void* p = temp_malloc(total);
            if (p) memset(p, 0, total);
            return p;
        }
    }
    
    if (t_in_hook) return real_calloc(nmemb, size);
    t_in_hook = 1;
    
    void* p = real_calloc(nmemb, size);
    
    pthread_mutex_lock(&g_lock);
    g_total_alloc += nmemb * size;
    g_alloc_count++;
    log_fmt("[STUB calloc] nmemb=%zu size=%zu -> ptr=%p\n", nmemb, size, p);
    pthread_mutex_unlock(&g_lock);
    
    t_in_hook = 0;
    return p;
}

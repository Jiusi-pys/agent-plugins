# Stub Interposition Skill

## 概述

运行时函数打桩技术，实现 **免改源码、免重编译** 的测试插桩。通过 `LD_PRELOAD` 机制劫持动态链接符号，自动记录 I/O、系统调用、内存操作等行为。

## 核心原理

基于 CSAPP (Chapter 7: Linking) 的 interposition 机制：

| 方案 | 机制 | 改源码 | 重编译 | 适用场景 |
|------|------|--------|--------|----------|
| **运行时打桩 (LD_PRELOAD)** | 动态链接器优先加载 stub.so | ❌ | ❌ | 动态链接程序 |
| 链接期打桩 (--wrap) | 链接器符号重定向 | ❌ | ✅ | 静态链接/嵌入式 |
| 编译期打桩 (宏替换) | #define 替换 | ✅ | ✅ | 源码可控时 |

**本 skill 优先使用 LD_PRELOAD 方案**，静态链接时退化到 `--wrap`。

## 使用方法

### 快速开始

```bash
# 1. 构建 stub 库（自动缓存）
./scripts/stubctl build write-logger

# 2. 运行目标程序（自动注入）
./scripts/stubctl run write-logger -- ./target arg1 arg2

# 3. 查看日志（从 stderr 输出）
./scripts/stubctl run write-logger -- ./target 2>&1 | tee test.log
```

### 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STUB_LOG_FD` | 2 | 日志输出 fd（固定 stderr） |
| `STUB_LOG_FILE` | - | 额外追加写入的日志文件 |
| `STUB_PREVIEW` | 80 | 内容预览字节数 |
| `STUB_HEX` | 0 | 1=输出 hex 编码（避免二进制污染终端） |
| `STUB_FILTER_FD` | - | 只记录指定 fd（如 `1,2`） |

### 可用 Stub 模块

#### write-logger
拦截 `write()` 系统调用，记录所有 I/O 输出。

```bash
./scripts/stubctl run write-logger -- ./myapp
```

输出示例：
```
[STUB write] ts=1705123456.789012345 pid=12345 tid=12345 fd=1 count=21 preview="hello stdout"
```

#### net-logger (可选)
拦截网络调用：`connect/send/recv/socket`

#### malloc-tracer (可选)
拦截内存分配：`malloc/free/realloc`

## 技术实现

### 核心机制：dlsym(RTLD_NEXT)

```c
// 获取真实函数指针
static ssize_t (*real_write)(int, const void*, size_t) = NULL;

__attribute__((constructor))
static void init_stub(void) {
    real_write = dlsym(RTLD_NEXT, "write");
}

// 拦截函数
ssize_t write(int fd, const void* buf, size_t count) {
    // 1. 记录日志（用 syscall 避免递归）
    log_to_fd2("[STUB] write fd=%d count=%zu", fd, count);
    
    // 2. 调用真实函数
    return real_write(fd, buf, count);
}
```

### 避免递归的关键

日志输出必须用 `syscall(SYS_write, 2, ...)` 直接系统调用，避免再次进入被 hook 的 `write()` 造成无限递归。

### 限制条件

1. **静态链接程序**：LD_PRELOAD 无效，需使用 `--wrap` 方案
2. **setuid/setgid 程序**：安全机制禁用 LD_PRELOAD
3. **多线程**：日志输出需原子化（单次 syscall 写完整行）

## 检测与自动选择

```bash
# 自动检测二进制类型
file ./target | grep -q "dynamically linked" && echo "可用 LD_PRELOAD" || echo "需要 --wrap"
```

Skill 会自动：
1. 检测目标是否动态链接
2. 动态链接 → LD_PRELOAD
3. 静态链接 → 提示使用 --wrap 或重新构建

## 与 OHOS 开发集成

### 交叉编译的 stub

为 ARM64/OHOS 目标构建 stub：

```bash
# 使用 OHOS 工具链构建
./scripts/stubctl build write-logger --target=arm64-ohos

# 推送到设备
hdc file send libstub_write.so /data/local/tmp/

# 在设备上运行
hdc shell "LD_PRELOAD=/data/local/tmp/libstub_write.so /system/bin/target"
```

### 调试 dsoftbus/rmw_dsoftbus

```bash
# 记录所有 IPC 写入
STUB_FILTER_FD=3,4,5 ./scripts/stubctl run write-logger -- ./ros2_node

# 记录网络通信
./scripts/stubctl run net-logger -- ./dsoftbus_test
```

## 工程结构

```
stub-interposition/
├── SKILL.md
├── scripts/
│   ├── stubctl              # 统一入口
│   ├── build.sh             # 构建脚本
│   └── run.sh               # 运行脚本
└── stubs/
    ├── write-logger/
    │   └── stub_write.c
    ├── net-logger/
    │   └── stub_net.c
    └── malloc-tracer/
        └── stub_malloc.c
```

## 参考

- CSAPP Chapter 7: Linking - Interposition
- dlsym(3) RTLD_NEXT
- ld.so(8) LD_PRELOAD

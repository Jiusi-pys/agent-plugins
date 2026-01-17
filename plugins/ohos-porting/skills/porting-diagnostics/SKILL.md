---
name: porting-diagnostics
description: Linux 到 OHOS 移植可行性诊断。分析源码的平台依赖、API 兼容性、移植难度。移植前分析时自动加载。
---

# Porting Diagnostics Skill

## 概述

提供 Linux 软件到 OpenHarmony 移植的可行性诊断能力，包括：
- 平台特定 API 检测
- 依赖库兼容性分析
- 移植难度评估
- 风险识别

## 诊断命令

### 快速扫描
```bash
# 使用 scripts/quick_scan.sh
./scripts/quick_scan.sh /path/to/source
```

### 详细分析
```bash
# 使用 scripts/full_analysis.py
python3 scripts/full_analysis.py /path/to/source --output report.json
```

## API 兼容性速查

### 完全兼容 (绿灯)
```
pthread_create, pthread_join, pthread_mutex_*
socket, bind, listen, accept, connect, send, recv
open, read, write, close, lseek, fstat
malloc, free, realloc, calloc
memcpy, memset, strcmp, strlen
printf, fprintf, sprintf, snprintf
```

### 需要适配 (黄灯)
```
epoll_create, epoll_ctl, epoll_wait     → poll() 或 select()
inotify_init, inotify_add_watch         → OHOS FileWatcher API
eventfd, timerfd_create                  → pipe() + timer
signalfd                                 → signal() handler
getauxval                                → 直接读取 /proc/self/auxv (受限)
```

### 不可移植 (红灯)
```
io_uring_*                               → 重写为同步/线程池
clone() with CLONE_NEWNS/NEWPID          → 不支持
unshare(), setns()                       → 不支持
perf_event_open()                        → 不支持
bpf()                                    → 不支持
```

## 难度评级标准

| 等级 | 红灯 API | 黄灯 API | 依赖状态 | 工时估计 |
|-----|---------|---------|---------|---------|
| A   | 0       | 0-5     | 全部可用 | < 1天   |
| B   | 0       | 5-20    | 大部分可用 | 1-3天   |
| C   | 1-5     | 20+     | 部分需移植 | 1-2周   |
| D   | 5+      | -       | 核心依赖不可用 | 放弃    |

## 参考文档

- [references/linux-api-mapping.md](references/linux-api-mapping.md) - 完整 API 映射表
- [references/common-issues.md](references/common-issues.md) - 常见问题和解决方案

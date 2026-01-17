---
name: api-mapping
description: Linux API 到 OHOS API 的映射知识库。查询 API 替代方案和适配代码。编写适配代码时自动加载。
---

# API Mapping Skill

## 概述

提供 Linux API 到 OpenHarmony API 的映射关系和适配代码模板。

## 快速查询

查询特定 API 的 OHOS 替代方案：
```bash
grep -A 10 "epoll" references/linux-api-mapping.md
```

## 映射分类

### 事件机制

| Linux API | OHOS 替代 | 复杂度 |
|-----------|----------|--------|
| epoll | poll/select | 中 |
| inotify | OHOS FileWatcher | 中 |
| eventfd | pipe | 低 |
| signalfd | signal handler | 中 |
| timerfd | timer_create | 低 |

### 进程/线程

| Linux API | OHOS 替代 | 复杂度 |
|-----------|----------|--------|
| clone (线程) | pthread_create | 低 |
| clone (namespace) | 不支持 | - |
| prctl | 部分支持 | 中 |
| sched_setaffinity | 部分支持 | 中 |

### 文件系统

| Linux API | OHOS 替代 | 复杂度 |
|-----------|----------|--------|
| /proc/self/* | 受限访问 | 高 |
| /sys/* | 不支持 | - |
| statfs | statvfs | 低 |

## 代码模板

详见 [references/code-templates.md](references/code-templates.md)

## 参考

- [references/linux-api-mapping.md](references/linux-api-mapping.md) - 完整映射表
- [references/code-templates.md](references/code-templates.md) - 适配代码模板

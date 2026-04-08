---
name: compile-error-analysis
description: OHOS 交叉编译错误分析。诊断编译失败原因，提供修复方案。编译出错时自动加载。
---

# Compile Error Analysis Skill

## 概述

提供 OHOS 交叉编译错误的诊断和修复能力。

## 错误分类

### 1. 头文件错误
- 症状: `fatal error: xxx.h: No such file or directory`
- 处理: 优先核对 sysroot 头文件路径、条件编译开关和替代头文件。

### 2. 符号未定义
- 症状: `undefined reference to 'xxx'`
- 处理: 核对链接顺序、目标库是否存在，以及 Linux 专有符号是否需要替换。

### 3. 类型不兼容
- 症状: `error: incompatible types`
- 处理: 对照 OHOS 头文件中的实际类型定义，检查 ABI 和条件编译差异。

### 4. 链接错误
- 症状: `cannot find -lxxx`
- 处理: 检查库名、sysroot 库目录和是否误用了 Linux 专有链接参数。

## 快速诊断

```bash
# 运行错误分析脚本
./scripts/analyze_errors.sh build.log
```

## 常见错误速查

| 错误 | 原因 | 修复 |
|-----|------|------|
| `sys/epoll.h not found` | Linux 特有 | 使用 poll.h |
| `undefined reference to 'epoll_create'` | Linux 特有 | 条件编译 |
| `cannot find -lrt` | OHOS 在 libc 中 | 移除 -lrt |
| `incompatible pointer type` | ABI 差异 | 检查类型定义 |

## OHOS 工具链检查

```bash
# 检查 clang
${OHOS_SDK}/native/llvm/bin/clang --version

# 检查 sysroot
ls -la ${OHOS_SDK}/native/sysroot/usr/include/

# 检查库路径
ls -la ${OHOS_SDK}/native/sysroot/usr/lib/aarch64-linux-ohos/
```

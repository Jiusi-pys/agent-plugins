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
- 参考: [references/header-errors.md](references/header-errors.md)

### 2. 符号未定义
- 症状: `undefined reference to 'xxx'`
- 参考: [references/undefined-symbols.md](references/undefined-symbols.md)

### 3. 类型不兼容
- 症状: `error: incompatible types`
- 参考: [references/type-errors.md](references/type-errors.md)

### 4. 链接错误
- 症状: `cannot find -lxxx`
- 参考: [references/linker-errors.md](references/linker-errors.md)

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

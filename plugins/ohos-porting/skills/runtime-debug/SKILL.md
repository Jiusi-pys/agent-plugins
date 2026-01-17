---
name: runtime-debug
description: OHOS 设备运行时调试。分析程序崩溃、权限错误、动态库问题。部署测试出错时自动加载。
---

# Runtime Debug Skill

## 概述

提供 OHOS 设备端程序运行时问题的诊断能力。

## 日志收集

### 系统日志
```bash
hdc shell "logcat -d" > logcat.txt
hdc shell "logcat -d | grep -E 'FATAL|CRASH|SIGSEGV'"
```

### 崩溃日志
```bash
hdc shell "ls /data/log/faultlog/"
hdc shell "cat /data/log/faultlog/cppcrash-*"
```

### 动态库依赖
```bash
hdc shell "ldd /data/local/tmp/myapp"
```

## 常见问题

### 1. 动态库加载失败
**症状**: `error while loading shared libraries`

**诊断**:
```bash
hdc shell "ldd /data/local/tmp/myapp"
```

**修复**:
- 推送缺失库到设备
- 使用静态链接
- 设置 LD_LIBRARY_PATH

### 2. 段错误 (SIGSEGV)
**症状**: 程序崩溃

**诊断**:
```bash
hdc shell "logcat -d | grep backtrace"
```

### 3. 权限错误
**症状**: `Permission denied`

**诊断**:
```bash
hdc shell "getenforce"
hdc shell "logcat -d | grep avc"
```

## 快速诊断脚本

```bash
./scripts/collect_logs.sh myapp
./scripts/analyze_crash.sh crash.txt
```

## 参考

- [references/crash-analysis.md](references/crash-analysis.md)
- [references/permission-issues.md](references/permission-issues.md)

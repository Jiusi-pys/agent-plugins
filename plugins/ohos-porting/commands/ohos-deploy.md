---
description: OHOS 部署测试。将编译产物推送到设备并运行测试。
allowed-tools: Bash, Read, Grep, Task
---

# OHOS Deploy: $ARGUMENTS

## 目标

将 `$ARGUMENTS` 部署到 OpenHarmony 设备并执行测试。

## 前置检查

### 设备连接
```bash
hdc list targets
```

### 设备信息
```bash
hdc shell "uname -a"
hdc shell "cat /etc/os-release 2>/dev/null || getprop ro.build.display.id"
```

## 部署流程

### Step 1: 确定部署文件

需要部署的文件：
- 可执行文件
- 动态库 (.so)
- 配置文件
- 测试数据

### Step 2: 推送文件

```bash
# 推送主程序
hdc file send ./build/$ARGUMENTS /data/local/tmp/

# 推送依赖库 (如有)
hdc file send ./build/lib*.so /data/local/tmp/

# 设置权限
hdc shell "chmod +x /data/local/tmp/$ARGUMENTS"
```

### Step 3: 配置运行环境

```bash
# 设置库路径 (如需)
hdc shell "export LD_LIBRARY_PATH=/data/local/tmp:\$LD_LIBRARY_PATH"
```

### Step 4: 运行测试

```bash
hdc shell "/data/local/tmp/$ARGUMENTS"
```

### Step 5: 错误处理

若运行失败，启动 runtime-debugger agent：

```
"分析运行时错误:
1. 收集 logcat 日志
2. 检查崩溃日志
3. 分析动态库依赖
4. 诊断根因"
```

### 日志收集命令

```bash
# 系统日志
hdc shell "logcat -d | tail -100"

# 崩溃日志
hdc shell "cat /data/log/faultlog/cppcrash-*" 2>/dev/null

# 库依赖检查
hdc shell "ldd /data/local/tmp/$ARGUMENTS"
```

### Step 6: 输出结果

```
╔════════════════════════════════════════════════════════╗
║         部署测试结果                                    ║
╠════════════════════════════════════════════════════════╣
║ 设备: {device_id}                                      ║
║ 程序: {program_name}                                   ║
║ 状态: {成功/失败}                                      ║
╚════════════════════════════════════════════════════════╝

[成功时]
退出码: 0
输出:
  {程序输出}

[失败时]
退出码: {code}
错误类型: {crash/permission/dependency/other}
错误信息:
  {error_message}

建议: {下一步操作}
```

## 清理

```bash
# 测试完成后清理
hdc shell "rm -f /data/local/tmp/$ARGUMENTS /data/local/tmp/lib*.so"
```

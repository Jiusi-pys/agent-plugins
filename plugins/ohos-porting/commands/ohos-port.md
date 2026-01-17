---
description: OHOS 移植可行性分析。分析 Linux 库/软件的移植难度和风险。
allowed-tools: Read, Grep, Glob, Bash, Task
---

# OHOS Porting Analysis: $ARGUMENTS

## 目标

分析 `$ARGUMENTS` 从 Linux 移植到 OpenHarmony 的可行性。

## 执行步骤

### Step 1: 源码定位
确定源码位置：
- 本地路径
- Git 仓库 URL
- 远程服务器路径

### Step 2: 启动诊断

启动 porting-analyzer agent 执行分析：

```
"对 $ARGUMENTS 执行完整移植可行性分析:
1. 扫描 Linux 特有 API 使用
2. 分析外部依赖
3. 评估移植难度 (A/B/C/D)
4. 列出风险项"
```

### Step 3: 输出报告

```
╔════════════════════════════════════════════════════════╗
║         OHOS 移植可行性报告                              ║
╠════════════════════════════════════════════════════════╣
║ 目标库: {name}                                          ║
║ 版本: {version}                                         ║
║ 评级: {A/B/C/D}                                         ║
║ 预估工时: {X} 天                                         ║
╚════════════════════════════════════════════════════════╝

【API 兼容性】
  兼容: XX 个
  需适配: XX 个
  不可移植: XX 个

【依赖库】
  ✓ {lib1} - OHOS 可用
  ✗ {lib2} - 需要移植
  ? {lib3} - 待验证

【风险项】
  ⚠ {风险1}
  ⚠ {风险2}

【建议】
  {根据评级给出建议}
```

### Step 4: 记录结果

调用 working-records skill 保存诊断结果。

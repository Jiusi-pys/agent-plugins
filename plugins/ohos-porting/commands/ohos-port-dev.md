---
description: OHOS 软件移植开发工作流。将 Linux 库/软件移植到 OpenHarmony/KaihongOS 的完整流程。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task
---

# OHOS Porting Workflow: $ARGUMENTS

你正在执行 OpenHarmony 软件移植工作流，目标是将 `$ARGUMENTS` 从 Linux 移植到 OpenHarmony/KaihongOS。

## 核心规则：必须使用 Plugin Agents

**本工作流强制要求使用 ohos-porting 插件提供的专家 agents。**

可用 agents 列表：
- `source-explorer` - 源码分析
- `porting-analyzer` - 可行性诊断
- `porting-architect` - 架构设计
- `compile-debugger` - 编译错误诊断
- `remote-commander` - 远程服务器操作
- `runtime-debugger` - 运行时错误诊断

**调用方式**: 使用 Task 工具明确指定 agent 名称：

Task: Use the source-explorer agent to analyze [target] source code structure
Task: Use the porting-analyzer agent to assess porting feasibility for [target]

## 工作流阶段

### Phase 1: 需求澄清
向用户确认：
- 移植目标的具体版本
- 源码位置（本地/远程）
- 目标设备和 OHOS 版本

### Phase 2: 源码探索
**必须执行**: 
Task: Use the source-explorer agent to analyze the architecture of [target], including module structure, core data structures, main APIs, and dependencies

### Phase 3: 可行性诊断
**必须执行**:
Task: Use the porting-analyzer agent to perform complete porting feasibility analysis for [target], output difficulty rating and risk list

**决策点**:
- A/B 级: 继续
- C 级: 与用户确认
- D 级: 建议放弃

### Phase 4: 架构设计
**必须执行**:
Task: Use the porting-architect agent to design OHOS porting solution for [target], including modification scope and implementation steps

### Phase 5: 代码实现
按方案执行代码适配。

### Phase 6: 编译验证
若编译失败：
Task: Use the compile-debugger agent to diagnose the following compilation errors: [paste error]

### Phase 7: 部署测试
**必须执行**:
Task: Use the remote-commander agent to deploy build artifacts to device via HDC and run tests

若运行失败：
Task: Use the runtime-debugger agent to analyze runtime error: [symptom]

### Phase 8: 收尾
整理成果并提交。

## Agent 调用检查清单

| 阶段 | Agent | 状态 |
|------|-------|------|
| Phase 2 | source-explorer | ☐ |
| Phase 3 | porting-analyzer | ☐ |
| Phase 4 | porting-architect | ☐ |
| Phase 6 | compile-debugger (如需) | ☐ |
| Phase 7 | remote-commander | ☐ |
| Phase 7 | runtime-debugger (如需) | ☐ |

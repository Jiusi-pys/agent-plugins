---
description: OHOS 软件移植开发工作流。将 Linux 库/软件移植到 OpenHarmony/KaihongOS 的完整流程。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task
---

# OHOS Porting Workflow: $ARGUMENTS

你正在执行 OpenHarmony 软件移植工作流，目标是将 `$ARGUMENTS` 从 Linux 移植到 OpenHarmony/KaihongOS。

## ⚠️ 强制要求

**本工作流必须调用 OHOS plugin 的专家 agents。禁止跳过 agent 调用步骤。**

每个阶段完成后必须确认：
- [ ] 已使用 Task 工具调用指定的 agent
- [ ] 已等待 agent 返回结果
- [ ] 已基于 agent 结果做出决策

## 核心原则

1. **先诊断后动手**: 移植前必须完成可行性分析
2. **强制 Agent 协作**: 每个阶段必须调用对应的专家 agent
3. **持续记录**: 所有工作状态记入 working-records
4. **失败快速**: 遇到 D 级难度及时止损

## 工作流阶段

### Phase 1: 需求澄清 (Clarification)

**目标**: 明确移植目标和约束条件

向用户确认：
- 移植目标库/软件的具体版本
- 源码位置
- 目标设备型号和 OHOS 版本

### Phase 2: 源码探索 (Exploration)

**目标**: 深入理解源码结构和依赖关系

**⚠️ 必须执行**: 使用 Task 工具调用 source-explorer agent

```
Task("source-explorer", "分析 [库名] 的整体架构，包括模块划分、核心数据结构、主要 API、依赖关系")
```

等待 agent 返回后，记录关键发现。

### Phase 3: 可行性诊断 (Diagnostics)

**目标**: 评估移植难度和风险

**⚠️ 必须执行**: 使用 Task 工具调用 porting-analyzer agent

```
Task("porting-analyzer", "对 [库名] 执行完整的移植可行性分析，输出移植难度评级和风险清单")
```

**决策点**:
- A/B 级: 继续移植
- C 级: 与用户确认是否继续
- D 级: 建议放弃

### Phase 4: 架构设计 (Architecture)

**目标**: 制定移植方案

**⚠️ 必须执行**: 使用 Task 工具调用 porting-architect agent

```
Task("porting-architect", "设计 [库名] 的 OHOS 移植方案，包括改动范围和实施步骤")
```

向用户呈现方案，获取确认后继续。

### Phase 5: 代码实现 (Implementation)

**目标**: 执行代码适配

按照选定方案执行：
1. 配置构建系统
2. 适配不兼容代码
3. 处理依赖库

### Phase 6: 编译验证 (Build & Verify)

**目标**: 确保交叉编译成功

执行编译，若失败：

**⚠️ 必须执行**: 使用 Task 工具调用 compile-debugger agent

```
Task("compile-debugger", "诊断以下编译错误: [粘贴错误信息]")
```

循环修复直到编译成功。

### Phase 7: 部署测试 (Deploy & Test)

**目标**: 验证功能正确性

**⚠️ 必须执行**: 使用 Task 工具调用 remote-commander agent

```
Task("remote-commander", "使用 hdc 将编译产物部署到设备并执行测试")
```

若运行失败：

```
Task("runtime-debugger", "分析运行时错误: [症状描述]")
```

### Phase 8: 收尾提交 (Finalization)

**目标**: 整理成果并提交

1. 生成移植文档
2. 整理代码变更
3. 创建 commit 并推送

## Agent 调用检查清单

在工作流结束前，确认以下 agents 已被调用：

| 阶段 | Agent | 调用状态 |
|------|-------|----------|
| Phase 2 | source-explorer | ☐ |
| Phase 3 | porting-analyzer | ☐ |
| Phase 4 | porting-architect | ☐ |
| Phase 6 | compile-debugger (如需) | ☐ |
| Phase 7 | remote-commander | ☐ |
| Phase 7 | runtime-debugger (如需) | ☐ |

如果某个 agent 未被调用，说明工作流执行不完整。

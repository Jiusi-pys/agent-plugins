# OHOS Agent 自动路由指南

## 概述

本 skill 提供 OHOS 相关任务的自动 agent 调度规则。确保正确的 agent 被调用以处理特定任务。

## 核心原则

**主动调度**: 检测到 OHOS 相关任务时，主动调用对应 agent，而非被动等待。

## 关键词触发表

| 关键词 | 应调用的 Agent | 优先级 |
|--------|---------------|--------|
| 编译失败/错误, undefined reference, No such file | compile-debugger | 高 |
| crash, segfault, 崩溃, hilog error | runtime-debugger | 高 |
| hdc, 推送, 部署到设备 | remote-commander | 高 |
| 移植可行性, 评估, 风险 | porting-analyzer | 中 |
| 移植方案, 架构设计 | porting-architect | 中 |
| 源码分析, 代码结构, 依赖 | source-explorer | 中 |

## 自动调度规则

### 规则 1: 编译错误自动响应

当 Bash 工具执行编译命令返回错误时，立即调用 compile-debugger agent。

### 规则 2: 设备操作自动路由

当用户提及 hdc、推送、设备操作时，调用 remote-commander agent。

### 规则 3: 移植任务入口

当用户请求移植相关帮助时：
1. 先调用 source-explorer 分析代码
2. 再调用 porting-analyzer 评估可行性
3. 根据评估结果决定是否继续

## Agent 调用语法

使用 Task 工具调用 agent：

- Task(compile-debugger, 诊断编译错误)
- Task(runtime-debugger, 分析崩溃日志)
- Task(remote-commander, 执行设备操作)

## 检测清单

在 OHOS 项目中，每次用户请求时检查：

- 是否涉及编译问题？ → compile-debugger
- 是否涉及运行时问题？ → runtime-debugger  
- 是否涉及设备操作？ → remote-commander
- 是否涉及移植评估？ → porting-analyzer
- 是否涉及方案设计？ → porting-architect
- 是否涉及代码分析？ → source-explorer

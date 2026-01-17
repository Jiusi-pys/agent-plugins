---
description: OHOS 软件移植开发工作流。将 Linux 库/软件移植到 OpenHarmony/KaihongOS 的完整流程。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task
---

# OHOS Porting Workflow: $ARGUMENTS

你正在执行 OpenHarmony 软件移植工作流，目标是将 `$ARGUMENTS` 从 Linux 移植到 OpenHarmony/KaihongOS。

## 核心原则

1. **先诊断后动手**: 移植前必须完成可行性分析
2. **分阶段推进**: 每个阶段有明确的输入输出
3. **持续记录**: 所有工作状态记入 working-records
4. **失败快速**: 遇到 D 级难度及时止损

## 工作流阶段

### Phase 1: 需求澄清 (Clarification)

**目标**: 明确移植目标和约束条件

向用户确认以下信息：
- 移植目标库/软件的具体版本
- 源码位置 (本地路径 / Git 仓库 / 远程服务器)
- 目标设备型号和 OHOS 版本
- 是否需要保持与 Linux 版本的 API 兼容
- 移植优先级 (功能完整 vs 快速可用)

### Phase 2: 源码探索 (Exploration)

**目标**: 深入理解源码结构和依赖关系

启动 2-3 个 source-explorer agent 并行分析：

```
Agent 1: "分析 [库名] 的整体架构，包括模块划分、核心数据结构、主要 API"
Agent 2: "扫描 [库名] 的依赖树，识别外部依赖和系统调用"
Agent 3: "检查 [库名] 的构建系统，分析编译选项和平台适配层"
```

等待 agents 返回后，阅读所有被标记为关键的文件。

### Phase 3: 可行性诊断 (Diagnostics)

**目标**: 评估移植难度和风险

启动 porting-analyzer agent 进行诊断：

```
"对 [库名] 执行完整的移植可行性分析，输出：
1. Linux 特有 API 使用统计
2. 系统调用依赖分析
3. 第三方库依赖清单
4. 移植难度评级 (A/B/C/D)
5. 风险项列表"
```

**决策点**:
- A/B 级: 继续移植
- C 级: 与用户确认是否继续
- D 级: 建议放弃，寻找替代方案

### Phase 4: 架构设计 (Architecture)

**目标**: 制定移植方案

启动 2 个 porting-architect agent 并行设计：

```
Agent 1 (最小改动方案): "设计 [库名] 的最小改动移植方案，最大化代码复用"
Agent 2 (重构方案): "设计 [库名] 的重构移植方案，优化 OHOS 适配性"
```

比较两种方案：
- 改动范围
- 维护成本
- 功能完整度
- 性能影响

向用户呈现方案对比，获取确认后继续。

### Phase 5: 代码实现 (Implementation)

**目标**: 执行代码适配

按照选定方案执行：

1. **配置构建系统**
   - 创建/修改 CMakeLists.txt 或 BUILD.gn
   - 配置 OHOS 工具链
   - 设置交叉编译参数

2. **适配不兼容代码**
   - 添加 `#ifdef __OHOS__` 条件编译
   - 替换 Linux 特有 API
   - 处理头文件路径

3. **处理依赖库**
   - 检查依赖是否已移植
   - 必要时递归移植依赖

每完成一个模块，执行增量编译验证。

### Phase 6: 编译验证 (Build & Verify)

**目标**: 确保交叉编译成功

1. 执行完整编译
2. 若失败，启动 compile-debugger agent 诊断：
   ```
   "分析编译错误，分类为：头文件缺失/API不兼容/链接错误/其他，给出修复方案"
   ```
3. 修复后重新编译
4. 循环直到编译成功

### Phase 7: 部署测试 (Deploy & Test)

**目标**: 验证功能正确性

1. 使用 hdc 推送到设备
2. 执行基础功能测试
3. 若失败，启动 runtime-debugger agent 诊断：
   ```
   "分析运行时错误，收集 logcat、crash dump，定位根因"
   ```
4. 修复后重新测试

### Phase 8: 收尾提交 (Finalization)

**目标**: 整理成果并提交

1. 生成移植文档
2. 整理代码变更
3. 创建 commit 并推送
4. 更新 working-records 状态为完成

## 状态管理

每个阶段开始前检查 working-records，若存在未完成任务则恢复上次进度。
每个阶段结束后更新 working-records。

## 异常处理

- 网络问题: 使用 remote-server-ssh-control 处理远程操作
- 设备离线: 检查 hdc 连接，必要时重连
- 编译超时: 检查资源占用，考虑分模块编译

## 输出格式

每个阶段完成后输出简报：

```
===== Phase N: {阶段名} 完成 =====
耗时: X 分钟
产出:
  - {产出物1}
  - {产出物2}
下一步: {Phase N+1 简述}
================================
```

# OHOS Porting Plugin

OpenHarmony/KaihongOS 软件移植工作流插件。将 Linux 库/软件移植到 OHOS 的完整解决方案。

## 功能特性

- **8 阶段工作流**: 需求澄清 → 源码探索 → 可行性诊断 → 架构设计 → 代码实现 → 编译验证 → 部署测试 → 收尾提交
- **7 个专用 Agent**: ohos-dispatcher, source-explorer, porting-analyzer, porting-architect, compile-debugger, runtime-debugger, remote-commander
- **14 个 Skill**: agent-routing, api-mapping, compile-error-analysis, git-cicd-workflow, hdc-kaihongOS, main-orchestrator, ohos-cpp-style, ohos-cross-compile, ohos-permission, porting-diagnostics, remote-server-ssh-control, runtime-debug, stub-interposition, working-records
- **自动错误诊断**: 编译失败时自动触发诊断
- **状态持久化**: 防止 context 丢失，支持任务恢复

## 安装

### 方式一: 从 marketplace 安装 (推荐)
```bash
# 在 Claude Code 中执行
/plugin marketplace add Jiusi-pys/agent-plugins
/plugin install ohos-porting@jiusi-agent-plugins
```

### 方式二: 本地安装
```bash
# 克隆到本地
git clone https://github.com/Jiusi-pys/agent-plugins.git

# 使用 --plugin-dir 加载
claude --plugin-dir ./agent-plugins/plugins/ohos-porting
```

`install.sh` 是旧版文件复制工具，不会注册 marketplace 或自动合并 hooks 配置；推荐使用上面的插件安装方式。Shell 脚本需要 Bash 环境（Windows 可使用 Git Bash 或 WSL）。

## 使用

### 启动移植工作流
```
/ohos-porting:ohos-port-dev libcurl
```

### 单独调用命令
```
/ohos-porting:ohos-port libcurl    # 移植分析
/ohos-porting:ohos-build libcurl   # 交叉编译
/ohos-porting:ohos-deploy libcurl  # 部署测试
```

### 调用专用 Agent
```
> 使用 source-explorer agent 分析 libcurl 的架构
> 使用 porting-analyzer agent 评估移植可行性
> 使用 compile-debugger agent 诊断编译错误
```

## 目录结构

```text
plugins/ohos-porting/
├── .claude-plugin/plugin.json
├── agents/                     # 7 个 Agent，包含 ohos-dispatcher
├── commands/                   # 4 个命令
├── skills/                     # 14 个 Skill
├── hooks/                      # hooks.json 与脚本
├── install.sh                  # 旧版文件复制工具
└── README.md
```

## 前置依赖

### 本地环境
- OHOS SDK (设置 $OHOS_SDK 环境变量)
- hdc 工具 (用于设备部署)
- SSH (用于远程服务器操作)

### 远程环境 (可选)
- OHOS 完整源码
- 编译工具链

## 工作流示例

```
┌─────────────────────────────────────────────────────┐
│ /ohos-porting:ohos-port-dev libcurl                 │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 1: 需求澄清                                    │
│   - 确认版本、源码位置、目标设备                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 2: 源码探索                                    │
│   - 启动 2-3 个 source-explorer agent 并行分析        │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 3: 可行性诊断                                  │
│   - porting-analyzer agent 评估难度 (A/B/C/D)        │
│   - D 级建议放弃                                     │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 4: 架构设计                                    │
│   - 2 个 porting-architect agent 设计方案            │
│   - 用户选择方案                                     │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 5: 代码实现                                    │
│   - 配置构建系统                                     │
│   - 适配不兼容代码                                   │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 6: 编译验证                                    │
│   - 交叉编译                                         │
│   - 失败时 compile-debugger agent 诊断               │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 7: 部署测试                                    │
│   - hdc 推送到设备                                   │
│   - 失败时 runtime-debugger agent 诊断               │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ Phase 8: 收尾提交                                    │
│   - 生成文档                                         │
│   - Git 提交                                         │
└─────────────────────────────────────────────────────┘
```

## 整合已有 skills

本插件已包含以下 skills，并在相应阶段使用：

- `hdc-kaihongOS` → 集成到 runtime-debugger 和 deploy 命令
- `ohos-cpp-style` → 集成到 porting-architect
- `ohos-cross-compile` → 集成到 compile-debugger
- `git-cicd-workflow` → 集成到 finalization 阶段

## 贡献

欢迎提交 Issue 和 PR。

## License

MIT

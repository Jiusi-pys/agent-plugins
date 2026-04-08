# OHOS Porting Plugin

OpenHarmony/KaihongOS 软件移植工作流插件。将 Linux 库/软件移植到 OHOS 的完整解决方案。

## 功能特性

- **8 阶段工作流**: 需求澄清 → 源码探索 → 可行性诊断 → 架构设计 → 代码实现 → 编译验证 → 部署测试 → 收尾提交
- **6 个专用 Agent**: source-explorer, porting-analyzer, porting-architect, compile-debugger, runtime-debugger, remote-commander
- **6 个 Skill**: porting-diagnostics, api-mapping, compile-error-analysis, runtime-debug, working-records, remote-server-ssh-control
- **自动错误诊断**: 编译失败时自动触发诊断
- **状态持久化**: 防止 context 丢失，支持任务恢复

## 安装

### 方式一: 从 marketplace 安装 (推荐)
```bash
# 在 Claude Code 中执行
/plugin install ohos-porting@your-marketplace
```

### 方式二: 本地安装
```bash
# 克隆到本地
git clone https://github.com/user/ohos-porting-plugin.git

# 使用 --plugin-dir 加载
claude --plugin-dir ./ohos-porting-plugin
```

### 方式三: 复制到用户目录
```bash
./install.sh
```

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

```
ohos-porting-plugin/
├── .claude-plugin/
│   └── plugin.json              # 插件清单
├── agents/
│   ├── source-explorer.md       # 源码探索
│   ├── porting-analyzer.md      # 可行性分析
│   ├── porting-architect.md     # 架构设计
│   ├── compile-debugger.md      # 编译调试
│   ├── runtime-debugger.md      # 运行时调试
│   └── remote-commander.md      # 远程服务器
├── commands/
│   ├── ohos-port-dev.md         # 主工作流
│   ├── ohos-port.md             # 移植分析
│   ├── ohos-build.md            # 编译命令
│   └── ohos-deploy.md           # 部署命令
├── skills/
│   ├── porting-diagnostics/     # 移植诊断
│   ├── api-mapping/             # API 映射
│   ├── compile-error-analysis/  # 编译错误分析
│   ├── runtime-debug/           # 运行时调试
│   ├── working-records/         # 工作记录
│   └── remote-server-ssh-control/ # 远程控制
├── hooks/
│   └── hooks.json               # 事件钩子
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

本插件设计为与你已有的 skills 配合使用：

- `hdc-kaihongOS` → 集成到 runtime-debugger 和 deploy 命令
- `ohos-cpp-style` → 集成到 porting-architect
- `ohos-cross-compile` → 集成到 compile-debugger
- `git-cicd-workflow` → 集成到 finalization 阶段

## 贡献

欢迎提交 Issue 和 PR。

## License

MIT

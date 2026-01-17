# 九思的 Claude Code 插件市场

Claude Code 插件集合，包含 OpenHarmony 移植工具、开发工作流等。

## 安装 Marketplace

```bash
# 在 Claude Code 中执行
/plugin marketplace add Jiusi-pys/agent-plugins
```

## 可用插件

### ohos-porting

OpenHarmony/KaihongOS 软件移植工作流插件。

**功能特性：**
- 8 阶段移植工作流
- 6 个专用 Agent
- 11 个 Skill（含已有的 git-cicd-workflow, hdc-kaihongOS, ohos-cpp-style, ohos-cross-compile 等）
- 自动错误诊断 Hook
- 工作状态持久化

**安装：**
```bash
/plugin install ohos-porting@jiusi-agent-plugins
```

**使用：**
```bash
/ohos-porting:ohos-port-dev libcurl
```

## License

MIT

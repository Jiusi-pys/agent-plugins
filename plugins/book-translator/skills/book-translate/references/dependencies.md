# EPUB 编排集成

唯一外部插件依赖为本仓库 `epub-editor` 的 `epub-edit`。Agentic Review 不是依赖，所有翻译审核指令都在 book-translator 内部。

当前适配的是现有 `0.1.x` CLI（可带 `+codex...` 构建后缀）。预检读取实际 manifest、skill 与脚本，检查帮助中存在 `--metadata`、`--inspect`、`--recount`。运行锁保存文件 SHA-256；中途升级依赖必须重新准备/审核作业，不能暗用新脚本。

实际调用为 `subprocess.run([python, script, source, output, '--metadata', patch, '--recount'])`，没有 shell 字符串拼接。只有退出 0、JSON issues 为空且输出存在才继续。之后通过 `--inspect` 和独立读回检查验证最终产物。

安装/更新必须从正确的 Git 分支获取，本仓库 Codex 来源为 `openai`：

```text
codex plugin marketplace add Jiusi-pys/agent-plugins --ref openai
codex plugin add epub-editor@jiusi-agent-plugins
codex plugin add book-translator@jiusi-agent-plugins
```

这些远程命令只适用于本次变更已经发布到该分支之后。未推送时，注册实际开发工作区作为本地来源再安装，或用隔离的 Codex 配置测试。先用 `codex plugin marketplace list` 核实来源，不能把仍指向旧 Git 快照的市场当成本地源码。

在新聊天中确认两个技能均可用。插件缓存之间可能相隔多个目录；只使用会话 catalog 指出的已启用技能路径。宿主不支持本地 Python 或 sub-agent 时，本工作流不能以相同流程执行。

没有已验证的任意插件间自动安装字段。`agents/openai.yaml` 的 `dependencies.tools` 用于 MCP，不应把技能插件填进去。`contracts/epub-editor.json` 是本插件的兼容性说明，**不是宿主识别的依赖声明**。

依据（2026-09-27 核实）：[插件打包](https://developers.openai.com/plugins/build/plugins)、[技能与 MCP](https://developers.openai.com/plugins/build/skills)、[sub-agent](https://developers.openai.com/codex/subagents)。

# OHOS Porting Plugin Marketplace

Claude Code plugin for OpenHarmony/KaihongOS software porting workflow.

## Installation

```bash
# Add this marketplace
/plugin marketplace add Jiusi-pys/agent-plugins

# Install the plugin
/plugin install ohos-porting@ohos-porting-marketplace
```

## Plugin: ohos-porting

**Purpose**: Complete software porting workflow from Linux to OpenHarmony/KaihongOS.

### Features

- **8-phase porting workflow**: From requirements to final submission
- **6 specialized agents**: source-explorer, porting-analyzer, porting-architect, compile-debugger, runtime-debugger, remote-commander
- **11+ skills**: Including cross-compilation, API mapping, error analysis, device control
- **Auto error diagnosis**: Hooks detect and diagnose compilation/runtime errors
- **Working state persistence**: Track progress across sessions

### Commands

| Command | Description |
|---------|-------------|
| `/ohos-port <library>` | Analyze porting feasibility for a library |
| `/ohos-port-dev <library>` | Full porting workflow with state tracking |
| `/ohos-build` | Build OHOS project with error diagnosis |
| `/ohos-deploy` | Deploy to OHOS device |

### Example Usage

```bash
# Analyze libcurl porting feasibility
/ohos-port libcurl

# Start full porting workflow
/ohos-port-dev libcurl
```

### Directory Structure

```
plugins/ohos-porting/
├── .claude-plugin/
│   └── plugin.json
├── agents/               # 6 specialized agents
├── commands/             # 4 CLI commands
├── hooks/                # Event hooks for error detection
├── skills/               # 11+ reusable skills
└── install.sh
```

## License

MIT

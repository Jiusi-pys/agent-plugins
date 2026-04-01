# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code plugin marketplace containing the **ohos-porting** plugin - a comprehensive OpenHarmony/KaihongOS software porting workflow with 8 phases, 6 agents, and multiple skills.

## Repository Structure

```
agent-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace manifest
├── .github/workflows/
│   └── validate-plugins.yml      # Plugin validation
├── plugins/
│   └── ohos-porting/             # OpenHarmony porting plugin
│       ├── .claude-plugin/
│       │   └── plugin.json       # Plugin manifest
│       ├── agents/               # Agent definitions (*.md with YAML frontmatter)
│       ├── commands/             # CLI commands (*.md with YAML frontmatter)
│       ├── hooks/                # Event hooks (hooks.json + scripts/)
│       ├── skills/               # Reusable skills
│       │   └── {skill-name}/
│       │       ├── SKILL.md
│       │       ├── references/
│       │       └── scripts/
│       └── install.sh
├── README.md
└── CLAUDE.md
```

## File Format Conventions

### Agent Definitions (`agents/*.md`)
```yaml
---
name: agent-name
description: What this agent does
tools: Read, Grep, Glob, Bash  # or list: ["Read", "Grep"]
model: sonnet                  # optional
permissionMode: default        # or "plan"
skills: skill1, skill2         # skills this agent can use
---
```

### Command Definitions (`commands/*.md`)
```yaml
---
description: What this command does
allowed-tools: Read, Grep, Bash, Task  # tools available to the command
---
```
Command content uses `$ARGUMENTS` to capture user input.

### Hooks Configuration (`hooks/hooks.json`)
```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Bash", "hooks": [...]}],
    "PostToolUse": [{"matcher": "Bash", "hooks": [...]}],
    "Stop": [{"matcher": "", "hooks": [...]}]
  }
}
```
Script paths use `${CLAUDE_PLUGIN_ROOT}` variable for portability.

## Development Commands

```bash
# Validate marketplace.json
jq . .claude-plugin/marketplace.json

# Validate plugin structure
cd plugins/ohos-porting && claude plugin validate . 2>/dev/null || echo "Validation requires claude CLI"
```

## OHOS Porting Plugin Architecture

**8-Phase Workflow**:
1. Requirements clarification
2. Source code exploration (`source-explorer` agent)
3. Feasibility diagnosis (`porting-analyzer` agent)
4. Architecture design (`porting-architect` agent)
5. Code implementation
6. Compilation verification (`compile-debugger` agent)
7. Deployment testing (`remote-commander` + `runtime-debugger` agents)
8. Finalization and submission

**Specialized Agents**:
| Agent | Purpose |
|-------|---------|
| `source-explorer` | Analyzes target architecture and dependencies |
| `porting-analyzer` | Assesses feasibility (A/B/C/D rating) |
| `porting-architect` | Designs porting strategy |
| `compile-debugger` | Diagnoses compilation errors |
| `runtime-debugger` | Debugs runtime failures |
| `remote-commander` | Manages device deployment via hdc/SSH |

**Key Skills**:
- `hdc-kaihongOS` - Device control via HDC
- `ohos-cross-compile` - Cross-compilation toolchain
- `ohos-cpp-style` - OHOS C++ coding standards
- `porting-diagnostics` - Feasibility analysis
- `api-mapping` - Linux-to-OHOS API mapping
- `compile-error-analysis` - Build failure diagnosis
- `runtime-debug` - Runtime debugging

## Marketplace Updates

When updating the plugin:
1. Update `version` in `.claude-plugin/plugin.json`
2. Update `version` in root `.claude-plugin/marketplace.json` (keep in sync)
3. Push to main branch - GitHub Actions validates automatically

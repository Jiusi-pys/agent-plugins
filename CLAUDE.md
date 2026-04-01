# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code plugin marketplace containing two plugins:

1. **ohos-porting** — OpenHarmony/KaihongOS software porting workflow with 8 phases, 7 agents, and 14 skills
2. **auto-clean** — Privacy cleanup tool that clears Claude Code tracking data and telemetry

## Repository Structure

```
agent-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace manifest (lists all plugins)
├── .github/workflows/
│   └── validate-plugins.yml      # Plugin validation (JSON + structure checks)
├── plugins/
│   ├── ohos-porting/             # OpenHarmony porting plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json       # Plugin manifest
│   │   ├── agents/               # Agent definitions (*.md with YAML frontmatter)
│   │   ├── commands/             # CLI command definitions (*.md with YAML frontmatter)
│   │   ├── hooks/                # Event hooks (hooks.json + scripts/)
│   │   ├── skills/               # Reusable skills
│   │   └── install.sh            # Copies plugin files to ~/.claude/ or ./.claude/
│   └── auto-clean/               # Privacy cleanup plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── commands/             # /init, /clean-history
│       ├── hooks/                # Auto-cleanup on Stop event
│       ├── scripts/              # Shell scripts for cleaning
│       └── README.md
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

### Skills (`skills/*/SKILL.md`)
```yaml
---
name: skill-name
description: What this skill provides
---
```

### Hooks Configuration (`hooks/hooks.json`)
```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Bash", "hooks": [...]}],
    "PostToolUse": [{"matcher": "Bash", "hooks": [...]}],
    "Stop": [{"matcher": "", "hooks": [...]}],
    "SessionEnd": [{"matcher": "", "hooks": [...]}]
  }
}
```
Script paths use `${CLAUDE_PLUGIN_ROOT}` variable for portability.

**Hook Lifecycle**:
- `PreToolUse` / `PostToolUse`: Tool execution hooks
- `Stop`: Triggered after Claude completes a response turn
- `SessionEnd`: Triggered when the session actually ends

## Development Commands

```bash
# Validate marketplace.json (metadata.version, not top-level version)
jq . .claude-plugin/marketplace.json

# Validate plugin structure (requires claude CLI)
cd plugins/ohos-porting && claude plugin validate . 2>/dev/null || echo "Validation requires claude CLI"

# Install plugins locally for testing
./plugins/ohos-porting/install.sh --user    # copies to ~/.claude/
./plugins/ohos-porting/install.sh --project # copies to ./.claude/
./plugins/auto-clean/install.sh --user
```

There are no traditional unit tests. Validation is performed by the GitHub Actions workflow (`validate-plugins.yml`), which checks that JSON files are valid and expected directories exist.

## Plugin: ohos-porting

### 8-Phase Workflow
1. Requirements clarification
2. Source code exploration (`source-explorer` agent)
3. Feasibility diagnosis (`porting-analyzer` agent)
4. Architecture design (`porting-architect` agent)
5. Code implementation
6. Compilation verification (`compile-debugger` agent)
7. Deployment testing (`remote-commander` + `runtime-debugger` agents)
8. Finalization and submission

### Specialized Agents
| Agent | Purpose |
|-------|---------|
| `ohos-dispatcher` | Routes user requests to the appropriate specialist agent |
| `source-explorer` | Analyzes target architecture and dependencies |
| `porting-analyzer` | Assesses feasibility (A/B/C/D rating) |
| `porting-architect` | Designs porting strategy |
| `compile-debugger` | Diagnoses compilation errors |
| `runtime-debugger` | Debugs runtime failures |
| `remote-commander` | Manages device deployment via hdc/SSH |

### CLI Commands
| Command | Description |
|---------|-------------|
| `/ohos-port <library>` | Analyze porting feasibility for a library |
| `/ohos-port-dev <library>` | Full 8-phase porting workflow with state tracking |
| `/ohos-build` | Build OHOS project with error diagnosis |
| `/ohos-deploy` | Deploy to OHOS device |

### Skills
| Skill | Purpose |
|-------|---------|
| `agent-routing` | Dispatcher logic for agent selection |
| `api-mapping` | Linux-to-OHOS API mapping |
| `compile-error-analysis` | Build failure diagnosis |
| `git-cicd-workflow` | CI/CD templates for OHOS projects |
| `hdc-kaihongOS` | Device control via HDC |
| `main-orchestrator` | Workflow orchestration utilities |
| `ohos-cpp-style` | OHOS C++ coding standards |
| `ohos-cross-compile` | Cross-compilation toolchain |
| `ohos-permission` | OHOS permission configuration |
| `porting-diagnostics` | Feasibility analysis methodology |
| `remote-server-ssh-control` | SSH-based remote operations |
| `runtime-debug` | Runtime debugging techniques |
| `stub-interposition` | Stub generation for missing APIs |
| `working-records` | Persistent task state across sessions |

### State Persistence (`working-records`)
The `working-records` skill persists multi-session porting progress in `~/.claude/working-records/` as YAML files. Agents read these records at phase start and write updates at phase completion. The `on_session_end.sh` hook ensures state is flushed when a session ends.

## Plugin: auto-clean

A privacy-focused utility plugin that clears Claude Code tracking data.

### Commands
| Command | Description |
|---------|-------------|
| `/init` | Full reset (Level 5), backs up config, restores plugins, sets CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC |
| `/clean-history` | Clear conversation history and session data (Level 3) |

### Cleanup Levels
- **Level 1** — Reset device identifiers (`userID`, `anonymousId`, etc.)
- **Level 2** — Clear telemetry and analytics data
- **Level 3** — Clear sessions, history, `session-env`, and `session-history`
- **Level 4** — Clear OAuth account linkage and keychain credentials
- **Level 5** — Full reset of `~/.claude/` and `~/.claude.json`

### Hooks
Hooks run on the `Stop` event (after Claude completes a response):
- **`clean.sh`** — Runs Level 1 + Level 2
- **`clear.sh`** — Runs Level 2

## Marketplace Updates

When updating any plugin:
1. Update `version` in the plugin's `.claude-plugin/plugin.json`
2. Update `metadata.version` in root `.claude-plugin/marketplace.json` (keep in sync)
3. Push to main branch — GitHub Actions validates automatically

## Claude Code Privacy Settings

For users concerned about data privacy, Claude Code supports official environment variables (set via `settings.json`):

- `DISABLE_TELEMETRY` — Disable telemetry collection
- `DISABLE_ERROR_REPORTING` — Disable error reporting
- `DISABLE_FEEDBACK_COMMAND` — Disable feedback command
- `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` — Disable feedback surveys
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` — Disable non-essential network traffic

See [Claude Code Data Usage documentation](https://code.claude.com/docs/en/data-usage) for details.

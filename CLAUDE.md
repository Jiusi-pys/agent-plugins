# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code plugin marketplace containing two plugins:

1. **ohos-porting** — OpenHarmony/KaihongOS software porting workflow with 8 phases, 7 agents, and 14 skills
2. **multi-review** — Evidence-gated code review with 9 agents, 1 command, 1 skill, deterministic preflight and a dynamic workflow

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
│   └── multi-review/             # Evidence-gated review plugin
│       ├── .claude-plugin/plugin.json
│       ├── agents/               # Router, 6 sensors, verifier, judge
│       ├── commands/             # multi-review command
│       ├── skills/               # review-contract
│       ├── scripts/              # Deterministic preflight
│       ├── templates/            # Intent and report templates
│       ├── workflows/            # Dynamic review workflow
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
claude plugin validate .
claude plugin validate ./plugins/ohos-porting
claude plugin validate ./plugins/multi-review
claude --plugin-dir ./plugins/ohos-porting
```

CI uses Claude Code 2.1.270 to validate the marketplace and each plugin, including skill frontmatter. Validation failures must fail CI. These checks do not test runtime behavior.

Use `/plugin marketplace add Jiusi-pys/agent-plugins` and install with `@jiusi-agent-plugins`. The legacy `install.sh` copies files but does not register the marketplace or merge hook settings.

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
| `/ohos-porting:ohos-port <library>` | Analyze porting feasibility for a library |
| `/ohos-porting:ohos-port-dev <library>` | Full 8-phase porting workflow with state tracking |
| `/ohos-porting:ohos-build` | Build OHOS project with error diagnosis |
| `/ohos-porting:ohos-deploy` | Deploy to OHOS device |

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

## Plugin: multi-review

The `/multi-review:multi-review` command launches a Workflow pipeline: preflight, risk routing, parallel read-only sensors, independent verification, and a unified judge. It does not edit code or merge changes. See [the plugin guide](plugins/multi-review/README.md) for target selection, requirements and verdicts.

## Marketplace Updates

1. Keep the stable marketplace name `jiusi-agent-plugins` and repository-relative `./plugins/<name>` sources.
2. Maintain plugin versions only in each `.claude-plugin/plugin.json`; bump the affected plugin for every release. Do not duplicate versions in marketplace entries.
3. Increment the catalog's top-level `version` independently for marketplace changes.
4. Preserve `renames` history. `auto-clean` maps to `null` because it was removed; automatic migration requires Claude Code 2.1.193+.
5. Update installation examples and component counts when contents change.
6. Run all validation commands above before pushing. GitHub Actions repeats them on pushes and pull requests to main.

Follow the [official marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces).

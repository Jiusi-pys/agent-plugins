# OHOS Porting Codex Conversion Design

## Goal

Convert `plugins/ohos-porting` from a Claude Code plugin into a Codex-oriented skill bundle on the `openai` branch.

The converted result should preserve only the capabilities the user still wants:

- `ohos-hdc`
- `ohos-cpp-style`
- `ohos-permission`

Everything else in the original Claude plugin is out of scope for this branch.

## Current State

`plugins/ohos-porting` currently mixes two layers:

1. Core OHOS knowledge and reusable resources:
   - HDC device control scripts and references
   - OHOS C/C++ style references and templates
   - OHOS permission scripts and templates
2. Claude-specific plugin shell:
   - `.claude-plugin/plugin.json`
   - `agents/`
   - `commands/`
   - `hooks/`
   - skills whose main job is orchestrating Claude agents or commands

For Codex, the second layer does not carry over cleanly. The branch should keep the reusable OHOS knowledge and remove the Claude-only shell.

## Target Outcome

The converted `plugins/ohos-porting` directory should expose three Codex-usable skills:

### 1. `ohos-hdc`

Purpose:
- device discovery
- shell execution on OHOS devices
- file transfer
- log collection
- platform-specific HDC wrapper guidance

Source:
- existing `skills/hdc-kaihongOS/`

Conversion:
- rename the skill directory to `skills/ohos-hdc/`
- keep existing `scripts/` and `references/`
- rewrite `SKILL.md` for Codex usage
- add `agents/openai.yaml`

### 2. `ohos-cpp-style`

Purpose:
- OHOS C/C++ conventions
- file and naming conventions
- GN and BUILD.gn guidance
- threading, serialization, and permission-related reference pointers

Source:
- existing `skills/ohos-cpp-style/`

Conversion:
- keep the directory name
- keep templates and references
- rewrite `SKILL.md` for Codex usage
- add `agents/openai.yaml`

### 3. `ohos-permission`

Purpose:
- OHOS permission configuration
- DSoftBus-related permission setup
- deployment and verification workflow

Source:
- existing `skills/ohos-permission/`

Conversion:
- keep the directory name
- keep `scripts/` and `templates/`
- rewrite `SKILL.md` for Codex usage
- add `agents/openai.yaml`

## Explicitly Removed Scope

The conversion will remove the following because they are Claude-specific or outside the retained capability set:

- `.claude-plugin/`
- `agents/`
- `commands/`
- `hooks/`
- `install.sh`
- `skills/agent-routing/`
- `skills/api-mapping/`
- `skills/compile-error-analysis/`
- `skills/git-cicd-workflow/`
- `skills/main-orchestrator/`
- `skills/ohos-cross-compile/`
- `skills/porting-diagnostics/`
- `skills/remote-server-ssh-control/`
- `skills/runtime-debug/`
- `skills/stub-interposition/`
- `skills/working-records/`

## Skill Design Rules

Each retained skill must follow Codex skill conventions:

- `SKILL.md` frontmatter contains only `name` and `description`
- descriptions must clearly state what the skill does and when it should trigger
- the body should be procedural and Codex-oriented, not Claude-agent-oriented
- Claude-only concepts like `Task`, plugin commands, or automatic hook behavior must be removed
- each retained skill gets `agents/openai.yaml`

## Repository Changes

The implementation should make these structural changes:

1. Rename `plugins/ohos-porting/skills/hdc-kaihongOS/` to `plugins/ohos-porting/skills/ohos-hdc/`
2. Rewrite the three retained `SKILL.md` files
3. Add `agents/openai.yaml` for each retained skill
4. Remove the Claude-only directories and files listed above
5. Rewrite `plugins/ohos-porting/README.md` so it documents the Codex-facing skill bundle instead of Claude plugin commands

## Validation

Validation for this conversion should focus on skill correctness, not Claude plugin validation:

- run the skill validator on each retained skill
- check that renamed paths referenced inside each skill still match the filesystem
- verify `agents/openai.yaml` exists and is structurally valid

## Non-Goals

The conversion does not need to:

- preserve one-to-one parity with Claude commands
- recreate hooks in Codex
- recreate Claude agents as separate Codex artifacts
- keep deprecated OHOS analysis or workflow skills

## Success Criteria

The conversion is complete when:

1. `plugins/ohos-porting` contains only the three retained OHOS skills plus supporting docs/resources
2. each retained skill is readable and triggerable by Codex conventions
3. each retained skill has `agents/openai.yaml`
4. no remaining retained file instructs Codex to use Claude-only concepts such as plugin commands, hooks, or `Task` agents

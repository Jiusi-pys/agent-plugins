# OpenAI Branch Plugins Realignment Design

Date: 2026-04-08

## Goal

Realign the `openai` branch from a root-level Codex skills repository into a Codex plugins repository.

The branch should package reusable Codex capabilities as repo-local plugins under `plugins/`, with:

- a fully converted `plugins/ohos-porting` plugin that carries forward the reusable capability set from `main`
- a separate `plugins/translate-web-to-chinese` plugin for the existing translation workflow
- repo-level Codex marketplace metadata and repo-level Codex hooks

This design supersedes the earlier `openai`-branch directions that moved between:

- converted plugin container preservation
- root-level skills normalization

The new steady state is a plugin-first repository.

## External Constraints

This design follows Codex platform structure rather than the old Claude marketplace shape:

- Skills define reusable workflows and can be packaged inside plugins.
- Plugins are the installable/distributable unit and use `.codex-plugin/plugin.json`.
- Repo-local plugin catalogs use `/.agents/plugins/marketplace.json`.
- Repo-local hooks use `/.codex/hooks.json`.

References:

- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/plugins
- https://developers.openai.com/codex/plugins/build
- https://developers.openai.com/codex/hooks

## User-Approved Scope

### In scope

- Convert `main` branch `plugins/ohos-porting` into a Codex-usable plugin.
- Migrate the reusable `ohos-porting` capability set from `main` into Codex skills.
- Do not recreate Claude `commands/` or Claude `agents/`.
- Replace the current `openai` branch OHOS content with the converted plugin content.
- Remove WSL-specific control flow and make `ohos-porting` Linux-only.
- Standardize OHOS build/tooling guidance around:
  - `command-line-tools`
  - `openharmony_prebuilts`
- Package the existing `translate-web-to-chinese` skill as its own plugin.
- Add repo-level Codex marketplace metadata.
- Add repo-level Codex hooks for OHOS-aware guidance and guardrails.
- Rewrite repository docs so the branch reads as a Codex plugins repository.

### Out of scope

- Recreating Claude `/commands`
- Recreating Claude `Task(...)`-style agent dispatch
- Preserving `.claude-plugin` manifests
- Preserving Windows, Git Bash/MSYS, macOS, or WSL control paths inside `ohos-porting`
- Supporting multiple OHOS host environment strategies in parallel

## Current State

On the `openai` branch, the repository currently behaves like a root-level skills repository:

- OHOS capabilities live directly under `skills/`
- `translate-web-to-chinese` also lives directly under `skills/`
- root docs describe the repository as a Codex skills repository
- there is no repo-local Codex marketplace scaffold
- there is no repo-local Codex hooks scaffold

On the `main` branch, `plugins/ohos-porting` still contains the larger OHOS capability set, but it is wrapped in Claude-specific structure:

- `.claude-plugin/`
- `commands/`
- `agents/`
- Claude-oriented hook payloads and messaging

## Desired End State

After the redesign, the `openai` branch should read like a Codex plugins repository with this high-level structure:

```text
.agents/plugins/marketplace.json
.codex/hooks.json
.codex/hooks/
plugins/
  ohos-porting/
    .codex-plugin/plugin.json
    README.md
    skills/
      ohos-porting-workflow/
      ohos-hdc/
      ohos-cpp-style/
      ohos-permission/
      ohos-cross-compile/
      api-mapping/
      compile-error-analysis/
      porting-diagnostics/
      runtime-debug/
      stub-interposition/
      working-records/
      ohos-remote-build/
      git-cicd-workflow/
  translate-web-to-chinese/
    .codex-plugin/plugin.json
    skills/
      translate-web-to-chinese/
```

Root-level `skills/ohos-*` directories should no longer be the distribution surface for the repo.

## Plugin Architecture

### 1. `plugins/ohos-porting`

This becomes the main converted Codex plugin for OpenHarmony and KaihongOS porting work.

Its role is to package the reusable workflow knowledge and helper assets from `main` in a Codex-native shape:

- plugin manifest in `.codex-plugin/plugin.json`
- Codex skills under `skills/`
- Linux-only helper scripts and references
- repo-level hooks, not plugin-level hooks

This plugin is the replacement for the current root-level OHOS skills on the `openai` branch.

### 2. `plugins/translate-web-to-chinese`

This is the plugin wrapper for the already-converted translation workflow currently living under root `skills/translate-web-to-chinese`.

The skill content remains Codex-oriented. The redesign only adds plugin packaging and moves it under `plugins/`.

## `ohos-porting` Capability Inventory

The converted `ohos-porting` plugin should keep the reusable capability set from `main`, but only in Codex skill form.

### Skills to keep

- `ohos-porting-workflow`
  - source: `main-orchestrator`
  - purpose: top-level migration workflow, assessment, preparation, adaptation, validation

- `ohos-hdc`
  - source: `hdc-kaihongOS`
  - purpose: Linux-only device control, deployment, file transfer, logs, and shell execution over `hdc_std` or `hdc`

- `ohos-cpp-style`
  - source: existing `openai` branch Codex version plus `main` references/assets
  - purpose: C/C++ style, naming, `BUILD.gn`, threading, serialization, permission-related native patterns

- `ohos-permission`
  - source: existing `openai` branch Codex version plus `main` references/assets
  - purpose: DSoftBus permission configuration, deployment, verification, and token notes

- `ohos-cross-compile`
  - source: `main`
  - purpose: OpenHarmony cross-compilation workflow and environment setup

- `api-mapping`
  - source: `main`
  - purpose: Linux API to OHOS API mapping and replacement guidance

- `compile-error-analysis`
  - source: `main`
  - purpose: compile failure diagnosis and structured repair workflow

- `porting-diagnostics`
  - source: `main`
  - purpose: feasibility scanning, dependency/risk analysis, portability assessment

- `runtime-debug`
  - source: `main`
  - purpose: crash, permission, shared-library, and runtime failure diagnosis on OHOS devices

- `stub-interposition`
  - source: `main`
  - purpose: `LD_PRELOAD`-based runtime instrumentation and stubbing

- `working-records`
  - source: `main`
  - purpose: persistent work tracking and handoff structure for long-running porting tasks

- `ohos-remote-build`
  - source: `remote-server-ssh-control`
  - purpose: remote OpenHarmony image compilation guidance, recast as a Codex skill

- `git-cicd-workflow`
  - source: `main`
  - purpose: structured Git delivery guidance retained as part of the plugin’s overall workflow support

### Capabilities not kept as skills

- `agent-routing`
  - reason: in Codex, this becomes repo-level hook behavior rather than a standalone user-facing skill

- Claude `agents/`
  - reason: out of scope for this migration

- Claude `commands/`
  - reason: out of scope for this migration

## Overwrite and Preservation Rules

The redesign should not blindly replace `openai` branch OHOS content with `main`.

### Rule 1: Use `main` as the capability/resource source

`main` remains the source of truth for the full `ohos-porting` capability inventory and for helper assets that never made it to `openai`.

### Rule 2: Preserve Codex-native rewrites already done on `openai`

Where the `openai` branch already contains a better Codex-native rewrite, keep that rewrite as the documentation baseline instead of reverting to Claude-oriented text.

This applies in particular to:

- `ohos-hdc` naming and Codex-oriented `SKILL.md`
- `ohos-cpp-style` Codex-oriented `SKILL.md`
- `ohos-permission` Codex-oriented `SKILL.md`
- `agents/openai.yaml` metadata already created for those skills

### Rule 3: Backfill missing resources from `main`

If `main` contains helper scripts, references, templates, or examples that are still relevant and missing on `openai`, copy them into the plugin.

This is especially important for `ohos-hdc`, where `main` still has Linux-side scripts that are missing on `openai`.

### Rule 4: Rename Claude-oriented identifiers where needed

The plugin should avoid Claude-era names when a Codex-facing name is clearer:

- `hdc-kaihongOS` -> `ohos-hdc`
- `main-orchestrator` -> `ohos-porting-workflow`
- `remote-server-ssh-control` -> `ohos-remote-build`

## Linux-Only Environment Standardization

The entire converted `ohos-porting` plugin should assume a Linux host environment.

### Required host assumptions

- shell execution is Linux shell first
- HDC commands are run directly via `hdc_std` or `hdc`
- no PowerShell bridge
- no WSL path translation
- no Git Bash/MSYS path handling
- no macOS-specific path handling

### Required build environment assumptions

All OHOS compilation guidance should standardize around:

- `command-line-tools`
- `openharmony_prebuilts`

The skills should not present multiple primary toolchain strategies in parallel.

### Consequences for specific skills

#### `ohos-hdc`

- remove WSL, Windows, and macOS guidance
- remove WSL wrappers and PowerShell execution logic
- rewrite usage examples around Linux direct shell execution
- prefer `hdc_std`, then `hdc`

#### `ohos-cross-compile`

- rewrite toolchain guidance to center on `command-line-tools` and `openharmony_prebuilts`
- remove WSL transfer/deployment examples
- avoid treating GCC Linaro as the default primary path

#### `runtime-debug`

- standardize examples on Linux direct `hdc shell`

#### `ohos-remote-build`

- describe remote build as Linux-to-Linux remote build support
- remove any implication that remote build is a workaround for mixed-platform host issues

## Hooks Design

Codex hooks should be repo-level rather than plugin-local.

### Repo files

- `/.codex/hooks.json`
- `/.codex/hooks/ohos_pre_tool_use.sh`
- `/.codex/hooks/ohos_post_tool_use.sh`

### PreToolUse behavior

For OHOS-relevant shell commands, provide Codex with OHOS-aware guidance before execution:

- remind Codex to use `plugins/ohos-porting` skills when relevant
- remind Codex to prefer `/data/local/tmp` for temporary deployment artifacts
- warn against modifying `/system` or `/vendor` without explicit authorization
- block clearly dangerous device mutations when the user has not authorized them

### PostToolUse behavior

For failed build/device commands, add context that points Codex toward the right migrated skill:

- compile and link errors -> `compile-error-analysis` or `ohos-cpp-style`
- permission failures -> `ohos-permission`
- deployment/device/log issues -> `ohos-hdc` or `runtime-debug`

### Explicit non-goal

Hooks should not recreate Claude agent dispatch or Claude command orchestration.

## Documentation Changes

### Root README

Rewrite `README.md` so the repository describes:

- the `main` vs `openai` branch split
- the `openai` branch as a Codex plugins repository
- the available plugins under `plugins/`
- repo-local marketplace and hook support

### `plugins/ohos-porting/README.md`

Rewrite as a Codex plugin README:

- no Claude installation instructions
- no `/plugin install` examples
- no Claude command syntax
- no Claude agent invocation syntax
- clear Linux-only host expectations
- clear OHOS environment assumptions around `command-line-tools` and `openharmony_prebuilts`

### `plugins/translate-web-to-chinese/README.md`

Optional for this pass. If created, it should describe the plugin as a Codex plugin and point to the packaged skill.

## Marketplace Design

Add a repo-local marketplace file at:

- `/.agents/plugins/marketplace.json`

It should list at least:

- `ohos-porting`
- `translate-web-to-chinese`

Each entry should use repo-local plugin source paths:

- `./plugins/ohos-porting`
- `./plugins/translate-web-to-chinese`

## Validation

The redesign is complete when all of the following are true:

1. `plugins/ohos-porting/.codex-plugin/plugin.json` exists and parses as JSON.
2. `plugins/translate-web-to-chinese/.codex-plugin/plugin.json` exists and parses as JSON.
3. `/.agents/plugins/marketplace.json` exists and parses as JSON.
4. `/.codex/hooks.json` exists and parses as JSON.
5. Every retained skill directory under both plugins passes the Codex skill validator.
6. All retained `.sh` files pass `bash -n`.
7. Repository searches no longer show stale WSL, PowerShell, Git Bash/MSYS, or macOS guidance inside `plugins/ohos-porting`.
8. Repository searches no longer show stale Claude plugin shell content or Claude invocation language in the shipped plugin docs and skills.
9. OHOS build guidance consistently points to `command-line-tools` and `openharmony_prebuilts`.
10. Root-level `skills/` directories are no longer the repository’s distribution surface.

## Risks

### Risk: Codex content regresses to Claude-era wording

Mitigation:

- keep existing `openai` Codex rewrites as the baseline where they are already stronger
- use `main` primarily for capability coverage and missing assets

### Risk: Linux-only conversion is incomplete

Mitigation:

- remove WSL-specific scripts from shipped plugin paths
- run repository searches for:
  - `WSL`
  - `powershell`
  - `/mnt/c/`
  - `MINGW`
  - `MSYS`
  - `CYGWIN`

### Risk: plugin-repo identity remains ambiguous

Mitigation:

- move distribution entry points under `plugins/`
- add repo marketplace metadata
- rewrite root docs to describe the plugin-first structure

### Risk: generic workflow skills become too coupled to old Claude flow

Mitigation:

- rewrite workflow skills around Codex skill usage and hook-assisted guidance
- remove any reference to Claude commands, Claude agents, or `Task(...)`

## Success Criteria

The redesign succeeds when:

1. The `openai` branch reads as a Codex plugins repository.
2. `plugins/ohos-porting` exposes the reusable capability set from `main` in Codex skill form.
3. The converted `ohos-porting` plugin is Linux-only and uses direct `hdc_std` / `hdc` execution.
4. OHOS build guidance is standardized on `command-line-tools` and `openharmony_prebuilts`.
5. `translate-web-to-chinese` is packaged as a separate Codex plugin.
6. Repo-level Codex hooks provide OHOS-aware guardrails without recreating Claude routing machinery.

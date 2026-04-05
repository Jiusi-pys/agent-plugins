# OpenAI Branch Repository Isolation Design

Date: 2026-04-04

## Goal

Make the `openai` branch repository semantics independent from the Claude Code marketplace baseline on `main`.

After this cleanup, the `openai` branch should not present itself as a Claude plugin marketplace and should not retain Claude plugin shell content such as marketplace manifests, Claude-only plugin folders, commands, or hooks.

## Required Outcome

- Remove the `auto-clean` Claude plugin from the `openai` branch.
- Remove remaining repository-level Claude marketplace metadata.
- Rewrite root documentation so the repository describes Codex-oriented outputs instead of Claude plugin installation and workflow.
- Preserve the already-converted Codex-facing `ohos-porting` content.

## In Scope

### Remove Claude-only content

- `plugins/auto-clean/`
- `.claude-plugin/marketplace.json`
- Claude-plugin-specific validation workflow if it only validates Claude marketplace structure

### Rewrite repository docs

- `README.md`
- `CLAUDE.md` if retained, or remove it entirely if it is only Claude-specific guidance

### Preserve Codex content

- `plugins/ohos-porting/`
- existing Codex skill structure and supporting files already migrated for `ohos-porting`

## Out of Scope

- Converting `auto-clean` into a Codex plugin or skill
- Expanding the repository with new Codex plugins beyond the current `ohos-porting`
- Reworking `ohos-porting` skill boundaries again unless required by repository-level cleanup

## Design Decisions

### 1. Repository identity changes

The root of the repository will describe the branch as a Codex-oriented migration/output branch, not a Claude marketplace.

That means removing:

- `/plugin install` examples
- Claude marketplace language
- claims about Claude agents, hooks, and commands

### 2. Claude shell removal is structural, not cosmetic

The cleanup must remove the remaining Claude plugin structure from version control instead of only hiding it in docs.

This includes:

- marketplace manifest files
- plugin directories that only make sense for Claude
- validation workflow that assumes Claude plugin structure

### 3. `ohos-porting` remains the only shipped output for now

After cleanup, the repo should read as a repository containing the Codex-compatible `ohos-porting` migration result and related design docs, nothing more.

## Planned File-Level Changes

### Delete

- `plugins/auto-clean/**`
- `.claude-plugin/**`
- `.github/workflows/validate-plugins.yml` if it remains Claude-marketplace-specific
- `CLAUDE.md` if it remains fully Claude-specific after review

### Rewrite

- `README.md`

The rewritten root README should:

- explain the `main` vs `openai` branch split
- state that `openai` contains Codex-compatible conversions
- state that the current converted output is `plugins/ohos-porting`
- list the retained Codex skills:
  - `ohos-hdc`
  - `ohos-cpp-style`
  - `ohos-permission`

## Verification

The cleanup is complete when all of the following are true:

1. `find`/`rg` no longer show repository-level Claude plugin shell files in tracked content.
2. `plugins/auto-clean` is gone.
3. `.claude-plugin` is gone.
4. Root README no longer describes a Claude marketplace or Claude plugin install flow.
5. `plugins/ohos-porting` remains intact and its retained skills still validate.

## Risks

### Risk: deleting repository metadata that is still needed

Mitigation:
- only remove files whose purpose is Claude-marketplace-specific
- keep design/spec docs and Codex skill content untouched

### Risk: incomplete isolation

Mitigation:
- verify with repository-wide searches for Claude plugin shell markers
- treat documentation and workflow files as part of the isolation surface, not just plugin directories

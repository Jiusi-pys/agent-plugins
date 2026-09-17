# OpenAI Branch Repository Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining Claude marketplace shell from the `openai` branch while preserving the Codex-facing `plugins/ohos-porting` skill bundle.

**Architecture:** Delete the last Claude-only tracked structures, then rewrite the root repository docs so the branch describes Codex-oriented migration output instead of Claude plugin installation. Verification is repository-wide search plus retained-skill validation.

**Tech Stack:** Git-tracked Markdown docs, YAML GitHub Actions workflow cleanup, shell filesystem operations, Codex skill validator.

---

### Task 1: Remove the remaining Claude-only tracked structures

**Files:**
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/auto-clean`
- Delete: `/Users/jiusi/Documents/agent-plugins/.claude-plugin/marketplace.json`
- Delete: `/Users/jiusi/Documents/agent-plugins/.github/workflows/validate-plugins.yml`
- Test: repository tree under `/Users/jiusi/Documents/agent-plugins`

- [ ] **Step 1: Write the failing repository-shell assertion**

```bash
test ! -d /Users/jiusi/Documents/agent-plugins/plugins/auto-clean \
  && test ! -e /Users/jiusi/Documents/agent-plugins/.claude-plugin/marketplace.json \
  && test ! -e /Users/jiusi/Documents/agent-plugins/.github/workflows/validate-plugins.yml
```

- [ ] **Step 2: Run the assertion to verify it fails**

Run:
```bash
test ! -d /Users/jiusi/Documents/agent-plugins/plugins/auto-clean \
  && test ! -e /Users/jiusi/Documents/agent-plugins/.claude-plugin/marketplace.json \
  && test ! -e /Users/jiusi/Documents/agent-plugins/.github/workflows/validate-plugins.yml
```
Expected: FAIL because the Claude-only plugin directory, marketplace manifest, and validation workflow are still tracked.

- [ ] **Step 3: Remove the Claude-only tracked structures**

Run:
```bash
rm -rf /Users/jiusi/Documents/agent-plugins/plugins/auto-clean
rm -f /Users/jiusi/Documents/agent-plugins/.claude-plugin/marketplace.json
rmdir /Users/jiusi/Documents/agent-plugins/.claude-plugin 2>/dev/null || true
rm -f /Users/jiusi/Documents/agent-plugins/.github/workflows/validate-plugins.yml
```

- [ ] **Step 4: Re-run the assertion to verify the structures are gone**

Run:
```bash
test ! -d /Users/jiusi/Documents/agent-plugins/plugins/auto-clean \
  && test ! -e /Users/jiusi/Documents/agent-plugins/.claude-plugin/marketplace.json \
  && test ! -e /Users/jiusi/Documents/agent-plugins/.github/workflows/validate-plugins.yml
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -u /Users/jiusi/Documents/agent-plugins/plugins/auto-clean \
          /Users/jiusi/Documents/agent-plugins/.claude-plugin \
          /Users/jiusi/Documents/agent-plugins/.github/workflows/validate-plugins.yml
git commit -m "Remove remaining Claude marketplace shell"
```

### Task 2: Rewrite root documentation for Codex branch semantics

**Files:**
- Modify: `/Users/jiusi/Documents/agent-plugins/README.md`
- Delete: `/Users/jiusi/Documents/agent-plugins/CLAUDE.md`
- Test: `/Users/jiusi/Documents/agent-plugins/README.md`

- [ ] **Step 1: Write the failing documentation assertion**

```bash
rg -n "Codex|openai branch|ohos-hdc|ohos-cpp-style|ohos-permission" \
  /Users/jiusi/Documents/agent-plugins/README.md \
  && test ! -e /Users/jiusi/Documents/agent-plugins/CLAUDE.md
```

- [ ] **Step 2: Run the assertion to verify it fails**

Run:
```bash
rg -n "Codex|openai branch|ohos-hdc|ohos-cpp-style|ohos-permission" \
  /Users/jiusi/Documents/agent-plugins/README.md \
  && test ! -e /Users/jiusi/Documents/agent-plugins/CLAUDE.md
```
Expected: FAIL because the current README still describes a Claude marketplace and `CLAUDE.md` still exists.

- [ ] **Step 3: Replace the root README with Codex-facing branch guidance**

Write this file:

```md
# agent-plugins (`openai` branch)

This branch is the Codex-oriented migration branch for content that originally lived as Claude Code plugins on `main`.

## Branch Roles

- `main`: Claude Code plugin and marketplace baseline
- `openai`: Codex-compatible conversions and cleanup work

## Current Converted Output

The repository currently keeps one converted bundle:

- `plugins/ohos-porting`

## Retained Codex Skills

`plugins/ohos-porting` currently ships these Codex-facing skills:

- `ohos-hdc`
- `ohos-cpp-style`
- `ohos-permission`

## Notes

- This branch does not keep Claude marketplace manifests, Claude commands, or Claude hooks.
- Repository-level docs should describe Codex-compatible outputs only.
```

- [ ] **Step 4: Remove the Claude-only repository guide**

Run:
```bash
rm -f /Users/jiusi/Documents/agent-plugins/CLAUDE.md
```

- [ ] **Step 5: Re-run the documentation assertion**

Run:
```bash
rg -n "Codex|openai branch|ohos-hdc|ohos-cpp-style|ohos-permission" \
  /Users/jiusi/Documents/agent-plugins/README.md \
  && test ! -e /Users/jiusi/Documents/agent-plugins/CLAUDE.md
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add /Users/jiusi/Documents/agent-plugins/README.md
git add -u /Users/jiusi/Documents/agent-plugins/CLAUDE.md
git commit -m "Rewrite repository docs for Codex branch"
```

### Task 3: Verify repository isolation without breaking retained Codex content

**Files:**
- Verify: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting`
- Verify: `/Users/jiusi/Documents/agent-plugins`
- Test: retained skills and repository-wide searches

- [ ] **Step 1: Write the final isolation verification command**

```bash
find /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting -name '*.sh' -exec bash -n {} + \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission \
  && ! rg -n -i 'claude code plugin|/plugin install|marketplace.json|plugins/auto-clean|\\.claude-plugin' /Users/jiusi/Documents/agent-plugins/README.md /Users/jiusi/Documents/agent-plugins/plugins /Users/jiusi/Documents/agent-plugins/.github 2>/dev/null
```

- [ ] **Step 2: Run the verification**

Run:
```bash
find /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting -name '*.sh' -exec bash -n {} + \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission \
  && ! rg -n -i 'claude code plugin|/plugin install|marketplace.json|plugins/auto-clean|\\.claude-plugin' /Users/jiusi/Documents/agent-plugins/README.md /Users/jiusi/Documents/agent-plugins/plugins /Users/jiusi/Documents/agent-plugins/.github 2>/dev/null
```
Expected: PASS

- [ ] **Step 3: Record the final tree and clean working state**

Run:
```bash
find /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting -maxdepth 2 -mindepth 1 | sort
git status --short
```
Expected: only the plan file remains untracked unless it is intentionally staged separately.

- [ ] **Step 4: Commit**

```bash
git add -u /Users/jiusi/Documents/agent-plugins
git commit -m "Verify openai branch repository isolation"
```

# Codex Skills Root Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the retained OHOS Codex skills out of the leftover plugin container and expose them directly under repository-root `skills/`.

**Architecture:** Relocate the three retained self-contained skill directories from `plugins/ohos-porting/skills/` to `skills/`, remove the old `plugins/ohos-porting/` container, and rewrite the root repository README so the branch reads as a Codex skills repo instead of a converted plugin repo.

**Tech Stack:** Markdown docs, YAML manifests, shell filesystem operations, repository-wide grep/find verification, Codex skill validator.

---

### Task 1: Move the retained OHOS skills to repository-root `skills/`

**Files:**
- Create: `/Users/jiusi/Documents/agent-plugins/skills/`
- Move: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc`
- Move: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style`
- Move: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission`
- Test: repository filesystem assertions

- [ ] **Step 1: Write the failing filesystem assertion**

```bash
test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-hdc \
  && test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-cpp-style \
  && test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-permission \
  && test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc
```

- [ ] **Step 2: Run the assertion to verify it fails**

Run:
```bash
test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-hdc \
  && test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-cpp-style \
  && test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-permission \
  && test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc
```
Expected: FAIL because the root-level `skills/` directories do not exist yet.

- [ ] **Step 3: Move the three retained skills**

Run:
```bash
mkdir -p /Users/jiusi/Documents/agent-plugins/skills
mv /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc /Users/jiusi/Documents/agent-plugins/skills/
mv /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style /Users/jiusi/Documents/agent-plugins/skills/
mv /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission /Users/jiusi/Documents/agent-plugins/skills/
```

- [ ] **Step 4: Re-run the assertion to verify the move**

Run:
```bash
test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-hdc \
  && test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-cpp-style \
  && test -d /Users/jiusi/Documents/agent-plugins/skills/ohos-permission \
  && test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A /Users/jiusi/Documents/agent-plugins/skills /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills
git commit -m "Move OHOS skills to repository root"
```

### Task 2: Remove the old plugin container and rewrite root repository docs

**Files:**
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting`
- Modify: `/Users/jiusi/Documents/agent-plugins/README.md`
- Test: repository structure and README assertions

- [ ] **Step 1: Write the failing repository assertion**

```bash
test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting \
  && rg -n 'skills/ohos-hdc|skills/ohos-cpp-style|skills/ohos-permission|Codex skills repository' /Users/jiusi/Documents/agent-plugins/README.md
```

- [ ] **Step 2: Run the assertion to verify it fails**

Run:
```bash
test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting \
  && rg -n 'skills/ohos-hdc|skills/ohos-cpp-style|skills/ohos-permission|Codex skills repository' /Users/jiusi/Documents/agent-plugins/README.md
```
Expected: FAIL because `plugins/ohos-porting` still exists and the README still points to the plugin container.

- [ ] **Step 3: Remove the old plugin container**

Run:
```bash
rm -rf /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting
rmdir /Users/jiusi/Documents/agent-plugins/plugins 2>/dev/null || true
```

- [ ] **Step 4: Replace the root README with root-level skill repo guidance**

Write this file:

```md
# Codex Skills Repository (`openai` branch)

This branch is the Codex-first branch of this repository.

## Branch Split

- `main` keeps the original Claude-oriented source layout.
- `openai` keeps Codex-ready skill outputs.

## Available Skills

The current root-level skills in this branch are:

- `skills/ohos-hdc`
- `skills/ohos-cpp-style`
- `skills/ohos-permission`

## Notes

- This branch is organized for direct Codex skill consumption.
- The retained OHOS skills are self-contained and can be copied or installed individually.
- Repository docs should describe the root-level `skills/` layout, not a plugin container layout.
```

- [ ] **Step 5: Re-run the repository assertion**

Run:
```bash
test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting \
  && rg -n 'skills/ohos-hdc|skills/ohos-cpp-style|skills/ohos-permission|Codex Skills Repository' /Users/jiusi/Documents/agent-plugins/README.md
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add /Users/jiusi/Documents/agent-plugins/README.md
git add -A /Users/jiusi/Documents/agent-plugins/plugins
git commit -m "Remove plugin container from openai branch"
```

### Task 3: Verify root-level Codex skills integrity after normalization

**Files:**
- Verify: `/Users/jiusi/Documents/agent-plugins/skills/ohos-hdc`
- Verify: `/Users/jiusi/Documents/agent-plugins/skills/ohos-cpp-style`
- Verify: `/Users/jiusi/Documents/agent-plugins/skills/ohos-permission`
- Test: shell syntax, skill validation, stale path searches

- [ ] **Step 1: Write the final verification command**

```bash
find /Users/jiusi/Documents/agent-plugins/skills -name '*.sh' -exec bash -n {} + \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/skills/ohos-hdc \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/skills/ohos-cpp-style \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/skills/ohos-permission \
  && ! rg -n 'plugins/ohos-porting' /Users/jiusi/Documents/agent-plugins
```

- [ ] **Step 2: Run the verification**

Run:
```bash
find /Users/jiusi/Documents/agent-plugins/skills -name '*.sh' -exec bash -n {} + \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/skills/ohos-hdc \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/skills/ohos-cpp-style \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/jiusi/Documents/agent-plugins/skills/ohos-permission \
  && ! rg -n 'plugins/ohos-porting' /Users/jiusi/Documents/agent-plugins
```
Expected: PASS

- [ ] **Step 3: Record final tree and clean status**

Run:
```bash
find /Users/jiusi/Documents/agent-plugins/skills -maxdepth 2 -mindepth 1 | sort
git status --short
```
Expected: only intentional plan/spec doc deltas remain, or the working tree is clean after commits.

- [ ] **Step 4: Commit**

```bash
git add -A /Users/jiusi/Documents/agent-plugins
git commit -m "Verify root-level Codex skills layout"
```

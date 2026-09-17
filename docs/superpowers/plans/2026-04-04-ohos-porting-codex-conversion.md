# OHOS Porting Codex Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `plugins/ohos-porting` into a Codex-facing OHOS skill bundle that keeps only `ohos-hdc`, `ohos-cpp-style`, and `ohos-permission`.

**Architecture:** Keep the reusable OHOS resources that still matter to Codex, rewrite the three retained skills so they trigger cleanly in Codex, add `agents/openai.yaml` metadata for each retained skill, and delete the Claude-only plugin shell and deprecated skills. Validation is filesystem- and skill-validator-based rather than Claude plugin validation.

**Tech Stack:** Markdown skills, YAML metadata, shell filesystem operations, existing OHOS shell/Python helper scripts, Codex skill validator.

---

### Task 1: Restructure `ohos-porting` around the three retained skills

**Files:**
- Modify: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/hdc-kaihongOS/`
- Create: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/`
- Test: filesystem assertions in `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting`

- [ ] **Step 1: Write the failing filesystem assertion**

```bash
test -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc \
  && test -f /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md \
  && test -f /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents/openai.yaml \
  && test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/hdc-kaihongOS
```

- [ ] **Step 2: Run the assertion to verify it fails**

Run:
```bash
test -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc \
  && test -f /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md \
  && test -f /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents/openai.yaml \
  && test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/hdc-kaihongOS
```
Expected: FAIL because `skills/ohos-hdc/` and its `agents/openai.yaml` do not exist yet, and `skills/hdc-kaihongOS/` still exists.

- [ ] **Step 3: Rename the HDC skill directory and create metadata directory**

Run:
```bash
mv /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/hdc-kaihongOS \
   /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc
mkdir -p /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents
```

- [ ] **Step 4: Re-run the assertion to verify the rename shell is in place**

Run:
```bash
test -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc \
  && test -f /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md \
  && test ! -d /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/hdc-kaihongOS
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc
git commit -m "refactor: rename hdc skill for codex"
```

### Task 2: Rewrite the `ohos-hdc` skill for Codex and add `openai.yaml`

**Files:**
- Modify: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md`
- Create: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents/openai.yaml`
- Test: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md`

- [ ] **Step 1: Write the failing skill-content assertions**

```bash
rg -n "name: ohos-hdc|Use when Codex needs to work with OHOS devices|device-control.sh|hdc-auto.sh" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md \
  && rg -n 'display_name: "OHOS HDC"|short_description: "Operate OpenHarmony devices with HDC"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents/openai.yaml
```

- [ ] **Step 2: Run the assertions to verify they fail**

Run:
```bash
rg -n "name: ohos-hdc|Use when Codex needs to work with OHOS devices|device-control.sh|hdc-auto.sh" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md \
  && rg -n 'display_name: "OHOS HDC"|short_description: "Operate OpenHarmony devices with HDC"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents/openai.yaml
```
Expected: FAIL because the skill still uses the old frontmatter and `openai.yaml` does not exist.

- [ ] **Step 3: Replace `SKILL.md` with Codex-oriented content**

Write this file:

```md
---
name: ohos-hdc
description: HDC operations for OpenHarmony and KaihongOS devices. Use when Codex needs to detect OHOS devices, choose a target device, run shell commands over HDC, transfer files, collect logs, install packages, or handle cross-platform HDC wrappers on Linux, macOS, Windows, or WSL.
---

# OHOS HDC

Use this skill to work with OpenHarmony or KaihongOS devices over HDC.

## Quick Start

Prefer `scripts/device-control.sh` for device-facing operations because it hides platform-specific quoting and wrapper differences.

```bash
./scripts/device-control.sh list
./scripts/device-control.sh -t <device_id> shell "uname -a"
./scripts/device-control.sh -t <device_id> file send ./local.bin /data/local/tmp/
./scripts/device-control.sh -t <device_id> hilog
```

Use `scripts/hdc-auto.sh` when you need the raw HDC command shape but still want automatic platform detection.

```bash
./scripts/hdc-auto.sh --platform
./scripts/hdc-auto.sh list targets
./scripts/hdc-auto.sh -t <device_id> shell
```

## Workflow

1. Detect the host platform and available HDC wrapper.
2. List devices and require `-t <device_id>` when more than one target is connected.
3. Use `device-control.sh` for shell, file, and log operations unless a raw HDC command is specifically needed.
4. Keep deployment artifacts under `/data/local/tmp` unless the user explicitly asks for a more permanent location.
5. Collect enough command output to confirm success before moving on.

## Common Operations

### List devices

```bash
./scripts/device-control.sh list
```

### Run a shell command

```bash
./scripts/device-control.sh -t <device_id> shell "ls -la /data/local/tmp"
```

### Push and pull files

```bash
./scripts/device-control.sh -t <device_id> file send ./artifact /data/local/tmp/
./scripts/device-control.sh -t <device_id> file recv /data/local/tmp/artifact ./artifact
```

### Collect logs

```bash
./scripts/device-control.sh -t <device_id> hilog
./scripts/linux/hilog-monitor.sh <device_id>
```

## Platform Notes

- Linux and macOS prefer `hdc_std` when present, then fall back to `hdc`.
- Windows uses `hdc` or `hdc.exe`.
- WSL uses the PowerShell wrapper path to avoid broken nested quoting.
- For platform-specific details, read:
  - `references/HDC-COMMANDS.md`
  - `references/LINUX-GUIDE.md`
  - `references/WSL-GUIDE.md`
  - `references/WORKFLOW-PATTERNS.md`

## Safety Rules

- Do not modify `/system` or `/vendor` unless the user explicitly authorizes it.
- Prefer `/data/local/tmp` for test binaries and temporary libraries.
- When multiple devices are attached, always specify the device target.
- Preserve command output for troubleshooting when file transfer or execution fails.
```

- [ ] **Step 4: Create `agents/openai.yaml`**

Write this file:

```yaml
interface:
  display_name: "OHOS HDC"
  short_description: "Operate OpenHarmony devices with HDC"
  default_prompt: "Use $ohos-hdc to inspect this device, run commands, transfer files, or collect logs over HDC."
```

- [ ] **Step 5: Run the assertions to verify they pass**

Run:
```bash
rg -n "name: ohos-hdc|Use when Codex needs to work with OHOS devices|device-control.sh|hdc-auto.sh" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md \
  && rg -n 'display_name: "OHOS HDC"|short_description: "Operate OpenHarmony devices with HDC"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents/openai.yaml
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/SKILL.md \
        /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc/agents/openai.yaml
git commit -m "feat: convert ohos hdc skill for codex"
```

### Task 3: Rewrite the `ohos-cpp-style` skill for Codex and add `openai.yaml`

**Files:**
- Modify: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/SKILL.md`
- Create: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/agents/openai.yaml`
- Test: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/SKILL.md`

- [ ] **Step 1: Write the failing skill-content assertions**

```bash
rg -n "Use when Codex needs to write or review OpenHarmony C/C\\+\\+ code|config.json|BUILD\\.gn|references/thread-patterns.md" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/SKILL.md \
  && rg -n 'display_name: "OHOS C\\+\\+ Style"|short_description: "Write OpenHarmony C/C\\+\\+ cleanly"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/agents/openai.yaml
```

- [ ] **Step 2: Run the assertions to verify they fail**

Run:
```bash
rg -n "Use when Codex needs to write or review OpenHarmony C/C\\+\\+ code|config.json|BUILD\\.gn|references/thread-patterns.md" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/SKILL.md \
  && rg -n 'display_name: "OHOS C\\+\\+ Style"|short_description: "Write OpenHarmony C/C\\+\\+ cleanly"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/agents/openai.yaml
```
Expected: FAIL because the current skill text is Claude-oriented and `openai.yaml` does not exist.

- [ ] **Step 3: Replace `SKILL.md` with Codex-oriented content**

Write this file:

```md
---
name: ohos-cpp-style
description: OpenHarmony and KaihongOS C/C++ coding guidance. Use when Codex needs to write, edit, review, or refactor OHOS-native C/C++ code, create or update BUILD.gn files, apply OHOS naming and file layout conventions, or check threading, serialization, and permission-related implementation patterns.
---

# OHOS C++ Style

Use this skill when producing or reviewing C/C++ code for OpenHarmony or KaihongOS projects.

## Start Here

Read `config.json` before relying on repository-specific paths or toolchain values.

```json
{
  "paths": {
    "openharmony_source": "/path/to/OpenHarmony",
    "openharmony_prebuilts": "/path/to/openharmony_prebuilts",
    "output_dir": "/path/to/out/<board>"
  }
}
```

If the config values are placeholders, keep generated code generic and avoid inventing machine-specific paths.

## Core Conventions

- Use `CamelCase` for namespaces, classes, and structs.
- Use `camelCase` for methods.
- Use `snake_case_` for member fields.
- Use `UPPER_SNAKE_CASE` for macros and constants.
- Use `snake_case` for file names.
- Keep platform-specific code isolated instead of scattering conditional compilation across unrelated files.

## File Skeleton

```cpp
/*
 * Copyright (c) 2024-2026 Your Organization
 * Licensed under the Apache License, Version 2.0
 */

#ifndef PROJECT__MODULE_NAME_H_
#define PROJECT__MODULE_NAME_H_

namespace OHOS {
class SessionManager {
public:
    int32_t Initialize();
private:
    bool initialized_ = false;
};
}  // namespace OHOS

#endif  // PROJECT__MODULE_NAME_H_
```

## BUILD.gn and Layout Guidance

- Prefer explicit targets and dependencies in `BUILD.gn`.
- Keep headers and sources grouped by responsibility.
- Use the templates in `asserts/BUILD.gn` and `references/gn-templates.md` as the baseline shape.
- When adding a new OHOS-specific module, keep the interface minimal and isolate adaptation code in a dedicated file pair.

## Formatting

Prefer the repository clang-format file when present.

```bash
clang-format -style=file -i file.cpp file.h
```

Use `asserts/.clang-format` as the reference when a project-local file is missing.

## Reference Files

Read these only when they are relevant:

- `references/gn-templates.md` for `BUILD.gn` patterns
- `references/thread-patterns.md` for synchronization and concurrency patterns
- `references/serialization.md` for data encoding and marshaling patterns
- `references/permission-config.md` for permission-related native code considerations

## Output Expectations

- Produce code that matches OHOS naming and layout conventions.
- Keep comments sparse and useful.
- Prefer small, focused files and explicit ownership boundaries.
```

- [ ] **Step 4: Create `agents/openai.yaml`**

Write this file:

```yaml
interface:
  display_name: "OHOS C++ Style"
  short_description: "Write OpenHarmony C/C++ cleanly"
  default_prompt: "Use $ohos-cpp-style to write or review this OpenHarmony C/C++ code and keep the result aligned with OHOS conventions."
```

- [ ] **Step 5: Run the assertions to verify they pass**

Run:
```bash
rg -n "Use when Codex needs to write or review OpenHarmony C/C\\+\\+ code|config.json|BUILD\\.gn|references/thread-patterns.md" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/SKILL.md \
  && rg -n 'display_name: "OHOS C\\+\\+ Style"|short_description: "Write OpenHarmony C/C\\+\\+ cleanly"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/agents/openai.yaml
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/SKILL.md \
        /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style/agents/openai.yaml
git commit -m "feat: convert ohos cpp style skill for codex"
```

### Task 4: Rewrite the `ohos-permission` skill for Codex and add `openai.yaml`

**Files:**
- Modify: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/SKILL.md`
- Create: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/agents/openai.yaml`
- Test: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/SKILL.md`

- [ ] **Step 1: Write the failing skill-content assertions**

```bash
rg -n "Use when Codex needs to configure or verify OpenHarmony permissions|deploy_softbus_permission\\.sh|verify_softbus_permission\\.sh|templates/verified\\.json" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/SKILL.md \
  && rg -n 'display_name: "OHOS Permission"|short_description: "Configure OpenHarmony permissions"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/agents/openai.yaml
```

- [ ] **Step 2: Run the assertions to verify they fail**

Run:
```bash
rg -n "Use when Codex needs to configure or verify OpenHarmony permissions|deploy_softbus_permission\\.sh|verify_softbus_permission\\.sh|templates/verified\\.json" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/SKILL.md \
  && rg -n 'display_name: "OHOS Permission"|short_description: "Configure OpenHarmony permissions"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/agents/openai.yaml
```
Expected: FAIL because the current skill text is not Codex-specific and `openai.yaml` does not exist.

- [ ] **Step 3: Replace `SKILL.md` with Codex-oriented content**

Write this file:

```md
---
name: ohos-permission
description: OpenHarmony and KaihongOS permission configuration guidance. Use when Codex needs to configure, deploy, or verify OHOS native permissions, especially DSoftBus session permissions, AccessToken-related setup, or device-side permission JSON updates.
---

# OHOS Permission

Use this skill when editing, deploying, or validating OpenHarmony permission configuration.

## Verified Workflow

Prefer the verified template and deployment scripts that already live in this skill.

```bash
cp templates/verified.json /tmp/softbus_perm.json
./scripts/deploy_softbus_permission.sh <DEVICE_ID> /tmp/softbus_perm.json
./scripts/verify_softbus_permission.sh <DEVICE_ID>
```

## Core Rules

- The DSoftBus permission file must use a top-level JSON array.
- Do not wrap the data in an extra `trans_permission` object.
- Device reboot may be required after updating the permission file.
- Keep a backup before overwriting a device-side permission file.

## Correct Shape

```json
[
  {
    "SESSION_NAME": "com.huawei.ros2_rmw_dsoftbus.*",
    "REGEXP": "true",
    "DEVID": "NETWORKID",
    "SEC_LEVEL": "public",
    "APP_INFO": [
      {
        "TYPE": "native_app",
        "PKG_NAME": "com.huawei.ros2_rmw_dsoftbus",
        "ACTIONS": "create,open"
      }
    ]
  }
]
```

## Working Files

- `templates/minimal.json` for the smallest valid starting point
- `templates/dev.json` for development-focused edits
- `templates/verified.json` for known-good deployment
- `scripts/deploy_softbus_permission.sh` for device-side installation
- `scripts/verify_softbus_permission.sh` for validation

## Practical Workflow

1. Pick the closest template.
2. Edit only the fields needed for the target package or session name.
3. Back up the current device file before deployment.
4. Deploy with the provided script.
5. Reboot if required by the target device.
6. Run the verification script and capture the output.

## Troubleshooting

- Permission denied after deployment usually means the JSON shape is wrong or the device has not restarted.
- If matching fails, check `REGEXP` and the exact package name or session name pattern.
- If the device rejects the file, validate the JSON structure before retrying.
```

- [ ] **Step 4: Create `agents/openai.yaml`**

Write this file:

```yaml
interface:
  display_name: "OHOS Permission"
  short_description: "Configure OpenHarmony permissions"
  default_prompt: "Use $ohos-permission to update or verify this OpenHarmony permission setup and keep the JSON and deployment steps correct."
```

- [ ] **Step 5: Run the assertions to verify they pass**

Run:
```bash
rg -n "Use when Codex needs to configure or verify OpenHarmony permissions|deploy_softbus_permission\\.sh|verify_softbus_permission\\.sh|templates/verified\\.json" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/SKILL.md \
  && rg -n 'display_name: "OHOS Permission"|short_description: "Configure OpenHarmony permissions"' \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/agents/openai.yaml
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/SKILL.md \
        /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission/agents/openai.yaml
git commit -m "feat: convert ohos permission skill for codex"
```

### Task 5: Remove Claude-only shell and deprecated skills

**Files:**
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/.claude-plugin/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/agents/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/commands/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/hooks/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/install.sh`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/agent-routing/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/api-mapping/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/compile-error-analysis/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/git-cicd-workflow/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/main-orchestrator/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cross-compile/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/porting-diagnostics/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/remote-server-ssh-control/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/runtime-debug/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/stub-interposition/`
- Delete: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/working-records/`
- Test: retained directory listing under `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting`

- [ ] **Step 1: Write the failing retained-set assertion**

```bash
find /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting -maxdepth 2 -mindepth 1 | sort
```

The expected retained top-level structure after cleanup is:

```text
/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md
/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills
/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style
/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc
/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission
```

- [ ] **Step 2: Run the listing to verify it currently fails the target shape**

Run:
```bash
find /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting -maxdepth 2 -mindepth 1 | sort
```
Expected: FAIL against the expected retained set because Claude plugin directories and deprecated skills are still present.

- [ ] **Step 3: Remove Claude-only and deprecated paths**

Run:
```bash
rm -rf /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/.claude-plugin \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/agents \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/commands \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/hooks \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/agent-routing \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/api-mapping \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/compile-error-analysis \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/git-cicd-workflow \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/main-orchestrator \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cross-compile \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/porting-diagnostics \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/remote-server-ssh-control \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/runtime-debug \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/stub-interposition \
       /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/working-records
rm -f /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/install.sh
```

- [ ] **Step 4: Re-run the retained-set listing and verify it matches the target**

Run:
```bash
find /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting -maxdepth 2 -mindepth 1 | sort
```
Expected: only `README.md`, `skills/`, and the three retained skill directories remain at this depth.

- [ ] **Step 5: Commit**

```bash
git add -A /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting
git commit -m "refactor: remove claude-only ohos plugin content"
```

### Task 6: Rewrite the plugin README and validate all retained skills

**Files:**
- Modify: `/Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md`
- Test: `/Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py`

- [ ] **Step 1: Write the failing README assertions**

```bash
rg -n "Codex|ohos-hdc|ohos-cpp-style|ohos-permission" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md \
  && ! rg -n "/ohos-port|Task:|Claude Code|commands/|agents/" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md
```

- [ ] **Step 2: Run the assertions to verify they fail**

Run:
```bash
rg -n "Codex|ohos-hdc|ohos-cpp-style|ohos-permission" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md \
  && ! rg -n "/ohos-port|Task:|Claude Code|commands/|agents/" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md
```
Expected: FAIL because the README still documents the Claude plugin workflow.

- [ ] **Step 3: Replace the README with Codex-facing documentation**

Write this file:

```md
# OHOS Porting Skills

This directory contains Codex-facing OpenHarmony and KaihongOS skills.

## Included Skills

### `ohos-hdc`

Use for device discovery, shell access, file transfer, and log collection over HDC.

### `ohos-cpp-style`

Use for OpenHarmony C/C++ naming, file layout, formatting, and `BUILD.gn` guidance.

### `ohos-permission`

Use for OHOS permission JSON editing, deployment, and verification, especially for DSoftBus-related setups.

## Layout

```text
plugins/ohos-porting/
├── README.md
└── skills/
    ├── ohos-cpp-style/
    ├── ohos-hdc/
    └── ohos-permission/
```

## Notes

- This branch keeps only the skills that remain useful in Codex.
- Claude plugin commands, hooks, and agent definitions are intentionally removed here.
- Each retained skill includes `agents/openai.yaml` so Codex can surface it cleanly.
```

- [ ] **Step 4: Run the README assertions to verify they pass**

Run:
```bash
rg -n "Codex|ohos-hdc|ohos-cpp-style|ohos-permission" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md \
  && ! rg -n "/ohos-port|Task:|Claude Code|commands/|agents/" \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md
```
Expected: PASS

- [ ] **Step 5: Validate all three skills**

Run:
```bash
python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style \
  && python3 /Users/jiusi/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission
```
Expected: PASS for all three skill directories.

- [ ] **Step 6: Commit**

```bash
git add /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/README.md \
        /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-hdc \
        /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-cpp-style \
        /Users/jiusi/Documents/agent-plugins/plugins/ohos-porting/skills/ohos-permission
git commit -m "docs: finalize codex ohos skill bundle"
```

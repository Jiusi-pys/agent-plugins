---
name: ohos-hdc
description: HDC operations for OpenHarmony and KaihongOS devices. Use when Codex needs to detect OHOS devices, choose a target device, run shell commands over HDC, transfer files, collect logs, or handle cross-platform HDC wrappers on Linux, macOS, Windows, or WSL.
---

# OHOS HDC

Use this skill to work with OpenHarmony or KaihongOS devices over HDC.

## Quick Start

Prefer `scripts/device-control.sh` for device-facing operations because it hides platform-specific quoting and wrapper differences.
These examples are for Linux, macOS, and Git Bash/MSYS on Windows. For WSL file transfer, follow the staged workflow in `references/WSL-GUIDE.md`.

```bash
./scripts/device-control.sh list targets
./scripts/device-control.sh -t <device_id> shell "uname -a"
./scripts/device-control.sh -t <device_id> file send ./local.bin /data/local/tmp/
./scripts/device-control.sh -t <device_id> hilog
```

## Workflow

1. Detect the host platform and available HDC wrapper.
2. List devices and require `-t <device_id>` when more than one target is connected.
3. Use `device-control.sh` for shell and log operations unless a raw HDC command is specifically needed. For WSL file transfer, follow the staged workflow in `references/WSL-GUIDE.md`.
4. Keep deployment artifacts under `/data/local/tmp` unless the user explicitly asks for a more permanent location.
5. Collect enough command output to confirm success before moving on.

## Common Operations

### List devices

```bash
./scripts/device-control.sh list targets
```

### Run a shell command

```bash
./scripts/device-control.sh -t <device_id> shell "ls -la /data/local/tmp"
```

### Push and pull files

For WSL, use the staged workflow in `references/WSL-GUIDE.md` instead of these direct file-transfer examples.

```bash
./scripts/device-control.sh -t <device_id> file send ./artifact /data/local/tmp/
./scripts/device-control.sh -t <device_id> file recv /data/local/tmp/artifact ./artifact
```

### Collect logs

```bash
./scripts/device-control.sh -t <device_id> hilog
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

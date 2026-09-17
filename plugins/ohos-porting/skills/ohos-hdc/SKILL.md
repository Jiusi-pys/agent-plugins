---
name: ohos-hdc
description: Linux-only HDC operations for OpenHarmony and KaihongOS devices. Use when Codex needs to detect devices, select a target, run shell commands, transfer files, collect logs, or deploy artifacts over direct `hdc_std` or `hdc`.
---

# OHOS HDC

Use this skill when a Linux host needs to operate an OpenHarmony or KaihongOS device over HDC.

## Host Assumptions

- The host is Linux.
- Prefer `hdc_std`; fall back to `hdc`.
- Do not route through host-side wrappers or staging paths.
- Use `./scripts/hdc-auto.sh` or `./scripts/device-control.sh` in examples unless you have already resolved the active HDC binary.

## Quick Start

```bash
./scripts/hdc-auto.sh list targets
./scripts/device-control.sh -t <device_id> shell "uname -a"
./scripts/device-control.sh -t <device_id> file send ./artifact /data/local/tmp/
./scripts/device-control.sh -t <device_id> hilog
```

## Workflow

1. Detect the available HDC binary with `scripts/hdc-auto.sh`.
2. List targets and require `-t <device_id>` whenever more than one device is visible.
3. Prefer `/data/local/tmp` for temporary binaries, logs, and test payloads.
4. Use the Linux helper scripts under `scripts/linux/` when you need repeatable deployment, device selection, log monitoring, or udev setup.
5. Do not modify `/system` or `/vendor` unless the user has explicitly authorized it.

## Files

- `scripts/hdc-auto.sh`: Resolve and run `hdc_std` or `hdc` on Linux.
- `scripts/device-control.sh`: Direct wrapper for shell, file, install, uninstall, reboot, and log flows.
- `scripts/linux/install-hdc.sh`: Verify Linux host assumptions and report how to expose `hdc_std` or `hdc` on `PATH`.
- `scripts/linux/setup-udev.sh`: Set up USB access for OpenHarmony devices on Linux.
- `references/LINUX-GUIDE.md`: Linux-specific HDC setup and troubleshooting.
- `references/HDC-COMMANDS.md`: Direct HDC command reference.
- `references/WORKFLOW-PATTERNS.md`: Common Linux-side deployment and debugging sequences.

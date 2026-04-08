---
name: ohos-cross-compile
description: Linux-only OpenHarmony cross-compilation guidance. Use when Codex needs to build or adapt native C/C++ software with OpenHarmony `command-line-tools` and `openharmony_prebuilts`, generate or edit BUILD.gn or CMake files, or prepare deployment outputs for HDC-based testing.
---

# OHOS Cross Compile

Use this skill to build native software for OpenHarmony from a Linux host.

## Standard Environment

All guidance in this skill assumes:

- Linux host shell
- OpenHarmony `command-line-tools`
- `openharmony_prebuilts`
- device deployment over direct `hdc_std` or `hdc`

Do not branch into alternate host-side staging flows.

## Required Setup Order

1. Fill in `ohos_toolchain_config.json` with the local Linux paths for `command-line-tools` and `openharmony_prebuilts`.
2. Run `scripts/check_toolchain.sh`.
3. Run `scripts/device_survey.sh` on the device before deployment to avoid library name collisions and environment surprises.
4. Build, deploy, and verify from Linux.

## Quick Start

```bash
./scripts/check_toolchain.sh
hdc shell 'sh /data/local/tmp/device_survey.sh'
```

## Files

- `ohos_toolchain_config.json`: Linux path contract for the OpenHarmony toolchain.
- `scripts/check_toolchain.sh`: Validate the configured command-line tools and prebuilts.
- `scripts/device_survey.sh`: Capture target-device library and runtime state.
- `references/compilation-flags.md`: Linux clang and linker flags for OpenHarmony builds.
- `references/linking-strategies.md`: Shared-library and runtime-path guidance for Linux-hosted OHOS builds.
- `references/toolchain-setup.md`: Standard Linux toolchain layout.
- `references/deployment-guide.md`: Linux HDC deployment sequence.
- `references/troubleshooting.md`: Linux build and deployment troubleshooting checklist.

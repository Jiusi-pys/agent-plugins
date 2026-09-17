# Linux Toolchain Setup

The supported host environment is Linux with OpenHarmony `command-line-tools` and `openharmony_prebuilts`.

## Required Paths

- `command-line-tools`: Linux OpenHarmony CLI tool bundle
- `openharmony_prebuilts`: prebuilts tree used by the target build

The config contract is:

- `command_line_tools_root`: bundle root, for example `/opt/command-line-tools`
- `openharmony_prebuilts_root`: prebuilts root, for example `/opt/openharmony_prebuilts`

`scripts/check_toolchain.sh` derives `sdk/native`, `llvm`, and `sysroot` from `command_line_tools_root` unless you override those paths explicitly.

## Standard environment

```bash
export OHOS_COMMAND_LINE_TOOLS=/opt/command-line-tools
export OHOS_PREBUILTS=/opt/openharmony_prebuilts
export OHOS_LLVM_ROOT=$OHOS_COMMAND_LINE_TOOLS/sdk/native/llvm
export PATH=$OHOS_LLVM_ROOT/bin:$OHOS_COMMAND_LINE_TOOLS/sdk/native/build-tools/cmake/bin:$PATH
```

## Validation

```bash
./scripts/check_toolchain.sh
```

The validation checks both roots, the derived native toolchain layout, and the configured `gn`/`ninja` binaries before any porting or deployment work starts.

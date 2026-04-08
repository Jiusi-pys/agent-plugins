# Linux Toolchain Setup

The supported host environment is Linux with OpenHarmony `command-line-tools` and `openharmony_prebuilts`.

## Required Paths

- `command-line-tools`: Linux OpenHarmony CLI tool bundle
- `openharmony_prebuilts`: prebuilts tree used by the target build

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

The validation should succeed before any porting or deployment work starts.

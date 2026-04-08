# Compilation Flags

Use the OpenHarmony clang toolchain from `command-line-tools`.

## Recommended baseline

```bash
-std=c++17 -O2 -fPIC -fuse-ld=lld
```

## Common additions

- `-fvisibility=default` for symbols loaded with `dlsym`
- `-Wl,-rpath,/data/local/tmp` for test-only runtime library paths
- `--target=aarch64-unknown-linux-ohos` when the wrapper compiler is not already target-specific

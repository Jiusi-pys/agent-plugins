# Linking Strategies

Prefer the OpenHarmony clang and sysroot from `command-line-tools`.

## Shared libraries

- keep deployable shared objects under `/data/local/tmp` during test cycles
- set an explicit runtime search path when the binary depends on side-loaded `.so` files
- avoid copying test libraries into `/system/lib64`

## Runtime choices

- use `libc++_shared.so` when you need smaller binaries and can deploy the runtime with the build output
- use `libc++_static.a` only when the target and license constraints allow static linkage
- verify `NEEDED`, `RPATH`, and `RUNPATH` with `llvm-readelf -d`

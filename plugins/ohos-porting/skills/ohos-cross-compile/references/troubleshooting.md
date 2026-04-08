# Linux Build Troubleshooting

## Check the toolchain

```bash
./scripts/check_toolchain.sh
```

## Check the target binary

```bash
file ./build/myapp
readelf -d ./build/myapp | grep NEEDED
```

## Check device-side deployment

```bash
HDC_BIN="${HDC_BIN:-$(command -v hdc_std || command -v hdc || true)}"
[ -n "$HDC_BIN" ] || { echo "HDC not found" >&2; exit 1; }
"$HDC_BIN" -t <device_id> shell 'ls -lh /data/local/tmp'
"$HDC_BIN" -t <device_id> shell 'ldd /data/local/tmp/myapp'
```

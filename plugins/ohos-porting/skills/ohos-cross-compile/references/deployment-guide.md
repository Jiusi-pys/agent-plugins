# Linux Deployment Guide

Use Linux direct `hdc_std` or `hdc` to deploy artifacts after cross-compilation.

## Example

```bash
HDC_BIN="${HDC_BIN:-$(command -v hdc_std || command -v hdc || true)}"
[ -n "$HDC_BIN" ] || { echo "HDC not found" >&2; exit 1; }
DEVICE_ID=$("$HDC_BIN" list targets | awk 'NF {print $1; exit}')
"$HDC_BIN" -t "$DEVICE_ID" shell 'mkdir -p /data/local/tmp/bin /data/local/tmp/lib'
"$HDC_BIN" -t "$DEVICE_ID" file send ./build/myapp /data/local/tmp/bin/myapp
"$HDC_BIN" -t "$DEVICE_ID" file send ./build/libmylib.so /data/local/tmp/lib/libmylib.so
"$HDC_BIN" -t "$DEVICE_ID" shell 'chmod +x /data/local/tmp/bin/myapp'
"$HDC_BIN" -t "$DEVICE_ID" shell 'LD_LIBRARY_PATH=/data/local/tmp/lib /data/local/tmp/bin/myapp --version'
```

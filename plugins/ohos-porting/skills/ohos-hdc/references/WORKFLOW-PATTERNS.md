# Linux Workflow Patterns

## Deploy a binary

```bash
HDC_BIN="${HDC_BIN:-$(command -v hdc_std || command -v hdc || true)}"
[ -n "$HDC_BIN" ] || { echo "HDC not found" >&2; exit 1; }
DEVICE_ID=$("$HDC_BIN" list targets | awk 'NF {print $1; exit}')
"$HDC_BIN" -t "$DEVICE_ID" file send ./build/myapp /data/local/tmp/myapp
"$HDC_BIN" -t "$DEVICE_ID" shell 'chmod +x /data/local/tmp/myapp'
"$HDC_BIN" -t "$DEVICE_ID" shell '/data/local/tmp/myapp --help'
```

## Monitor logs

```bash
"$HDC_BIN" -t "$DEVICE_ID" hilog | grep -i myapp
```

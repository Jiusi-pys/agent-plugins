# HDC Command Reference

Linux-only HDC reference for direct `hdc_std` or `hdc` use.

Resolve the active binary first when you are not using `./scripts/hdc-auto.sh`:

```bash
HDC_BIN="${HDC_BIN:-$(command -v hdc_std || command -v hdc || true)}"
[ -n "$HDC_BIN" ] || { echo "HDC not found" >&2; exit 1; }
```

## Device discovery

```bash
"$HDC_BIN" list targets
"$HDC_BIN" list targets -v
```

## Common commands

```bash
"$HDC_BIN" -t <device_id> shell 'uname -a'
"$HDC_BIN" -t <device_id> file send ./artifact /data/local/tmp/
"$HDC_BIN" -t <device_id> file recv /data/log/faultlog ./faultlog
"$HDC_BIN" -t <device_id> hilog
"$HDC_BIN" -t <device_id> install ./app.hap
```

Always provide `-t <device_id>` when more than one target is attached.

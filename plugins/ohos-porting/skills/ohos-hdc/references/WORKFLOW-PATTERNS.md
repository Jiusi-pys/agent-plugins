# Linux Workflow Patterns

## Deploy a binary

```bash
DEVICE_ID=$(hdc list targets | awk 'NF {print $1; exit}')
hdc -t "$DEVICE_ID" file send ./build/myapp /data/local/tmp/myapp
hdc -t "$DEVICE_ID" shell 'chmod +x /data/local/tmp/myapp'
hdc -t "$DEVICE_ID" shell '/data/local/tmp/myapp --help'
```

## Monitor logs

```bash
hdc -t "$DEVICE_ID" hilog | grep -i myapp
```

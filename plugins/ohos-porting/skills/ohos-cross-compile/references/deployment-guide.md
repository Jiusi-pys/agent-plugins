# Linux Deployment Guide

Use Linux direct `hdc_std` or `hdc` to deploy artifacts after cross-compilation.

## Example

```bash
DEVICE_ID=$(hdc list targets | awk 'NF {print $1; exit}')
hdc -t "$DEVICE_ID" shell 'mkdir -p /data/local/tmp/bin /data/local/tmp/lib'
hdc -t "$DEVICE_ID" file send ./build/myapp /data/local/tmp/bin/myapp
hdc -t "$DEVICE_ID" file send ./build/libmylib.so /data/local/tmp/lib/libmylib.so
hdc -t "$DEVICE_ID" shell 'chmod +x /data/local/tmp/bin/myapp'
hdc -t "$DEVICE_ID" shell 'LD_LIBRARY_PATH=/data/local/tmp/lib /data/local/tmp/bin/myapp --version'
```

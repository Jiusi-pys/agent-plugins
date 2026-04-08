---
name: runtime-debug
description: Linux-hosted runtime debugging for OpenHarmony devices. Use when Codex needs to inspect crashes, permission failures, missing shared libraries, or bad runtime behavior over direct `hdc` shell and log collection.
---

# Runtime Debug

Use this skill when an OHOS binary fails after deployment.

## Quick Checks

```bash
hdc -t <device_id> hilog
hdc -t <device_id> shell 'ls /data/log/faultlog/'
hdc -t <device_id> shell 'ldd /data/local/tmp/myapp'
```

## Workflow

1. Collect `hilog` output and any fault logs.
2. Check dynamic library resolution with `ldd`.
3. Check file permissions and execution path under `/data/local/tmp`.
4. If the failure smells like access control or session policy, hand off to `ohos-permission`.

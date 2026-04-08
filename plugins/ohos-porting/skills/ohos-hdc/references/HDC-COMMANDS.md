# HDC Command Reference

Linux-only HDC reference for direct `hdc_std` or `hdc` use.

## Device discovery

```bash
hdc list targets
hdc list targets -v
```

## Common commands

```bash
hdc -t <device_id> shell 'uname -a'
hdc -t <device_id> file send ./artifact /data/local/tmp/
hdc -t <device_id> file recv /data/log/faultlog ./faultlog
hdc -t <device_id> hilog
hdc -t <device_id> install ./app.hap
```

Always provide `-t <device_id>` when more than one target is attached.

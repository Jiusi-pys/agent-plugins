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
hdc -t <device_id> shell 'ls -lh /data/local/tmp'
hdc -t <device_id> shell 'ldd /data/local/tmp/myapp'
```

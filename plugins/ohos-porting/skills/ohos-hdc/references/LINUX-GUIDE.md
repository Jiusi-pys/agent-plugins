# Native Linux HDC Guide

This guide assumes a Linux host and direct device access over USB or TCP.

## Quick Start

```bash
./scripts/linux/install-hdc.sh /opt/command-line-tools
sudo ./scripts/linux/setup-udev.sh
./scripts/hdc-auto.sh list targets
```

## Notes

- Prefer `hdc_std`; fall back to `hdc`.
- `scripts/linux/install-hdc.sh` verifies Linux host assumptions and reports whether `hdc_std` or `hdc` is already available on `PATH`; it does not download the bundle for you.
- Use `scripts/linux/select-device.sh` when multiple devices are attached.
- Use `/data/local/tmp` for temporary binaries and test payloads.

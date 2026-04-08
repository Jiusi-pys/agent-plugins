# Native Linux HDC Guide

This guide assumes a Linux host and direct device access over USB or TCP.

## Quick Start

```bash
./scripts/linux/install-hdc.sh
sudo ./scripts/linux/setup-udev.sh
hdc list targets
```

## Notes

- Prefer `hdc_std`; fall back to `hdc`.
- Use `scripts/linux/select-device.sh` when multiple devices are attached.
- Use `/data/local/tmp` for temporary binaries and test payloads.

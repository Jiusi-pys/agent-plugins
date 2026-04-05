# Native Linux HDC Guide

## Overview

Use this guide when running on native Linux instead of WSL. The supported Codex-facing workflow is:

1. Install `hdc` or `hdc_std` on the host.
2. Configure USB access with udev rules if you are using a USB-connected device.
3. Run device operations through `./scripts/device-control.sh`.

## Requirements

- Ubuntu 18.04+ / Debian 10+ / similar Linux distribution
- `bash`
- USB access for direct device connections
- `sudo` only when editing udev rules

## Install HDC

### Option 1: Use an existing package or SDK install

If your environment already ships `hdc` or `hdc_std`, add it to `PATH` and verify:

```bash
command -v hdc_std || command -v hdc
hdc version || hdc_std version
```

### Option 2: Extract HDC from the OpenHarmony SDK

1. Download the Linux SDK/toolchain bundle from the OpenHarmony release assets.
2. Extract the `toolchains/hdc` or `toolchains/hdc_std` binary.
3. Put it somewhere stable, for example `~/.local/bin`.

```bash
mkdir -p ~/.local/bin
cp toolchains/hdc ~/.local/bin/hdc
chmod +x ~/.local/bin/hdc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## USB Access on Linux

If `hdc list targets` works only under `sudo`, add a udev rule.

1. Create `/etc/udev/rules.d/51-openharmony.rules`.
2. Add rules for the device vendor IDs you use most often.
3. Reload udev and reconnect the device.

Example:

```udev
SUBSYSTEM=="usb", ATTR{idVendor}=="12d1", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="2207", MODE="0666", GROUP="plugdev"
```

Apply the change:

```bash
sudo groupadd -f plugdev
sudo usermod -aG plugdev "$USER"
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then log out and back in before retesting.

To discover the vendor ID:

```bash
lsusb
```

## Preferred Workflow

Use the repository wrapper instead of raw `hdc` when possible.

### List devices

```bash
./scripts/device-control.sh list targets
```

### Run a shell command

```bash
./scripts/device-control.sh -t <device_id> shell "uname -a"
```

### Send and receive files

```bash
./scripts/device-control.sh -t <device_id> file send ./artifact /data/local/tmp/
./scripts/device-control.sh -t <device_id> file recv /data/local/tmp/artifact ./artifact
```

### Collect logs

```bash
./scripts/device-control.sh -t <device_id> hilog
```

## Raw HDC Equivalents

If you need a command the wrapper does not cover cleanly, run raw `hdc` or `hdc_std`:

```bash
hdc list targets
hdc -t <device_id> shell
hdc -t <device_id> file send ./local /data/local/tmp/
hdc -t <device_id> hilog
```

## Troubleshooting

### `hdc` not found

- Verify the binary is on `PATH`.
- On Linux, `device-control.sh` prefers `hdc_std` first, then `hdc`.

### No devices listed

- Reconnect the USB cable.
- Confirm the device is in developer/debug mode.
- Recheck your udev rules and group membership.

### Permission denied on USB devices

- Ensure the user is in `plugdev`.
- Reload udev rules and reconnect the device.
- Test once with `sudo hdc list targets` to confirm it is a host-permission issue.

## Native Linux vs WSL

- Native Linux gives the simplest USB path and best performance.
- WSL should be reserved for environments that already depend on Windows-side `hdc.exe`.

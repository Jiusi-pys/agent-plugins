---
name: hdc-kaihongos
description: HDC (HarmonyOS Device Connector) operations for RK3588S KaihongOS development boards. Auto-detects platform (Linux/Windows/WSL) and uses correct HDC command. Use when: (1) Executing shell commands on KaihongOS device, (2) Transferring files between host and device, (3) Managing device connections and ports, (4) Installing/uninstalling OpenHarmony applications (.hap/.hsp), (5) Debugging device logs and processes, (6) Port forwarding for remote debugging. Supports: Native Linux (hdc_std), Windows (hdc), WSL (powershell.exe wrapper). CRITICAL: Multi-device scenarios require -t parameter for device selection.
---

# HDC KaihongOS Operations

HDC commands for interacting with RK3588S KaihongOS devices. **Supports multiple platforms with automatic detection.**

## For Claude Agents: Use `device-control.sh` (Recommended)

Claude agents should use `device-control.sh` for all device operations. This wrapper:
- ✅ Automatically detects your platform (Linux/Windows/WSL/macOS)
- ✅ Safely handles complex commands with quotes (no escaping needed)
- ✅ Provides a unified interface regardless of environment
- ✅ **You don't need to think about platform differences**

```bash
# Just use it directly - platform detection is automatic
./scripts/device-control.sh list                              # List devices
./scripts/device-control.sh -t <device_id> shell ls          # Run command
./scripts/device-control.sh -t <device_id> file send app /tmp/   # Push file
./scripts/device-control.sh -t <device_id> hilog             # View logs

# Complex commands work without quote escaping issues
./scripts/device-control.sh -t <id> shell "echo 'hello world' && ls -la"
```

**Why use this?** On WSL with PowerShell, complex commands with mixed quotes (like `hdc shell 'echo "test"'`) cause quote matching errors. This wrapper handles all the escaping automatically.

See `device-control.sh --help` for all available operations.

---

## For Users: Quick Start with Auto Platform Detection

Use `hdc-auto.sh` for automatic platform detection - no need to remember which HDC command to use!

```bash
# Check your platform
./scripts/hdc-auto.sh --platform

# Auto-detect and execute HDC commands
./scripts/hdc-auto.sh list targets
./scripts/hdc-auto.sh -t <device_id> shell
./scripts/hdc-auto.sh file send ./local /remote
```

### Platform Detection Logic

| Platform | Detection | HDC Command |
|----------|-----------|-------------|
| **Native Linux** | `uname -s` = Linux, no Microsoft in /proc/version | `hdc_std` (优先) / `hdc` |
| **Windows** | MINGW/MSYS/CYGWIN | `hdc` / `hdc.exe` |
| **WSL** | Linux + Microsoft in /proc/version | `powershell.exe -c "hdc ..."` |
| **macOS** | Darwin | `hdc_std` / `hdc` |

### Setup Alias (Recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc
alias hdc="./path/to/scripts/hdc-auto.sh"

# Then use normally
hdc list targets
hdc -t \$DEVICE_ID shell
```



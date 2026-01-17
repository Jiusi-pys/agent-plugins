---
name: hdc-kaihongos
description: HDC (HarmonyOS Device Connector) operations for RK3588S KaihongOS development boards. Use when: (1) Executing shell commands on KaihongOS device, (2) Transferring files between host and device, (3) Managing device connections and ports, (4) Installing/uninstalling OpenHarmony applications (.hap/.hsp), (5) Debugging device logs and processes, (6) Port forwarding for remote debugging. Environment: Windows 10 host with PowerShell. CRITICAL: Multi-device scenarios require -t parameter for device selection.
---

# HDC KaihongOS Operations

HDC commands execute via PowerShell on Windows 10 host to interact with RK3588S KaihongOS device.

## CRITICAL: Multi-Device Handling

**ALL commands MUST use `-t <device_id>` to avoid ambiguity.**

```powershell
# Standard pattern for ALL operations
hdc -t <device_id> <command> [options]
```

### Device Discovery

```powershell
# List all connected devices
hdc list targets -v

# Output format:
# <device_id>                         <state>   <type>
# 7001005458323933328a0b3f00000000    device    USB
# 192.168.1.100:5555                  device    TCP
```

### Device Selection Pattern

```powershell
# Store device ID at session start
$DEVICE_ID = (hdc list targets | Select-Object -First 1).Split()[0]

# Or specify explicitly
$DEVICE_ID = "7001005458323933328a0b3f00000000"

# All subsequent commands use $DEVICE_ID
hdc -t $DEVICE_ID shell whoami
hdc -t $DEVICE_ID file send ./app /data/
```

## Core Operations

### Server Management

```powershell
hdc start [-r]           # Start server, -r to restart
hdc kill [-r]            # Kill server, -r to restart
hdc list targets -v      # List devices (no -t needed)
```

### Shell Access

```powershell
# Interactive shell
hdc -t $DEVICE_ID shell

# Single command execution
hdc -t $DEVICE_ID shell <command>

# Examples
hdc -t $DEVICE_ID shell ls -la /system
hdc -t $DEVICE_ID shell "cat /proc/version"
hdc -t $DEVICE_ID shell "ps -ef | grep softbus"
```

### File Transfer

```powershell
# Send to device
hdc -t $DEVICE_ID file send [options] <local_path> <remote_path>

# Receive from device
hdc -t $DEVICE_ID file recv [options] <remote_path> <local_path>

# Options:
#   -a    preserve timestamp
#   -z    compress transfer
#   -sync update newer files only

# Examples
hdc -t $DEVICE_ID file send -z ./build/app /data/local/tmp/app
hdc -t $DEVICE_ID file recv -a /data/log/app.log ./logs/
```

### Application Management

```powershell
# Install HAP/HSP
hdc -t $DEVICE_ID install [-r] <package_path>
#   -r: replace existing

# Uninstall
hdc -t $DEVICE_ID uninstall [-k] <package_name>
#   -k: keep data/cache

# Examples
hdc -t $DEVICE_ID install -r ./MyApp.hap
hdc -t $DEVICE_ID uninstall com.example.myapp
```

### Port Forwarding

```powershell
# Forward local to device
hdc -t $DEVICE_ID fport tcp:<local_port> tcp:<remote_port>

# Reverse forward (device to host)
hdc -t $DEVICE_ID rport tcp:<remote_port> tcp:<local_port>

# List/remove forwards
hdc -t $DEVICE_ID fport ls
hdc -t $DEVICE_ID fport rm <taskstr>

# JDWP debugging
hdc -t $DEVICE_ID fport tcp:5005 jdwp:<pid>
```

### Debugging

```powershell
# Device log stream
hdc -t $DEVICE_ID hilog

# Filtered log
hdc -t $DEVICE_ID hilog | Select-String "dsoftbus"

# Bug report
hdc -t $DEVICE_ID bugreport ./report.txt

# List debuggable processes
hdc -t $DEVICE_ID jpid
```

### System Operations

```powershell
# Mount read-write
hdc -t $DEVICE_ID target mount

# Reboot
hdc -t $DEVICE_ID target boot
hdc -t $DEVICE_ID target boot -recovery
hdc -t $DEVICE_ID target boot -bootloader

# Root mode
hdc -t $DEVICE_ID smode        # Enable root
hdc -t $DEVICE_ID smode -r     # Disable root

# Switch connection mode
hdc -t $DEVICE_ID tmode port 5555   # Enable TCP
hdc -t $DEVICE_ID tmode usb         # USB only
```

## Common Workflows

### Deploy Binary to Specific Device

```powershell
# Select device
$DEVICE_ID = "7001005458323933328a0b3f00000000"

# Mount and deploy
hdc -t $DEVICE_ID target mount
hdc -t $DEVICE_ID file send -z ./build/my_app /system/bin/my_app
hdc -t $DEVICE_ID shell chmod 755 /system/bin/my_app
hdc -t $DEVICE_ID shell /system/bin/my_app
```

### Multi-Device Parallel Deployment

```powershell
# Get all device IDs
$devices = (hdc list targets) -split "`n" | ForEach-Object { $_.Split()[0] } | Where-Object { $_ }

# Deploy to each
foreach ($dev in $devices) {
    Write-Host "Deploying to: $dev"
    hdc -t $dev file send -z ./build/ /data/local/tmp/
    hdc -t $dev shell chmod -R 755 /data/local/tmp/bin/
}
```

### ROS2 rmw_dsoftbus Testing

```powershell
$DEVICE_ID = "your_device_id"

# Deploy library
hdc -t $DEVICE_ID file send ./lib/librmw_dsoftbus.z.so /system/lib64/

# Check dsoftbus service
hdc -t $DEVICE_ID shell "ps -ef | grep softbus"

# Monitor logs
hdc -t $DEVICE_ID hilog | Select-String "(dsoftbus|rmw)"
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "No targets found" | No device / USB issue | Check USB, `hdc kill -r` |
| "Multiple targets" | -t not specified | Use `hdc -t <id>` |
| "Permission denied" | Not root | `hdc -t $id smode` |
| "Target mount failed" | Already mounted | Reboot device |

## WSL Ubuntu Support

For WSL Ubuntu environment, use wrapper scripts in `scripts/wsl/`.

### WSL Architecture

```
WSL Ubuntu                    Windows 10                  KaihongOS Device
    │                              │                            │
    ├─ hdc-wrapper.sh ──────────► powershell.exe ──► hdc.exe ──►│
    │                              │                            │
    ├─ hdc-send.sh:                │                            │
    │   1. cp to /mnt/c/tmp/ ────► C:\tmp\                      │
    │   2. powershell hdc send ──► hdc file send ─────────────► │
    │                              │                            │
    └─ hdc-recv.sh:                │                            │
        1. powershell hdc recv ──► hdc file recv ◄───────────── │
        2. cp from /mnt/c/tmp/ ◄── C:\tmp\                      │
```

### WSL Quick Start

```bash
# 1. Select device
DEVICE_ID=$(./scripts/wsl/select-device.sh)

# 2. Basic commands via wrapper
./scripts/wsl/hdc-wrapper.sh -t $DEVICE_ID shell ls
./scripts/wsl/hdc-wrapper.sh -t $DEVICE_ID hilog

# 3. File transfer (auto staging via /mnt/c/tmp)
./scripts/wsl/hdc-send.sh -t $DEVICE_ID ./build /data/local/tmp/ -z
./scripts/wsl/hdc-recv.sh -t $DEVICE_ID /data/log/app.log ./logs/

# 4. Full deployment
./scripts/wsl/deploy.sh -t $DEVICE_ID -s ./out/rk3588s -d /opt/ros2 -z -c -p
```

### WSL Environment Setup

```bash
# Add to ~/.bashrc
export HDC_DEVICE="your_device_id"
alias hdc='./scripts/wsl/hdc-wrapper.sh'
alias hdc-send='./scripts/wsl/hdc-send.sh'
alias hdc-recv='./scripts/wsl/hdc-recv.sh'

# Or use select-device with export
eval $(./scripts/wsl/select-device.sh --export)
```

### WSL File Transfer Notes

**Critical**: Direct WSL-to-device transfer not supported. All transfers stage through `/mnt/c/tmp/hdc_staging`.

| Operation | Staging Path | Automatic |
|-----------|--------------|-----------|
| Send | WSL → `/mnt/c/tmp` → device | Yes |
| Recv | device → `/mnt/c/tmp` → WSL | Yes |
| Cleanup | Auto-delete after transfer | Yes (use `-k` to keep) |

## References

- [HDC-COMMANDS.md](references/HDC-COMMANDS.md): Complete command reference with all options
- [WORKFLOW-PATTERNS.md](references/WORKFLOW-PATTERNS.md): Advanced automation patterns
- [WSL-GUIDE.md](references/WSL-GUIDE.md): Detailed WSL integration guide

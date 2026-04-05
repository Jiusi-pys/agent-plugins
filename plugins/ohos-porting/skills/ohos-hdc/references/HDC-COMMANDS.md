# HDC Command Reference

Complete command reference for HDC with multi-device support.

## Table of Contents

1. [Global Options](#global-options)
2. [Device Selection](#device-selection)
3. [Session Commands](#session-commands)
4. [Service Commands](#service-commands)
5. [File Commands](#file-commands)
6. [Forward Commands](#forward-commands)
7. [Application Commands](#application-commands)
8. [Debug Commands](#debug-commands)
9. [Security Commands](#security-commands)

## Global Options

| Option | Description |
|--------|-------------|
| `-h/help [verbose]` | Print help, 'verbose' for extended commands |
| `-v/version` | Print HDC version |
| `-t <device_id>` | **REQUIRED for multi-device**: Specify target device |

## Device Selection

### Getting Device ID

```powershell
# List all devices
hdc list targets -v

# Sample output:
# 7001005458323933328a0b3f00000000    device    USB
# 192.168.1.100:5555                  device    TCP
# emulator-5554                       device    TCP
```

### PowerShell Device Selection Patterns

```powershell
# Pattern 1: First available device
$DEVICE_ID = (hdc list targets | Select-Object -First 1).Split()[0]

# Pattern 2: Specific device by partial match
$DEVICE_ID = (hdc list targets | Select-String "7001005").Line.Split()[0]

# Pattern 3: USB device only
$DEVICE_ID = (hdc list targets -v | Select-String "USB").Line.Split()[0]

# Pattern 4: TCP device by IP
$DEVICE_ID = "192.168.1.100:5555"

# Pattern 5: Interactive selection
$devices = @((hdc list targets) -split "`n" | Where-Object { $_ -match '\S' })
for ($i = 0; $i -lt $devices.Count; $i++) {
    Write-Host "[$i] $($devices[$i])"
}
$choice = Read-Host "Select device"
$DEVICE_ID = $devices[$choice].Split()[0]
```

### Verify Selection

```powershell
# Confirm device is responsive
hdc -t $DEVICE_ID shell echo "Connected to $(hostname)"
```

## Session Commands

```powershell
# These do NOT require -t (server-side operations)
hdc list targets [-v]     # List devices, -v for details
hdc start [-r]            # Start server, -r to restart
hdc kill [-r]             # Kill server, -r to restart
```

## Service Commands

All service commands REQUIRE `-t <device_id>`:

### target mount

```powershell
hdc -t $DEVICE_ID target mount
```

Remount `/system` and `/vendor` as read-write.

### target boot

```powershell
hdc -t $DEVICE_ID target boot                # Normal reboot
hdc -t $DEVICE_ID target boot -bootloader    # Bootloader
hdc -t $DEVICE_ID target boot -recovery      # Recovery
hdc -t $DEVICE_ID target boot [MODE]         # Custom mode
```

### smode

```powershell
hdc -t $DEVICE_ID smode       # Enable root
hdc -t $DEVICE_ID smode -r    # Disable root
```

### tmode

```powershell
hdc -t $DEVICE_ID tmode usb           # USB only mode
hdc -t $DEVICE_ID tmode port [port]   # TCP mode (default 5555)
```

## File Commands

### file send

```powershell
hdc -t $DEVICE_ID file send [options] <local> <remote>
```

| Option | Description |
|--------|-------------|
| `-a` | Preserve timestamp |
| `-sync` | Update only if local is newer |
| `-z` | Compress transfer |
| `-m` | Mode sync |

Examples:
```powershell
# Basic send
hdc -t $DEVICE_ID file send ./app /data/local/tmp/app

# Compressed with timestamp
hdc -t $DEVICE_ID file send -a -z ./build/ /data/build/

# Incremental sync
hdc -t $DEVICE_ID file send -sync ./src/ /data/src/
```

### file recv

```powershell
hdc -t $DEVICE_ID file recv [options] <remote> <local>
```

Same options as `file send`.

Examples:
```powershell
# Pull log
hdc -t $DEVICE_ID file recv /data/log/app.log ./logs/

# Pull with compression
hdc -t $DEVICE_ID file recv -z /data/coredump ./crash/
```

## Forward Commands

### fport (local to device)

```powershell
hdc -t $DEVICE_ID fport <local_node> <remote_node>
```

Node formats:

| Schema | Example |
|--------|---------|
| `tcp:<port>` | `tcp:8080` |
| `localfilesystem:<path>` | `localfilesystem:/tmp/sock` |
| `localabstract:<name>` | `localabstract:@mysock` |
| `jdwp:<pid>` | `jdwp:1234` (remote only) |

Examples:
```powershell
# TCP forward
hdc -t $DEVICE_ID fport tcp:8080 tcp:8080

# JDWP debug
$pid = hdc -t $DEVICE_ID shell pidof my_app
hdc -t $DEVICE_ID fport tcp:5005 jdwp:$pid
```

### rport (device to local)

```powershell
hdc -t $DEVICE_ID rport <remote_node> <local_node>
```

### fport management

```powershell
hdc -t $DEVICE_ID fport ls              # List all forwards
hdc -t $DEVICE_ID fport rm <taskstr>    # Remove by task string
```

## Application Commands

### install

```powershell
hdc -t $DEVICE_ID install [-r|-s] <src>
```

| Option | Description |
|--------|-------------|
| `-r` | Replace existing |
| `-s` | Install as shared bundle |

`src` accepts: `.hap`, `.hsp`, multiple packages, directories.

Examples:
```powershell
hdc -t $DEVICE_ID install ./MyApp.hap
hdc -t $DEVICE_ID install -r ./MyApp.hap
hdc -t $DEVICE_ID install ./packages/
```

### uninstall

```powershell
hdc -t $DEVICE_ID uninstall [-k] [-s] <package>
```

| Option | Description |
|--------|-------------|
| `-k` | Keep data/cache |
| `-s` | Remove shared bundle |

## Debug Commands

### hilog

```powershell
hdc -t $DEVICE_ID hilog [-h]
```

Filter patterns:
```powershell
# By keyword
hdc -t $DEVICE_ID hilog | Select-String "MyApp"

# By level (E=Error, W=Warn, I=Info, D=Debug)
hdc -t $DEVICE_ID hilog | Select-String "\sE/"

# Multiple patterns
hdc -t $DEVICE_ID hilog | Select-String "(ERROR|dsoftbus|rmw)"

# Save to file
hdc -t $DEVICE_ID hilog > ./device.log
```

### shell

```powershell
# Interactive
hdc -t $DEVICE_ID shell

# Command execution
hdc -t $DEVICE_ID shell <command>
hdc -t $DEVICE_ID shell "ls -la /data"
hdc -t $DEVICE_ID shell "cat /proc/version"
```

### bugreport

```powershell
hdc -t $DEVICE_ID bugreport [FILE]
```

### jpid

```powershell
hdc -t $DEVICE_ID jpid
```

List PIDs with JDWP transport.

## Security Commands

### keygen

```powershell
hdc keygen <FILE>    # No -t needed (local operation)
```

Creates `FILE` (private) and `FILE.pub` (public).

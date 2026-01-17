# Workflow Patterns

Advanced HDC workflow patterns for multi-device RK3588S KaihongOS development.

## Table of Contents

1. [Device Selection Strategies](#device-selection-strategies)
2. [Development Environment Setup](#development-environment-setup)
3. [Cross-compilation Deployment](#cross-compilation-deployment)
4. [ROS2 rmw_dsoftbus Development](#ros2-rmw_dsoftbus-development)
5. [Remote Debugging](#remote-debugging)
6. [Multi-Device Operations](#multi-device-operations)
7. [Automation Scripts](#automation-scripts)

## Device Selection Strategies

### Session Initialization Pattern

```powershell
# Always start scripts with device selection
function Get-HdcDevice {
    param(
        [string]$Hint = ""
    )
    
    $devices = @((hdc list targets) -split "`n" | Where-Object { $_ -match '\S' })
    
    if ($devices.Count -eq 0) {
        throw "No devices connected"
    }
    
    if ($devices.Count -eq 1) {
        return $devices[0].Split()[0]
    }
    
    # Multiple devices - require selection
    if ($Hint) {
        $match = $devices | Where-Object { $_ -match $Hint }
        if ($match) {
            return $match.Split()[0]
        }
    }
    
    Write-Host "Multiple devices found:"
    for ($i = 0; $i -lt $devices.Count; $i++) {
        Write-Host "  [$i] $($devices[$i])"
    }
    $choice = Read-Host "Select device"
    return $devices[$choice].Split()[0]
}

# Usage
$DEVICE_ID = Get-HdcDevice
# Or with hint
$DEVICE_ID = Get-HdcDevice -Hint "USB"
```

### Environment Variable Pattern

```powershell
# Set once per terminal session
$env:HDC_DEVICE = "7001005458323933328a0b3f00000000"

# Helper function
function hdc-exec {
    if (-not $env:HDC_DEVICE) {
        throw "HDC_DEVICE not set. Run: `$env:HDC_DEVICE = <device_id>"
    }
    hdc -t $env:HDC_DEVICE @args
}

# Usage
hdc-exec shell ls
hdc-exec file send ./app /data/
```

## Development Environment Setup

### Initial Device Configuration

```powershell
# 1. Select device
$DEVICE_ID = (hdc list targets | Select-Object -First 1).Split()[0]
Write-Host "Using device: $DEVICE_ID"

# 2. Verify connection
hdc -t $DEVICE_ID shell echo "Device OK"

# 3. Enable root
hdc -t $DEVICE_ID smode

# 4. Mount partitions
hdc -t $DEVICE_ID target mount

# 5. Optional: Enable TCP for wireless dev
hdc -t $DEVICE_ID tmode port 5555
# After reboot, connect via: hdc -t <ip>:5555
```

### WSL-Windows-Device Bridge

```powershell
# hdc-bridge.ps1 - Call from WSL
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceId,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Command
)
& hdc.exe -t $DeviceId @Command
```

From WSL:
```bash
# Execute via PowerShell
powershell.exe -File /mnt/c/tools/hdc-bridge.ps1 -DeviceId "7001005..." shell ls
```

## Cross-compilation Deployment

### Standard Deploy Workflow

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceId,
    [string]$BuildDir = ".\out\rk3588s",
    [string]$DeviceDir = "/data/local/tmp/ros2"
)

# Clean previous
hdc -t $DeviceId shell "rm -rf $DeviceDir"
hdc -t $DeviceId shell "mkdir -p $DeviceDir"

# Deploy
hdc -t $DeviceId file send -z $BuildDir $DeviceDir

# Set permissions
hdc -t $DeviceId shell "chmod -R 755 $DeviceDir/bin"
hdc -t $DeviceId shell "chmod -R 755 $DeviceDir/lib"

Write-Host "Deployed to $DeviceId:$DeviceDir"
```

### Incremental Deploy

```powershell
# Sync only changed files
hdc -t $DEVICE_ID file send -sync $BUILD_DIR $DEVICE_DIR
```

### Library Hot-reload

```powershell
# Quick iteration on specific library
$DEVICE_ID = "your_device_id"

hdc -t $DEVICE_ID file send .\lib\librmw_dsoftbus.z.so /system/lib64/
hdc -t $DEVICE_ID shell "sync"

# Restart dependent process
hdc -t $DEVICE_ID shell "pkill -f ros2_node"
hdc -t $DEVICE_ID shell "/opt/ros2/bin/ros2_node &"
```

## ROS2 rmw_dsoftbus Development

### Environment Setup

```powershell
$DEVICE_ID = "your_device_id"

# Set ROS2 environment
hdc -t $DEVICE_ID shell "export RMW_IMPLEMENTATION=rmw_dsoftbus_cpp"
hdc -t $DEVICE_ID shell "export ROS_DOMAIN_ID=0"

# Verify dsoftbus
hdc -t $DEVICE_ID shell "ps -ef | grep softbus"
hdc -t $DEVICE_ID shell "cat /proc/\$(pidof softbus_server)/status"
```

### Deploy rmw_dsoftbus

```powershell
$DEVICE_ID = "your_device_id"
$RMW_PKG = ".\install\rmw_dsoftbus_cpp"

hdc -t $DEVICE_ID target mount
hdc -t $DEVICE_ID file send -z $RMW_PKG /opt/ros2/
hdc -t $DEVICE_ID shell "echo '/opt/ros2/lib' >> /etc/ld.so.conf"
hdc -t $DEVICE_ID shell "ldconfig"
```

### Two-Device Communication Test

```powershell
# Device A: Publisher
$DEV_A = "device_a_id"
$DEV_B = "device_b_id"

# Start publisher on A
Start-Job -ScriptBlock {
    param($dev)
    hdc -t $dev shell "/opt/ros2/bin/ros2 run demo_nodes_cpp talker"
} -ArgumentList $DEV_A

# Start subscriber on B
hdc -t $DEV_B shell "/opt/ros2/bin/ros2 run demo_nodes_cpp listener"
```

### Debug dsoftbus Layer

```powershell
$DEVICE_ID = "your_device_id"

# Monitor dsoftbus logs
hdc -t $DEVICE_ID hilog | Select-String "(dsoftbus|softbus|Session|Discovery)"

# Check socket status
hdc -t $DEVICE_ID shell "netstat -anp | grep softbus"

# Trace system calls
hdc -t $DEVICE_ID shell "strace -f -e network /opt/ros2/bin/ros2 topic list 2>&1"
```

## Remote Debugging

### GDB Server

```powershell
$DEVICE_ID = "your_device_id"

# Start gdbserver on device
hdc -t $DEVICE_ID shell "gdbserver :5000 /path/to/executable"

# Forward port
hdc -t $DEVICE_ID fport tcp:5000 tcp:5000

# From host GDB:
# (gdb) target remote localhost:5000
```

### JDWP Debug

```powershell
$DEVICE_ID = "your_device_id"

# Get debuggable process PID
$pid = hdc -t $DEVICE_ID shell "pidof my_java_app"

# Setup forward
hdc -t $DEVICE_ID fport tcp:5005 jdwp:$pid

# Connect IDE to localhost:5005
```

### Core Dump Collection

```powershell
$DEVICE_ID = "your_device_id"

# Enable core dumps
hdc -t $DEVICE_ID shell "ulimit -c unlimited"
hdc -t $DEVICE_ID shell "echo '/data/coredump/core.%e.%p' > /proc/sys/kernel/core_pattern"
hdc -t $DEVICE_ID shell "mkdir -p /data/coredump"

# After crash
hdc -t $DEVICE_ID file recv -z /data/coredump/ .\crash\
```

## Multi-Device Operations

### Parallel Deployment

```powershell
$BUILD_DIR = ".\build"
$TARGET_DIR = "/data/local/tmp"

# Get all devices
$devices = @((hdc list targets) -split "`n" | ForEach-Object { $_.Split()[0] } | Where-Object { $_ })

Write-Host "Deploying to $($devices.Count) devices..."

# Parallel jobs
$jobs = foreach ($dev in $devices) {
    Start-Job -ScriptBlock {
        param($device, $src, $dst)
        hdc -t $device file send -z $src $dst
        hdc -t $device shell "chmod -R 755 $dst"
        return "Deployed to $device"
    } -ArgumentList $dev, $BUILD_DIR, $TARGET_DIR
}

# Wait and collect results
$jobs | Wait-Job | ForEach-Object {
    Receive-Job $_
    Remove-Job $_
}
```

### Device-Specific Configuration

```powershell
# config.json
# {
#   "devices": {
#     "dev_board_1": { "id": "700100...", "role": "publisher" },
#     "dev_board_2": { "id": "700200...", "role": "subscriber" }
#   }
# }

$config = Get-Content .\config.json | ConvertFrom-Json

foreach ($name in $config.devices.PSObject.Properties.Name) {
    $dev = $config.devices.$name
    Write-Host "Configuring $name ($($dev.role))..."
    
    hdc -t $dev.id shell "echo 'ROLE=$($dev.role)' > /etc/node.conf"
}
```

### Synchronized Test Execution

```powershell
$devices = @("device_1_id", "device_2_id")

# Prepare all devices
foreach ($dev in $devices) {
    hdc -t $dev file send -z .\test\ /data/test/
}

# Start test simultaneously
$jobs = foreach ($dev in $devices) {
    Start-Job -ScriptBlock {
        param($device)
        $result = hdc -t $device shell "/data/test/run.sh"
        return @{ Device = $device; Output = $result }
    } -ArgumentList $dev
}

# Collect results
$results = $jobs | Wait-Job | ForEach-Object {
    $r = Receive-Job $_
    Remove-Job $_
    $r
}

# Analyze
$results | ForEach-Object {
    Write-Host "=== $($_.Device) ===" -ForegroundColor Cyan
    Write-Host $_.Output
}
```

## Automation Scripts

### Complete Deploy-Test Cycle

```powershell
# deploy-test.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceId,
    [string]$BuildDir = ".\build",
    [int]$Iterations = 1
)

$ErrorActionPreference = "Stop"

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "`n=== Iteration $i/$Iterations ===" -ForegroundColor Cyan
    
    # Deploy
    Write-Host "[*] Deploying..." -ForegroundColor Yellow
    hdc -t $DeviceId file send -z $BuildDir /data/test/
    
    # Run test
    Write-Host "[*] Running tests..." -ForegroundColor Yellow
    $result = hdc -t $DeviceId shell "/data/test/run_tests.sh"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Test failed" -ForegroundColor Red
        hdc -t $DeviceId bugreport ".\crash\bugreport_$i.txt"
        exit 1
    }
    
    Write-Host "[+] Pass" -ForegroundColor Green
    Start-Sleep -Seconds 1
}

Write-Host "`nAll $Iterations iterations passed" -ForegroundColor Green
```

### Watchdog Monitor

```powershell
# watchdog.ps1 - Restart process if it crashes
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceId,
    [string]$ProcessName = "ros2_node",
    [string]$StartCommand = "/opt/ros2/bin/ros2_node",
    [int]$CheckInterval = 5
)

Write-Host "Monitoring $ProcessName on $DeviceId..."

while ($true) {
    $pid = hdc -t $DeviceId shell "pidof $ProcessName" 2>$null
    
    if (-not $pid) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Process died, restarting..." -ForegroundColor Yellow
        hdc -t $DeviceId shell "$StartCommand &"
        Start-Sleep -Seconds 2
    }
    
    Start-Sleep -Seconds $CheckInterval
}
```

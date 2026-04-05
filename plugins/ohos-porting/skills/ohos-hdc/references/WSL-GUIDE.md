# WSL Integration Guide

Detailed guide for using HDC from WSL Ubuntu to interact with KaihongOS devices.

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Script Reference](#script-reference)
4. [File Transfer](#file-transfer)
5. [Common Workflows](#common-workflows)
6. [Troubleshooting](#troubleshooting)

## Architecture

### Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   WSL Ubuntu    │     │   Windows 10     │     │   KaihongOS     │
│                 │     │                  │     │   (RK3588S)     │
│ ./hdc-wrapper.sh├────►│ powershell.exe   │     │                 │
│                 │     │       │          │     │                 │
│                 │     │       ▼          │     │                 │
│                 │     │   hdc.exe ───────┼────►│   HDC Daemon    │
│                 │     │                  │ USB │                 │
│ /mnt/c/tmp/     │◄───►│ C:\tmp\          │     │                 │
│ hdc_staging/    │     │ hdc_staging\     │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Component Responsibilities

| Component | Role |
|-----------|------|
| `hdc-wrapper.sh` | Translates WSL calls to PowerShell |
| `powershell.exe` | Bridges WSL to Windows executables |
| `hdc.exe` | Windows HDC client (on Windows) |
| `/mnt/c/tmp/` | File staging area (WSL view) |
| `C:\tmp\` | File staging area (Windows view) |

## Prerequisites

### Windows Side

1. HDC installed and in PATH
2. Device connected via USB
3. Staging directory accessible: `C:\tmp\hdc_staging`

```powershell
# Verify on Windows
hdc list targets -v
mkdir C:\tmp\hdc_staging
```

### WSL Side

1. WSL2 recommended (better interop)
2. Access to `/mnt/c/` mount
3. Scripts executable

```bash
# Verify WSL
ls /mnt/c/
powershell.exe -Command "echo OK"

# Make scripts executable
chmod +x scripts/wsl/*.sh
```

## Script Reference

### hdc-wrapper.sh

Basic HDC command wrapper.

```bash
# Syntax
./hdc-wrapper.sh [hdc_options] <command> [args...]

# Examples
./hdc-wrapper.sh list targets -v
./hdc-wrapper.sh -t $DEVICE_ID shell ls
./hdc-wrapper.sh -t $DEVICE_ID hilog

# With environment variable
export HDC_DEVICE="7001005..."
./hdc-wrapper.sh shell ls  # Auto-adds -t
```

### select-device.sh

Interactive device selector.

```bash
# Interactive selection
DEVICE_ID=$(./select-device.sh)

# Auto-select first
DEVICE_ID=$(./select-device.sh --first)

# Filter by type
DEVICE_ID=$(./select-device.sh --hint USB)

# Export to environment
eval $(./select-device.sh --export)
echo $HDC_DEVICE
```

### hdc-send.sh

Send files from WSL to device via staging.

```bash
# Syntax
./hdc-send.sh -t <device_id> <local_path> <remote_path> [options]

# Options
#   -z    Compress transfer
#   -a    Preserve timestamp
#   -k    Keep staging files

# Examples
./hdc-send.sh -t $DEVICE_ID ./build /data/local/tmp/ -z
./hdc-send.sh -t $DEVICE_ID ./lib/libfoo.so /system/lib64/ -a
./hdc-send.sh -t $DEVICE_ID ./config/ /etc/myapp/ -k  # Keep staging for debug
```

### hdc-recv.sh

Receive files from device to WSL via staging.

```bash
# Syntax
./hdc-recv.sh -t <device_id> <remote_path> <local_path> [options]

# Options
#   -z    Compress transfer
#   -a    Preserve timestamp
#   -k    Keep staging files

# Examples
./hdc-recv.sh -t $DEVICE_ID /data/log/app.log ./logs/
./hdc-recv.sh -t $DEVICE_ID /data/coredump ./crash/ -z
```

### deploy.sh

Full deployment workflow.

```bash
# Syntax
./deploy.sh -t <device_id> [options]

# Options
#   -s <path>   Source directory (default: ./build)
#   -d <path>   Device destination (default: /data/local/tmp)
#   -z          Compress transfer
#   -c          Clean destination before deploy
#   -p          Set executable permissions

# Examples
./deploy.sh -t $DEVICE_ID -s ./out/rk3588s -d /opt/ros2 -z -c -p
./deploy.sh -t $DEVICE_ID -s ./lib -d /system/lib64 -z
```

### hilog-monitor.sh

Monitor device logs.

```bash
# Syntax
./hilog-monitor.sh -t <device_id> [options]

# Options
#   -f <pattern>  Filter regex
#   -l <level>    Log level (D/I/W/E/F)
#   -g <tag>      Filter by tag
#   -o <file>     Output to file
#   -d <seconds>  Duration
#   -c            Clear logs first

# Examples
./hilog-monitor.sh -t $DEVICE_ID -f "dsoftbus|rmw" -l E
./hilog-monitor.sh -t $DEVICE_ID -g ROS2 -o ./ros2.log -d 60 -c
```

## File Transfer

### Staging Mechanism

All file transfers use `/mnt/c/tmp/hdc_staging` as intermediate storage:

```
Send:
  1. cp <WSL_file> /mnt/c/tmp/hdc_staging/stage_xxx/
  2. powershell hdc file send C:\tmp\hdc_staging\stage_xxx\<file> <remote>
  3. rm -rf /mnt/c/tmp/hdc_staging/stage_xxx/

Recv:
  1. powershell hdc file recv <remote> C:\tmp\hdc_staging\stage_xxx\
  2. cp /mnt/c/tmp/hdc_staging/stage_xxx/* <WSL_dest>
  3. rm -rf /mnt/c/tmp/hdc_staging/stage_xxx/
```

### Large File Considerations

For large transfers (>100MB):
- Use `-z` compression
- Consider splitting into chunks
- Monitor staging directory space

```bash
# Check staging space
df -h /mnt/c/tmp

# Clean old staging if needed
rm -rf /mnt/c/tmp/hdc_staging/stage_*
```

### Preserving Permissions

WSL-to-Windows-to-device transfer loses Unix permissions. Use `-p` flag with deploy.sh or set manually:

```bash
# After transfer
./hdc-wrapper.sh -t $DEVICE_ID shell "chmod 755 /data/app/my_binary"
./hdc-wrapper.sh -t $DEVICE_ID shell "chmod -R 755 /data/app/bin/"
```

## Common Workflows

### Development Cycle

```bash
# Setup (once per session)
DEVICE_ID=$(./scripts/wsl/select-device.sh)
export DEVICE_ID

# Build (in WSL)
cd ~/ros2_ws
colcon build

# Deploy
./scripts/wsl/deploy.sh -t $DEVICE_ID -s ./install -d /opt/ros2 -z -c -p

# Test
./scripts/wsl/hdc-wrapper.sh -t $DEVICE_ID shell "/opt/ros2/bin/my_node"

# Monitor logs
./scripts/wsl/hilog-monitor.sh -t $DEVICE_ID -f "my_node"
```

### Debug Session

```bash
# Clear and start fresh
./scripts/wsl/hdc-wrapper.sh -t $DEVICE_ID shell "rm -rf /data/log/*"
./scripts/wsl/hilog-monitor.sh -t $DEVICE_ID -c -o ./debug.log &

# Run test
./scripts/wsl/hdc-wrapper.sh -t $DEVICE_ID shell "/opt/ros2/bin/test_node"

# Collect results
./scripts/wsl/hdc-recv.sh -t $DEVICE_ID /data/log ./logs/ -z
```

### Multi-Device (Two Terminals)

Terminal 1 (Publisher):
```bash
DEVICE_A=$(./scripts/wsl/select-device.sh --hint "7001005")
./scripts/wsl/hdc-wrapper.sh -t $DEVICE_A shell \
    "/opt/ros2/bin/ros2 run demo_nodes_cpp talker"
```

Terminal 2 (Subscriber):
```bash
DEVICE_B=$(./scripts/wsl/select-device.sh --hint "7002005")
./scripts/wsl/hdc-wrapper.sh -t $DEVICE_B shell \
    "/opt/ros2/bin/ros2 run demo_nodes_cpp listener"
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `powershell.exe: command not found` | PATH issue | Use full path: `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe` |
| `hdc: command not found` | HDC not in Windows PATH | Set `HDC_PATH` env or use full path |
| `/mnt/c` not accessible | Drive not mounted | Check `/etc/wsl.conf`, restart WSL |
| Slow transfers | No compression | Use `-z` flag |
| Permission denied | Staging dir issue | `mkdir -p /mnt/c/tmp/hdc_staging` |

### Debugging

```bash
# Verify PowerShell access
powershell.exe -Command "echo 'PowerShell OK'"

# Verify HDC access
powershell.exe -Command "hdc version"

# Verify staging
ls -la /mnt/c/tmp/hdc_staging/

# Manual staging test
cp ./test_file /mnt/c/tmp/
powershell.exe -Command "hdc -t '$DEVICE_ID' file send 'C:\tmp\test_file' '/data/test'"
```

### Performance Tips

1. **Use WSL2**: Better file system performance
2. **Compress large transfers**: Always use `-z` for >10MB
3. **Batch operations**: Deploy once rather than multiple small transfers
4. **Local staging**: Keep staging in `/mnt/c/tmp`, not network drives

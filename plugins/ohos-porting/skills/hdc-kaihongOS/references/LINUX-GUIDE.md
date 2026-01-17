# Native Linux HDC Guide

## Overview

本指南介绍如何在原生 Ubuntu/Linux 系统上安装和使用 HDC (OpenHarmony Device Connector)。

## System Requirements

- Ubuntu 18.04+ / Debian 10+ / 其他基于 apt 的发行版
- x86_64 或 aarch64 架构
- USB 端口 (用于连接设备)
- sudo 权限 (用于 udev 规则配置)

## Installation

### Quick Install

```bash
# 1. 安装 HDC
./scripts/linux/install-hdc.sh

# 2. 配置 USB 权限 (需要 sudo)
sudo ./scripts/linux/setup-udev.sh

# 3. 重新加载 shell 配置
source ~/.bashrc

# 4. 测试连接
hdc list targets
```

### Manual Installation

如果自动安装失败，可以手动安装：

1. **下载 OpenHarmony SDK**:
   - 访问 [OpenHarmony Release Notes](https://gitee.com/openharmony/docs/tree/master/zh-cn/release-notes)
   - 下载 "Public SDK package for the standard system" (Linux 版本)

2. **提取 HDC**:
   ```bash
   unzip toolchains-linux-x64-*.zip
   mkdir -p ~/.local/bin
   cp toolchains/hdc ~/.local/bin/
   chmod +x ~/.local/bin/hdc
   ```

3. **配置 PATH**:
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

4. **配置 USB 权限**:
   ```bash
   sudo ./scripts/linux/setup-udev.sh
   ```

## USB Permissions (udev Rules)

Linux 系统需要配置 udev 规则才能让普通用户访问 USB 设备。

### Automatic Setup

```bash
sudo ./scripts/linux/setup-udev.sh
```

### Manual Setup

1. 创建规则文件:
   ```bash
   sudo vim /etc/udev/rules.d/51-openharmony.rules
   ```

2. 添加以下内容:
   ```
   # Huawei / OpenHarmony devices
   SUBSYSTEM=="usb", ATTR{idVendor}=="12d1", MODE="0666", GROUP="plugdev"
   
   # Rockchip devices (RK3568, RK3588)
   SUBSYSTEM=="usb", ATTR{idVendor}=="2207", MODE="0666", GROUP="plugdev"
   ```

3. 重新加载规则:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. 将用户添加到 plugdev 组:
   ```bash
   sudo usermod -aG plugdev $USER
   # 重新登录生效
   ```

### Finding Your Device Vendor ID

如果设备未被识别:

```bash
# 列出 USB 设备
lsusb

# 输出示例:
# Bus 001 Device 005: ID 2207:0006 Fuzhou Rockchip Electronics Company

# 2207 就是 Vendor ID
```

然后添加对应规则:
```bash
sudo ./scripts/linux/setup-udev.sh add-vendor 2207
```

## Basic Usage

### List Devices

```bash
hdc list targets
```

### Shell Access

```bash
# 单设备
hdc shell

# 多设备 (指定设备)
hdc -t <device_id> shell

# 执行单个命令
hdc -t <device_id> shell ls -la /system
```

### File Transfer

```bash
# 发送文件到设备
hdc -t <device_id> file send ./local_file /data/local/tmp/

# 从设备接收文件
hdc -t <device_id> file recv /data/log/app.log ./

# 使用脚本 (自动选择设备)
./scripts/linux/deploy.sh ./build/app /data/local/tmp/
```

### Log Monitoring

```bash
# 查看实时日志
hdc -t <device_id> hilog

# 使用脚本 (带过滤和颜色)
./scripts/linux/hilog-monitor.sh -f "myapp"
./scripts/linux/hilog-monitor.sh -l ERROR
```

## Scripts Reference

| Script | Description |
|--------|-------------|
| `install-hdc.sh` | 安装 HDC |
| `setup-udev.sh` | 配置 USB 权限 |
| `hdc-wrapper.sh` | HDC 命令包装器 |
| `deploy.sh` | 文件部署脚本 |
| `hilog-monitor.sh` | 日志监控脚本 |
| `select-device.sh` | 设备选择脚本 |

## Troubleshooting

### "No targets found"

1. 检查设备是否连接:
   ```bash
   lsusb | grep -i "rockchip\|huawei\|openharmony"
   ```

2. 检查 udev 规则:
   ```bash
   sudo ./scripts/linux/setup-udev.sh verify
   ```

3. 重启 HDC 服务:
   ```bash
   hdc kill
   hdc start
   ```

4. 重新插拔 USB 线

### "Permission denied"

- 确保 udev 规则已配置
- 确保用户在 plugdev 组中
- 重新登录或重启

### Device connected but not listed

1. 检查设备是否在调试模式
2. 检查 USB 线是否支持数据传输 (非仅充电线)
3. 尝试其他 USB 端口

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HDC_CMD` | HDC 可执行文件路径 | `hdc` |
| `HDC_TARGET` | 默认设备 ID | - |
| `HDC_INSTALL_DIR` | HDC 安装目录 | `~/.local/share/hdc` |
| `HDC_BIN_DIR` | HDC 可执行文件目录 | `~/.local/bin` |

## Comparison: Native Linux vs WSL

| Feature | Native Linux | WSL |
|---------|-------------|-----|
| USB Access | Direct | Via Windows |
| Performance | Best | Good |
| Setup | udev rules | PowerShell bridge |
| File Transfer | Direct | Staged via /mnt/c |

对于原生 Linux 开发环境，推荐使用 Native Linux 方案以获得最佳性能和最简单的配置。

#!/bin/bash
# ============================================================================
# Device Selection Script for Native Linux
# ============================================================================

set -e

HDC_CMD="\${HDC_CMD:-hdc}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 HDC
if ! command -v "\$HDC_CMD" &>/dev/null; then
    echo -e "\${RED}[ERROR]\${NC} HDC 未安装" >&2
    exit 1
fi

# 获取设备列表
DEVICES=\$(\$HDC_CMD list targets 2>/dev/null | grep -v "^\$" || true)

if [[ -z "\$DEVICES" ]]; then
    echo -e "\${RED}[ERROR]\${NC} 未检测到设备" >&2
    echo "请确保:" >&2
    echo "  1. 设备已连接" >&2
    echo "  2. USB 调试已开启" >&2
    echo "  3. udev 规则已配置 (sudo ./setup-udev.sh)" >&2
    exit 1
fi

DEVICE_COUNT=\$(echo "\$DEVICES" | wc -l)

if [[ \$DEVICE_COUNT -eq 1 ]]; then
    echo "\$DEVICES"
    exit 0
fi

# 多设备选择
echo -e "\${YELLOW}检测到 \$DEVICE_COUNT 个设备:\${NC}" >&2
echo "" >&2

i=1
while IFS= read -r device; do
    # 获取设备信息
    MODEL=\$(\$HDC_CMD -t "\$device" shell getprop ro.product.model 2>/dev/null || echo "Unknown")
    echo -e "  [\$i] \$device (\$MODEL)" >&2
    ((i++))
done <<< "\$DEVICES"

echo "" >&2
echo -n "请选择设备 [1-\$DEVICE_COUNT]: " >&2
read -r choice

if [[ \$choice -lt 1 || \$choice -gt \$DEVICE_COUNT ]] 2>/dev/null; then
    echo -e "\${RED}[ERROR]\${NC} 无效选择" >&2
    exit 1
fi

SELECTED=\$(echo "\$DEVICES" | sed -n "\${choice}p")
echo "\$SELECTED"

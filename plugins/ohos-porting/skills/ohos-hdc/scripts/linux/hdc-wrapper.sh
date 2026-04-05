#!/bin/bash
# ============================================================================
# HDC Wrapper for Native Linux
# ============================================================================
# 提供统一的 HDC 接口，处理设备选择和错误处理
# ============================================================================

set -e

# 配置
HDC_CMD="\${HDC_CMD:-hdc}"
DEFAULT_TIMEOUT=30

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 HDC 是否可用
check_hdc() {
    if ! command -v "\$HDC_CMD" &>/dev/null; then
        echo -e "\${RED}[ERROR]\${NC} HDC 未安装或不在 PATH 中" >&2
        echo "请运行: ./install-hdc.sh" >&2
        exit 1
    fi
}

# 获取设备列表
list_devices() {
    \$HDC_CMD list targets 2>/dev/null | grep -v "^\$" || true
}

# 选择设备
select_device() {
    local devices
    devices=\$(list_devices)
    
    if [[ -z "\$devices" ]]; then
        echo -e "\${RED}[ERROR]\${NC} 未检测到设备" >&2
        echo "请确保:" >&2
        echo "  1. 设备已连接并开启 USB 调试" >&2
        echo "  2. udev 规则已配置 (sudo ./setup-udev.sh)" >&2
        echo "  3. USB 线缆连接正常" >&2
        exit 1
    fi
    
    local count
    count=\$(echo "\$devices" | wc -l)
    
    if [[ \$count -eq 1 ]]; then
        echo "\$devices"
        return 0
    fi
    
    echo -e "\${YELLOW}检测到多个设备:\${NC}" >&2
    local i=1
    while IFS= read -r device; do
        echo "  [\$i] \$device" >&2
        ((i++))
    done <<< "\$devices"
    
    echo -n "请选择设备 [1-\$count]: " >&2
    read -r choice
    
    if [[ \$choice -lt 1 || \$choice -gt \$count ]]; then
        echo -e "\${RED}[ERROR]\${NC} 无效选择" >&2
        exit 1
    fi
    
    echo "\$devices" | sed -n "\${choice}p"
}

# 执行 HDC 命令
run_hdc() {
    local target="\$1"
    shift
    
    if [[ -n "\$target" ]]; then
        \$HDC_CMD -t "\$target" "\$@"
    else
        \$HDC_CMD "\$@"
    fi
}

# 主函数
main() {
    check_hdc
    
    case "\$1" in
        list)
            list_devices
            ;;
        select)
            select_device
            ;;
        *)
            # 透传其他命令
            if [[ -n "\$HDC_TARGET" ]]; then
                run_hdc "\$HDC_TARGET" "\$@"
            else
                \$HDC_CMD "\$@"
            fi
            ;;
    esac
}

main "\$@"

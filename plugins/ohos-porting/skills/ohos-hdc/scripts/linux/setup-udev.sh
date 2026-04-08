#!/bin/bash
# ============================================================================
# HDC USB udev Rules Setup Script
# ============================================================================
# 功能: 配置 udev 规则，使普通用户可以访问 OpenHarmony 设备
# 需要: sudo 权限
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "\${BLUE}[INFO]\${NC} \$1"; }
log_success() { echo -e "\${GREEN}[SUCCESS]\${NC} \$1"; }
log_warn() { echo -e "\${YELLOW}[WARN]\${NC} \$1"; }
log_error() { echo -e "\${RED}[ERROR]\${NC} \$1"; }

UDEV_RULES_FILE="/etc/udev/rules.d/51-openharmony.rules"

# 检查 root 权限
check_root() {
    if [[ \$EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限"
        log_info "请使用: sudo \$0"
        exit 1
    fi
}

# 检测设备 Vendor ID
detect_device() {
    log_info "检测已连接的设备..."
    
    if ! command -v lsusb &>/dev/null; then
        log_warn "lsusb 未安装，安装 usbutils..."
        apt-get update && apt-get install -y usbutils
    fi
    
    echo ""
    echo "当前 USB 设备列表:"
    echo "----------------------------------------"
    lsusb
    echo "----------------------------------------"
    echo ""
    
    # 已知的 OpenHarmony/HarmonyOS 设备 Vendor ID
    KNOWN_VENDORS=(
        "12d1"  # Huawei
        "2717"  # Xiaomi
        "18d1"  # Google (部分设备)
        "1d6b"  # Linux Foundation
        "2a70"  # OnePlus
        "0e8d"  # MediaTek
        "1782"  # Spreadtrum
        "2c7c"  # Quectel
    )
    
    log_info "已知 OpenHarmony 设备 Vendor IDs: \${KNOWN_VENDORS[*]}"
}

# 创建 udev 规则
create_udev_rules() {
    log_info "创建 udev 规则..."
    
    # 获取当前用户组
    if [[ -n "\$SUDO_USER" ]]; then
        USER_GROUP=\$(id -gn "\$SUDO_USER")
    else
        USER_GROUP="plugdev"
    fi
    
    # 检查 plugdev 组是否存在
    if ! getent group plugdev &>/dev/null; then
        log_info "创建 plugdev 组..."
        groupadd plugdev
    fi
    
    # 将用户添加到 plugdev 组
    if [[ -n "\$SUDO_USER" ]]; then
        if ! groups "\$SUDO_USER" | grep -q plugdev; then
            log_info "将用户 \$SUDO_USER 添加到 plugdev 组..."
            usermod -aG plugdev "\$SUDO_USER"
        fi
    fi
    
    # 创建 udev 规则文件
    cat > "\$UDEV_RULES_FILE" << 'RULES'
# ============================================================================
# OpenHarmony / KaihongOS Device udev Rules
# ============================================================================
# 此文件允许普通用户访问 OpenHarmony 设备进行 HDC 调试
# 安装位置: /etc/udev/rules.d/51-openharmony.rules
# ============================================================================

# Huawei devices (including HarmonyOS/OpenHarmony)
SUBSYSTEM=="usb", ATTR{idVendor}=="12d1", MODE="0666", GROUP="plugdev"

# Rockchip devices (RK3568, RK3588, etc.)
SUBSYSTEM=="usb", ATTR{idVendor}=="2207", MODE="0666", GROUP="plugdev"

# Allwinner devices
SUBSYSTEM=="usb", ATTR{idVendor}=="1f3a", MODE="0666", GROUP="plugdev"

# Amlogic devices
SUBSYSTEM=="usb", ATTR{idVendor}=="1b8e", MODE="0666", GROUP="plugdev"

# Generic OpenHarmony device (ADB compatible)
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="plugdev"

# Xiaomi devices
SUBSYSTEM=="usb", ATTR{idVendor}=="2717", MODE="0666", GROUP="plugdev"

# OnePlus devices
SUBSYSTEM=="usb", ATTR{idVendor}=="2a70", MODE="0666", GROUP="plugdev"

# MediaTek devices
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="plugdev"

# Spreadtrum/Unisoc devices
SUBSYSTEM=="usb", ATTR{idVendor}=="1782", MODE="0666", GROUP="plugdev"

# HiSilicon devices
SUBSYSTEM=="usb", ATTR{idVendor}=="12d1", ATTR{idProduct}=="107e", MODE="0666", GROUP="plugdev"

# Generic fallback for any USB device in download/debug mode
# Uncomment if your device is not recognized
# SUBSYSTEM=="usb", MODE="0666", GROUP="plugdev"

# ============================================================================
# 如果您的设备仍未被识别，请执行以下步骤:
# 1. 运行 lsusb 查看设备的 Vendor ID 和 Product ID
# 2. 添加类似规则: SUBSYSTEM=="usb", ATTR{idVendor}=="XXXX", MODE="0666", GROUP="plugdev"
# 3. 重新加载规则: sudo udevadm control --reload-rules && sudo udevadm trigger
# ============================================================================
RULES

    log_success "udev 规则已创建: \$UDEV_RULES_FILE"
}

# 重新加载规则
reload_rules() {
    log_info "重新加载 udev 规则..."
    
    udevadm control --reload-rules
    udevadm trigger
    
    log_success "udev 规则已重新加载"
}

# 添加自定义 Vendor ID
add_custom_vendor() {
    local VENDOR_ID="\$1"
    
    if [[ -z "\$VENDOR_ID" ]]; then
        log_error "请提供 Vendor ID"
        return 1
    fi
    
    # 验证格式
    if ! [[ "\$VENDOR_ID" =~ ^[0-9a-fA-F]{4}\$ ]]; then
        log_error "无效的 Vendor ID 格式，应为 4 位十六进制数"
        return 1
    fi
    
    VENDOR_ID=\$(echo "\$VENDOR_ID" | tr '[:upper:]' '[:lower:]')
    
    # 检查是否已存在
    if grep -q "idVendor}==\"\$VENDOR_ID\"" "\$UDEV_RULES_FILE" 2>/dev/null; then
        log_warn "Vendor ID \$VENDOR_ID 已存在于规则中"
        return 0
    fi
    
    # 添加新规则
    echo "" >> "\$UDEV_RULES_FILE"
    echo "# Custom device (added by user)" >> "\$UDEV_RULES_FILE"
    echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"\$VENDOR_ID\", MODE=\"0666\", GROUP=\"plugdev\"" >> "\$UDEV_RULES_FILE"
    
    log_success "已添加 Vendor ID: \$VENDOR_ID"
    reload_rules
}

# 验证配置
verify_setup() {
    log_info "验证配置..."
    
    if [[ -f "\$UDEV_RULES_FILE" ]]; then
        log_success "udev 规则文件存在"
    else
        log_error "udev 规则文件不存在"
        return 1
    fi
    
    if getent group plugdev &>/dev/null; then
        log_success "plugdev 组存在"
    else
        log_warn "plugdev 组不存在"
    fi
    
    if [[ -n "\$SUDO_USER" ]] && groups "\$SUDO_USER" | grep -q plugdev; then
        log_success "用户 \$SUDO_USER 已在 plugdev 组中"
    else
        log_warn "用户可能不在 plugdev 组中，需要重新登录"
    fi
    
    echo ""
    log_info "测试设备连接:"
    log_info "  1. 重新插拔设备"
    log_info "  2. 运行: hdc list targets"
    echo ""
}

# 显示帮助
show_help() {
    cat << EOF
Usage: sudo \$0 [COMMAND] [OPTIONS]

Commands:
    install             安装 udev 规则 (默认)
    add-vendor ID       添加自定义 Vendor ID
    detect              检测当前 USB 设备
    verify              验证配置
    help                显示帮助

Examples:
    sudo \$0                    # 安装默认规则
    sudo \$0 add-vendor 1234    # 添加自定义 Vendor ID
    sudo \$0 detect             # 检测设备
EOF
}

# 主函数
main() {
    check_root
    
    case "\${1:-install}" in
        install)
            detect_device
            create_udev_rules
            reload_rules
            verify_setup
            ;;
        add-vendor)
            add_custom_vendor "\$2"
            ;;
        detect)
            detect_device
            ;;
        verify)
            verify_setup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: \$1"
            show_help
            exit 1
            ;;
    esac
    
    echo ""
    log_success "配置完成!"
    log_warn "如果您刚被添加到 plugdev 组，需要重新登录才能生效"
}

main "\$@"

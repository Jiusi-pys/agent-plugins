#!/bin/bash
# ============================================================================
# Device Control Wrapper - Platform-Agnostic HDC Operations
# ============================================================================
# 目的: 为 Claude Agent 提供统一的设备控制接口，自动处理平台差异
# 特性:
#   - 自动平台检测 (Linux/Windows/WSL/macOS)
#   - 参数安全处理，避免引号问题
#   - 完整的错误报告
#   - Agent 无需关心运行环境
# ============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# 平台检测
# ============================================================================
detect_platform() {
    if [[ "$(uname -s)" == "Linux" ]]; then
        if grep -qi microsoft /proc/version 2>/dev/null; then
            echo "wsl"
        else
            echo "linux"
        fi
    elif [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$(uname -s)" == CYGWIN* ]]; then
        echo "windows"
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# ============================================================================
# 获取 HDC 可执行文件
# ============================================================================
get_hdc_command() {
    local platform="$1"

    case "$platform" in
        linux|macos)
            if command -v hdc_std &>/dev/null; then
                echo "hdc_std"
            elif command -v hdc &>/dev/null; then
                echo "hdc"
            else
                echo ""
            fi
            ;;
        windows)
            if command -v hdc.exe &>/dev/null; then
                echo "hdc.exe"
            elif command -v hdc &>/dev/null; then
                echo "hdc"
            else
                echo ""
            fi
            ;;
        wsl)
            echo "wsl_powershell"
            ;;
        *)
            echo ""
            ;;
    esac
}

# ============================================================================
# 安全的 PowerShell 执行 (WSL)
# ============================================================================
wsl_execute() {
    local ps_cmd=""
    if command -v powershell.exe &>/dev/null; then
        ps_cmd="powershell.exe"
    elif [[ -f "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" ]]; then
        ps_cmd="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    else
        echo -e "${RED}[ERROR]${NC} PowerShell not found in WSL environment" >&2
        return 1
    fi

    # 构建参数数组，每个参数单独用引号包装
    local ps_args=()
    for arg in "$@"; do
        # 转义单引号: 单引号 -> 两个单引号 (PowerShell 标准)
        arg="${arg//\'/\'\'}"
        ps_args+=("'$arg'")
    done

    # 在 PowerShell 中执行 hdc
    # 使用 & 调用操作符和参数展开，避免所有引号问题
    $ps_cmd -NoProfile -NonInteractive -Command "& hdc $(printf '%s ' "${ps_args[@]}")" 2>&1
}

# ============================================================================
# 主执行函数
# ============================================================================
main() {
    local platform=$(detect_platform)
    local hdc_cmd=$(get_hdc_command "$platform")

    # 验证 HDC 可用性
    if [[ -z "$hdc_cmd" && "$platform" != "wsl" ]]; then
        echo -e "${RED}[ERROR]${NC} HDC not found on $platform platform" >&2
        echo "Platform: $platform" >&2
        echo "Run 'hdc-auto.sh --install' to install HDC" >&2
        return 1
    fi

    # 无参数显示帮助
    if [[ $# -eq 0 ]]; then
        show_help
        return 0
    fi

    # 执行设备命令
    case "$platform" in
        linux|windows|macos)
            # 直接执行，参数自动安全处理
            "$hdc_cmd" "$@"
            ;;
        wsl)
            # WSL: 通过 PowerShell 执行
            wsl_execute "$@"
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} Unsupported platform: $platform" >&2
            return 1
            ;;
    esac
}

# ============================================================================
# 帮助信息
# ============================================================================
show_help() {
    cat << 'EOF'
Device Control Wrapper - Unified Interface for OHOS Device Operations

Usage: device-control.sh <operation> [arguments]

Supported Operations:

  DEVICE LISTING & INFO:
    device-control.sh list              List connected devices
    device-control.sh targets           List device targets
    device-control.sh -t <id> info      Get device info

  SHELL COMMANDS:
    device-control.sh -t <id> shell <cmd>     Execute shell command on device
    device-control.sh -t <id> shell           Enter interactive shell

  FILE TRANSFER:
    device-control.sh -t <id> file send <src> <dst>   Push file to device
    device-control.sh -t <id> file recv <src> <dst>   Pull file from device

  APPLICATION MANAGEMENT:
    device-control.sh -t <id> install <hap>          Install application
    device-control.sh -t <id> uninstall <bundle>     Uninstall application

  PROCESS & DEBUGGING:
    device-control.sh -t <id> hilog                   View device logs
    device-control.sh -t <id> ps                      List processes

  SYSTEM OPERATIONS:
    device-control.sh -t <id> reboot                  Reboot device
    device-control.sh version                         Show HDC version

Examples:

  # List connected devices
  device-control.sh list

  # Execute command on device (id: FA00ABCD01234567)
  device-control.sh -t FA00ABCD01234567 shell ls -la /data/local/tmp

  # Push binary to device
  device-control.sh -t FA00ABCD01234567 file send ./myapp /data/local/tmp/

  # Pull log from device
  device-control.sh -t FA00ABCD01234567 file recv /data/log/system.txt ./

  # Install app
  device-control.sh -t FA00ABCD01234567 install ./app.hap

  # View logs
  device-control.sh -t FA00ABCD01234567 hilog | grep myapp

Platform Detection:

  This script automatically detects your platform:
  - Linux:   Uses hdc_std or hdc
  - Windows: Uses hdc.exe or hdc
  - WSL:     Uses PowerShell to call Windows-side hdc.exe
  - macOS:   Uses hdc_std or hdc

No explicit platform specification needed!

Note: For complex commands with quotes, this wrapper properly escapes them
for PowerShell on WSL, so you don't need to worry about quote matching errors.
EOF
}

# ============================================================================
# Entry Point
# ============================================================================
main "$@"

#!/bin/bash
# ============================================================================
# HDC Auto Platform Detection Script
# ============================================================================
# 功能: 自动检测当前平台并选择正确的 HDC 调用方式
# 支持: Native Linux (hdc_std), Windows (hdc), WSL (powershell.exe 嵌套)
# ============================================================================

set -e

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
        linux)
            # 原生 Linux: 优先使用 hdc_std (OpenHarmony 标准命名)
            if command -v hdc_std &>/dev/null; then
                echo "hdc_std"
            elif [[ -f "$HOME/.local/bin/hdc_std" ]]; then
                echo "$HOME/.local/bin/hdc_std"
            elif command -v hdc &>/dev/null; then
                echo "hdc"
            elif [[ -f "$HOME/.local/bin/hdc" ]]; then
                echo "$HOME/.local/bin/hdc"
            else
                echo ""
            fi
            ;;
        windows)
            # Windows: 使用 hdc 或 hdc.exe
            if command -v hdc &>/dev/null; then
                echo "hdc"
            elif command -v hdc.exe &>/dev/null; then
                echo "hdc.exe"
            else
                echo ""
            fi
            ;;
        wsl)
            # WSL: 返回特殊标记，使用 PowerShell 包装
            echo "wsl_powershell"
            ;;
        macos)
            if command -v hdc_std &>/dev/null; then
                echo "hdc_std"
            elif command -v hdc &>/dev/null; then
                echo "hdc"
            else
                echo ""
            fi
            ;;
        *)
            echo ""
            ;;
    esac
}

# ============================================================================
# WSL PowerShell 包装执行
# ============================================================================
wsl_execute() {
    local args="$@"
    
    # 查找 PowerShell
    local ps_cmd=""
    if command -v powershell.exe &>/dev/null; then
        ps_cmd="powershell.exe"
    elif [[ -f "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" ]]; then
        ps_cmd="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    else
        echo -e "${RED}[ERROR]${NC} PowerShell not found" >&2
        return 1
    fi
    
    # 通过 PowerShell 执行 Windows 侧的 hdc
    $ps_cmd -NoProfile -Command "hdc $args"
}

# ============================================================================
# WSL 文件路径转换
# ============================================================================
convert_wsl_path() {
    local path="$1"
    
    # 如果是 WSL 路径，转换为 Windows 路径
    if [[ "$path" == /mnt/* ]]; then
        # /mnt/c/foo -> C:\foo
        local drive=\$(echo "$path" | cut -d'/' -f3)
        local rest=\$(echo "$path" | cut -d'/' -f4-)
        echo "${drive^^}:\\${rest//\//\\}"
    elif [[ -f "$path" || -d "$path" ]]; then
        # 暂存到 Windows 可访问的路径
        local staging_dir="/mnt/c/tmp/hdc_staging"
        mkdir -p "$staging_dir"
        local filename=\$(basename "$path")
        cp -r "$path" "$staging_dir/$filename"
        echo "C:\\tmp\\hdc_staging\\$filename"
    else
        echo "$path"
    fi
}

# ============================================================================
# 显示帮助
# ============================================================================
show_help() {
    cat << 'HELPEOF'
HDC Auto Platform Detection Script

Usage: hdc-auto.sh [OPTIONS] [HDC_COMMAND] [ARGS...]

自动检测平台并使用正确的 HDC 调用方式:
  - Native Linux (Ubuntu):  hdc_std (优先) / hdc
  - Windows:                hdc / hdc.exe
  - WSL:                    powershell.exe -c "hdc ..."

Options:
    --platform      显示检测到的平台
    --hdc-path      显示 HDC 命令路径
    --install       运行平台特定的安装脚本
    -h, --help      显示帮助

Examples:
    hdc-auto.sh list targets
    hdc-auto.sh -t <device_id> shell
    hdc-auto.sh file send ./local /remote
    hdc-auto.sh --platform

Platform Detection:
    linux       Native Ubuntu/Debian/etc. -> hdc_std
    windows     Windows (Git Bash/MSYS2)  -> hdc
    wsl         WSL Ubuntu                -> powershell.exe hdc
    macos       macOS (experimental)      -> hdc_std/hdc
HELPEOF
}

# ============================================================================
# 安装脚本
# ============================================================================
run_installer() {
    local platform="$1"
    
    case "$platform" in
        linux)
            if [[ -f "$SCRIPT_DIR/linux/install-hdc.sh" ]]; then
                bash "$SCRIPT_DIR/linux/install-hdc.sh"
            else
                echo -e "${YELLOW}[INFO]${NC} 请手动安装 HDC:"
                echo "  1. 下载 OpenHarmony SDK"
                echo "  2. 提取 toolchains/hdc_std 到 ~/.local/bin/"
                echo "  3. chmod +x ~/.local/bin/hdc_std"
            fi
            ;;
        wsl)
            echo -e "${YELLOW}[WSL]${NC} WSL 使用 Windows 侧的 HDC"
            echo "请确保 Windows 已安装 HDC 并添加到 PATH"
            echo ""
            echo "验证: powershell.exe -c 'hdc version'"
            ;;
        windows)
            echo -e "${YELLOW}[Windows]${NC} 请手动安装 HDC:"
            echo "  1. 下载 OpenHarmony SDK"
            echo "  2. 提取 toolchains/hdc.exe 到 PATH 目录"
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} 不支持的平台: $platform"
            exit 1
            ;;
    esac
}

# ============================================================================
# 主函数
# ============================================================================
main() {
    local platform=\$(detect_platform)
    local hdc_cmd=\$(get_hdc_command "$platform")
    
    # 处理特殊选项
    case "${1:-}" in
        --platform)
            echo "$platform"
            exit 0
            ;;
        --hdc-path)
            if [[ -z "$hdc_cmd" && "$platform" != "wsl" ]]; then
                echo -e "${RED}[ERROR]${NC} HDC not found for platform: $platform" >&2
                exit 1
            fi
            if [[ "$platform" == "wsl" ]]; then
                echo "powershell.exe -c 'hdc'"
            else
                echo "$hdc_cmd"
            fi
            exit 0
            ;;
        --install)
            run_installer "$platform"
            exit 0
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
    esac
    
    # 检查 HDC 可用性
    if [[ -z "$hdc_cmd" && "$platform" != "wsl" ]]; then
        echo -e "${RED}[ERROR]${NC} HDC not found" >&2
        echo "Platform: $platform" >&2
        echo "Run '$0 --install' to install HDC" >&2
        exit 1
    fi
    
    # 无参数时显示帮助
    if [[ \$# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    # 执行 HDC 命令
    case "$platform" in
        linux|windows|macos)
            $hdc_cmd "$@"
            ;;
        wsl)
            # WSL: 文件传输需要特殊处理
            if [[ "$1" == "file" && "$2" == "send" ]]; then
                # 转换本地路径
                shift 2
                local new_args=()
                local skip_next=false
                for arg in "$@"; do
                    if [[ "$skip_next" == true ]]; then
                        skip_next=false
                        new_args+=("$arg")
                        continue
                    fi
                    if [[ "$arg" == "-t" ]]; then
                        new_args+=("-t")
                        skip_next=true
                    elif [[ -f "$arg" || -d "$arg" ]]; then
                        new_args+=("\$(convert_wsl_path "$arg")")
                    else
                        new_args+=("$arg")
                    fi
                done
                wsl_execute file send "${new_args[@]}"
            else
                wsl_execute "$@"
            fi
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} Unsupported platform: $platform" >&2
            exit 1
            ;;
    esac
}

main "$@"

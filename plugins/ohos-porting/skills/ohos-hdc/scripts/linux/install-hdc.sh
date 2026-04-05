#!/bin/bash
# ============================================================================
# HDC Installation Script for Native Ubuntu/Linux
# ============================================================================
# 功能: 在原生 Ubuntu/Linux 系统上安装 HDC (OpenHarmony Device Connector)
# 支持: Ubuntu 18.04+, Debian 10+, 其他基于 apt 的发行版
# ============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认配置
HDC_INSTALL_DIR="\${HDC_INSTALL_DIR:-\$HOME/.local/share/hdc}"
HDC_BIN_DIR="\${HDC_BIN_DIR:-\$HOME/.local/bin}"
SDK_VERSION="\${SDK_VERSION:-5.0.2}"
API_VERSION="\${API_VERSION:-14}"

# 日志函数
log_info() { echo -e "\${BLUE}[INFO]\${NC} \$1"; }
log_success() { echo -e "\${GREEN}[SUCCESS]\${NC} \$1"; }
log_warn() { echo -e "\${YELLOW}[WARN]\${NC} \$1"; }
log_error() { echo -e "\${RED}[ERROR]\${NC} \$1"; }

# 显示帮助
show_help() {
    cat << EOF
Usage: \$0 [OPTIONS]

Options:
    -d, --dir DIR       HDC 安装目录 (默认: \$HOME/.local/share/hdc)
    -b, --bin DIR       HDC 可执行文件目录 (默认: \$HOME/.local/bin)
    -v, --version VER   SDK 版本 (默认: 5.0.2)
    -a, --api VER       API 版本 (默认: 14)
    -h, --help          显示此帮助信息

Examples:
    \$0                           # 使用默认配置安装
    \$0 -d /opt/hdc -b /usr/local/bin  # 自定义安装路径
    \$0 --version 5.0.1 --api 13       # 指定 SDK 版本
EOF
}

# 解析参数
while [[ \$# -gt 0 ]]; do
    case \$1 in
        -d|--dir) HDC_INSTALL_DIR="\$2"; shift 2 ;;
        -b|--bin) HDC_BIN_DIR="\$2"; shift 2 ;;
        -v|--version) SDK_VERSION="\$2"; shift 2 ;;
        -a|--api) API_VERSION="\$2"; shift 2 ;;
        -h|--help) show_help; exit 0 ;;
        *) log_error "Unknown option: \$1"; show_help; exit 1 ;;
    esac
done

# 检查系统
check_system() {
    log_info "检查系统环境..."
    
    if [[ "\$(uname -s)" != "Linux" ]]; then
        log_error "此脚本仅支持 Linux 系统"
        exit 1
    fi
    
    # 检查是否在 WSL 中
    if grep -qi microsoft /proc/version 2>/dev/null; then
        log_warn "检测到 WSL 环境，建议使用 wsl/ 目录下的脚本"
        log_warn "继续安装原生 Linux 版本..."
    fi
    
    # 检查架构
    ARCH=\$(uname -m)
    case \$ARCH in
        x86_64) ARCH_NAME="x64" ;;
        aarch64) ARCH_NAME="arm64" ;;
        *) log_error "不支持的架构: \$ARCH"; exit 1 ;;
    esac
    
    log_success "系统检查通过: Linux \$ARCH"
}

# 安装依赖
install_deps() {
    log_info "检查并安装依赖..."
    
    DEPS=(curl unzip libusb-1.0-0)
    MISSING=()
    
    for dep in "\${DEPS[@]}"; do
        if ! command -v "\$dep" &>/dev/null && ! dpkg -l | grep -q "\$dep"; then
            MISSING+=("\$dep")
        fi
    done
    
    if [[ \${#MISSING[@]} -gt 0 ]]; then
        log_info "安装缺失的依赖: \${MISSING[*]}"
        sudo apt-get update
        sudo apt-get install -y "\${MISSING[@]}"
    fi
    
    log_success "依赖检查完成"
}

# 下载 SDK
download_sdk() {
    log_info "准备下载 OpenHarmony SDK..."
    
    mkdir -p "\$HDC_INSTALL_DIR"
    cd "\$HDC_INSTALL_DIR"
    
    # SDK 下载 URL (从 OpenHarmony 官方获取)
    SDK_BASE_URL="https://repo.huaweicloud.com/openharmony/os/\$SDK_VERSION"
    TOOLCHAIN_FILE="toolchains-linux-\$ARCH_NAME-\$SDK_VERSION.zip"
    
    if [[ -f "\$HDC_INSTALL_DIR/toolchains/hdc" ]]; then
        log_warn "HDC 已存在，跳过下载"
        return 0
    fi
    
    log_info "下载 toolchains 包: \$TOOLCHAIN_FILE"
    log_info "下载地址: \$SDK_BASE_URL/\$TOOLCHAIN_FILE"
    
    if ! curl -L -o "toolchains.zip" "\$SDK_BASE_URL/\$TOOLCHAIN_FILE" 2>/dev/null; then
        log_warn "从官方源下载失败，尝试备用方案..."
        
        # 备用: 提示用户手动下载
        cat << EOF

========================================
自动下载失败，请手动下载 SDK:

1. 访问 OpenHarmony 发布页面:
   https://gitee.com/openharmony/docs/blob/master/zh-cn/release-notes/OpenHarmony-v\$SDK_VERSION-release.md

2. 下载 "Public SDK package for the standard system" (Linux 版本)

3. 解压后将 toolchains 目录复制到:
   \$HDC_INSTALL_DIR/toolchains

4. 重新运行此脚本完成安装
========================================
EOF
        exit 1
    fi
    
    log_info "解压 toolchains..."
    unzip -o toolchains.zip
    rm -f toolchains.zip
    
    log_success "SDK 下载完成"
}

# 安装 HDC
install_hdc() {
    log_info "安装 HDC..."
    
    HDC_SRC="\$HDC_INSTALL_DIR/toolchains/hdc"
    
    if [[ ! -f "\$HDC_SRC" ]]; then
        log_error "HDC 可执行文件不存在: \$HDC_SRC"
        log_error "请确保 SDK 下载正确"
        exit 1
    fi
    
    # 创建 bin 目录
    mkdir -p "\$HDC_BIN_DIR"
    
    # 复制并设置权限
    cp "\$HDC_SRC" "\$HDC_BIN_DIR/hdc"
    chmod +x "\$HDC_BIN_DIR/hdc"
    
    # 创建符号链接 (兼容旧版命名)
    ln -sf "\$HDC_BIN_DIR/hdc" "\$HDC_BIN_DIR/hdc_std" 2>/dev/null || true
    
    log_success "HDC 安装到: \$HDC_BIN_DIR/hdc"
}

# 配置 PATH
setup_path() {
    log_info "配置 PATH 环境变量..."
    
    SHELL_RC=""
    if [[ -n "\$BASH_VERSION" ]]; then
        SHELL_RC="\$HOME/.bashrc"
    elif [[ -n "\$ZSH_VERSION" ]]; then
        SHELL_RC="\$HOME/.zshrc"
    else
        SHELL_RC="\$HOME/.profile"
    fi
    
    PATH_LINE="export PATH=\"\$HDC_BIN_DIR:\\\$PATH\""
    
    if ! grep -q "\$HDC_BIN_DIR" "\$SHELL_RC" 2>/dev/null; then
        echo "" >> "\$SHELL_RC"
        echo "# HDC (OpenHarmony Device Connector)" >> "\$SHELL_RC"
        echo "\$PATH_LINE" >> "\$SHELL_RC"
        log_success "PATH 已添加到 \$SHELL_RC"
    else
        log_info "PATH 已配置，跳过"
    fi
    
    # 立即生效
    export PATH="\$HDC_BIN_DIR:\$PATH"
}

# 验证安装
verify_install() {
    log_info "验证安装..."
    
    if command -v hdc &>/dev/null; then
        HDC_VERSION=\$(hdc version 2>/dev/null || echo "unknown")
        log_success "HDC 安装成功!"
        log_info "版本: \$HDC_VERSION"
        log_info "路径: \$(which hdc)"
    else
        log_error "HDC 安装验证失败"
        log_error "请手动将 \$HDC_BIN_DIR 添加到 PATH"
        exit 1
    fi
}

# 显示后续步骤
show_next_steps() {
    cat << EOF

========================================
\${GREEN}HDC 安装完成!\${NC}
========================================

下一步:
1. 重新加载 shell 配置:
   source ~/.bashrc  # 或 source ~/.zshrc

2. 配置 USB 权限 (重要):
   sudo ./setup-udev.sh

3. 连接设备并测试:
   hdc list targets

常用命令:
   hdc list targets          # 列出设备
   hdc -t <serial> shell     # 进入设备 shell
   hdc file send <本地> <远程>  # 发送文件
   hdc file recv <远程> <本地>  # 接收文件

更多帮助:
   hdc -h
========================================
EOF
}

# 主函数
main() {
    echo ""
    echo "======================================"
    echo "  HDC Installation for Native Linux"
    echo "======================================"
    echo ""
    
    check_system
    install_deps
    download_sdk
    install_hdc
    setup_path
    verify_install
    show_next_steps
}

main "\$@"

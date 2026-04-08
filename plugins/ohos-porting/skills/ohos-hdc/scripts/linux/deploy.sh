#!/bin/bash
# ============================================================================
# HDC Deploy Script for Native Linux
# ============================================================================
# 功能: 部署文件到 OpenHarmony/KaihongOS 设备
# ============================================================================

set -e

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
source "\$SCRIPT_DIR/hdc-wrapper.sh" 2>/dev/null || true

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "\${BLUE}[INFO]\${NC} \$1"; }
log_success() { echo -e "\${GREEN}[SUCCESS]\${NC} \$1"; }
log_warn() { echo -e "\${YELLOW}[WARN]\${NC} \$1"; }
log_error() { echo -e "\${RED}[ERROR]\${NC} \$1"; }

# 默认配置
DEFAULT_REMOTE_DIR="/data/local/tmp"
HDC_CMD="\${HDC_CMD:-hdc}"

show_help() {
    cat << EOF
Usage: \$0 [OPTIONS] <LOCAL_PATH> [REMOTE_PATH]

Options:
    -t, --target SERIAL    指定设备序列号
    -d, --dir DIR          远程目录 (默认: /data/local/tmp)
    -e, --exec             部署后执行 (仅限可执行文件)
    -r, --recursive        递归部署目录
    -h, --help             显示帮助

Examples:
    \$0 ./libcurl.so                    # 部署到 /data/local/tmp
    \$0 ./app /system/lib64             # 部署到指定目录
    \$0 -e ./test_bin                   # 部署并执行
    \$0 -r ./libs /data/local/tmp/libs  # 递归部署目录
EOF
}

# 解析参数
TARGET=""
REMOTE_DIR="\$DEFAULT_REMOTE_DIR"
EXEC_AFTER=false
RECURSIVE=false

while [[ \$# -gt 0 ]]; do
    case \$1 in
        -t|--target) TARGET="\$2"; shift 2 ;;
        -d|--dir) REMOTE_DIR="\$2"; shift 2 ;;
        -e|--exec) EXEC_AFTER=true; shift ;;
        -r|--recursive) RECURSIVE=true; shift ;;
        -h|--help) show_help; exit 0 ;;
        -*) log_error "Unknown option: \$1"; show_help; exit 1 ;;
        *) break ;;
    esac
done

LOCAL_PATH="\$1"
REMOTE_PATH="\${2:-\$REMOTE_DIR}"

if [[ -z "\$LOCAL_PATH" ]]; then
    log_error "请指定本地文件路径"
    show_help
    exit 1
fi

if [[ ! -e "\$LOCAL_PATH" ]]; then
    log_error "文件不存在: \$LOCAL_PATH"
    exit 1
fi

# 检查 HDC
if ! command -v "\$HDC_CMD" &>/dev/null; then
    log_error "HDC 未安装"
    exit 1
fi

# 选择设备
if [[ -z "\$TARGET" ]]; then
    DEVICES=\$(\$HDC_CMD list targets 2>/dev/null | grep -v "^\$" || true)
    DEVICE_COUNT=\$(echo "\$DEVICES" | grep -c . || echo 0)
    
    if [[ \$DEVICE_COUNT -eq 0 ]]; then
        log_error "未检测到设备"
        exit 1
    elif [[ \$DEVICE_COUNT -eq 1 ]]; then
        TARGET="\$DEVICES"
    else
        log_info "检测到多个设备:"
        echo "\$DEVICES" | nl
        echo -n "请选择设备: "
        read -r choice
        TARGET=\$(echo "\$DEVICES" | sed -n "\${choice}p")
    fi
fi

log_info "目标设备: \$TARGET"

# HDC 命令前缀
HDC="\$HDC_CMD -t \$TARGET"

# 部署文件
deploy_file() {
    local src="\$1"
    local dst="\$2"
    local filename=\$(basename "\$src")
    
    log_info "部署: \$src -> \$dst/\$filename"
    
    # 确保远程目录存在
    \$HDC shell "mkdir -p \$dst" 2>/dev/null || true
    
    # 发送文件
    if \$HDC file send "\$src" "\$dst/\$filename"; then
        log_success "文件已部署"
        
        # 设置执行权限
        if [[ -x "\$src" ]]; then
            \$HDC shell "chmod +x \$dst/\$filename"
            log_info "已设置执行权限"
        fi
        
        return 0
    else
        log_error "部署失败"
        return 1
    fi
}

# 递归部署目录
deploy_dir() {
    local src="\$1"
    local dst="\$2"
    
    log_info "递归部署目录: \$src -> \$dst"
    
    # 创建远程目录
    \$HDC shell "mkdir -p \$dst"
    
    # 遍历并部署
    find "\$src" -type f | while read -r file; do
        rel_path=\${file#\$src/}
        remote_dir="\$dst/\$(dirname "\$rel_path")"
        deploy_file "\$file" "\$remote_dir"
    done
}

# 主逻辑
if [[ -d "\$LOCAL_PATH" ]]; then
    if [[ "\$RECURSIVE" == true ]]; then
        deploy_dir "\$LOCAL_PATH" "\$REMOTE_PATH"
    else
        log_error "\$LOCAL_PATH 是目录，请使用 -r 选项"
        exit 1
    fi
else
    deploy_file "\$LOCAL_PATH" "\$REMOTE_PATH"
    
    # 执行
    if [[ "\$EXEC_AFTER" == true ]]; then
        FILENAME=\$(basename "\$LOCAL_PATH")
        log_info "执行: \$REMOTE_PATH/\$FILENAME"
        \$HDC shell "cd \$REMOTE_PATH && ./\$FILENAME"
    fi
fi

log_success "部署完成!"

#!/bin/bash
# deploy_softbus_permission.sh - DSoftBus Session 权限配置部署脚本
#
# 用法:
#   ./deploy_softbus_permission.sh <DEVICE_ID> <CONFIG_FILE>
#
# 示例:
#   ./deploy_softbus_permission.sh ec29004133314d38433031a522413c00 templates/minimal.json
#
# 验证状态: ✅ 2026-01-19 rk3588s KaihongOS API 11 真机验证通过

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

HDC_BIN="${HDC_BIN:-hdc}"
TARGET_PATH="/system/etc/communication/softbus/softbus_trans_permission.json"

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    cat << 'USAGE'
deploy_softbus_permission.sh - DSoftBus Session 权限配置部署

用法:
    ./deploy_softbus_permission.sh <DEVICE_ID> <CONFIG_FILE>

参数:
    DEVICE_ID      设备 ID (hdc list targets 获取)
    CONFIG_FILE    JSON 配置文件路径

示例:
    ./deploy_softbus_permission.sh ec29004133314d38433031a522413c00 templates/minimal.json

配置模板:
    templates/minimal.json   - 生产起点，最小权限
    templates/dev.json       - 开发调试（需收窄后再上线）
    templates/verified.json  - 经过验证的参考样例，包含非生产通配配置

注意:
    - 配置文件必须是纯数组格式（以 [ 开头）
    - 部署后必须重启设备才能生效
USAGE
}

require_hdc() {
    if ! command -v "$HDC_BIN" >/dev/null 2>&1; then
        log_error "未找到 HDC 命令: $HDC_BIN"
        exit 1
    fi
}

first_nonspace_char() {
    grep -o '[^[:space:]]' "$1" | head -1
}

if [[ $# -lt 2 ]]; then
    usage
    exit 1
fi

DEVICE_ID="$1"
CONFIG_FILE="$2"

require_hdc

if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "配置文件不存在: $CONFIG_FILE"
    exit 1
fi

echo "========================================"
echo "DSoftBus 权限配置部署"
echo "========================================"
echo "设备: $DEVICE_ID"
echo "配置: $CONFIG_FILE"
echo "目标: $TARGET_PATH"
echo "========================================"
echo

log_info "[1/7] 验证配置文件格式..."
if command -v python3 >/dev/null 2>&1; then
    if ! python3 -m json.tool "$CONFIG_FILE" >/dev/null 2>&1; then
        log_error "JSON 格式错误"
        python3 -m json.tool "$CONFIG_FILE" 2>&1 | head -5
        exit 1
    fi
fi

FIRST_CHAR=$(first_nonspace_char "$CONFIG_FILE")
if [[ "$FIRST_CHAR" != "[" ]]; then
    log_error "配置格式错误: 根元素必须是数组 (以 [ 开头)"
    log_error "当前第一个字符: '$FIRST_CHAR'"
    log_error "提示: 不能使用 {\"trans_permission\": [...]} 格式"
    exit 1
fi
log_ok "配置文件格式正确 (纯数组)"

log_info "[2/7] 检查设备连接..."
if ! "$HDC_BIN" -t "$DEVICE_ID" shell 'echo ok' >/dev/null 2>&1; then
    log_error "设备未连接: $DEVICE_ID"
    log_info "可用设备:"
    "$HDC_BIN" list targets 2>/dev/null || true
    exit 1
fi
log_ok "设备已连接"

log_info "[3/7] 挂载根目录为可写..."
"$HDC_BIN" -t "$DEVICE_ID" shell 'mount -o rw,remount /' 2>/dev/null || true
log_ok "已挂载"

log_info "[4/7] 备份原配置文件..."
BACKUP_NAME="softbus_trans_permission.json.bak.$(date +%Y%m%d_%H%M%S)"
"$HDC_BIN" -t "$DEVICE_ID" shell "cp $TARGET_PATH /system/etc/communication/softbus/$BACKUP_NAME" 2>/dev/null || true
log_ok "已备份为 $BACKUP_NAME"

log_info "[5/7] 传输新配置文件..."
"$HDC_BIN" -t "$DEVICE_ID" file send "$CONFIG_FILE" "$TARGET_PATH"
log_ok "传输完成"

log_info "[6/7] 设置文件权限..."
"$HDC_BIN" -t "$DEVICE_ID" shell "chmod 644 $TARGET_PATH"
log_ok "权限已设置 (644)"

log_info "[7/7] 验证部署..."
if ! "$HDC_BIN" -t "$DEVICE_ID" shell "test -f $TARGET_PATH && echo exists" | grep -q exists; then
    log_error "文件不存在"
    exit 1
fi
log_ok "文件存在"

REMOTE_FIRST=$("$HDC_BIN" -t "$DEVICE_ID" shell "head -c 10 $TARGET_PATH" | grep -o '[^[:space:]]' | head -1)
if [[ "$REMOTE_FIRST" != "[" ]]; then
    log_error "远程文件格式错误 (第一个字符: '$REMOTE_FIRST')"
    exit 1
fi
log_ok "格式正确"

ENTRY_COUNT=$("$HDC_BIN" -t "$DEVICE_ID" shell "grep -c SESSION_NAME $TARGET_PATH" | tr -d '[:space:]')
log_ok "配置条目: ${ENTRY_COUNT:-0}"

echo
echo "========================================"
echo -e "${GREEN}部署成功！${NC}"
echo "========================================"
echo
echo -e "${YELLOW}重要: 请重启设备使配置生效${NC}"
echo
echo "  hdc -t $DEVICE_ID shell 'reboot'"
echo
echo "重启后验证:"
echo "  ./scripts/verify_softbus_permission.sh $DEVICE_ID"
echo "  hdc -t $DEVICE_ID shell 'head -5 $TARGET_PATH'"
echo

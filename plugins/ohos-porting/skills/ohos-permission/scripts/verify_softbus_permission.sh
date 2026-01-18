#!/bin/bash
# verify_softbus_permission.sh - 验证 DSoftBus 权限配置
#
# 用法:
#   ./verify_softbus_permission.sh <DEVICE_ID>

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEVICE_ID="\${1:-}"
TARGET_PATH="/system/etc/communication/softbus/softbus_trans_permission.json"

if [ -z "\$DEVICE_ID" ]; then
    echo "用法: \$0 <DEVICE_ID>"
    echo "示例: \$0 ec29004133314d38433031a522413c00"
    exit 1
fi

echo "========================================"
echo "DSoftBus 权限配置验证"
echo "========================================"
echo "设备: \$DEVICE_ID"
echo "目标: \$TARGET_PATH"
echo "========================================"
echo

PASS=0
FAIL=0
WARN=0

check_pass() { echo -e "${GREEN}✓${NC} \$1"; ((PASS++)); }
check_fail() { echo -e "${RED}✗${NC} \$1"; ((FAIL++)); }
check_warn() { echo -e "${YELLOW}!${NC} \$1"; ((WARN++)); }

# [1] 设备连接
echo -n "[1/6] 设备连接... "
if hdc -t "\$DEVICE_ID" shell 'echo ok' > /dev/null 2>&1; then
    check_pass "已连接"
else
    check_fail "未连接"
    exit 1
fi

# [2] 配置文件存在
echo -n "[2/6] 配置文件存在... "
if hdc -t "\$DEVICE_ID" shell "test -f \$TARGET_PATH && echo exists" | grep -q exists; then
    check_pass "存在"
else
    check_fail "不存在"
    exit 1
fi

# [3] 配置格式 (纯数组)
echo -n "[3/6] 配置格式 (纯数组)... "
FIRST_CHAR=\$(hdc -t "\$DEVICE_ID" shell "head -c 10 \$TARGET_PATH" | grep -o '[^[:space:]]' | head -1)
if [ "\$FIRST_CHAR" = "[" ]; then
    check_pass "正确 (以 [ 开头)"
else
    check_fail "错误 (第一个字符: '\$FIRST_CHAR', 应为 '[')"
fi

# [4] 文件权限
echo -n "[4/6] 文件权限... "
PERM=\$(hdc -t "\$DEVICE_ID" shell "stat -c %a \$TARGET_PATH 2>/dev/null || ls -la \$TARGET_PATH | awk '{print \$1}'" | tr -d '[:space:]')
if [[ "\$PERM" == *"644"* ]] || [[ "\$PERM" == *"rw-r--r--"* ]]; then
    check_pass "644"
else
    check_warn "\$PERM (建议 644)"
fi

# [5] softbus_server 进程
echo -n "[5/6] softbus_server 进程... "
if hdc -t "\$DEVICE_ID" shell 'ps -ef 2>/dev/null || ps aux' | grep -v grep | grep -q softbus_server; then
    check_pass "运行中"
else
    check_warn "未运行 (可能需要重启设备)"
fi

# [6] 配置条目数
echo -n "[6/6] 配置条目... "
ENTRY_COUNT=\$(hdc -t "\$DEVICE_ID" shell "grep -c SESSION_NAME \$TARGET_PATH 2>/dev/null" | tr -d '[:space:]')
if [ -n "\$ENTRY_COUNT" ] && [ "\$ENTRY_COUNT" -gt 0 ]; then
    check_pass "\$ENTRY_COUNT 条"
else
    check_fail "0 条 (配置可能为空)"
fi

echo
echo "========================================"
echo "验证结果: ${GREEN}\$PASS 通过${NC}, ${RED}\$FAIL 失败${NC}, ${YELLOW}\$WARN 警告${NC}"
echo "========================================"

# 显示配置预览
echo
echo "配置预览 (前 20 行):"
echo "----------------------------------------"
hdc -t "\$DEVICE_ID" shell "head -20 \$TARGET_PATH"
echo "----------------------------------------"

# 显示已配置的 SESSION_NAME
echo
echo "已配置的 Session 名称:"
hdc -t "\$DEVICE_ID" shell "grep SESSION_NAME \$TARGET_PATH" | sed 's/.*"SESSION_NAME"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/  - \1/'

if [ \$FAIL -gt 0 ]; then
    echo
    echo -e "${RED}存在失败项，请检查配置${NC}"
    exit 1
fi

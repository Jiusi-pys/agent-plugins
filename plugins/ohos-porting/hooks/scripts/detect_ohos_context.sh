#!/bin/bash
# detect_ohos_context.sh - 检测 OHOS 项目上下文

# 读取 stdin 的 JSON 输入
INPUT=$(cat)

# 提取命令内容
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# 检测是否是 OHOS 相关操作
OHOS_PATTERNS=(
    "hdc"
    "ohos"
    "openharmony"
    "BUILD.gn"
    "aarch64-linux-ohos"
    "toolchain.*ohos"
    "hilog"
    "softbus"
)

IS_OHOS=false
for pattern in "${OHOS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qi "$pattern"; then
        IS_OHOS=true
        break
    fi
done

if [ "$IS_OHOS" = true ]; then
    # 输出提示信息供 Claude 参考
    echo "[ohos-porting] OHOS 相关操作检测，可用 agents:" >&2
    echo "  - compile-debugger: 编译错误诊断" >&2
    echo "  - runtime-debugger: 运行时问题诊断" >&2
    echo "  - remote-commander: 设备操作" >&2
fi

exit 0

#!/bin/bash
# on_compile_error.sh - 编译错误检测与 agent 调用建议

# 读取 stdin 的 JSON 输入
INPUT=$(cat)

# 提取退出码和输出
EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // 0' 2>/dev/null)
STDOUT=$(echo "$INPUT" | jq -r '.tool_response.stdout // empty' 2>/dev/null)
STDERR=$(echo "$INPUT" | jq -r '.tool_response.stderr // empty' 2>/dev/null)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# 合并输出
OUTPUT="$STDOUT$STDERR"

# 如果退出码为 0，直接返回
if [ "$EXIT_CODE" = "0" ]; then
    exit 0
fi

# 检测是否是编译命令
IS_BUILD=false
BUILD_PATTERNS=("make" "cmake" "gcc" "g++" "clang" "ninja" "cargo" "gn" "build")
for pattern in "${BUILD_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qi "$pattern"; then
        IS_BUILD=true
        break
    fi
done

if [ "$IS_BUILD" = false ]; then
    exit 0
fi

# 检测错误类型
ERROR_TYPE="unknown"
AGENT_SUGGESTION=""

if echo "$OUTPUT" | grep -qE "undefined reference|multiple definition"; then
    ERROR_TYPE="link_error"
    AGENT_SUGGESTION="compile-debugger"
elif echo "$OUTPUT" | grep -qE "error:.*No such file|fatal error:.*not found"; then
    ERROR_TYPE="header_missing"
    AGENT_SUGGESTION="compile-debugger"
elif echo "$OUTPUT" | grep -qE "error:.*undeclared|error:.*was not declared"; then
    ERROR_TYPE="symbol_error"
    AGENT_SUGGESTION="compile-debugger"
elif echo "$OUTPUT" | grep -qE "error:.*invalid|error:.*cannot convert"; then
    ERROR_TYPE="type_error"
    AGENT_SUGGESTION="compile-debugger"
fi

# 如果检测到编译错误，输出建议
if [ -n "$AGENT_SUGGESTION" ]; then
    echo "" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "[ohos-porting] 检测到编译错误 ($ERROR_TYPE)" >&2
    echo "建议: 调用 $AGENT_SUGGESTION agent 进行诊断" >&2
    echo "" >&2
    echo "调用方式:" >&2
    echo "  Task(\"$AGENT_SUGGESTION\", \"诊断编译错误: [错误摘要]\")" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
fi

exit 0

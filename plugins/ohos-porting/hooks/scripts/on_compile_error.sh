#!/bin/bash
# on_compile_error.sh - 编译错误自动诊断
# 由 hooks 在编译失败时自动调用

# 从环境变量获取工具输出
OUTPUT="${CLAUDE_TOOL_OUTPUT:-}"
EXIT_CODE="${CLAUDE_TOOL_EXIT_CODE:-1}"

# 检测是否是编译错误
if echo "$OUTPUT" | grep -qE "error:|undefined reference|No such file"; then
    echo "检测到编译错误，建议使用 compile-debugger agent 进行诊断"
    echo ""
    echo "快速诊断:"
    
    # 统计错误类型
    HEADER_ERRORS=$(echo "$OUTPUT" | grep -c "No such file or directory" || echo 0)
    UNDEF_ERRORS=$(echo "$OUTPUT" | grep -c "undefined reference" || echo 0)
    
    echo "  头文件错误: $HEADER_ERRORS"
    echo "  符号未定义: $UNDEF_ERRORS"
    
    # 检测 Linux 特有 API
    if echo "$OUTPUT" | grep -qE "epoll|inotify|eventfd|signalfd|timerfd"; then
        echo ""
        echo "⚠ 检测到 Linux 特有 API 相关错误"
        echo "  请参考 api-mapping skill 获取替代方案"
    fi
fi

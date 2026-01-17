#!/bin/bash
# analyze_errors.sh - 分析编译错误日志
# 用法: ./analyze_errors.sh build.log

LOG_FILE="${1:-build.log}"

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file not found: $LOG_FILE"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════╗"
echo "║         编译错误分析报告                                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 统计错误类型
echo "【错误统计】"

HEADER_ERRORS=$(grep -c "No such file or directory\|file not found" "$LOG_FILE" 2>/dev/null || echo 0)
UNDEFINED_ERRORS=$(grep -c "undefined reference" "$LOG_FILE" 2>/dev/null || echo 0)
TYPE_ERRORS=$(grep -c "incompatible\|conflicting types" "$LOG_FILE" 2>/dev/null || echo 0)
LINKER_ERRORS=$(grep -c "cannot find -l\|library not found" "$LOG_FILE" 2>/dev/null || echo 0)

echo "  头文件缺失: $HEADER_ERRORS"
echo "  符号未定义: $UNDEFINED_ERRORS"
echo "  类型不兼容: $TYPE_ERRORS"
echo "  链接错误: $LINKER_ERRORS"
echo ""

# 头文件错误详情
if [ "$HEADER_ERRORS" -gt 0 ]; then
    echo "【头文件错误详情】"
    grep -E "No such file or directory|file not found" "$LOG_FILE" | \
        sed 's/.*fatal error: /  /' | \
        sed 's/: No such.*//' | \
        sort | uniq -c | sort -rn | head -10
    echo ""
    
    # 检查 Linux 特有头文件
    echo "  Linux 特有头文件检测:"
    LINUX_HEADERS="sys/epoll.h sys/inotify.h sys/signalfd.h sys/eventfd.h sys/timerfd.h linux/"
    for h in $LINUX_HEADERS; do
        if grep -q "$h" "$LOG_FILE" 2>/dev/null; then
            echo "    ⚠ $h (需要替代方案)"
        fi
    done
    echo ""
fi

# 符号未定义详情
if [ "$UNDEFINED_ERRORS" -gt 0 ]; then
    echo "【符号未定义详情】"
    grep "undefined reference" "$LOG_FILE" | \
        sed "s/.*undefined reference to '/  /" | \
        sed "s/'.*//" | \
        sort | uniq -c | sort -rn | head -10
    echo ""
    
    # 检查常见 Linux 特有符号
    echo "  Linux 特有符号检测:"
    LINUX_SYMBOLS="epoll_create epoll_ctl epoll_wait inotify_init inotify_add_watch eventfd signalfd timerfd_create"
    for s in $LINUX_SYMBOLS; do
        if grep -q "undefined reference to '$s'" "$LOG_FILE" 2>/dev/null; then
            echo "    ⚠ $s (需要替代实现)"
        fi
    done
    echo ""
fi

# 链接错误详情
if [ "$LINKER_ERRORS" -gt 0 ]; then
    echo "【链接错误详情】"
    grep -E "cannot find -l|library not found" "$LOG_FILE" | \
        sed 's/.*cannot find -l/  -l/' | \
        sed 's/.*library not found for /  -l/' | \
        sort | uniq
    echo ""
fi

# 修复建议
echo "【修复建议】"
if [ "$HEADER_ERRORS" -gt 0 ]; then
    echo "  1. 头文件问题:"
    echo "     - 检查 OHOS SDK sysroot 中是否存在对应头文件"
    echo "     - Linux 特有头文件需要条件编译或替代实现"
fi
if [ "$UNDEFINED_ERRORS" -gt 0 ]; then
    echo "  2. 符号问题:"
    echo "     - 检查链接库是否完整 (-l 参数)"
    echo "     - Linux 特有 API 需要条件编译或封装层"
fi
if [ "$LINKER_ERRORS" -gt 0 ]; then
    echo "  3. 链接问题:"
    echo "     - 确认库文件在 OHOS sysroot 中存在"
    echo "     - 检查 -L 库搜索路径"
fi
echo ""

# 第一个需要修复的错误
echo "【首个错误】"
grep -m1 -E "error:" "$LOG_FILE" | head -1

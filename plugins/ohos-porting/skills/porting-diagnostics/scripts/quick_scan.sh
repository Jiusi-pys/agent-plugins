#!/bin/bash
# quick_scan.sh - OHOS 移植快速诊断脚本
# 用法: ./quick_scan.sh /path/to/source

set -e

SOURCE_DIR="${1:-.}"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Directory not found: $SOURCE_DIR"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════╗"
echo "║         OHOS 移植快速诊断                               ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║ 目标目录: $SOURCE_DIR"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

cd "$SOURCE_DIR"

# 统计源文件
echo "【源文件统计】"
C_FILES=$(find . -name "*.c" | wc -l)
CPP_FILES=$(find . -name "*.cpp" -o -name "*.cc" -o -name "*.cxx" | wc -l)
H_FILES=$(find . -name "*.h" -o -name "*.hpp" | wc -l)
echo "  C 文件: $C_FILES"
echo "  C++ 文件: $CPP_FILES"
echo "  头文件: $H_FILES"
echo ""

# 红灯 API 检测
echo "【红灯 API (不可移植)】"
RED_APIS="io_uring|clone\(.*CLONE_NEW|unshare\(|setns\(|perf_event_open|bpf\("
RED_COUNT=$(grep -rEc "$RED_APIS" --include="*.c" --include="*.cpp" --include="*.h" 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
echo "  发现: $RED_COUNT 处"
if [ "$RED_COUNT" -gt 0 ]; then
    echo "  详情:"
    grep -rn "$RED_APIS" --include="*.c" --include="*.cpp" --include="*.h" 2>/dev/null | head -10 | sed 's/^/    /'
    [ "$RED_COUNT" -gt 10 ] && echo "    ... 更多 $((RED_COUNT - 10)) 处"
fi
echo ""

# 黄灯 API 检测
echo "【黄灯 API (需要适配)】"
YELLOW_APIS="epoll_|inotify_|eventfd|signalfd|timerfd_|getauxval"
YELLOW_COUNT=$(grep -rEc "$YELLOW_APIS" --include="*.c" --include="*.cpp" --include="*.h" 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
echo "  发现: $YELLOW_COUNT 处"
if [ "$YELLOW_COUNT" -gt 0 ]; then
    echo "  详情:"
    grep -rn "$YELLOW_APIS" --include="*.c" --include="*.cpp" --include="*.h" 2>/dev/null | head -10 | sed 's/^/    /'
    [ "$YELLOW_COUNT" -gt 10 ] && echo "    ... 更多 $((YELLOW_COUNT - 10)) 处"
fi
echo ""

# /proc /sys 使用
echo "【/proc /sys 使用】"
PROC_COUNT=$(grep -rc '"/proc\|"/sys' --include="*.c" --include="*.cpp" --include="*.h" 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
echo "  发现: $PROC_COUNT 处"
if [ "$PROC_COUNT" -gt 0 ]; then
    grep -rn '"/proc\|"/sys' --include="*.c" --include="*.cpp" --include="*.h" 2>/dev/null | head -5 | sed 's/^/    /'
fi
echo ""

# 外部依赖
echo "【外部依赖库】"
if [ -f "CMakeLists.txt" ]; then
    echo "  从 CMakeLists.txt 检测:"
    grep -E "find_package|pkg_check_modules|target_link_libraries" CMakeLists.txt 2>/dev/null | head -10 | sed 's/^/    /'
elif [ -f "Makefile" ]; then
    echo "  从 Makefile 检测:"
    grep -E "LDFLAGS|LIBS|pkg-config" Makefile 2>/dev/null | head -10 | sed 's/^/    /'
fi
echo ""

# 难度评估
echo "【移植难度评估】"
if [ "$RED_COUNT" -gt 5 ]; then
    GRADE="D"
    ADVICE="建议放弃，寻找替代库"
elif [ "$RED_COUNT" -gt 0 ]; then
    GRADE="C"
    ADVICE="需要重构，与用户确认是否继续"
elif [ "$YELLOW_COUNT" -gt 20 ]; then
    GRADE="C"
    ADVICE="大量 API 需要适配，预估 1-2 周"
elif [ "$YELLOW_COUNT" -gt 5 ]; then
    GRADE="B"
    ADVICE="中等难度，预估 1-3 天"
else
    GRADE="A"
    ADVICE="简单移植，预估 < 1 天"
fi

echo "  ┌─────────────────────────────────────┐"
echo "  │ 评级: $GRADE                            │"
echo "  │ 建议: $ADVICE"
echo "  └─────────────────────────────────────┘"
echo ""
echo "详细分析请运行: python3 scripts/full_analysis.py $SOURCE_DIR"

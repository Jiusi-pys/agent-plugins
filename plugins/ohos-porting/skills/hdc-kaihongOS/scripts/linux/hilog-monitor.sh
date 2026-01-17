#!/bin/bash
# ============================================================================
# HiLog Monitor for Native Linux
# ============================================================================
# 功能: 实时监控 OpenHarmony 设备日志
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

HDC_CMD="\${HDC_CMD:-hdc}"
TARGET=""
FILTER=""
LOG_LEVEL=""
OUTPUT_FILE=""
FOLLOW=true

show_help() {
    cat << EOF
Usage: \$0 [OPTIONS]

Options:
    -t, --target SERIAL    指定设备序列号
    -f, --filter PATTERN   过滤日志 (grep 模式)
    -l, --level LEVEL      日志级别 (DEBUG/INFO/WARN/ERROR/FATAL)
    -o, --output FILE      输出到文件
    -n, --no-follow        不持续监控 (只显示当前日志)
    -c, --clear            清除设备日志后开始监控
    -h, --help             显示帮助

Log Levels:
    DEBUG   调试信息
    INFO    一般信息
    WARN    警告信息
    ERROR   错误信息
    FATAL   致命错误

Examples:
    \$0                         # 监控所有日志
    \$0 -f "ROS2\|DDS"          # 过滤包含 ROS2 或 DDS 的日志
    \$0 -l ERROR                # 只显示错误日志
    \$0 -o debug.log            # 输出到文件
    \$0 -c -f "myapp"           # 清除日志后监控指定应用
EOF
}

CLEAR_LOG=false

while [[ \$# -gt 0 ]]; do
    case \$1 in
        -t|--target) TARGET="\$2"; shift 2 ;;
        -f|--filter) FILTER="\$2"; shift 2 ;;
        -l|--level) LOG_LEVEL="\$2"; shift 2 ;;
        -o|--output) OUTPUT_FILE="\$2"; shift 2 ;;
        -n|--no-follow) FOLLOW=false; shift ;;
        -c|--clear) CLEAR_LOG=true; shift ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown option: \$1"; show_help; exit 1 ;;
    esac
done

# 检查 HDC
if ! command -v "\$HDC_CMD" &>/dev/null; then
    echo -e "\${RED}[ERROR]\${NC} HDC 未安装"
    exit 1
fi

# 选择设备
if [[ -z "\$TARGET" ]]; then
    DEVICES=\$(\$HDC_CMD list targets 2>/dev/null | grep -v "^\$" || true)
    if [[ -z "\$DEVICES" ]]; then
        echo -e "\${RED}[ERROR]\${NC} 未检测到设备"
        exit 1
    fi
    TARGET=\$(echo "\$DEVICES" | head -1)
fi

HDC="\$HDC_CMD -t \$TARGET"

echo -e "\${GREEN}[HiLog Monitor]\${NC} 目标设备: \$TARGET"

# 清除日志
if [[ "\$CLEAR_LOG" == true ]]; then
    echo -e "\${YELLOW}[INFO]\${NC} 清除设备日志..."
    \$HDC shell "hilog -r" 2>/dev/null || true
fi

# 构建 hilog 命令
HILOG_CMD="hilog"

if [[ -n "\$LOG_LEVEL" ]]; then
    case \$LOG_LEVEL in
        DEBUG|debug) HILOG_CMD="\$HILOG_CMD -L D" ;;
        INFO|info) HILOG_CMD="\$HILOG_CMD -L I" ;;
        WARN|warn) HILOG_CMD="\$HILOG_CMD -L W" ;;
        ERROR|error) HILOG_CMD="\$HILOG_CMD -L E" ;;
        FATAL|fatal) HILOG_CMD="\$HILOG_CMD -L F" ;;
    esac
fi

# 颜色化输出函数
colorize_log() {
    while IFS= read -r line; do
        if [[ "\$line" =~ "ERROR" ]] || [[ "\$line" =~ "FATAL" ]]; then
            echo -e "\${RED}\$line\${NC}"
        elif [[ "\$line" =~ "WARN" ]]; then
            echo -e "\${YELLOW}\$line\${NC}"
        elif [[ "\$line" =~ "DEBUG" ]]; then
            echo -e "\${CYAN}\$line\${NC}"
        else
            echo "\$line"
        fi
    done
}

# 执行监控
echo -e "\${GREEN}[HiLog Monitor]\${NC} 开始监控... (Ctrl+C 退出)"
echo "----------------------------------------"

if [[ "\$FOLLOW" == true ]]; then
    if [[ -n "\$FILTER" ]]; then
        if [[ -n "\$OUTPUT_FILE" ]]; then
            \$HDC shell "\$HILOG_CMD" 2>/dev/null | grep --line-buffered -E "\$FILTER" | tee "\$OUTPUT_FILE" | colorize_log
        else
            \$HDC shell "\$HILOG_CMD" 2>/dev/null | grep --line-buffered -E "\$FILTER" | colorize_log
        fi
    else
        if [[ -n "\$OUTPUT_FILE" ]]; then
            \$HDC shell "\$HILOG_CMD" 2>/dev/null | tee "\$OUTPUT_FILE" | colorize_log
        else
            \$HDC shell "\$HILOG_CMD" 2>/dev/null | colorize_log
        fi
    fi
else
    if [[ -n "\$FILTER" ]]; then
        \$HDC shell "\$HILOG_CMD -x" 2>/dev/null | grep -E "\$FILTER" | colorize_log
    else
        \$HDC shell "\$HILOG_CMD -x" 2>/dev/null | colorize_log
    fi
fi

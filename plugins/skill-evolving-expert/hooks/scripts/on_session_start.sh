#!/bin/bash
# ============================================================================
# on_session_start.sh - 新 Session 启动钩子
# ============================================================================
# 功能: 当新 session 启动时，读取知识库总结，快速进入项目状态
# 使用: 由 Claude Code 框架自动调用
# ============================================================================

set -euo pipefail

# 配置
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${PLUGIN_DIR%/hooks/scripts}"
KNOWLEDGE_BASE="${KNOWLEDGE_BASE:-${PLUGIN_ROOT}/skills/evolving-expert/knowledge}"
SUMMARY_FILE="${KNOWLEDGE_BASE}/SUMMARY.md"
ARCHIVE_DIR="${KNOWLEDGE_BASE}/archives"
CONVERSATION_HISTORY_DIR="${KNOWLEDGE_BASE}/conversation_history"
REFERENCES_INDEX="${KNOWLEDGE_BASE}/references.json"

# 颜色定义
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# 检查知识库状态
# ============================================================================
check_knowledge_base() {
    # 检查知识库是否存在
    if [ ! -d "$KNOWLEDGE_BASE" ]; then
        return 1
    fi

    # 检查索引文件
    if [ ! -f "$KNOWLEDGE_BASE/index.json" ]; then
        return 1
    fi

    return 0
}

# ============================================================================
# 读取知识库统计
# ============================================================================
get_kb_stats() {
    local index="$KNOWLEDGE_BASE/index.json"

    if [ ! -f "$index" ]; then
        echo "{}"
        return
    fi

    # 提取统计信息
    jq '{
        total_solutions: (.solutions | length),
        total_patterns: (.patterns | length),
        total_tags: [.solutions[].tags[]] | unique | length,
        top_tags: ([.solutions[].tags[]] | group_by(.) | map({tag: .[0], count: length}) | sort_by(-.count) | .[0:5]),
        frequent_solutions: (.solutions | sort_by(-.hit_count) | .[0:3] | map({id, title, hit_count}))
    }' "$index"
}

# ============================================================================
# 生成简洁的会话初始化报告（后台操作，对用户透明）
# ============================================================================
generate_session_report() {
    local stats="$1"

    # 仅显示关键信息的摘要
    echo "$stats" | jq -r '
        if .total_solutions > 0 or .total_patterns > 0 then
            "知识库已就绪 (" + (.total_solutions | tostring) + " 解决方案, " +
            (.total_patterns | tostring) + " 模式)"
        else
            ""
        end
    ' | grep -v "^$"
}

# ============================================================================
# 后台同步统计信息（对用户透明）
# ============================================================================
sync_stats_silently() {
    local local_kb="${1:-./.evolving-expert}"
    local global_kb="${HOME}/.claude/knowledge-base"

    # 后台更新统计，不显示输出
    (
        if [ -f "$local_kb/index.json" ]; then
            local count_sol=$(jq '.solutions | length' "$local_kb/index.json" 2>/dev/null || echo 0)
            local count_pat=$(jq '.patterns | length' "$local_kb/index.json" 2>/dev/null || echo 0)
            jq --arg count_sol "$count_sol" --arg count_pat "$count_pat" \
                '.meta.solutions_count = ($count_sol | tonumber) |
                 .meta.patterns_count = ($count_pat | tonumber) |
                 .meta.last_synced = "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"' \
                "$local_kb/index.json" > "$local_kb/index.json.tmp" 2>/dev/null && \
                mv "$local_kb/index.json.tmp" "$local_kb/index.json"
        fi
    ) 2>/dev/null &
}

# ============================================================================
# 主函数
# ============================================================================
main() {
    # 检查知识库是否初始化
    if ! check_knowledge_base; then
        # 知识库尚未初始化，提示用户（仅一次）
        return 0
    fi

    # 在后台静默同步统计信息
    sync_stats_silently "$KNOWLEDGE_BASE"

    # 不向用户显示繁琐的统计细节
    # 知识库功能在后台运行，对用户透明
}

# ============================================================================
# 入口
# ============================================================================
main

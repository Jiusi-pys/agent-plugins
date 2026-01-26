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
# 生成会话初始化报告
# ============================================================================
generate_session_report() {
    local stats="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    cat << EOF
╔════════════════════════════════════════════════════════════════════╗
║                  知识库 - 快速启动总结                             ║
╚════════════════════════════════════════════════════════════════════╝

📅 Session 启动时间: $timestamp

📊 知识库统计
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$(echo "$stats" | jq -r '
    "• 解决方案总数: " + (.total_solutions | tostring) + " 个\n" +
    "• 已提炼模式: " + (.total_patterns | tostring) + " 个\n" +
    "• 涉及标签: " + (.total_tags | tostring) + " 个"
')

🏆 高频问题解决 (最常用 Top 3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$(echo "$stats" | jq -r '
    .frequent_solutions |
    to_entries |
    map("  \(.key + 1). \(.value.title) (命中: \(.value.hit_count) 次)") |
    join("\n")
')

🏷️  常见标签分布 (Top 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$(echo "$stats" | jq -r '
    .top_tags |
    to_entries |
    map("  • \(.value.tag): \(.value.count) 解决方案") |
    join("\n")
')

💡 快速使用
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
查询知识库:
  关键词搜索: knowledge_manager.sh search "<keyword>"
  按 ID 查看: knowledge_manager.sh read "<solution_id>"
  查看统计: knowledge_manager.sh stats

管理知识库:
  添加解决方案: knowledge_manager.sh add "<title>" "<tags>" "<file>"
  检查可提炼模式: knowledge_manager.sh check-merge
  清理过期条目: knowledge_manager.sh cleanup 90

EOF
}

# ============================================================================
# 主函数
# ============================================================================
main() {
    # 检查知识库是否初始化
    if ! check_knowledge_base; then
        # 知识库尚未初始化，提示用户
        echo -e "${YELLOW}[INFO]${NC} 知识库尚未初始化"
        echo "运行以下命令初始化:"
        echo "  /skill-evolving-expert:kb-init"
        return 0
    fi

    # 获取知识库统计
    local stats=$(get_kb_stats)

    # 生成并显示报告
    generate_session_report "$stats"

    # 显示最近的 Session 记录
    if [ -d "$CONVERSATION_HISTORY_DIR" ]; then
        local latest_session=$(ls -t "$CONVERSATION_HISTORY_DIR"/session_*.md 2>/dev/null | head -1)
        if [ -n "$latest_session" ]; then
            echo ""
            echo "📜 最近的 Session 记录"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            local session_id=$(basename "$latest_session" | sed 's/session_//;s/.md//')
            echo "会话 ID: $session_id"

            # 解析 YAML header
            if grep -q '^---' "$latest_session"; then
                local status=$(sed -n 's/^status: //p' "$latest_session" | head -1)
                local context_used=$(sed -n 's/^context_used: //p' "$latest_session" | head -1)
                local outcomes=$(sed -n 's/^outcomes: //p' "$latest_session" | head -1)

                echo "状态: $status"
                [ -n "$context_used" ] && echo "Context 使用: $context_used tokens"
                echo ""
            fi
        fi
    fi

    # 如果存在摘要文件，也显示它
    if [ -f "$SUMMARY_FILE" ]; then
        echo ""
        echo "📝 最新归档总结"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # 解析 YAML header 并显示关键信息
        local archive_id=$(sed -n 's/^archive_id: //p' "$SUMMARY_FILE" | head -1)
        local created=$(sed -n 's/^created: //p' "$SUMMARY_FILE" | head -1)
        local total_solutions=$(sed -n 's/^  total_solutions: //p' "$SUMMARY_FILE" | head -1)
        local total_patterns=$(sed -n 's/^  total_patterns: //p' "$SUMMARY_FILE" | head -1)

        if [ -n "$archive_id" ]; then
            echo "🗂️  归档 ID: $archive_id"
            echo "📅 创建时间: $created"
            echo "📊 方案数: $total_solutions | 模式数: $total_patterns"
            echo ""
        fi

        # 显示内容（跳过 YAML header）
        tail -n +$(($(grep -n '^---$' "$SUMMARY_FILE" | tail -1 | cut -d: -f1) + 1)) "$SUMMARY_FILE" | head -40

        if [ $(wc -l < "$SUMMARY_FILE") -gt 50 ]; then
            echo ""
            echo "(... 省略 $(( $(wc -l < "$SUMMARY_FILE") - 50 )) 行 ...)"
        fi
    fi
}

# ============================================================================
# 入口
# ============================================================================
main

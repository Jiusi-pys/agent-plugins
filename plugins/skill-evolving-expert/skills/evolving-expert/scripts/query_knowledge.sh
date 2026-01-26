#!/bin/bash
# query_knowledge.sh - 智能查询知识库

set -euo pipefail

# 配置
LOCAL_KB="./docs/.evolving-expert"
GLOBAL_KB="$HOME/.claude/knowledge-base"
LOCAL_INDEX="$LOCAL_KB/index.json"
GLOBAL_INDEX="$GLOBAL_KB/index.json"

# ============================================================================
# 辅助函数
# ============================================================================

log_info() {
    echo "[INFO] $*" >&2
}

# 计算相关度分数
calculate_relevance() {
    local solution="$1"
    local keywords="$2"

    local score=0

    # 标签匹配（每个匹配的标签 +10 分）
    IFS=',' read -ra KW_ARRAY <<< "$keywords"
    for kw in "${KW_ARRAY[@]}"; do
        kw=$(echo "$kw" | xargs | tr '[:upper:]' '[:lower:]')
        if echo "$solution" | jq -e ".tags[] | test(\"$kw\"; \"i\")" >/dev/null 2>&1; then
            score=$((score + 10))
        fi
    done

    # 标题匹配（+5 分）
    for kw in "${KW_ARRAY[@]}"; do
        kw=$(echo "$kw" | xargs | tr '[:upper:]' '[:lower:]')
        if echo "$solution" | jq -e ".title | test(\"$kw\"; \"i\")" >/dev/null 2>&1; then
            score=$((score + 5))
        fi
    done

    # 命中次数（每次命中 +1 分）
    local hit_count=$(echo "$solution" | jq '.hit_count // 0')
    score=$((score + hit_count))

    echo "$score"
}

# ============================================================================
# 查询函数
# ============================================================================

query_solutions() {
    local keywords="$1"
    local max_results="${2:-5}"

    log_info "查询关键词: $keywords"

    local all_results="[]"

    # 查询本地知识库
    if [ -f "$LOCAL_INDEX" ]; then
        log_info "查询本地知识库..."

        IFS=',' read -ra KW_ARRAY <<< "$keywords"
        local query_filter='false'

        for kw in "${KW_ARRAY[@]}"; do
            kw=$(echo "$kw" | xargs)
            query_filter="$query_filter or (.tags[] | test(\"$kw\"; \"i\")) or (.title | test(\"$kw\"; \"i\"))"
        done

        local local_results=$(jq --arg source "local" "
            .solutions[] |
            select($query_filter) |
            . + {source: \$source}
        " "$LOCAL_INDEX" 2>/dev/null | jq -s '.')

        all_results=$(jq -s '.[0] + .[1]' <(echo "$all_results") <(echo "$local_results"))
    fi

    # 查询全局知识库
    if [ -f "$GLOBAL_INDEX" ]; then
        log_info "查询全局知识库..."

        IFS=',' read -ra KW_ARRAY <<< "$keywords"
        local query_filter='false'

        for kw in "${KW_ARRAY[@]}"; do
            kw=$(echo "$kw" | xargs)
            query_filter="$query_filter or (.tags[] | test(\"$kw\"; \"i\")) or (.title | test(\"$kw\"; \"i\"))"
        done

        local global_results=$(jq --arg source "global" "
            .solutions[] |
            select($query_filter) |
            . + {source: \$source}
        " "$GLOBAL_INDEX" 2>/dev/null | jq -s '.')

        all_results=$(jq -s '.[0] + .[1]' <(echo "$all_results") <(echo "$global_results"))
    fi

    # 计算相关度并排序
    local total=$(echo "$all_results" | jq 'length')

    if [ "$total" -eq 0 ]; then
        echo "[]"
        return
    fi

    # 添加相关度分数并排序
    local scored_results="[]"
    echo "$all_results" | jq -c '.[]' | while read -r solution; do
        local score=$(calculate_relevance "$solution" "$keywords")
        scored_results=$(jq --argjson sol "$solution" --arg score "$score" \
            '. + [$sol + {relevance_score: ($score | tonumber)}]' \
            <<< "$scored_results")
    done

    # 排序并返回前 N 个
    jq "sort_by(-.relevance_score) | .[0:$max_results]" <<< "$scored_results"
}

# ============================================================================
# 读取解决方案详情
# ============================================================================

read_solution() {
    local solution_id="$1"
    local source="${2:-local}"

    if [ "$source" = "local" ] && [ -f "$LOCAL_INDEX" ]; then
        local file=$(jq -r ".solutions[] | select(.id == \"$solution_id\") | .file" "$LOCAL_INDEX")
        if [ -n "$file" ] && [ "$file" != "null" ] && [ -f "$LOCAL_KB/$file" ]; then
            cat "$LOCAL_KB/$file"

            # 更新命中次数
            jq "(.solutions[] | select(.id == \"$solution_id\")).hit_count += 1" \
               "$LOCAL_INDEX" > "$LOCAL_INDEX.tmp" && \
               mv "$LOCAL_INDEX.tmp" "$LOCAL_INDEX"

            return 0
        fi
    fi

    if [ "$source" = "global" ] && [ -f "$GLOBAL_INDEX" ]; then
        local file=$(jq -r ".solutions[] | select(.id == \"$solution_id\") | .local_file" "$GLOBAL_INDEX")
        if [ -n "$file" ] && [ "$file" != "null" ] && [ -f "$file" ]; then
            cat "$file"

            # 更新命中次数
            jq "(.solutions[] | select(.id == \"$solution_id\")).hit_count += 1" \
               "$GLOBAL_INDEX" > "$GLOBAL_INDEX.tmp" && \
               mv "$GLOBAL_INDEX.tmp" "$GLOBAL_INDEX"

            return 0
        fi
    fi

    log_info "未找到解决方案: $solution_id"
    return 1
}

# ============================================================================
# 格式化输出
# ============================================================================

format_results() {
    local results="$1"
    local total=$(echo "$results" | jq 'length')

    if [ "$total" -eq 0 ]; then
        cat << 'EOF'
❌ 知识库中未找到相关解决方案

建议:
  1. 尝试解决此问题
  2. 问题解决后，记录到知识库
  3. 使用: /knowledge-manager add "标题" "标签" "文件"
EOF
        return
    fi

    cat << EOF
🔍 知识库检索结果

找到 $total 个相关的解决方案：

EOF

    echo "$results" | jq -r 'to_entries[] |
        "\n\(.key + 1). [\(.value.id)] \(.value.title)\n" +
        "   来源: \(.value.source)\n" +
        "   标签: \(.value.tags | join(", "))\n" +
        "   创建时间: \(.value.created)\n" +
        "   命中次数: \(.value.hit_count // 0) 次\n" +
        "   相关度: \(
            if .value.relevance_score >= 15 then "高 ⭐⭐⭐"
            elif .value.relevance_score >= 10 then "中 ⭐⭐"
            else "低 ⭐" end
        )"
    '

    cat << 'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

建议:
  • 优先查看相关度最高的解决方案
  • 使用 Read 工具读取完整内容
  • 评估是否适用于当前问题
  • 如果适用，应用该方案
EOF
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    local keywords="${1:-}"
    local max_results="${2:-5}"

    if [ -z "$keywords" ]; then
        echo "用法: query_knowledge.sh <关键词> [最大结果数]"
        echo ""
        echo "示例:"
        echo "  query_knowledge.sh \"cmake,ros2,error\" 5"
        echo "  query_knowledge.sh \"compilation,build\" 3"
        exit 1
    fi

    # 查询知识库
    local results=$(query_solutions "$keywords" "$max_results")

    # 格式化输出
    format_results "$results"

    # 如果找到结果，提示如何读取
    if [ "$(echo "$results" | jq 'length')" -gt 0 ]; then
        echo ""
        echo "📖 读取完整解决方案："
        echo "$results" | jq -r '.[0] |
            "   bash query_knowledge.sh read \(.id) \(.source)"
        '
    fi
}

# ============================================================================
# 命令入口
# ============================================================================

case "${1:-}" in
    read)
        read_solution "$2" "${3:-local}"
        ;;
    *)
        main "$@"
        ;;
esac

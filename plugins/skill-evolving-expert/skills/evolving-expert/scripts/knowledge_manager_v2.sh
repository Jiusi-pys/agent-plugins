#!/bin/bash
# knowledge_manager_v2.sh - 支持本地和全局知识库的管理脚本

set -e

# 确定知识库路径
WORK_DIR="$(pwd)"
LOCAL_KB="${LOCAL_KB:=$WORK_DIR/docs/.evolving-expert}"
GLOBAL_KB="${GLOBAL_KB:=${HOME}/.claude/knowledge-base}"

LOCAL_INDEX="$LOCAL_KB/index.json"
GLOBAL_INDEX="$GLOBAL_KB/index.json"

# 添加解决方案到本地知识库
add_solution() {
    local title="$1"
    local tags="$2"
    local content_file="$3"

    if [ ! -f "$content_file" ]; then
        echo "错误: 文件不存在 $content_file"
        return 1
    fi

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local topic=$(echo "$title" | tr ' ' '_' | tr -cd '[:alnum:]_' | cut -c1-30)
    local solution_id="${timestamp}_${topic}"
    local solution_file="solutions/${solution_id}.md"

    # 创建解决方案文件
    mkdir -p "$LOCAL_KB/solutions"
    cp "$content_file" "$LOCAL_KB/$solution_file"

    # 构建标签数组
    local tags_json=$(echo "$tags" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | jq -R . | jq -s .)

    # 添加到本地索引
    local entry=$(jq -n \
        --arg id "$solution_id" \
        --arg title "$title" \
        --argjson tags "$tags_json" \
        --arg file "$solution_file" \
        --arg created "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{id: $id, title: $title, tags: $tags, file: $file, created: $created, hit_count: 0}')

    jq --argjson entry "$entry" '.solutions += [$entry]' "$LOCAL_INDEX" > "$LOCAL_INDEX.tmp"
    mv "$LOCAL_INDEX.tmp" "$LOCAL_INDEX"

    # 同步到全局知识库
    if [ -f "$GLOBAL_INDEX" ]; then
        local global_entry=$(jq -n \
            --arg id "$solution_id" \
            --arg title "$title" \
            --argjson tags "$tags_json" \
            --arg workspace "$WORK_DIR" \
            --arg file "$LOCAL_KB/$solution_file" \
            --arg created "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            '{id: $id, title: $title, tags: $tags, workspace: $workspace, local_file: $file, created: $created, hit_count: 0}')

        jq --argjson entry "$global_entry" '.solutions += [$entry]' "$GLOBAL_INDEX" > "$GLOBAL_INDEX.tmp"
        mv "$GLOBAL_INDEX.tmp" "$GLOBAL_INDEX"
    fi
}

# 搜索解决方案
search_solutions() {
    local keyword="$1"
    local scope="${2:-local}"  # local 或 global

    if [ "$scope" = "local" ] && [ -f "$LOCAL_INDEX" ]; then
        jq --arg kw "$keyword" '.solutions[] | select(.title | test($kw; "i") or .tags[] | test($kw; "i"))' "$LOCAL_INDEX"
    elif [ "$scope" = "global" ] && [ -f "$GLOBAL_INDEX" ]; then
        jq --arg kw "$keyword" '.solutions[] | select(.title | test($kw; "i") or .tags[] | test($kw; "i"))' "$GLOBAL_INDEX"
    fi
}

# 读取解决方案
read_solution() {
    local solution_id="$1"

    # 先在本地查找
    if [ -f "$LOCAL_INDEX" ]; then
        local file=$(jq -r --arg id "$solution_id" '.solutions[] | select(.id == $id) | .file' "$LOCAL_INDEX")

        if [ -n "$file" ] && [ -f "$LOCAL_KB/$file" ]; then
            # 更新命中计数
            jq --arg id "$solution_id" '(.solutions[] | select(.id == $id)).hit_count += 1' "$LOCAL_INDEX" > "$LOCAL_INDEX.tmp"
            mv "$LOCAL_INDEX.tmp" "$LOCAL_INDEX"

            # 同步到全局
            if [ -f "$GLOBAL_INDEX" ]; then
                jq --arg id "$solution_id" '(.solutions[] | select(.id == $id)).hit_count += 1' "$GLOBAL_INDEX" > "$GLOBAL_INDEX.tmp"
                mv "$GLOBAL_INDEX.tmp" "$GLOBAL_INDEX"
            fi

            cat "$LOCAL_KB/$file"
            return 0
        fi
    fi

    # 在全局查找
    if [ -f "$GLOBAL_INDEX" ]; then
        local file=$(jq -r --arg id "$solution_id" '.solutions[] | select(.id == $id) | .local_file' "$GLOBAL_INDEX")

        if [ -n "$file" ] && [ -f "$file" ]; then
            jq --arg id "$solution_id" '(.solutions[] | select(.id == $id)).hit_count += 1' "$GLOBAL_INDEX" > "$GLOBAL_INDEX.tmp"
            mv "$GLOBAL_INDEX.tmp" "$GLOBAL_INDEX"

            cat "$file"
            return 0
        fi
    fi

    echo "未找到: $solution_id"
    return 1
}

# 内部：统计解决方案数量
_count_solutions() {
    local index_file="$1"
    [ -f "$index_file" ] && jq '.solutions | length' "$index_file" || echo 0
}

# 内部：统计模式数量
_count_patterns() {
    local index_file="$1"
    [ -f "$index_file" ] && jq '.patterns | length' "$index_file" || echo 0
}

# 获取统计摘要（对用户友好，隐藏细节）
get_stats_summary() {
    local local_solutions=$(_count_solutions "$LOCAL_INDEX")
    local local_patterns=$(_count_patterns "$LOCAL_INDEX")
    local global_solutions=$(_count_solutions "$GLOBAL_INDEX")

    echo "📊 知识库状态"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  本地解决方案: $local_solutions"
    echo "  本地模式: $local_patterns"
    if [ "$global_solutions" -gt 0 ]; then
        echo "  全局可用: $global_solutions"
    fi
}

# 显示用法
show_usage() {
    cat << 'EOF'
用法: knowledge_manager_v2.sh <命令> [参数]

命令:
  add <标题> <标签> <文件>    添加解决方案到本地知识库
  search <关键词> [local|global]  搜索解决方案
  read <id>                   读取解决方案内容
  stats                       显示知识库统计

示例:
  ./knowledge_manager_v2.sh add "修复编译错误" "ros2,compilation" solution.md
  ./knowledge_manager_v2.sh search "编译" local
  ./knowledge_manager_v2.sh read 20260126_123456_fix_compile
  ./knowledge_manager_v2.sh stats
EOF
}

# 主入口
case "$1" in
    add)
        add_solution "$2" "$3" "$4"
        ;;
    search)
        search_solutions "$2" "${3:-local}"
        ;;
    read)
        read_solution "$2"
        ;;
    stats)
        get_stats_summary
        ;;
    *)
        show_usage
        ;;
esac

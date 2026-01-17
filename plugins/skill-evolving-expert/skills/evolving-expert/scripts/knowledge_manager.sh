#!/bin/bash
# knowledge_manager.sh - 知识库管理脚本

KNOWLEDGE_BASE="${KNOWLEDGE_BASE:-./knowledge}"
INDEX_FILE="$KNOWLEDGE_BASE/index.json"

# 初始化知识库
init_kb() {
    mkdir -p "$KNOWLEDGE_BASE"/{solutions,patterns}
    if [ ! -f "$INDEX_FILE" ]; then
        echo '{"solutions":[],"patterns":[]}' > "$INDEX_FILE"
        echo "知识库初始化完成: $KNOWLEDGE_BASE"
    else
        echo "知识库已存在"
    fi
}

# 添加解决方案
# 用法: add_solution "标题" "tag1,tag2,tag3" "内容文件路径"
add_solution() {
    local title="$1"
    local tags="$2"
    local content_file="$3"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local topic=$(echo "$title" | tr ' ' '_' | tr -cd '[:alnum:]_' | cut -c1-30)
    local id="${timestamp}_${topic}"
    local filename="solutions/${id}.md"
    
    # 复制内容到知识库
    cp "$content_file" "$KNOWLEDGE_BASE/$filename"
    
    # 构建标签数组
    local tags_json=$(echo "$tags" | tr ',' '\n' | jq -R . | jq -s .)
    
    # 更新索引
    local new_entry=$(jq -n \
        --arg id "$id" \
        --arg title "$title" \
        --argjson tags "$tags_json" \
        --arg file "$filename" \
        --arg created "$(date +%Y-%m-%d)" \
        '{id: $id, title: $title, tags: $tags, file: $file, created: $created, hit_count: 0}')
    
    jq --argjson entry "$new_entry" '.solutions += [$entry]' "$INDEX_FILE" > "$INDEX_FILE.tmp"
    mv "$INDEX_FILE.tmp" "$INDEX_FILE"
    
    echo "已添加: $id"
}

# 检索解决方案
# 用法: search_solutions "关键词"
search_solutions() {
    local keyword="$1"
    
    echo "=== 按标签检索 ==="
    jq --arg kw "$keyword" '.solutions[] | select(.tags | any(. | test($kw; "i")))' "$INDEX_FILE"
    
    echo ""
    echo "=== 按标题检索 ==="
    jq --arg kw "$keyword" '.solutions[] | select(.title | test($kw; "i"))' "$INDEX_FILE"
}

# 读取解决方案内容
# 用法: read_solution "solution_id"
read_solution() {
    local id="$1"
    local file=$(jq -r --arg id "$id" '.solutions[] | select(.id == $id) | .file' "$INDEX_FILE")
    
    if [ -n "$file" ] && [ -f "$KNOWLEDGE_BASE/$file" ]; then
        # 增加命中计数
        jq --arg id "$id" '(.solutions[] | select(.id == $id)).hit_count += 1' "$INDEX_FILE" > "$INDEX_FILE.tmp"
        mv "$INDEX_FILE.tmp" "$INDEX_FILE"
        
        cat "$KNOWLEDGE_BASE/$file"
    else
        echo "未找到: $id"
        return 1
    fi
}

# 统计信息
stats() {
    echo "=== 知识库统计 ==="
    echo "解决方案数量: $(jq '.solutions | length' "$INDEX_FILE")"
    echo "模式数量: $(jq '.patterns | length' "$INDEX_FILE")"
    echo ""
    echo "=== 标签分布 ==="
    jq '[.solutions[].tags[]] | group_by(.) | map({tag: .[0], count: length}) | sort_by(-.count)' "$INDEX_FILE"
    echo ""
    echo "=== 高频解决方案 Top 5 ==="
    jq '.solutions | sort_by(-.hit_count) | .[0:5] | .[] | {id, title, hit_count}' "$INDEX_FILE"
}

# 检查是否需要模式提炼
check_pattern_merge() {
    local threshold=${1:-3}
    
    echo "=== 可提炼为模式的标签（出现 >= $threshold 次）==="
    jq --argjson t "$threshold" '
        [.solutions[].tags[]] | group_by(.) | 
        map({tag: .[0], count: length}) | 
        map(select(.count >= $t)) | 
        sort_by(-.count)
    ' "$INDEX_FILE"
}

# 清理过期条目
cleanup() {
    local days=${1:-90}
    local cutoff=$(date -d "$days days ago" +%Y-%m-%d 2>/dev/null || date -v-${days}d +%Y-%m-%d)
    
    echo "清理 $cutoff 之前且 hit_count=0 的条目..."
    
    # 列出待清理条目
    jq --arg cutoff "$cutoff" '
        .solutions[] | 
        select(.created < $cutoff and .hit_count == 0) | 
        {id, title, created}
    ' "$INDEX_FILE"
}

# 主入口
case "$1" in
    init)
        init_kb
        ;;
    add)
        add_solution "$2" "$3" "$4"
        ;;
    search)
        search_solutions "$2"
        ;;
    read)
        read_solution "$2"
        ;;
    stats)
        stats
        ;;
    check-merge)
        check_pattern_merge "$2"
        ;;
    cleanup)
        cleanup "$2"
        ;;
    *)
        echo "用法: $0 {init|add|search|read|stats|check-merge|cleanup}"
        echo ""
        echo "命令:"
        echo "  init                        初始化知识库"
        echo "  add <标题> <标签> <文件>    添加解决方案"
        echo "  search <关键词>             检索解决方案"
        echo "  read <id>                   读取解决方案内容"
        echo "  stats                       统计信息"
        echo "  check-merge [阈值]          检查可提炼模式"
        echo "  cleanup [天数]              清理过期条目"
        ;;
esac

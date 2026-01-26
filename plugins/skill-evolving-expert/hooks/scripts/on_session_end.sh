#!/bin/bash
# ============================================================================
# on_session_end.sh - Session 结束钩子 (用于 /clear 或 /exit)
# ============================================================================
# 功能: 当执行 /clear 或 /exit 时，执行知识归档和组织
#       - 扫描高频解决方案，提炼为模式
#       - 生成知识库总结
#       - 创建时间戳式档案
# 使用: 由 Claude Code 框架自动调用
# ============================================================================

set -euo pipefail

# 配置
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${PLUGIN_DIR%/hooks/scripts}"
KNOWLEDGE_BASE="${KNOWLEDGE_BASE:-${PLUGIN_ROOT}/skills/evolving-expert/knowledge}"
SCRIPT_DIR="${PLUGIN_ROOT}/skills/evolving-expert/scripts"
HOOKS_SCRIPT_DIR="${PLUGIN_DIR}"
INDEX_FILE="$KNOWLEDGE_BASE/index.json"
ARCHIVE_DIR="${KNOWLEDGE_BASE}/archives"
SUMMARY_FILE="${KNOWLEDGE_BASE}/SUMMARY.md"
CONVERSATION_HISTORY_DIR="${KNOWLEDGE_BASE}/conversation_history"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# 检查依赖
# ============================================================================
check_dependencies() {
    if [ ! -f "$SCRIPT_DIR/knowledge_manager.sh" ]; then
        echo -e "${RED}[ERROR]${NC} knowledge_manager.sh 不存在" >&2
        return 1
    fi

    if [ ! -f "$INDEX_FILE" ]; then
        echo -e "${YELLOW}[INFO]${NC} 知识库未初始化，跳过归档" >&2
        return 0
    fi

    return 0
}

# ============================================================================
# 创建档案目录
# ============================================================================
prepare_archive_dir() {
    if [ ! -d "$ARCHIVE_DIR" ]; then
        mkdir -p "$ARCHIVE_DIR"
    fi
}

# ============================================================================
# 统计知识库信息
# ============================================================================
get_knowledge_stats() {
    if [ ! -f "$INDEX_FILE" ]; then
        echo "{}"
        return
    fi

    jq '{
        timestamp: now | todate,
        total_solutions: (.solutions | length),
        total_patterns: (.patterns | length),
        total_tags: [.solutions[].tags[]] | unique | length,
        top_tags: ([.solutions[].tags[]] | group_by(.) | map({tag: .[0], count: length}) | sort_by(-.count) | .[0:10]),
        frequent_solutions: (.solutions | sort_by(-.hit_count) | .[0:10] | map({id, title, hit_count, tags}))
    }' "$INDEX_FILE"
}

# ============================================================================
# 检查并提炼高频模式
# ============================================================================
extract_patterns() {
    local threshold=${1:-3}

    if [ ! -f "$INDEX_FILE" ]; then
        return 0
    fi

    echo -e "${BLUE}[INFO]${NC} 检查可提炼的高频模式..."

    # 获取出现次数 >= 阈值的标签
    local patterns=$(jq --argjson t "$threshold" '
        [.solutions[].tags[]] |
        group_by(.) |
        map({tag: .[0], count: length}) |
        map(select(.count >= $t))
    ' "$INDEX_FILE")

    local pattern_count=$(echo "$patterns" | jq 'length')

    if [ "$pattern_count" -gt 0 ]; then
        echo -e "${GREEN}[INFO]${NC} 发现 $pattern_count 个可提炼模式"

        # 生成模式总结
        echo "$patterns" | jq -r '.[] | "- \(.tag) (出现 \(.count) 次)"' | while read line; do
            echo "  $line"
        done
    else
        echo -e "${YELLOW}[INFO]${NC} 没有发现可提炼的高频模式"
    fi
}

# ============================================================================
# 生成知识库总结
# ============================================================================
generate_summary() {
    local stats="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local iso_timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    local archive_timestamp=$(date '+%Y%m%d_%H%M%S')

    echo -e "${BLUE}[INFO]${NC} 生成知识库总结..."

    # 生成带 YAML header 的总结
    cat > "$SUMMARY_FILE" << EOF
---
title: 知识库档案 - $timestamp
archive_id: ${archive_timestamp}
created: ${iso_timestamp}
version: 1.0.0
agent: skill-evolving-expert
metadata:
  total_solutions: $(echo "$stats" | jq '.total_solutions')
  total_patterns: $(echo "$stats" | jq '.total_patterns')
  total_tags: $(echo "$stats" | jq '.total_tags')
  solutions_added_this_session: 0
  patterns_discovered: 0
description: Session 结束时的知识库快照，包含统计信息和最常用方案
tags: [knowledge-archive, session-summary]
references:
  - type: archive
    id: knowledge_archive_${archive_timestamp}
    path: archives/knowledge_archive_${archive_timestamp}.tar.gz
    size_bytes: 0
---

# 知识库档案 - $timestamp

## 📊 知识库快照

| 指标 | 数值 |
|------|------|
| 解决方案 | $(echo "$stats" | jq '.total_solutions') 个 |
| 已提炼模式 | $(echo "$stats" | jq '.total_patterns') 个 |
| 涉及标签 | $(echo "$stats" | jq '.total_tags') 个 |

## 🏆 最常用解决方案 (Top 10)

$(echo "$stats" | jq -r '
    .frequent_solutions |
    to_entries |
    map("### \(.key + 1). \(.value.title)")  +
    .frequent_solutions |
    to_entries |
    map("- **命中**: \(.value.hit_count) 次")  +
    .frequent_solutions |
    to_entries |
    map("- **标签**: \(.value.tags | join(\", \"))")  |
    map("- **ID**: \`\(.value.id)\`\n") |
    join("\n---\n\n")
')

## 🏷️ 标签分布 (Top 10)

$(echo "$stats" | jq -r '
    .top_tags |
    to_entries |
    map("\(.key + 1). **\(.value.tag)**: \(.value.count) 解决方案") |
    join("\n")
')

## 📝 归档信息

- **创建时间**: $timestamp
- **档案 ID**: $archive_timestamp
- **知识库路径**: $KNOWLEDGE_BASE

---

## 使用指南

### 快速检索
\`\`\`bash
knowledge_manager.sh search "<关键词>"
knowledge_manager.sh read "<solution_id>"
\`\`\`

### 添加新解决方案
\`\`\`bash
knowledge_manager.sh add "标题" "tag1,tag2,tag3" solution.md
\`\`\`

### 查看统计
\`\`\`bash
knowledge_manager.sh stats
knowledge_manager.sh check-merge
\`\`\`

---

**文件自动生成，最后修改**: $timestamp
EOF

    echo -e "${GREEN}[INFO]${NC} 总结已生成: $SUMMARY_FILE"
}

# ============================================================================
# 创建时间戳式档案
# ============================================================================
create_timestamped_archive() {
    local archive_timestamp=$(date '+%Y%m%d_%H%M%S')
    local archive_name="knowledge_archive_${archive_timestamp}.tar.gz"
    local archive_path="$ARCHIVE_DIR/$archive_name"

    echo -e "${BLUE}[INFO]${NC} 创建时间戳式档案..."

    # 归档知识库（不包括 archives 目录本身）
    tar -czf "$archive_path" \
        -C "$KNOWLEDGE_BASE" \
        --exclude='archives' \
        .

    if [ -f "$archive_path" ]; then
        local size=$(du -h "$archive_path" | cut -f1)
        echo -e "${GREEN}[INFO]${NC} 档案已创建: $archive_path ($size)"

        # 更新档案清单
        echo "$archive_timestamp $(basename $archive_path)" >> "$ARCHIVE_DIR/manifest.txt"
    else
        echo -e "${RED}[ERROR]${NC} 创建档案失败" >&2
        return 1
    fi
}

# ============================================================================
# 清理过期解决方案
# ============================================================================
cleanup_stale_solutions() {
    local days=${1:-90}

    echo -e "${BLUE}[INFO]${NC} 清理 $days 天前且未被使用过的解决方案..."

    if [ ! -f "$SCRIPT_DIR/knowledge_manager.sh" ]; then
        echo -e "${YELLOW}[WARN]${NC} knowledge_manager.sh 不可用，跳过清理" >&2
        return 0
    fi

    # 统计待清理条目（仅显示，不删除）
    local cutoff=$(date -d "$days days ago" +%Y-%m-%d 2>/dev/null || date -v-${days}d +%Y-%m-%d)
    local stale_count=$(jq --arg cutoff "$cutoff" '
        [.solutions[] | select(.created < $cutoff and .hit_count == 0)] | length
    ' "$INDEX_FILE" 2>/dev/null || echo 0)

    if [ "$stale_count" -gt 0 ]; then
        echo -e "${YELLOW}[INFO]${NC} 发现 $stale_count 个可清理条目"
        jq --arg cutoff "$cutoff" '
            .solutions[] |
            select(.created < $cutoff and .hit_count == 0) |
            {id, title, created}
        ' "$INDEX_FILE" 2>/dev/null | while read -r line; do
            echo "  - $line"
        done
    else
        echo -e "${GREEN}[INFO]${NC} 无需清理"
    fi
}

# ============================================================================
# 生成档案报告
# ============================================================================
print_archive_report() {
    local stats="$1"

    cat << EOF

╔════════════════════════════════════════════════════════════════════╗
║              知识库归档与组织完成                                  ║
╚════════════════════════════════════════════════════════════════════╝

✅ 已完成的操作:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✓ 知识库扫描
  ✓ 高频模式检查
  ✓ 生成总结文档
  ✓ 时间戳档案备份
  ✓ 清理过期条目分析

📊 本次归档统计:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • 解决方案: $(echo "$stats" | jq '.total_solutions') 个
  • 已提炼模式: $(echo "$stats" | jq '.total_patterns') 个
  • 涉及标签: $(echo "$stats" | jq '.total_tags') 个

📁 档案位置:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • 总结文档: $SUMMARY_FILE
  • 备份档案: $ARCHIVE_DIR/

💡 下次 Session 启动时，会自动显示本次归档总结。

EOF
}

# ============================================================================
# 主函数
# ============================================================================
main() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}       知识库自动归档 - Session 结束钩子${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # 检查依赖
    if ! check_dependencies; then
        echo -e "${YELLOW}[SKIP]${NC} 知识库不可用，跳过归档"
        return 0
    fi

    # 准备档案目录
    prepare_archive_dir

    # 获取知识库统计
    local stats=$(get_knowledge_stats)

    # 如果知识库是空的，直接返回
    local total_solutions=$(echo "$stats" | jq '.total_solutions')
    if [ "$total_solutions" -eq 0 ]; then
        echo -e "${YELLOW}[INFO]${NC} 知识库为空，无需归档"
        return 0
    fi

    # 执行归档操作
    extract_patterns 3
    echo ""

    generate_summary "$stats"
    echo ""

    create_timestamped_archive
    echo ""

    cleanup_stale_solutions 90
    echo ""

    # 打印报告
    print_archive_report "$stats"
}

# ============================================================================
# 入口
# ============================================================================
main

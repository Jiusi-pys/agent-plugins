#!/bin/bash
# preload_knowledge_summary.sh - 在 SessionStart 时预加载知识摘要

set -euo pipefail

# 配置
WORK_DIR="$(pwd)"
LOCAL_KB="./docs/.evolving-expert"
GLOBAL_KB="$HOME/.claude/knowledge-base"
LOCAL_INDEX="$LOCAL_KB/index.json"
GLOBAL_INDEX="$GLOBAL_KB/index.json"

# CLAUDE.md 路径
CLAUDE_MD="./CLAUDE.md"

# ============================================================================
# 生成知识库摘要
# ============================================================================

generate_knowledge_summary() {
    local summary=""

    # 统计本地知识库
    local local_count=0
    if [ -f "$LOCAL_INDEX" ]; then
        local_count=$(jq '.solutions | length' "$LOCAL_INDEX" 2>/dev/null || echo 0)
    fi

    # 统计全局知识库
    local global_count=0
    if [ -f "$GLOBAL_INDEX" ]; then
        global_count=$(jq '.solutions | length' "$GLOBAL_INDEX" 2>/dev/null || echo 0)
    fi

    # 如果知识库为空，不生成摘要
    if [ "$local_count" -eq 0 ] && [ "$global_count" -eq 0 ]; then
        return
    fi

    # 生成摘要标题
    summary="## 📚 可用的知识库资源\n\n"
    summary="${summary}**重要**：遇到任何问题时，优先查询知识库中的已有解决方案，避免重复工作。\n\n"

    # 本地知识库摘要
    if [ "$local_count" -gt 0 ]; then
        summary="${summary}### 本地知识库 (当前项目)\n\n"
        summary="${summary}**解决方案总数**: $local_count\n\n"

        # 列出高频解决方案
        if [ -f "$LOCAL_INDEX" ]; then
            local top_solutions=$(jq -r '
                .solutions |
                sort_by(-.hit_count) |
                .[0:5] |
                .[] |
                "- [\(.id)] \(.title) (标签: \(.tags | join(", "))) - 使用 \(.hit_count) 次"
            ' "$LOCAL_INDEX" 2>/dev/null)

            if [ -n "$top_solutions" ]; then
                summary="${summary}**常用解决方案**:\n${top_solutions}\n\n"
            fi

            # 列出常见标签
            local top_tags=$(jq -r '
                [.solutions[].tags[]] |
                group_by(.) |
                map({tag: .[0], count: length}) |
                sort_by(-.count) |
                .[0:8] |
                .[] |
                "  - \(.tag): \(.count) 个方案"
            ' "$LOCAL_INDEX" 2>/dev/null)

            if [ -n "$top_tags" ]; then
                summary="${summary}**主要标签**:\n${top_tags}\n\n"
            fi
        fi
    fi

    # 全局知识库摘要
    if [ "$global_count" -gt 0 ]; then
        summary="${summary}### 全局知识库 (跨项目)\n\n"
        summary="${summary}**解决方案总数**: $global_count (来自多个项目)\n\n"

        # 列出最相关的解决方案（与当前工作目录相关）
        if [ -f "$GLOBAL_INDEX" ]; then
            local workspace_name=$(basename "$WORK_DIR")

            # 尝试找到与当前项目相关的解决方案
            local relevant_solutions=$(jq -r --arg ws "$workspace_name" '
                .solutions[] |
                select(.tags[] | test($ws; "i")) |
                "- [\(.id)] \(.title) (来自: \(.workspace // "未知"))"
            ' "$GLOBAL_INDEX" 2>/dev/null | head -5)

            if [ -n "$relevant_solutions" ]; then
                summary="${summary}**可能相关的方案**:\n${relevant_solutions}\n\n"
            fi
        fi
    fi

    # 使用说明
    summary="${summary}### 如何查询知识库\n\n"
    summary="${summary}当遇到问题时：\n"
    summary="${summary}1. **自动查询** - 告诉我你遇到的问题，我会自动查询知识库\n"
    summary="${summary}2. **手动查询** - 明确要求：\"查询知识库中关于 <关键词> 的解决方案\"\n"
    summary="${summary}3. **浏览所有** - 查看 \`$LOCAL_INDEX\` 和 \`$GLOBAL_INDEX\`\n\n"

    summary="${summary}**示例**:\n"
    summary="${summary}- \"查询知识库中关于 cmake 编译的解决方案\"\n"
    summary="${summary}- \"之前解决过这个 ROS2 配置问题吗？\"\n"
    summary="${summary}- \"检索关于 DSoftBus 的文档\"\n\n"

    summary="${summary}---\n\n"

    echo -e "$summary"
}

# ============================================================================
# 更新 CLAUDE.md
# ============================================================================

update_claude_md() {
    local summary="$1"

    if [ -z "$summary" ]; then
        # 知识库为空，不更新
        return
    fi

    # 检查 CLAUDE.md 是否存在
    if [ ! -f "$CLAUDE_MD" ]; then
        # 创建新的 CLAUDE.md
        cat > "$CLAUDE_MD" << 'EOF'
# CLAUDE.md

此文件为 Claude Code 提供项目特定的上下文和指导。

EOF
    fi

    # 检查是否已有知识库部分
    if grep -q "## 📚 可用的知识库资源" "$CLAUDE_MD" 2>/dev/null; then
        # 删除旧的知识库部分
        sed -i '/## 📚 可用的知识库资源/,/^---$/d' "$CLAUDE_MD"
    fi

    # 追加新的知识库摘要
    echo -e "\n$summary" >> "$CLAUDE_MD"

    log_info "知识库摘要已更新到 CLAUDE.md"
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    # 生成知识库摘要
    local summary=$(generate_knowledge_summary)

    # 更新到 CLAUDE.md
    update_claude_md "$summary"

    # 静默完成（对用户透明）
}

main

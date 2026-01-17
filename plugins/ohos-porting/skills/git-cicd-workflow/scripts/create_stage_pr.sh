#!/bin/bash
#
# Stage Draft PR 创建脚本
# 用途：基于 Stage 总结创建 Draft PR
#

set -e

# 参数解析
TRACK="$1"
STAGE="$2"

if [ -z "$TRACK" ] || [ -z "$STAGE" ]; then
    echo "用法: $0 <track> <stage>"
    echo
    echo "示例:"
    echo "  $0 track1 stage1"
    echo "  $0 rmw-dsoftbus-dev core-infrastructure"
    exit 1
fi

# Stage 总结文件路径
SUMMARY_FILE="docs/progress/$TRACK/$STAGE/STAGE_SUMMARY.md"

# 检查总结文件是否存在
if [ ! -f "$SUMMARY_FILE" ]; then
    echo "❌ 错误: Stage 总结文件不存在"
    echo "   期望路径: $SUMMARY_FILE"
    echo
    echo "请先生成 Stage 总结报告"
    exit 1
fi

# 提取 Stage 标题（从第一个 # 标题）
STAGE_TITLE=$(grep -m 1 '^# ' "$SUMMARY_FILE" | sed 's/^# //')

if [ -z "$STAGE_TITLE" ]; then
    STAGE_TITLE="$STAGE"
fi

# PR 标题
PR_TITLE="[$TRACK/$STAGE] $STAGE_TITLE"

# PR 正文（从总结文件）
PR_BODY=$(cat "$SUMMARY_FILE")

echo "=== 创建 Draft PR ==="
echo "Title: $PR_TITLE"
echo "Body from: $SUMMARY_FILE"
echo

# 检查 gh 命令是否可用
if ! command -v gh &> /dev/null; then
    echo "❌ 错误: gh (GitHub CLI) 未安装"
    echo "   安装: https://cli.github.com/"
    exit 1
fi

# 创建 Draft PR
echo "Creating Draft PR..."
gh pr create \
    --title "$PR_TITLE" \
    --body "$PR_BODY" \
    --draft

if [ $? -eq 0 ]; then
    echo
    echo "✅ Draft PR created successfully"
    echo
    echo "下一步:"
    echo "  1. 运行集成测试"
    echo "  2. 测试通过后: gh pr ready <pr-number>"
    echo "  3. Code review"
    echo "  4. Review 通过后: gh pr merge <pr-number> --squash"
else
    echo "❌ PR 创建失败"
    exit 1
fi

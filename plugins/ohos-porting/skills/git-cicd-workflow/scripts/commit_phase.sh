#!/bin/bash
#
# Phase Commit 自动化脚本
# 用途：生成符合规范的 Phase commit message
#

set -e

# 参数解析
TRACK="$1"
STAGE="$2"
PHASE="$3"
MESSAGE="$4"
TYPE="${5:-feat}"

if [ -z "$TRACK" ] || [ -z "$STAGE" ] || [ -z "$PHASE" ] || [ -z "$MESSAGE" ]; then
    echo "用法: $0 <track> <stage> <phase> <message> [type]"
    echo
    echo "示例:"
    echo "  $0 track1 stage1 phase1 '初始化框架' feat"
    echo "  $0 track1 stage2 phase3 '修复权限问题' fix"
    echo
    echo "Type 选项: feat, fix, refactor, docs, test, build"
    exit 1
fi

# 生成 commit message
COMMIT_MSG_FILE="/tmp/commit_msg_$$.txt"

cat > "$COMMIT_MSG_FILE" <<EOF
[$TRACK/$STAGE/$PHASE] $MESSAGE ($TYPE)

Phase: $PHASE
Stage: $STAGE
Track: $TRACK

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF

# 显示 commit message
echo "=== Commit Message ==="
cat "$COMMIT_MSG_FILE"
echo "===================="
echo

# 执行 git add
echo "Adding files..."
git add .

# 执行 commit
echo "Committing..."
git commit -F "$COMMIT_MSG_FILE"

# 清理
rm -f "$COMMIT_MSG_FILE"

# 显示 commit 信息
echo
echo "✅ Phase commit completed"
echo
git log -1 --oneline

# 提示推送
echo
echo "推送到远程:"
echo "  git push origin $TRACK/$STAGE/$PHASE"

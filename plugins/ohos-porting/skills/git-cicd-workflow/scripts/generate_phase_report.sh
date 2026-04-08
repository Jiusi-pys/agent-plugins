#!/bin/bash
#
# Phase 报告生成脚本
# 用途：生成符合规范的 Phase 完成报告
#

set -e

# 参数解析
TRACK="$1"
STAGE="$2"
PHASE="$3"

if [ -z "$TRACK" ] || [ -z "$STAGE" ] || [ -z "$PHASE" ]; then
    echo "用法: $0 <track> <stage> <phase>"
    echo
    echo "示例:"
    echo "  $0 track1 stage1 phase1"
    exit 1
fi

# 报告文件路径
REPORT_DIR="docs/progress/$TRACK/$STAGE"
REPORT_FILE="$REPORT_DIR/${PHASE}_report.md"

# 创建目录
mkdir -p "$REPORT_DIR"

# 获取最近的 commit 信息
LAST_COMMIT_HASH=$(git log -1 --format="%H")
LAST_COMMIT_SHORT=$(git log -1 --format="%h")
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

# 获取改动的文件
CHANGED_FILES=$(git diff --name-status HEAD~1 HEAD 2>/dev/null || echo "")

# 生成报告模板
cat > "$REPORT_FILE" <<EOF
# Phase 完成报告: $PHASE

## Phase 信息
- **Phase**: $PHASE
- **Stage**: $STAGE
- **Track**: $TRACK
- **完成时间**: $TIMESTAMP
- **Commit**: $LAST_COMMIT_SHORT

## 改动概述
<请填写本 Phase 的主要改动>

## 代码改动详情

### 文件改动列表
\`\`\`
$CHANGED_FILES
\`\`\`

### 新增文件
<列出新增的文件及其用途>

### 修改文件
<列出修改的文件及其改动内容>

## 编译和测试

### 编译
- 编译命令: \`make -f Makefile.aarch64 all\`
- 编译状态: ⬜ 待测试 / ✅ 通过 / ❌ 失败
- 编译输出: <如有错误，粘贴错误信息>

### 单元测试
- 测试命令: <test-command>
- 测试状态: ⬜ 待测试 / ✅ 通过 / ❌ 失败
- 测试结果: <summary>

### 设备验证
- 部署设备: Device <device-id>
- 验证命令: <command>
- 验证状态: ⬜ 待测试 / ✅ 通过 / ❌ 失败
- 验证结果: <summary>

## 遇到的问题和解决方案

### 问题 1: <如有问题>

**错误信息**:
\`\`\`
<error-output>
\`\`\`

**相关 Issue**: #<issue-number>（如果查到）

**解决方案**:
<解决步骤>

**参考文档**:
- \`<skill-or-doc-path>\`

**结果**: ✅ 已解决 / ⚠️ 临时方案 / ❌ 未解决

## 参考的 Skills 和文档
- \`ohos-cpp-style/SKILL.md\` - <使用的规范>
- \`ohos-cpp-style/references/<doc>.md\` - <参考的详细文档>
- \`ohos-cross-compile/references/<doc>.md\` - <参考的编译文档>

## 下一步
Phase <next-phase>: <description>

---

**生成时间**: $TIMESTAMP
**Commit**: $LAST_COMMIT_HASH
EOF

echo "✅ Phase 报告已生成: $REPORT_FILE"
echo
echo "请编辑报告，填写详细内容："
echo "  \${EDITOR:-vi} $REPORT_FILE"
echo
echo "编辑完成后执行 commit："
echo "  ./scripts/git-workflow/commit_phase.sh $TRACK $STAGE $PHASE '<message>' <type>"

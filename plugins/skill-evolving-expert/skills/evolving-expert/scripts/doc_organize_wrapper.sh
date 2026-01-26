#!/bin/bash
# doc_organize_wrapper.sh - 文档整理命令的包装脚本
# 用于 Claude Code slash-command 调用

set -euo pipefail

# 默认参数
SCAN_ROOT="."
DEFAULT_TAGS="documentation,legacy"
EXCLUDE_DIRS=""
OUTPUT_DIR="./docs/.evolving-expert/archives"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --scan-root)
            SCAN_ROOT="$2"
            shift 2
            ;;
        --default-tags)
            DEFAULT_TAGS="$2"
            shift 2
            ;;
        --exclude)
            EXCLUDE_DIRS="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# 主逻辑
# ============================================================================

echo "📚 开始文档整理..."
echo ""
echo "扫描设置："
echo "  扫描根目录: $SCAN_ROOT"
echo "  默认标签: $DEFAULT_TAGS"
echo "  输出目录: $OUTPUT_DIR"
echo ""

# 检查和初始化知识库
if [ ! -d "./docs/.evolving-expert" ]; then
    echo "初始化本地知识库目录..."
    mkdir -p "./docs/.evolving-expert"/{solutions,patterns,archives/imported}
    echo "✓ 知识库目录已创建"
fi

# 运行扫描脚本
echo "正在扫描文档..."
ORGANIZE_SCRIPT="${SCRIPT_DIR}/organize_documents_v2.sh"

if [ ! -f "$ORGANIZE_SCRIPT" ]; then
    echo "错误: 找不到脚本 $ORGANIZE_SCRIPT"
    exit 1
fi

# 调用扫描脚本
SCAN_ROOT="$SCAN_ROOT" \
OUTPUT_DIR="$OUTPUT_DIR" \
DEFAULT_TAGS="$DEFAULT_TAGS" \
bash "$ORGANIZE_SCRIPT"

# ============================================================================
# 显示结果
# ============================================================================

echo ""
echo "✓ 文档整理完成！"
echo ""

# 显示报告
if [ -f "$OUTPUT_DIR/report.txt" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat "$OUTPUT_DIR/report.txt"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

echo ""

# 显示统计摘要
if [ -f "$OUTPUT_DIR/metadata.json" ]; then
    echo "📊 统计摘要"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    TOTAL_DOCS=$(jq '.scan.files_imported' "$OUTPUT_DIR/metadata.json" 2>/dev/null || echo 0)
    TOTAL_LINES=$(jq '.statistics.total_lines' "$OUTPUT_DIR/metadata.json" 2>/dev/null || echo 0)
    TOTAL_SIZE=$(jq '.statistics.total_size' "$OUTPUT_DIR/metadata.json" 2>/dev/null || echo 0)

    echo "  文档总数: $TOTAL_DOCS"
    echo "  总行数: $TOTAL_LINES"
    echo "  总大小: $TOTAL_SIZE bytes"
    echo ""

    # 显示标签分布
    echo "🏷️  标签分布"
    jq -r '.documents[].tags[]' "$OUTPUT_DIR/metadata.json" 2>/dev/null | \
        sort | uniq -c | sort -rn | head -10 | \
        while read count tag; do
            printf "  • %s: %d 文档\n" "$tag" "$count"
        done || echo "  (暂无标签)"

    echo ""

    # 显示文档清单（前5个）
    echo "📋 导入的文档清单 (前 5 个)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    jq -r '.documents[] | "  [\(.import_id)] \(.title)\n      路径: \(.original_path)\n      标签: \(.tags | join(", "))"' \
        "$OUTPUT_DIR/metadata.json" 2>/dev/null | head -30 || echo "  (暂无文档)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 后续步骤
echo "✅ 后续步骤："
echo ""
echo "1️⃣ 查看完整报告:"
echo "   cat $OUTPUT_DIR/report.txt"
echo ""
echo "2️⃣ 查看元数据索引 (JSON):"
echo "   cat $OUTPUT_DIR/metadata.json | jq ."
echo ""
echo "3️⃣ 将文档导入知识库 (批量):"
echo "   for doc in $OUTPUT_DIR/imported/*.md; do"
echo '       filename=$(basename "$doc" .md)'
echo '       title=$(jq -r ".documents[] | select(.import_id == \\"$filename\\") | .title" \'
echo "           $OUTPUT_DIR/metadata.json)"
echo '       tags=$(jq -r ".documents[] | select(.import_id == \\"$filename\\") | .tags | join(\\",\\")" \'
echo "           $OUTPUT_DIR/metadata.json)"
echo "       knowledge_manager_v2.sh add \"\$title\" \"\$tags\" \"\$doc\""
echo "   done"
echo ""
echo "4️⃣ 查看已归档文档:"
echo "   ls -lh $OUTPUT_DIR/imported/"
echo ""

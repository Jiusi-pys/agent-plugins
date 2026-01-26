#!/bin/bash
# generate_archive_report.sh - 生成详细的文档归档报告

set -e

WORK_DIR="$(pwd)"
ARCHIVE_DIR="${1:-./.evolving-expert/archives}"
METADATA_FILE="$ARCHIVE_DIR/metadata.json"

if [ ! -f "$METADATA_FILE" ]; then
    echo "错误: 找不到元数据文件 $METADATA_FILE"
    exit 1
fi

# ============================================================================
# 报告生成
# ============================================================================

cat << 'HEADER'
╔════════════════════════════════════════════════════════════════════╗
║                      📚 文档归档报告                               ║
╚════════════════════════════════════════════════════════════════════╝

HEADER

echo "扫描信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
jq -r '.scan | "  扫描时间: \(.timestamp)\n  扫描目录: \(.scan_root)\n  导入文件: \(.files_imported) 个\n  总大小: \(.total_size_bytes) bytes"' "$METADATA_FILE"

echo ""
echo "文档统计"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

local_lines=$(jq '.statistics.total_lines' "$METADATA_FILE")
local_size=$(jq '.statistics.total_size' "$METADATA_FILE")
local_docs=$(jq '.documents | length' "$METADATA_FILE")

echo "  文档总数: $local_docs"
echo "  总行数: $local_lines"
echo "  总大小: $local_size bytes"
if [ "$local_docs" -gt 0 ]; then
    avg_size=$((local_size / local_docs))
    avg_lines=$((local_lines / local_docs))
    echo "  平均文档大小: $avg_size bytes"
    echo "  平均行数: $avg_lines lines"
fi

echo ""
echo "标签分布"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

jq -r '.documents[].tags[]' "$METADATA_FILE" | sort | uniq -c | sort -rn | head -10 | \
while read count tag; do
    printf "  • %s: %d 文档\n" "$tag" "$count"
done

echo ""
echo "最大的文档 (Top 5)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

jq -r '.documents | sort_by(-.file_size) | .[0:5][] | "  \(.title): \(.file_size) bytes (\(.line_count) lines)"' "$METADATA_FILE"

echo ""
echo "导入的文档清单"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

jq -r '.documents[] | "  [\(.import_id)] \(.title)\n      路径: \(.original_path)\n      标签: \(.tags | join(", "))\n      大小: \(.file_size) bytes | 行数: \(.line_count)"' "$METADATA_FILE"

echo ""
echo "总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  归档目录: $ARCHIVE_DIR"
echo "  元数据: $ARCHIVE_DIR/metadata.json"
echo "  报告: 本报告"
echo "  文档文件: $ARCHIVE_DIR/imported/"

echo ""
echo "后续步骤"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. 查看元数据: jq . $METADATA_FILE"
echo "  2. 将文档导入知识库:"
echo "     knowledge_manager_v2.sh add '文档标题' '标签' '文件路径'"
echo "  3. 关联到解决方案: 编辑 metadata.json 添加 related_solutions 字段"

#!/bin/bash
# organize_documents_v2.sh - 简化和改进的文档整理脚本

set -euo pipefail

# 配置
WORK_DIR="$(pwd)"
SCAN_ROOT="${SCAN_ROOT:-.}"
OUTPUT_DIR="${OUTPUT_DIR:-./.evolving-expert/archives}"
DEFAULT_TAGS="${DEFAULT_TAGS:-documentation,legacy}"

# 创建输出目录
mkdir -p "$OUTPUT_DIR/imported"

echo "[INFO] 扫描根目录: $SCAN_ROOT"
echo "[INFO] 输出目录: $OUTPUT_DIR"

# ============================================================================
# 辅助函数
# ============================================================================

extract_title() {
    local file="$1"

    # 从 Markdown H1 提取
    if grep -q "^# " "$file" 2>/dev/null; then
        grep -m1 "^# " "$file" | sed 's/^# //'
        return
    fi

    # 从 YAML header 提取
    if grep -q "^title:" "$file" 2>/dev/null; then
        sed -n 's/^title: //p' "$file" | head -1
        return
    fi

    # 默认使用文件名
    basename "$file" | sed 's/\.[^.]*$//' | tr '_-' ' '
}

extract_summary() {
    local file="$1"

    # 跳过 YAML header 和标题，获取前几行
    sed '1,/^---$/d' "$file" | \
        grep -v "^# " | \
        grep -v "^#" | \
        sed '/^[[:space:]]*$/d' | \
        head -3 | \
        tr '\n' ' ' | \
        sed 's/[*`\[\]]//g' | \
        cut -c1-150
}

analyze_tags() {
    local file="$1"
    local dir_path="$2"
    local filename=$(basename "$file")

    local tags=("$DEFAULT_TAGS")

    # 基于目录路径添加标签
    if [[ $dir_path == *"docs"* ]]; then
        tags+=("documentation")
    fi
    if [[ $dir_path == *"api"* ]]; then
        tags+=("api")
    fi
    if [[ $dir_path == *"guide"* ]] || [[ $dir_path == *"tutorial"* ]]; then
        tags+=("guide")
    fi

    # 基于文件名添加标签
    if [[ $filename == *"setup"* ]] || [[ $filename == *"install"* ]]; then
        tags+=("setup")
    fi
    if [[ $filename == *"build"* ]] || [[ $filename == *"cmake"* ]]; then
        tags+=("build")
    fi

    # 去重并输出为 JSON 数组
    printf '%s\n' "${tags[@]}" | sort -u | jq -R . | jq -s .
}

# ============================================================================
# 主扫描逻辑
# ============================================================================

documents="[]"
doc_count=0
total_size=0
total_lines=0

# 扫描所有 Markdown 和文本文件
find "$SCAN_ROOT" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.rst" \) | sort | while read -r file; do
    # 跳过隐藏文件和特殊目录
    if [[ $(basename "$file") == .* ]]; then
        continue
    fi
    if [[ $file == *"/.git/"* ]] || [[ $file == *"/__pycache__/"* ]]; then
        continue
    fi

    ((doc_count++))
    echo "[DEBUG] [$doc_count] 处理: $file"

    # 获取文件信息
    local file_size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
    local line_count=$(wc -l < "$file" 2>/dev/null || echo 0)

    # 生成导入 ID
    local timestamp=$(date +%Y%m%d)
    local title=$(extract_title "$file" | tr ' ' '_' | tr -cd '[:alnum:]_' | cut -c1-40)
    local import_id="${timestamp}_$(printf "%03d" $doc_count)_${title}"

    # 获取相对路径
    local rel_path="${file#$SCAN_ROOT/}"

    # 复制文件
    local ext="${file##*.}"
    cp "$file" "$OUTPUT_DIR/imported/${import_id}.${ext}"

    # 累计统计
    total_size=$((total_size + file_size))
    total_lines=$((total_lines + line_count))

    # 构建文档条目
    local entry=$(jq -n \
        --arg id "$import_id" \
        --arg title "$(extract_title "$file")" \
        --arg path "$rel_path" \
        --arg summary "$(extract_summary "$file")" \
        --argjson tags "$(analyze_tags "$file" "$rel_path")" \
        --arg size "$file_size" \
        --arg lines "$line_count" \
        '{
            import_id: $id,
            original_path: $path,
            title: $title,
            file_size: ($size | tonumber),
            line_count: ($lines | tonumber),
            tags: $tags,
            summary: $summary,
            archived_path: "imported/'"${import_id}"'.'"${ext}"'",
            created: "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
            confidence: 0.9
        }')

    documents=$(jq --argjson entry "$entry" '. += [$entry]' <<< "$documents")

done

# ============================================================================
# 生成报告
# ============================================================================

# 生成最终的索引
final_index=$(jq -n \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg root "$SCAN_ROOT" \
    --argjson docs "$documents" \
    --arg total_size "$total_size" \
    --arg total_lines "$total_lines" \
    '{
        scan: {
            timestamp: $timestamp,
            scan_root: $root,
            total_files_scanned: ($docs | length),
            files_imported: ($docs | length),
            total_size_bytes: ($total_size | tonumber)
        },
        documents: $docs,
        statistics: {
            total_documents: ($docs | length),
            total_lines: ($total_lines | tonumber),
            total_size: ($total_size | tonumber),
            avg_doc_size: (if ($docs | length) > 0 then ($total_size | tonumber) / ($docs | length) else 0 end)
        }
    }')

# 保存索引
echo "$final_index" | jq . > "$OUTPUT_DIR/metadata.json"

# 生成报告
cat > "$OUTPUT_DIR/report.txt" << 'REPORT'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 文档整理报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPORT

echo "" >> "$OUTPUT_DIR/report.txt"
echo "扫描信息" >> "$OUTPUT_DIR/report.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_DIR/report.txt"
echo "  扫描时间: $(echo "$final_index" | jq -r '.scan.timestamp')" >> "$OUTPUT_DIR/report.txt"
echo "  扫描根目录: $(echo "$final_index" | jq -r '.scan.scan_root')" >> "$OUTPUT_DIR/report.txt"
echo "  导入文档数: $(echo "$final_index" | jq '.scan.files_imported')" >> "$OUTPUT_DIR/report.txt"
echo "" >> "$OUTPUT_DIR/report.txt"

echo "文档统计" >> "$OUTPUT_DIR/report.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_DIR/report.txt"
echo "  总行数: $(echo "$final_index" | jq '.statistics.total_lines')" >> "$OUTPUT_DIR/report.txt"
echo "  总大小: $(echo "$final_index" | jq '.statistics.total_size') bytes" >> "$OUTPUT_DIR/report.txt"
echo "" >> "$OUTPUT_DIR/report.txt"

echo "导入的文档清单" >> "$OUTPUT_DIR/report.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_DIR/report.txt"
echo "$final_index" | jq -r '.documents[] | "  [\(.import_id)] \(.title) (\(.line_count) lines, \(.file_size) bytes)"' >> "$OUTPUT_DIR/report.txt"
echo "" >> "$OUTPUT_DIR/report.txt"

echo "归档位置" >> "$OUTPUT_DIR/report.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$OUTPUT_DIR/report.txt"
echo "  元数据: $OUTPUT_DIR/metadata.json" >> "$OUTPUT_DIR/report.txt"
echo "  报告: $OUTPUT_DIR/report.txt" >> "$OUTPUT_DIR/report.txt"
echo "  文档: $OUTPUT_DIR/imported/" >> "$OUTPUT_DIR/report.txt"

# 显示报告
echo ""
cat "$OUTPUT_DIR/report.txt"

echo ""
echo "✓ 文档整理完成！"
echo "  导入的文档: $(echo "$final_index" | jq '.scan.files_imported')"
echo "  总行数: $(echo "$final_index" | jq '.statistics.total_lines')"

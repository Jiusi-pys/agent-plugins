#!/bin/bash
# organize_documents.sh - 扫描、整理、归档仓库文档

set -e

# ============================================================================
# 配置
# ============================================================================

WORK_DIR="$(pwd)"
SCAN_ROOT="${SCAN_ROOT:-.}"
OUTPUT_DIR="${OUTPUT_DIR:-./.evolving-expert/archives}"
ARCHIVE_INDEX="${OUTPUT_DIR}/metadata.json"
REPORT_FILE="${OUTPUT_DIR}/report.txt"
STATS_FILE="${OUTPUT_DIR}/stats.json"

# 支持的文件类型
DEFAULT_FILE_TYPES="md,txt,rst"
FILE_TYPES="${FILE_TYPES:-$DEFAULT_FILE_TYPES}"

# 排除的目录
DEFAULT_EXCLUDE="tests,build,node_modules,.git,venv,__pycache__,target,dist,coverage,vendor"
EXCLUDE_DIRS="${EXCLUDE_DIRS:-$DEFAULT_EXCLUDE}"

# 默认标签
DEFAULT_TAGS="${DEFAULT_TAGS:-documentation,legacy}"

# ============================================================================
# 辅助函数
# ============================================================================

log_info() {
    echo "[INFO] $*" >&2
}

log_error() {
    echo "[ERROR] $*" >&2
}

# 获取文件标题
extract_title() {
    local file="$1"
    local title=""

    # 尝试从 Markdown H1 标题提取
    if [[ $file == *.md ]]; then
        title=$(grep -m1 "^# " "$file" | sed 's/^# //' | head -1)
        if [ -n "$title" ]; then
            echo "$title"
            return 0
        fi
    fi

    # 尝试从 Markdown YAML header 提取
    if [ -f "$file" ]; then
        title=$(sed -n 's/^title: //p' "$file" | head -1)
        if [ -n "$title" ]; then
            echo "$title"
            return 0
        fi
    fi

    # 默认使用文件名作为标题
    local basename=$(basename "$file")
    local name="${basename%.*}"
    echo "$name" | tr '_-' ' '
}

# 提取摘要（前几行或第一段）
extract_summary() {
    local file="$1"
    local summary=""

    # 跳过 YAML header
    local start_line=1
    if grep -q "^---" "$file" 2>/dev/null; then
        start_line=$(grep -n "^---" "$file" | tail -1 | cut -d: -f1)
        start_line=$((start_line + 1))
    fi

    # 提取摘要（跳过标题和空行）
    summary=$(tail -n +$start_line "$file" 2>/dev/null | \
              grep -v "^# " | \
              grep -v "^#" | \
              sed '/^[[:space:]]*$/d' | \
              head -3 | \
              tr '\n' ' ')

    # 去除markdown特殊字符，截断到150字符
    summary=$(echo "$summary" | sed 's/\[//g;s/\]//g;s/\*//g;s/`//g' | cut -c1-150)
    echo "$summary"
}

# 生成导入ID
generate_import_id() {
    local file="$1"
    local seq="$2"
    local title=$(extract_title "$file" | tr ' ' '_' | tr -cd '[:alnum:]_' | cut -c1-40)

    local timestamp=$(date +%Y%m%d)
    echo "${timestamp}_$(printf "%03d" $seq)_${title}"
}

# 获取文件信息
get_file_info() {
    local file="$1"

    if [ ! -f "$file" ]; then
        echo "{}"
        return
    fi

    local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    local lines=$(wc -l < "$file" | tr -d ' ')
    local modified=$(stat -f%Sm -t%Y-%m-%d "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d' ' -f1)

    jq -n \
        --arg size "$size" \
        --arg lines "$lines" \
        --arg modified "$modified" \
        '{size: ($size | tonumber), lines: ($lines | tonumber), modified: $modified}'
}

# 分析标签
analyze_tags() {
    local file="$1"
    local dir_path="$2"
    local filename=$(basename "$file")

    local tags=()

    # 添加默认标签
    IFS=',' read -ra DEFAULT_TAG_ARRAY <<< "$DEFAULT_TAGS"
    for tag in "${DEFAULT_TAG_ARRAY[@]}"; do
        tags+=("$(echo "$tag" | xargs)")
    done

    # 基于目录路径添加标签
    if [[ $dir_path == *"docs"* ]]; then
        tags+=("documentation")
    fi
    if [[ $dir_path == *"api"* ]]; then
        tags+=("api")
    fi
    if [[ $dir_path == *"tutorial"* ]] || [[ $dir_path == *"guide"* ]]; then
        tags+=("guide")
    fi
    if [[ $dir_path == *"troubleshoot"* ]] || [[ $dir_path == *"faq"* ]]; then
        tags+=("troubleshooting")
    fi

    # 基于文件名添加标签
    if [[ $filename == *"setup"* ]] || [[ $filename == *"install"* ]]; then
        tags+=("setup")
    fi
    if [[ $filename == *"build"* ]] || [[ $filename == *"compile"* ]] || [[ $filename == *"cmake"* ]]; then
        tags+=("build")
    fi
    if [[ $filename == *"config"* ]]; then
        tags+=("configuration")
    fi

    # 去重
    printf '%s\n' "${tags[@]}" | sort -u | jq -R . | jq -s .
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    log_info "开始扫描文档..."
    log_info "扫描根目录: $SCAN_ROOT"
    log_info "文件类型: $FILE_TYPES"
    log_info "排除目录: $EXCLUDE_DIRS"

    # 创建输出目录
    mkdir -p "$OUTPUT_DIR/imported"

    # 执行扫描
    local documents="[]"
    local doc_count=0
    local total_size=0
    local total_lines=0
    local tag_stats="{}"

    # 使用 find 扫描文档
    find "$SCAN_ROOT" -type f \( \
        -name "*.md" -o -name "*.txt" -o -name "*.rst" \
    \) | sort | while read -r file; do
        # 跳过某些文件
        if [[ $(basename "$file") == .* ]]; then
            continue
        fi

        ((doc_count++))

        log_info "处理 [$doc_count] $file"

        # 生成导入ID
        local import_id=$(generate_import_id "$file" $doc_count)

        # 提取元数据
        local title=$(extract_title "$file")
        local summary=$(extract_summary "$file")
        local tags=$(analyze_tags "$file" "$(dirname "$file")")
        local file_info=$(get_file_info "$file")

        # 获取相对路径
        local rel_path=$(python3 -c "import os; print(os.path.relpath('$file', '$SCAN_ROOT'))" 2>/dev/null || \
                        echo "${file#$SCAN_ROOT/}")

        # 复制文件到归档目录
        cp "$file" "$OUTPUT_DIR/imported/${import_id}.$(basename "$file" | rev | cut -d. -f1 | rev)"
        local archived_path="imported/${import_id}.$(basename "$file" | rev | cut -d. -f1 | rev)"

        # 构建文档条目
        local entry=$(jq -n \
            --arg id "$import_id" \
            --arg title "$title" \
            --arg path "$rel_path" \
            --arg summary "$summary" \
            --argjson tags "$tags" \
            --argjson info "$file_info" \
            --arg archived "$archived_path" \
            --arg created "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            '{
                import_id: $id,
                original_path: $path,
                title: $title,
                file_size: $info.size,
                line_count: $info.lines,
                modified: $info.modified,
                tags: $tags,
                summary: $summary,
                archived_path: $archived,
                created: $created,
                confidence: 0.9
            }')

        documents=$(echo "$documents" | jq --argjson entry "$entry" '. += [$entry]')

        # 累计统计
        total_size=$((total_size + $(echo "$file_info" | jq '.size')))
        total_lines=$((total_lines + $(echo "$file_info" | jq '.lines')))

        # 更新标签统计
        echo "$tags" | jq '.[]' | while read -r tag; do
            tag=$(echo "$tag" | tr -d '"')
            tag_stats=$(echo "$tag_stats" | jq --arg t "$tag" '.[$t] = ((.[$t] // 0) + 1)')
        done

    done > /dev/null 2>&1

    # 构建最终的索引
    local final_index=$(jq -n \
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
    echo "$final_index" | jq . > "$ARCHIVE_INDEX"
    log_info "✓ 索引已保存: $ARCHIVE_INDEX"

    # 生成报告
    generate_report "$final_index"

    log_info "✓ 文档整理完成！"
    log_info "  导入的文档: $(echo "$final_index" | jq '.scan.files_imported')"
    log_info "  总行数: $(echo "$final_index" | jq '.statistics.total_lines')"
    log_info "  总大小: $(numfmt --to=iec-i --suffix=B $(echo "$final_index" | jq '.statistics.total_size') 2>/dev/null || echo "$(echo "$final_index" | jq '.statistics.total_size') B")"
}

# ============================================================================
# 报告生成
# ============================================================================

generate_report() {
    local index="$1"

    cat > "$REPORT_FILE" << 'REPORT_EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 文档整理报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPORT_EOF

    echo "" >> "$REPORT_FILE"
    echo "扫描信息" >> "$REPORT_FILE"
    echo "  扫描时间: $(echo "$index" | jq -r '.scan.timestamp')" >> "$REPORT_FILE"
    echo "  扫描根目录: $(echo "$index" | jq -r '.scan.scan_root')" >> "$REPORT_FILE"
    echo "  导入文档数: $(echo "$index" | jq '.scan.files_imported')" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo "文档统计" >> "$REPORT_FILE"
    echo "  总行数: $(echo "$index" | jq '.statistics.total_lines')" >> "$REPORT_FILE"
    echo "  总大小: $(echo "$index" | jq '.statistics.total_size') bytes" >> "$REPORT_FILE"
    echo "  平均文档大小: $(printf "%.0f" $(echo "$index" | jq '.statistics.avg_doc_size')) bytes" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo "导入的文档清单" >> "$REPORT_FILE"
    echo "$index" | jq -r '.documents[] | "  \(.import_id): \(.title) (\(.line_count) lines)"' >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo "归档位置" >> "$REPORT_FILE"
    echo "  元数据: $ARCHIVE_INDEX" >> "$REPORT_FILE"
    echo "  报告: $REPORT_FILE" >> "$REPORT_FILE"
    echo "  文档: $OUTPUT_DIR/imported/" >> "$REPORT_FILE"

    cat "$REPORT_FILE"
}

# ============================================================================
# 入口
# ============================================================================

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --scan-root)
            SCAN_ROOT="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --file-types)
            FILE_TYPES="$2"
            shift 2
            ;;
        --exclude)
            EXCLUDE_DIRS="$2"
            shift 2
            ;;
        --default-tags)
            DEFAULT_TAGS="$2"
            shift 2
            ;;
        *)
            log_error "未知参数: $1"
            exit 1
            ;;
    esac
done

main

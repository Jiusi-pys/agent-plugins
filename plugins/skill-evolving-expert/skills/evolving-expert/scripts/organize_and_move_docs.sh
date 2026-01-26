#!/bin/bash
# organize_and_move_docs.sh - 智能文档组织和移动脚本

set -euo pipefail

# ============================================================================
# 配置
# ============================================================================

SCAN_ROOT="${SCAN_ROOT:-.}"
OUTPUT_ROOT="${OUTPUT_ROOT:-./docs}"
STRATEGY="${STRATEGY:-by-function}"  # by-function, by-stage, by-tag
NAMING="${NAMING:-auto-numbered}"    # auto-numbered, by-title, original
ACTION="${ACTION:-move}"              # move, copy, symlink
DRY_RUN="${DRY_RUN:-false}"          # true/false - 仅显示会做什么，不实际执行

# 策略定义
declare -A FUNCTION_CATEGORIES=(
    ["api"]="API 文档"
    ["guides"]="使用指南"
    ["architecture"]="架构设计"
    ["tutorials"]="教程示例"
    ["reference"]="参考文档"
    ["troubleshooting"]="问题排查"
    ["setup"]="安装配置"
)

declare -A STAGE_CATEGORIES=(
    ["setup"]="安装和配置"
    ["development"]="开发指南"
    ["deployment"]="部署指南"
    ["maintenance"]="维护文档"
    ["troubleshooting"]="问题排查"
)

# ============================================================================
# 日志函数
# ============================================================================

log_info() {
    echo "[INFO] $*" >&2
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_success() {
    echo "[✓] $*" >&2
}

log_warn() {
    echo "[WARN] $*" >&2
}

# ============================================================================
# 分类和标签识别
# ============================================================================

# 根据文件名和内容识别分类
identify_category() {
    local file="$1"
    local filename=$(basename "$file")
    local content="$file"

    # 基于文件名的关键词识别
    if [[ $filename =~ ^(api|interface|endpoint|protocol) ]]; then
        echo "api"
    elif [[ $filename =~ ^(guide|tutorial|example|learn|getting.?start) ]]; then
        echo "guides"
    elif [[ $filename =~ ^(architecture|design|pattern|structure) ]]; then
        echo "architecture"
    elif [[ $filename =~ ^(setup|install|configure|config|prerequisite) ]]; then
        echo "setup"
    elif [[ $filename =~ ^(deploy|release|production|docker|k8s) ]]; then
        echo "deployment"
    elif [[ $filename =~ ^(troubleshoot|debug|faq|issue|problem|error) ]]; then
        echo "troubleshooting"
    elif [[ $filename =~ ^(develop|build|compile|contribute|development) ]]; then
        echo "development"
    elif [[ $filename =~ ^(maintain|update|upgrade|migrate) ]]; then
        echo "maintenance"
    elif [[ $filename =~ ^(reference|spec|api|index|glossary) ]]; then
        echo "reference"
    else
        # 默认分类
        echo "reference"
    fi
}

# 获取目标目录
get_target_directory() {
    local category="$1"
    local strategy="$2"

    if [ "$strategy" = "by-function" ]; then
        echo "${OUTPUT_ROOT}/${category}"
    elif [ "$strategy" = "by-stage" ]; then
        # 将 by-function 的分类映射到 by-stage
        case $category in
            setup) echo "${OUTPUT_ROOT}/setup" ;;
            development|guides|architecture) echo "${OUTPUT_ROOT}/development" ;;
            deployment) echo "${OUTPUT_ROOT}/deployment" ;;
            maintenance) echo "${OUTPUT_ROOT}/maintenance" ;;
            troubleshooting) echo "${OUTPUT_ROOT}/troubleshooting" ;;
            *) echo "${OUTPUT_ROOT}/reference" ;;
        esac
    elif [ "$strategy" = "by-tag" ]; then
        echo "${OUTPUT_ROOT}/${category}"
    else
        echo "${OUTPUT_ROOT}/uncategorized"
    fi
}

# 生成目标文件名
generate_filename() {
    local file="$1"
    local seq="$2"
    local naming="$3"
    local ext="${file##*.}"
    local basename=$(basename "$file" ".$ext")

    case $naming in
        auto-numbered)
            printf "%02d_%s.%s" "$seq" "$(echo "$basename" | tr ' ' '_' | tr -cd '[:alnum:]_')" "$ext"
            ;;
        by-title)
            printf "%s.%s" "$(echo "$basename" | tr ' ' '_')" "$ext"
            ;;
        original)
            basename "$file"
            ;;
        *)
            printf "%02d_%s.%s" "$seq" "$(echo "$basename" | tr ' ' '_')" "$ext"
            ;;
    esac
}

# ============================================================================
# 文件操作函数
# ============================================================================

execute_action() {
    local action="$1"
    local source="$2"
    local target="$3"
    local dry_run="$4"

    if [ "$dry_run" = "true" ]; then
        case $action in
            move)
                log_info "[DRY RUN] 移动: $source → $target"
                ;;
            copy)
                log_info "[DRY RUN] 复制: $source → $target"
                ;;
            symlink)
                log_info "[DRY RUN] 创建软链: $source → $target"
                ;;
        esac
    else
        # 确保目标目录存在
        mkdir -p "$(dirname "$target")"

        case $action in
            move)
                mv "$source" "$target"
                log_success "移动: $source → $target"
                ;;
            copy)
                cp "$source" "$target"
                log_success "复制: $source → $target"
                ;;
            symlink)
                ln -sf "$(cd "$(dirname "$source")" && pwd)/$(basename "$source")" "$target"
                log_success "软链: $source → $target"
                ;;
        esac
    fi
}

# ============================================================================
# 主扫描和组织函数
# ============================================================================

organize_documents() {
    log_info "开始组织文档..."
    log_info "扫描根目录: $SCAN_ROOT"
    log_info "输出根目录: $OUTPUT_ROOT"
    log_info "分类策略: $STRATEGY"
    log_info "命名规范: $NAMING"
    log_info "执行操作: $ACTION"
    [ "$DRY_RUN" = "true" ] && log_warn "干运行模式 (DRY RUN) - 不会实际移动文件"
    echo ""

    # 创建输出目录
    if [ "$DRY_RUN" != "true" ]; then
        mkdir -p "$OUTPUT_ROOT"
    fi

    # 统计
    local total_files=0
    local organized_files=0
    local failed_files=0
    declare -A category_count

    # 扫描并组织文档
    find "$SCAN_ROOT" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.rst" \) | sort | while read -r file; do
        # 跳过隐藏文件
        if [[ $(basename "$file") == .* ]]; then
            continue
        fi

        # 跳过已经在输出目录中的文件
        if [[ "$file" == "$OUTPUT_ROOT"/* ]]; then
            continue
        fi

        ((total_files++))

        # 识别分类
        local category=$(identify_category "$file")
        local target_dir=$(get_target_directory "$category" "$STRATEGY")
        local seq=$((${category_count[$category]:-0} + 1))
        category_count[$category]=$seq

        # 生成目标文件名
        local filename=$(generate_filename "$file" "$seq" "$NAMING")
        local target_path="${target_dir}/${filename}"

        # 执行操作
        if execute_action "$ACTION" "$file" "$target_path" "$DRY_RUN"; then
            ((organized_files++))
        else
            ((failed_files++))
            log_warn "处理失败: $file"
        fi
    done

    # 显示统计
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 组织结果"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  找到文档: $total_files"
    echo "  成功处理: $organized_files"
    if [ $failed_files -gt 0 ]; then
        echo "  处理失败: $failed_files"
    fi
    echo ""

    if [ "$DRY_RUN" = "true" ]; then
        log_warn "这是干运行模式，未实际移动任何文件"
        log_info "如果结果看起来正确，请运行:"
        log_info "  export DRY_RUN=false && bash $0 [参数]"
    fi
}

# ============================================================================
# 生成目录导航
# ============================================================================

generate_navigation() {
    log_info "生成目录导航..."

    local nav_file="${OUTPUT_ROOT}/README.md"

    cat > "$nav_file" << 'EOF'
# 📚 文档目录

本文档目录已自动组织和分类。

EOF

    if [ "$STRATEGY" = "by-function" ]; then
        cat >> "$nav_file" << 'EOF'
## 按功能分类

### 📖 [使用指南](./guides/)
快速开始、配置、最佳实践

### 🏗️ [架构设计](./architecture/)
系统设计、组件划分、数据流

### 🔌 [API 文档](./api/)
接口说明、协议定义、端点参考

### 🎓 [教程示例](./tutorials/)
实践教程、代码示例、学习资源

### 📋 [参考文档](./reference/)
术语表、规范、索引

### ⚙️ [安装配置](./setup/)
环境要求、安装步骤、初始配置

### 📦 [部署指南](./deployment/)
发布流程、容器化、生产配置

### 🔧 [维护文档](./maintenance/)
更新升级、迁移指南、维护任务

### 🐛 [问题排查](./troubleshooting/)
常见问题、调试指南、错误解决

EOF
    elif [ "$STRATEGY" = "by-stage" ]; then
        cat >> "$nav_file" << 'EOF'
## 按开发阶段分类

### ⚙️ [安装和配置](./setup/)
环境要求、安装步骤、初始配置

### 💻 [开发指南](./development/)
开发流程、代码规范、架构设计、最佳实践

### 🚀 [部署指南](./deployment/)
发布流程、容器化、生产配置

### 🔧 [维护文档](./maintenance/)
更新升级、迁移指南、维护任务

### 🐛 [问题排查](./troubleshooting/)
常见问题、调试指南、错误解决

EOF
    fi

    cat >> "$nav_file" << 'EOF'

---

**最后更新**: $(date '+%Y-%m-%d %H:%M:%S')

EOF

    log_success "目录导航已生成: $nav_file"
}

# ============================================================================
# 显示帮助
# ============================================================================

show_help() {
    cat << 'EOF'
用法: organize_and_move_docs.sh [选项]

选项:
  --scan-root <path>        扫描的根目录 (默认: .)
  --output-root <path>      输出的根目录 (默认: ./docs)
  --strategy <strategy>     分类策略 (默认: by-function)
                            - by-function: 按功能分类
                            - by-stage: 按开发阶段分类
                            - by-tag: 按标签分类
  --naming <style>          命名规范 (默认: auto-numbered)
                            - auto-numbered: 自动编号 (01_xxx.md)
                            - by-title: 按标题 (xxx.md)
                            - original: 保持原名
  --action <action>         执行操作 (默认: move)
                            - move: 移动文件
                            - copy: 复制文件
                            - symlink: 创建软链接
  --dry-run                 干运行模式 (仅显示会做什么，不实际执行)
  --help                    显示此帮助信息

示例:
  # 按功能分类并移动文件
  ./organize_and_move_docs.sh --scan-root . --output-root ./docs --strategy by-function

  # 按开发阶段分类 (干运行)
  ./organize_and_move_docs.sh --scan-root . --strategy by-stage --dry-run

  # 按标签分类，使用自动编号，复制而非移动
  ./organize_and_move_docs.sh --scan-root . --strategy by-tag --naming auto-numbered --action copy

EOF
}

# ============================================================================
# 参数解析
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --scan-root)
            SCAN_ROOT="$2"
            shift 2
            ;;
        --output-root)
            OUTPUT_ROOT="$2"
            shift 2
            ;;
        --strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --naming)
            NAMING="$2"
            shift 2
            ;;
        --action)
            ACTION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# 执行
# ============================================================================

organize_documents
generate_navigation

log_success "文档组织完成！"
echo ""
log_info "查看组织结果:"
log_info "  ls -la $OUTPUT_ROOT"
log_info "  cat $OUTPUT_ROOT/README.md"

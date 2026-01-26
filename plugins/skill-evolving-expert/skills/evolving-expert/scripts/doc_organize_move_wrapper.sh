#!/bin/bash
# doc_organize_move_wrapper.sh - 文档组织和移动的包装脚本

set -euo pipefail

# 默认参数
SCAN_ROOT="."
OUTPUT_ROOT="./docs"
STRATEGY="by-function"
NAMING="auto-numbered"
ACTION="move"
DRY_RUN="false"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 解析参数
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
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# 验证参数
# ============================================================================

validate_params() {
    local valid_strategies=("by-function" "by-stage" "by-tag")
    local valid_naming=("auto-numbered" "by-title" "original")
    local valid_actions=("move" "copy" "symlink")

    # 验证策略
    if [[ ! " ${valid_strategies[@]} " =~ " ${STRATEGY} " ]]; then
        echo "错误: 无效的策略 '$STRATEGY'"
        echo "有效选项: ${valid_strategies[*]}"
        exit 1
    fi

    # 验证命名规范
    if [[ ! " ${valid_naming[@]} " =~ " ${NAMING} " ]]; then
        echo "错误: 无效的命名规范 '$NAMING'"
        echo "有效选项: ${valid_naming[*]}"
        exit 1
    fi

    # 验证操作
    if [[ ! " ${valid_actions[@]} " =~ " ${ACTION} " ]]; then
        echo "错误: 无效的操作 '$ACTION'"
        echo "有效选项: ${valid_actions[*]}"
        exit 1
    fi

    # 验证目录
    if [ ! -d "$SCAN_ROOT" ]; then
        echo "错误: 扫描根目录不存在: $SCAN_ROOT"
        exit 1
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    echo "📚 开始文档组织和移动..."
    echo ""
    echo "组织设置："
    echo "  扫描根目录: $SCAN_ROOT"
    echo "  输出根目录: $OUTPUT_ROOT"
    echo "  分类策略: $STRATEGY"
    echo "  命名规范: $NAMING"
    echo "  执行操作: $ACTION"
    [ "$DRY_RUN" = "true" ] && echo "  ⚠️  干运行模式 (不会实际移动文件)"
    echo ""

    # 查找脚本
    local organize_script="${SCRIPT_DIR}/organize_and_move_docs.sh"

    if [ ! -f "$organize_script" ]; then
        echo "错误: 找不到脚本 $organize_script"
        exit 1
    fi

    # 调用脚本
    SCAN_ROOT="$SCAN_ROOT" \
    OUTPUT_ROOT="$OUTPUT_ROOT" \
    STRATEGY="$STRATEGY" \
    NAMING="$NAMING" \
    ACTION="$ACTION" \
    DRY_RUN="$DRY_RUN" \
    bash "$organize_script"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ 文档组织完成！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # 显示下一步
    if [ "$ACTION" = "move" ]; then
        echo "📋 后续步骤："
        echo ""
        echo "1️⃣ 查看组织结果："
        echo "   ls -la $OUTPUT_ROOT"
        echo ""
        echo "2️⃣ 查看目录导航："
        echo "   cat $OUTPUT_ROOT/README.md"
        echo ""
        echo "3️⃣ 检查文件内容："
        echo "   find $OUTPUT_ROOT -type f -name '*.md' | head -5"
        echo ""
    elif [ "$ACTION" = "copy" ]; then
        echo "📋 后续步骤："
        echo ""
        echo "1️⃣ 查看副本位置："
        echo "   ls -la $OUTPUT_ROOT"
        echo ""
        echo "2️⃣ 原文件仍在："
        echo "   find $SCAN_ROOT -type f -name '*.md' | head -5"
        echo ""
    fi

    if [ "$DRY_RUN" = "true" ]; then
        echo "ℹ️  这是干运行模式的预览。如果结果看起来正确，请运行："
        echo ""
        echo "   /doc-organize \\"
        echo "     --scan-root \"$SCAN_ROOT\" \\"
        echo "     --output-root \"$OUTPUT_ROOT\" \\"
        echo "     --strategy \"$STRATEGY\" \\"
        echo "     --naming \"$NAMING\" \\"
        echo "     --action \"$ACTION\""
        echo ""
    fi
}

# ============================================================================
# 帮助信息
# ============================================================================

show_help() {
    cat << 'EOF'
文档组织和移动工具

用法: /doc-organize [选项]

选项:
  --scan-root <path>       扫描的源目录 (默认: .)
  --output-root <path>     组织后的目录 (默认: ./docs)
  --strategy <name>        分类策略 (默认: by-function)
                           - by-function: 按功能分类
                           - by-stage: 按开发阶段分类
                           - by-tag: 按标签分类
  --naming <style>         命名规范 (默认: auto-numbered)
                           - auto-numbered: 自动编号 (01_xxx.md)
                           - by-title: 按标题保存 (xxx.md)
                           - original: 保持原名
  --action <op>            文件操作 (默认: move)
                           - move: 移动文件
                           - copy: 复制文件
                           - symlink: 创建软链接
  --dry-run                干运行模式 (预览不实际执行)
  --help, -h               显示此帮助信息

常见用法:

  # 按功能分类并移动文件（推荐）
  /doc-organize

  # 先预览结果，不实际移动
  /doc-organize --dry-run

  # 按开发阶段分类
  /doc-organize --strategy by-stage

  # 使用自动编号并复制（保留原文件）
  /doc-organize --naming auto-numbered --action copy

  # 按标签分类
  /doc-organize --strategy by-tag

  # 完整配置
  /doc-organize \
    --scan-root . \
    --output-root ./docs \
    --strategy by-function \
    --naming auto-numbered \
    --action move

分类策略说明:

  按功能 (by-function):
    - api/ 、guides/、architecture/、tutorials/、reference/
    - setup/、deployment/、maintenance/、troubleshooting/

  按阶段 (by-stage):
    - setup/ (安装和配置)
    - development/ (开发指南、架构、教程)
    - deployment/ (部署指南)
    - maintenance/ (维护文档)
    - troubleshooting/ (问题排查)

  按标签 (by-tag):
    - 根据内容自动识别标签（如 ros2、cmake 等）

命名规范说明:

  自动编号 (auto-numbered): 01_title.md、02_title.md ...
  按标题 (by-title): title.md
  保持原名 (original): 原始文件名

文件操作说明:

  移动 (move): 将文件移动到新位置 - 推荐
  复制 (copy): 复制文件，原文件保持不变
  软链接 (symlink): 创建符号链接

EOF
}

# ============================================================================
# 执行
# ============================================================================

validate_params
main

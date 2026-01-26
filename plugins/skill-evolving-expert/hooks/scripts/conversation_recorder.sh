#!/bin/bash
# ============================================================================
# conversation_recorder.sh - 对话历史和指令记录管理
# ============================================================================
# 功能: 完整记录 Session 中的对话历史、指令、文档链接
#       避免冗余内容占据 context space，使用引用系统
# ============================================================================

set -euo pipefail

# 配置
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${PLUGIN_DIR%/hooks/scripts}"
KNOWLEDGE_BASE="${KNOWLEDGE_BASE:-${PLUGIN_ROOT}/skills/evolving-expert/knowledge}"
SESSION_LOGS_DIR="${KNOWLEDGE_BASE}/session_logs"
CONVERSATION_HISTORY_DIR="${KNOWLEDGE_BASE}/conversation_history"
REFERENCES_INDEX="${KNOWLEDGE_BASE}/references.json"

# 颜色定义
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# 初始化记录目录
# ============================================================================
init_recording_dirs() {
    mkdir -p "$SESSION_LOGS_DIR"
    mkdir -p "$CONVERSATION_HISTORY_DIR"
    mkdir -p "$KNOWLEDGE_BASE/references"
}

# ============================================================================
# 初始化 References 索引
# ============================================================================
init_references_index() {
    if [ ! -f "$REFERENCES_INDEX" ]; then
        cat > "$REFERENCES_INDEX" << 'EOF'
{
  "version": "1.0.0",
  "description": "引用系统 - 管理所有外部链接和内部文档引用，避免冗余复制",
  "last_updated": "2025-01-26T00:00:00Z",
  "categories": {
    "internal_docs": {
      "description": "内部文档引用",
      "references": []
    },
    "external_resources": {
      "description": "外部资源引用",
      "references": []
    },
    "api_docs": {
      "description": "API 文档引用",
      "references": []
    },
    "error_patterns": {
      "description": "错误模式引用",
      "references": []
    }
  },
  "index": {}
}
EOF
    fi
}

# ============================================================================
# 添加引用
# ============================================================================
add_reference() {
    local category="$1"
    local ref_id="$2"
    local title="$3"
    local url="$4"
    local description="${5:-}"

    init_references_index

    local ref_entry=$(jq -n \
        --arg id "$ref_id" \
        --arg title "$title" \
        --arg url "$url" \
        --arg desc "$description" \
        '{id: $id, title: $title, url: $url, description: $desc, added: now | todate}')

    # 添加到对应类别
    jq --arg cat "$category" --argjson ref "$ref_entry" '
        .categories[$cat].references += [$ref] |
        .index[$ref.id] = $ref |
        .last_updated = now | todate
    ' "$REFERENCES_INDEX" > "$REFERENCES_INDEX.tmp"
    mv "$REFERENCES_INDEX.tmp" "$REFERENCES_INDEX"

    echo -e "${GREEN}[INFO]${NC} 引用已添加: $ref_id"
}

# ============================================================================
# 创建对话记录文档
# ============================================================================
create_conversation_record() {
    local session_id="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local iso_timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    local record_file="$CONVERSATION_HISTORY_DIR/session_${session_id}.md"

    # 创建带 YAML header 的对话记录模板
    cat > "$record_file" << EOF
---
session_id: ${session_id}
start_time: ${iso_timestamp}
end_time:
status: in_progress
agent: skill-evolving-expert
claude_version: claude-haiku-4-5-20251001
context_used: 0
context_limit: 200000
tags: []
objectives: []
references: []
outcomes: []
---

# Session ${session_id} - 对话记录

**开始时间**: ${timestamp}

## 📋 Session 概述

- **会话 ID**: ${session_id}
- **代理**: skill-evolving-expert
- **目标**: [待填写]
- **状态**: 进行中

## 💬 对话历史

### [记录位置]

本部分使用引用系统，避免冗余复制。

**使用的引用**:
- 查看 \`references.json\` 了解所有外部资源链接
- 使用 \`ref:<ref_id>\` 格式引用文档

## 📝 指令日志

\`\`\`bash
# 在此记录执行的所有指令
# 格式: [时间戳] <指令> -> <结果>
\`\`\`

## 📚 文档链接

使用引用而不是复制内容：

| 文档 | 引用 ID | 说明 |
|------|--------|------|
| 内部文档 | ref:internal_* | [描述] |
| 外部资源 | ref:external_* | [描述] |

## 🔗 相关知识库条目

| 解决方案 ID | 标题 | 关联性 |
|----------|------|-------|
| - | - | - |

## 📊 Context 使用情况

- **当前使用**: 0 tokens
- **上限**: 200,000 tokens
- **使用率**: 0.0%

## ✅ 本 Session 成果

- 解决的问题: []
- 新增知识点: []
- 发现的模式: []

---

**最后更新**: ${timestamp}

EOF

    echo -e "${GREEN}[INFO]${NC} 对话记录已创建: $record_file"
    echo "$record_file"
}

# ============================================================================
# 记录指令
# ============================================================================
log_instruction() {
    local session_id="$1"
    local instruction="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    local record_file="$CONVERSATION_HISTORY_DIR/session_${session_id}.md"

    if [ ! -f "$record_file" ]; then
        echo -e "${YELLOW}[WARN]${NC} Session 记录不存在" >&2
        return 1
    fi

    # 追加指令到文件
    sed -i "/## 📝 指令日志/a\\
\`\`\`bash\\
[${timestamp}] ${instruction}\\
\`\`\`\n" "$record_file"

    echo -e "${GREEN}[INFO]${NC} 指令已记录: $instruction"
}

# ============================================================================
# 更新 Session 元数据
# ============================================================================
update_session_metadata() {
    local session_id="$1"
    local end_time=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    local context_used="${2:-0}"
    local status="${3:-completed}"

    local record_file="$CONVERSATION_HISTORY_DIR/session_${session_id}.md"

    if [ ! -f "$record_file" ]; then
        echo -e "${YELLOW}[WARN]${NC} Session 记录不存在" >&2
        return 1
    fi

    # 使用 sed 更新 YAML header
    sed -i "s/^end_time: .*/end_time: ${end_time}/" "$record_file"
    sed -i "s/^status: .*/status: ${status}/" "$record_file"
    sed -i "s/^context_used: .*/context_used: ${context_used}/" "$record_file"

    echo -e "${GREEN}[INFO]${NC} Session 元数据已更新"
}

# ============================================================================
# 生成引用总结报告
# ============================================================================
generate_references_report() {
    if [ ! -f "$REFERENCES_INDEX" ]; then
        echo "{}}"
        return
    fi

    cat << EOF
# 📚 引用系统总结

## 类别统计

EOF

    jq -r '.categories | to_entries[] | "### \(.key): \(.value.references | length) 项\n\(.value.description)"' "$REFERENCES_INDEX" >> /dev/null

    cat << EOF

## 内部文档引用

EOF

    jq -r '.categories.internal_docs.references[] | "- [\(.title)](\(.url)) - \(.description)"' "$REFERENCES_INDEX" >> /dev/null

    cat << EOF

## 外部资源引用

EOF

    jq -r '.categories.external_resources.references[] | "- [\(.title)](\(.url)) - \(.description)"' "$REFERENCES_INDEX" >> /dev/null
}

# ============================================================================
# 清理过期的 Session 记录
# ============================================================================
cleanup_old_sessions() {
    local days=${1:-30}

    echo -e "${BLUE}[INFO]${NC} 清理 $days 天前的 Session 记录..."

    find "$CONVERSATION_HISTORY_DIR" -name "session_*.md" -mtime +$days -delete

    echo -e "${GREEN}[INFO]${NC} 清理完成"
}

# ============================================================================
# 主函数
# ============================================================================
main() {
    case "${1:-}" in
        init)
            init_recording_dirs
            init_references_index
            echo -e "${GREEN}[INFO]${NC} 对话记录系统已初始化"
            ;;
        add-reference)
            if [ $# -lt 5 ]; then
                echo "用法: $0 add-reference <category> <ref_id> <title> <url> [描述]" >&2
                return 1
            fi
            add_reference "$2" "$3" "$4" "$5" "${6:-}"
            ;;
        create-session)
            if [ $# -lt 2 ]; then
                echo "用法: $0 create-session <session_id>" >&2
                return 1
            fi
            create_conversation_record "$2"
            ;;
        log-instruction)
            if [ $# -lt 3 ]; then
                echo "用法: $0 log-instruction <session_id> <instruction>" >&2
                return 1
            fi
            log_instruction "$2" "$3"
            ;;
        update-metadata)
            if [ $# -lt 2 ]; then
                echo "用法: $0 update-metadata <session_id> [context_used] [status]" >&2
                return 1
            fi
            update_session_metadata "$2" "${3:-0}" "${4:-completed}"
            ;;
        references-report)
            generate_references_report
            ;;
        cleanup)
            cleanup_old_sessions "${2:-30}"
            ;;
        *)
            cat << 'USAGE'
对话记录和引用管理系统

用法: conversation_recorder.sh <command> [options]

命令:
  init                              初始化记录系统
  add-reference <cat> <id> <title> <url> [desc]
                                    添加引用
  create-session <session_id>       创建新 Session 记录
  log-instruction <session_id> <cmd>
                                    记录指令执行
  update-metadata <session_id> [context] [status]
                                    更新 Session 元数据
  references-report                 生成引用报告
  cleanup [days]                    清理过期 Session (默认30天)

USAGE
            ;;
    esac
}

# ============================================================================
# 入口
# ============================================================================
main "$@"

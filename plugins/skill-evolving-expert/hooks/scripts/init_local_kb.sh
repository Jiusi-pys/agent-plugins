#!/bin/bash
# init_local_kb.sh - 初始化本地知识库

set -e

# 获取当前工作目录
WORK_DIR="$(pwd)"
LOCAL_KB="$WORK_DIR/docs/.evolving-expert"
GLOBAL_KB="${HOME}/.claude/knowledge-base"

# 创建目录结构
mkdir -p "$LOCAL_KB"/{solutions,patterns}
mkdir -p "$GLOBAL_KB"/{solutions,patterns,summaries}

# 初始化本地索引文件
if [ ! -f "$LOCAL_KB/index.json" ]; then
    cat > "$LOCAL_KB/index.json" << 'EOF'
{
  "meta": {
    "version": "2.0",
    "scope": "local",
    "workspace": "",
    "created": "",
    "description": "本地项目知识库索引"
  },
  "config": {
    "auto_extract": true,
    "pattern_merge_threshold": 3,
    "global_kb_path": ""
  },
  "solutions": [],
  "patterns": [],
  "references": {
    "global": []
  }
}
EOF

    # 填充动态信息
    jq --arg ws "$WORK_DIR" \
       --arg created "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       --arg global "$GLOBAL_KB" \
       '.meta.workspace = $ws | .meta.created = $created | .config.global_kb_path = $global' \
       "$LOCAL_KB/index.json" > "$LOCAL_KB/index.json.tmp" && \
       mv "$LOCAL_KB/index.json.tmp" "$LOCAL_KB/index.json"
fi

# 初始化全局索引文件（如果不存在）
if [ ! -f "$GLOBAL_KB/index.json" ]; then
    cat > "$GLOBAL_KB/index.json" << 'EOF'
{
  "meta": {
    "version": "2.0",
    "scope": "global",
    "created": "",
    "description": "跨项目知识库索引"
  },
  "config": {
    "auto_extract": true,
    "pattern_merge_threshold": 5
  },
  "solutions": [],
  "patterns": [],
  "workspaces": []
}
EOF

    jq --arg created "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       '.meta.created = $created' \
       "$GLOBAL_KB/index.json" > "$GLOBAL_KB/index.json.tmp" && \
       mv "$GLOBAL_KB/index.json.tmp" "$GLOBAL_KB/index.json"
fi

# 在全局索引中注册当前工作空间
WORKSPACE_ENTRY=$(jq -n \
    --arg name "$(basename "$WORK_DIR")" \
    --arg path "$WORK_DIR" \
    --arg registered "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{name: $name, path: $path, registered: $registered}')

# 检查是否已注册，避免重复
if ! jq --arg path "$WORK_DIR" '.workspaces[] | select(.path == $path)' "$GLOBAL_KB/index.json" | grep -q .; then
    jq --argjson entry "$WORKSPACE_ENTRY" '.workspaces += [$entry]' "$GLOBAL_KB/index.json" > "$GLOBAL_KB/index.json.tmp" && \
    mv "$GLOBAL_KB/index.json.tmp" "$GLOBAL_KB/index.json"
fi

echo "✓ 知识库已初始化"

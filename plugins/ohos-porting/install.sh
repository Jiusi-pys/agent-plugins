#!/bin/bash
# install.sh - 安装 OHOS Porting Plugin
# 用法: ./install.sh [--user | --project]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:---user}"

case "$MODE" in
    --user)
        TARGET_DIR="$HOME/.claude"
        echo "安装到用户目录: $TARGET_DIR"
        ;;
    --project)
        TARGET_DIR=".claude"
        echo "安装到项目目录: $TARGET_DIR"
        ;;
    *)
        echo "用法: $0 [--user | --project]"
        exit 1
        ;;
esac

# 创建目录
mkdir -p "$TARGET_DIR"/{agents,commands,skills}

# 复制 agents
echo "复制 agents..."
cp -r "$SCRIPT_DIR/agents/"* "$TARGET_DIR/agents/" 2>/dev/null || true

# 复制 commands
echo "复制 commands..."
cp -r "$SCRIPT_DIR/commands/"* "$TARGET_DIR/commands/" 2>/dev/null || true

# 复制 skills
echo "复制 skills..."
for skill in "$SCRIPT_DIR/skills/"*/; do
    skill_name=$(basename "$skill")
    mkdir -p "$TARGET_DIR/skills/$skill_name"
    cp -r "$skill"* "$TARGET_DIR/skills/$skill_name/" 2>/dev/null || true
done

# 复制 hooks (如果存在)
if [ -d "$SCRIPT_DIR/hooks" ]; then
    echo "复制 hooks..."
    mkdir -p "$TARGET_DIR/hooks"
    cp -r "$SCRIPT_DIR/hooks/"* "$TARGET_DIR/hooks/" 2>/dev/null || true
fi

# 设置脚本权限
echo "设置脚本权限..."
find "$TARGET_DIR" -name "*.sh" -exec chmod +x {} \;
find "$TARGET_DIR" -name "*.py" -exec chmod +x {} \;

# 创建 working-records 目录
mkdir -p "$HOME/.claude/working-records"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║         OHOS Porting Plugin 安装完成                    ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "已安装组件:"
echo "  - 6 个 agents"
echo "  - 4 个 commands"
echo "  - 6 个 skills"
echo ""
echo "使用方法:"
echo "  /ohos-port-dev libcurl    # 启动移植工作流"
echo "  /ohos-port libcurl        # 移植分析"
echo "  /ohos-build libcurl       # 交叉编译"
echo "  /ohos-deploy libcurl      # 部署测试"
echo ""
echo "注意: 如果使用 plugin 模式加载，请使用:"
echo "  claude --plugin-dir $SCRIPT_DIR"

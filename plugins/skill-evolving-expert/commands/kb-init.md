---
description: 初始化自进化知识库
---

# 知识库初始化命令

初始化自进化专家系统的知识库。

## 执行步骤

1. 创建知识库目录结构
2. 初始化索引文件
3. 复制管理脚本到工作目录

## 初始化脚本

\`\`\`bash
# 设置知识库路径
KNOWLEDGE_BASE="\${KNOWLEDGE_BASE:-./.evolving-expert/knowledge}"

# 创建目录结构
mkdir -p "\$KNOWLEDGE_BASE"/{solutions,patterns}

# 初始化索引
if [ ! -f "\$KNOWLEDGE_BASE/index.json" ]; then
    cat > "\$KNOWLEDGE_BASE/index.json" << 'INDEXEOF'
{
  "meta": {
    "version": "1.0",
    "created": "$(date +%Y-%m-%d)",
    "description": "自进化专家知识库"
  },
  "config": {
    "auto_extract": true,
    "pattern_merge_threshold": 3,
    "max_solutions_per_tag": 50,
    "cleanup_days": 90
  },
  "solutions": [],
  "patterns": [],
  "statistics": {
    "total_solutions": 0,
    "total_patterns": 0,
    "total_hits": 0,
    "last_updated": "$(date +%Y-%m-%d)"
  }
}
INDEXEOF
    echo "知识库初始化完成: \$KNOWLEDGE_BASE"
else
    echo "知识库已存在: \$KNOWLEDGE_BASE"
fi
\`\`\`

初始化后，可以使用 knowledge_manager.sh 脚本管理知识：
- \`./knowledge_manager.sh add "标题" "tag1,tag2" content.md\` - 添加解决方案
- \`./knowledge_manager.sh search "关键词"\` - 检索知识
- \`./knowledge_manager.sh stats\` - 查看统计

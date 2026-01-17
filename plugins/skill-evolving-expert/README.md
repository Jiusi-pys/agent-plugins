# Self-Evolving Expert Plugin

自我进化专家系统插件。实现 Claude Code sub-agent 的自我进化机制。

## 核心功能

- **知识闭环**: 解决问题 → 提取知识 → 存储索引 → 检索应用
- **渐进积累**: 单次解决方案 → 高频模式提炼 → 领域知识体系
- **最小冗余**: 相似问题合并，保留差异点

## 安装

\`\`\`bash
/plugin marketplace add Jiusi-pys/agent-plugins
/plugin install skill-evolving-expert@jiusi-agent-plugins
\`\`\`

## 使用

### 初始化知识库

\`\`\`bash
/skill-evolving-expert:kb-init
\`\`\`

### 工作流程

1. **任务启动前** - 检索相关历史知识
2. **任务执行** - 正常执行，记录过程
3. **任务完成后** - 自动提取知识点
4. **模式提炼** - 周期性合并高频解决方案

### 知识管理脚本

\`\`\`bash
# 添加解决方案
./knowledge_manager.sh add "标题" "tag1,tag2,tag3" solution.md

# 检索
./knowledge_manager.sh search "关键词"

# 读取
./knowledge_manager.sh read "solution_id"

# 统计
./knowledge_manager.sh stats

# 检查可合并模式
./knowledge_manager.sh check-merge

# 清理过期条目
./knowledge_manager.sh cleanup 90
\`\`\`

## 知识提取触发条件

满足任一即触发：
- 解决了新问题
- 发现了更优方案
- 踩坑并找到原因

## 目录结构

\`\`\`
knowledge/
├── index.json        # 索引文件
├── solutions/        # 单次解决方案
│   └── YYYYMMDD_HHMMSS_topic.md
└── patterns/         # 高频模式
    └── category.md
\`\`\`

## 配置

在 index.json 中配置：

\`\`\`json
{
  "config": {
    "auto_extract": true,
    "pattern_merge_threshold": 3,
    "max_solutions_per_tag": 50,
    "cleanup_days": 90
  }
}
\`\`\`

## License

MIT

# Skill-Evolving-Expert 使用指南

## 架构设计

该系统采用 **分层知识库架构**，支持跨工作目录的知识累积和复用：

```
知识库架构
├── 全局知识库 (~/.claude/knowledge-base/)
│   ├── 跨项目解决方案总结
│   ├── 提炼的模式和最佳实践
│   └── 工作空间注册表
│
└── 本地知识库 (./docs/.evolving-expert/)
    ├── 项目特定的详细文档
    ├── 解决方案实现细节
    └── 本地索引和引用
```

### 存储策略

| 内容类型 | 存储位置 | 用途 |
|---------|--------|------|
| **总结文档** | `~/.claude/knowledge-base/summaries/` | 全局复用，YAML header清晰 |
| **详情文档** | `./docs/.evolving-expert/solutions/` | 项目本地，完整实现细节 |
| **引用索引** | 两处同步 | 统计准确，跨项目查询 |

## 自动初始化

在任何工作目录开启 Claude 时，系统会**自动**进行：

1. ✅ 创建本地知识库目录（`./docs/.evolving-expert/`）
2. ✅ 初始化本地索引文件（带有工作空间信息）
3. ✅ 在全局知识库中注册当前工作空间
4. ✅ 后台同步统计信息（对用户透明）

**用户无需执行任何命令**，这一切都在 SessionStart 时自动完成。

## 添加解决方案

### 方法 1：使用管理脚本（推荐）

```bash
# 进入项目目录
cd /home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus

# 添加解决方案
./docs/.evolving-expert/knowledge_manager_v2.sh add \
    "修复编译错误" \
    "ros2,compilation,cmake" \
    solution.md
```

### 方法 2：手动添加

1. 在 `./docs/.evolving-expert/solutions/` 中创建 Markdown 文件
2. 文件名格式：`YYYYMMDD_HHMMSS_topic.md`
3. 文件必须包含 YAML header：

```markdown
---
title: 问题标题
tags: [tag1, tag2, tag3]
created: 2026-01-26
workspace: /home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus
references:
  - path: ../docs/implementation.md
    type: detail
  - url: https://example.com/docs
    type: external
---

## 问题描述
...

## 解决方案
...
```

## 文档整理和归档（新功能）

### 为什么需要文档整理?

对于已使用多年的代码仓库，通常存在：
- 📄 散落的文档（docs、README、注释等）
- 🔀 不规范的目录结构
- 📝 缺失的元数据和分类
- 🔗 文档之间没有关联关系

**文档整理的目的**：将这些散落的文档系统化、结构化，建立清晰的索引和分类，为知识复用奠定基础。

### 快速开始

#### 1. 一行命令扫描整个仓库

```bash
cd /home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus

# 扫描所有文档，自动分类和归档
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --output-dir ./docs/.evolving-expert/archives
```

#### 2. 查看归档报告

```bash
# 查看详细的扫描和导入报告
cat ./docs/.evolving-expert/archives/report.txt

# 查看元数据 (JSON 格式)
cat ./docs/.evolving-expert/archives/metadata.json | jq .
```

#### 3. 高级选项

```bash
# 仅扫描特定目录
./docs/.evolving-expert/organize_documents.sh \
  --scan-root ./docs \
  --exclude "tests,build,node_modules"

# 指定文件类型
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --file-types "md,txt,rst"

# 添加自定义默认标签
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --default-tags "ros2,legacy,documentation"
```

### 输出结构

整理后的归档目录结构：

```
./docs/.evolving-expert/archives/
├── metadata.json              # 所有导入文档的完整元数据
├── report.txt                 # 扫描和导入报告
├── stats.json                 # 统计数据（可选）
└── imported/
    ├── 20260126_001_xxx.md
    ├── 20260126_002_yyy.md
    └── ...                    # 所有整理后的文档副本
```

### 元数据文件详解

`metadata.json` 包含所有文档的详细信息：

```json
{
  "scan": {
    "timestamp": "2026-01-26T10:45:00Z",
    "scan_root": ".",
    "total_files_scanned": 42,
    "files_imported": 18,
    "total_size_bytes": 1024000
  },
  "documents": [
    {
      "import_id": "20260126_001_cmake_build_guide",
      "original_path": "docs/cmake_build_guide.md",
      "title": "CMake Build Configuration Guide",
      "file_size": 5240,
      "line_count": 120,
      "created": "2026-01-26T10:45:00Z",
      "modified": "2026-01-25",
      "tags": ["cmake", "build", "documentation", "ros2"],
      "summary": "Complete guide for setting up CMake configuration...",
      "archived_path": "imported/20260126_001_cmake_build_guide.md",
      "confidence": 0.95
    }
  ],
  "statistics": {
    "total_documents": 18,
    "total_lines": 3250,
    "total_size": 1024000,
    "avg_doc_size": 56889,
    "by_tag": {
      "documentation": 12,
      "ros2": 10,
      "cmake": 7
    }
  }
}
```

### 标签和分类

整理脚本会**自动**分配标签：

1. **默认标签** - 应用于所有文档
   ```
   documentation, legacy
   ```

2. **基于目录的标签** - 根据文件所在目录
   ```
   docs/api/          → api, reference
   docs/tutorials/    → guide, tutorial
   docs/troubleshoot/ → troubleshooting, faq
   ```

3. **基于文件名的标签** - 根据文件名关键词
   ```
   setup_guide.md     → setup, installation
   build_instructions.md → build, compilation
   ```

### 示例输出

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 文档整理报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

扫描信息
  扫描时间: 2026-01-26T10:45:00Z
  扫描根目录: /home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus
  导入文件: 18 个
  总大小: 1.02 MB

文档统计
  总行数: 3,250
  总大小: 1,048,576 bytes
  平均文档大小: 58,254 bytes

标签分布 (Top 10)
  • documentation: 12 文档
  • ros2: 10 文档
  • cmake: 7 文档
  • build: 5 文档
  • api: 4 文档

最大的文档 (Top 5)
  cmake_build_guide: 120 lines
  ros2_setup_guide: 98 lines
  api_reference: 85 lines
  ...

导入的文档清单
  [20260126_001] CMake Build Configuration Guide
      路径: docs/cmake_build_guide.md
      标签: cmake, build, documentation
      大小: 5,240 bytes | 行数: 120

  [20260126_002] ROS2 Setup Instructions
      路径: docs/ros2_setup.md
      标签: ros2, setup, installation
      大小: 4,120 bytes | 行数: 95
  ...

总结
  归档目录: ./docs/.evolving-expert/archives
  元数据: ./docs/.evolving-expert/archives/metadata.json
  文档文件: ./docs/.evolving-expert/archives/imported/
```

### 将归档文档导入知识库

整理完成后，可以将这些文档导入到知识库中：

```bash
# 遍历所有归档文档，导入到知识库
for doc in ./docs/.evolving-expert/archives/imported/*.md; do
    # 从元数据中获取标题和标签
    import_id=$(basename "$doc" .md)
    title=$(jq -r ".documents[] | select(.archived_path | endswith(\"$(basename \"$doc\")\")) | .title" \
            ./docs/.evolving-expert/archives/metadata.json)
    tags=$(jq -r ".documents[] | select(.archived_path | endswith(\"$(basename \"$doc\")\")) | .tags | join(\",\")" \
           ./docs/.evolving-expert/archives/metadata.json)

    # 导入到知识库
    /home/jiusi/agent-plugins/plugins/skill-evolving-expert/skills/evolving-expert/scripts/knowledge_manager_v2.sh add \
        "$title" "$tags" "$doc"
done
```

### 配置文件

可以创建 `organize.config` 文件自定义扫描规则：

```bash
# 复制配置模板
cp ./docs/.evolving-expert/organize.config.example \
   ./docs/.evolving-expert/organize.config

# 编辑配置文件
vim ./docs/.evolving-expert/organize.config

# 使用自定义配置 (脚本会自动读取)
./docs/.evolving-expert/organize_documents.sh \
  --scan-root .
```

配置文件支持：
- 自定义扫描规则（包含/排除目录）
- 自定义分类规则（基于目录和文件名）
- 自定义标签策略
- 自定义元数据提取方式

详见 `organize.config.example` 了解所有选项。

---

## 查询知识库

### 搜索解决方案

```bash
# 搜索本地知识库
./docs/.evolving-expert/knowledge_manager_v2.sh search "编译" local

# 搜索全局知识库
./docs/.evolving-expert/knowledge_manager_v2.sh search "编译" global
```

### 读取完整内容

```bash
./docs/.evolving-expert/knowledge_manager_v2.sh read 20260126_123456_fix_compile
```

### 查看统计

```bash
./docs/.evolving-expert/knowledge_manager_v2.sh stats
```

输出示例：
```
📊 知识库状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  本地解决方案: 5
  本地模式: 2
  全局可用: 23
```

## 索引文件格式

### 本地索引 (`./docs/.evolving-expert/index.json`)

```json
{
  "meta": {
    "version": "2.0",
    "scope": "local",
    "workspace": "/home/jiusi/M-DDS/ros2/...",
    "created": "2026-01-26T...",
    "description": "本地项目知识库索引"
  },
  "solutions": [
    {
      "id": "20260126_123456_fix_compile",
      "title": "修复编译错误",
      "tags": ["ros2", "compilation"],
      "file": "solutions/20260126_123456_fix_compile.md",
      "created": "2026-01-26T...",
      "hit_count": 0
    }
  ],
  "references": {
    "global": [
      "20260125_234500_cmake_tips"
    ]
  }
}
```

### 全局索引 (`~/.claude/knowledge-base/index.json`)

```json
{
  "meta": {
    "version": "2.0",
    "scope": "global"
  },
  "workspaces": [
    {
      "name": "rmw_dsoftbus",
      "path": "/home/jiusi/M-DDS/...",
      "registered": "2026-01-26T..."
    }
  ],
  "solutions": [
    {
      "id": "20260126_123456_fix_compile",
      "title": "修复编译错误",
      "workspace": "/home/jiusi/M-DDS/...",
      "local_file": "/home/jiusi/.../solutions/...md",
      "hit_count": 0
    }
  ]
}
```

## 参考字段规范

解决方案中的 `references` 字段应该包含准确的路径：

```yaml
references:
  # 相对路径（相对于解决方案文件）
  - path: ../docs/implementation.md
    type: detail
    description: 详细实现说明

  # 绝对路径（用于跨项目引用）
  - path: /home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus/docs/cmake_config.md
    type: config
    description: CMake 配置文档

  # 外部链接
  - url: https://ros.org/documentation
    type: external
    description: ROS 官方文档
```

## 后台统计更新

系统采用 **后台静默更新** 策略：

- ✅ 每次 SessionStart 时自动同步统计
- ✅ 无冗长输出，对用户完全透明
- ✅ 统计信息始终保持最新
- ❌ 不会在启动时显示繁琐的统计细节

## 常见问题

### Q: 在不同工作目录创建的知识库之间如何关联？

A: 它们通过全局索引 (`~/.claude/knowledge-base/`) 自动关联。当你在 rmw_dsoftbus 目录添加解决方案时，它同时被记录在全局索引中；当你切换到另一个项目时，也能通过全局索引查询到其他项目的解决方案。

### Q: 如何在 Claude 对话中自动使用知识库？

A: 知识库被设计为 Claude Code 的底层能力。在你遇到问题时，Claude 会自动：
1. 检索相关的历史解决方案
2. 应用已提炼的最佳实践
3. 提出优化建议

用户无需手动查询。

### Q: 全局知识库和本地知识库的区别是什么？

A:
- **全局知识库** (`~/.claude/knowledge-base/`)：跨所有项目的解决方案集合，用于模式识别和知识复用
- **本地知识库** (`./docs/.evolving-expert/`)：当前项目的详细文档和实现细节

### Q: 统计信息为什么不实时显示？

A: 这是 **有意设计**。统计在后台更新，确保：
- 用户界面简洁清晰
- 不中断工作流程
- 性能最优化

## 文件位置速查

```
本地知识库
├── docs/.evolving-expert/
│   ├── index.json              # 本地索引
│   ├── solutions/              # 解决方案文件
│   │   ├── 20260126_123456_xxx.md
│   │   └── ...
│   ├── patterns/               # 提炼的模式
│   └── knowledge_manager_v2.sh # 管理脚本

全局知识库
├── ~/.claude/knowledge-base/
│   ├── index.json              # 全局索引
│   ├── solutions/              # 全局解决方案（可选）
│   ├── patterns/               # 全局模式（可选）
│   └── summaries/              # 跨项目总结
```

---

**设计理念**：知识库是 Claude Code 的底层能力，对用户透明。你只需专注于解决问题，知识的累积和复用由系统自动完成。

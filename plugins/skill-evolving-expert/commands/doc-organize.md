---
description: 整理和归档仓库中的现有文档
allowed-tools:
  - Bash(find,grep,stat)
---

# 文档整理和归档

扫描当前仓库中的文档，自动整理、分类、归档到知识库，并生成统计报告。

## 功能概述

此命令会：

1. **扫描文档** - 递归扫描仓库中的所有文档文件（支持自定义扩展名）
2. **提取元数据** - 自动识别文档标题、分类、内容摘要
3. **分类标签化** - 根据目录结构和内容自动生成标签
4. **归档导入** - 将文档导入知识库，建立引用关系
5. **生成报告** - 输出详细的统计和分类报告

## 支持的文档格式

- Markdown (`.md`)
- 纯文本 (`.txt`)
- 代码注释文档 (`.c`, `.h`, `.py`, `.js`, `.rs`, etc.)
- 配置说明 (`.yaml`, `.json`, `.toml`)

## 使用示例

### 基础用法 - 扫描整个仓库

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --output-dir ./docs/.evolving-expert/archives
```

### 扫描特定目录

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root ./docs \
  --exclude tests,build,node_modules \
  --output-dir ./docs/.evolving-expert/archives
```

### 仅扫描特定类型

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --file-types "md,txt" \
  --output-dir ./docs/.evolving-expert/archives
```

### 指定默认标签

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root ./docs \
  --default-tags "ros2,documentation,legacy" \
  --output-dir ./docs/.evolving-expert/archives
```

## 输出结果

### 归档文件结构

```
./docs/.evolving-expert/archives/
├── metadata.json           # 所有导入文档的元数据索引
├── report.txt              # 详细的扫描和归档报告
├── stats.json              # 统计数据（JSON格式）
└── imported/
    ├── 20260126_001_cmake_build_guide.md
    ├── 20260126_002_ros2_setup_instructions.md
    └── ...
```

### 元数据格式 (metadata.json)

```json
{
  "scan": {
    "timestamp": "2026-01-26T10:45:00Z",
    "scan_root": "/home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus",
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
      "created": "2026-01-20",
      "modified": "2026-01-25",
      "tags": ["cmake", "build", "documentation", "ros2"],
      "summary": "Complete guide for setting up CMake configuration for ROS2 projects...",
      "sections": ["Overview", "Prerequisites", "Configuration", "Troubleshooting"],
      "has_code_blocks": true,
      "has_tables": true,
      "confidence": 0.95,
      "archived_path": "imported/20260126_001_cmake_build_guide.md"
    }
  ],
  "statistics": {
    "by_tag": {
      "documentation": 12,
      "ros2": 10,
      "cmake": 7,
      "build": 5
    },
    "by_directory": {
      "docs": 15,
      "src": 2,
      "config": 1
    },
    "by_type": {
      "markdown": 16,
      "text": 2
    },
    "total_lines": 3250,
    "total_words": 28000,
    "avg_doc_size": 1800
  }
}
```

### 报告样例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 文档整理报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

扫描信息
  扫描时间: 2026-01-26 10:45:00
  扫描根目录: /home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus
  扫描文件总数: 42
  成功导入: 18
  导入成功率: 85.7%

文档统计
  总行数: 3,250
  总字数: 28,000
  总大小: 1.02 MB
  平均文档大小: 1.8 KB
  最大文档: cmake_build_guide.md (120 行)
  最小文档: readme.txt (8 行)

标签分布 (Top 10)
  documentation: 12 份
  ros2: 10 份
  cmake: 7 份
  build: 5 份
  configuration: 4 份
  ...

目录分布
  docs/: 15 份 (83%)
  src/: 2 份 (11%)
  config/: 1 份 (6%)

内容分析
  包含代码块的文档: 14 份
  包含表格的文档: 8 份
  包含链接的文档: 16 份
  包含图片的文档: 3 份

导入的文档清单
  1. cmake_build_guide.md → 20260126_001_cmake_build_guide
  2. ros2_setup_instructions.md → 20260126_002_ros2_setup_instructions
  3. compilation_troubleshooting.md → 20260126_003_compilation_troubleshooting
  ...

归档位置
  元数据: ./docs/.evolving-expert/archives/metadata.json
  报告: ./docs/.evolving-expert/archives/report.txt
  统计: ./docs/.evolving-expert/archives/stats.json
  文档: ./docs/.evolving-expert/archives/imported/

下一步建议
  • 检查低信度的导入 (confidence < 0.8)
  • 为未标签化的文档添加手动标签
  • 定期更新过时的文档
  • 按标签将文档与解决方案关联
```

## 配置文件 (可选)

在 `.evolving-expert/organize.config` 中定制规则：

```yaml
# 扫描规则
scan:
  # 包含的文件类型
  file_types: [md, txt, rst, adoc]

  # 排除的目录
  exclude_dirs: [tests, build, node_modules, .git, venv, __pycache__]

  # 排除的文件模式
  exclude_patterns: ["*.test.md", "*~", ".*.bak"]

# 分类规则
categorization:
  # 基于目录路径的自动标签
  directory_tags:
    docs/architecture: [architecture, design]
    docs/api: [api, reference]
    docs/tutorials: [tutorial, guide]
    docs/troubleshooting: [troubleshooting, faq]

  # 基于文件名的关键词
  filename_keywords:
    setup: [setup, installation, configure]
    build: [build, compile, cmake]
    test: [test, unittest, qa]

# 元数据提取
metadata:
  # 自动检测的标题来源
  title_sources: [h1_heading, filename]

  # 默认标签（应用于所有文档）
  default_tags: [documentation, legacy]

  # 提取摘要的方法
  summary_method: first_paragraph  # 或 auto_extract

# 导入规则
import:
  # 是否创建原始文档的副本
  preserve_original: true

  # 是否保持相对路径关系
  preserve_structure: false

  # 文档ID生成方式
  id_format: "yyyymmdd_seq_slugified_title"
```

## 常见问题

**Q: 如何只导入特定目录的文档?**

A: 使用 `--scan-root` 指定起点目录，例如 `--scan-root ./docs`

**Q: 导入后如何修改标签?**

A: 编辑 `archives/metadata.json` 中的 `tags` 字段，或使用 `knowledge_manager_v2.sh` 更新

**Q: 如何增量导入（仅导入新添加的文档）?**

A: 保存 `metadata.json` 的时间戳，下次扫描时只导入更新的文件

**Q: 导入的文档如何与解决方案关联?**

A: 在 `metadata.json` 中设置 `related_solutions` 字段，或在知识库索引中手动建立关系

---

**设计理念**: 文档整理是知识库的初始化阶段，帮助将遗留项目的文档系统化、结构化，为知识复用打下基础。

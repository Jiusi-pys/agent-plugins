---
description: 整理和归档仓库中的现有文档
allowed-tools:
  - Bash(find,stat,wc,head,grep)
---

# 整理和归档文档

为当前项目扫描、整理、分类和归档所有现有文档，生成完整的文档索引和统计报告。

## 命令功能

你可以使用这个命令来：

1. **📄 扫描文档** - 自动发现仓库中的所有文档（Markdown、文本、RST等）
2. **🏷️ 自动分类** - 根据目录路径和文件名自动生成标签
3. **📊 提取元数据** - 自动识别标题、摘要、大小、行数等
4. **📦 归档整理** - 将文档副本保存到 `archives/imported/` 目录
5. **📈 生成报告** - 生成详细的统计报告和 JSON 元数据索引

## 快速使用

### 最简单的方式 - 扫描整个项目

我会为你：
1. 检查当前项目的 `./docs/.evolving-expert/` 是否存在（自动初始化）
2. 运行文档整理脚本扫描所有文档
3. 生成详细的扫描报告
4. 显示统计结果和导入的文档清单

**只需说**："执行 `/doc-organize`"

### 带选项的扫描

你也可以指定：
- `--scan-root <path>` - 扫描的起始目录（默认：`.`）
- `--default-tags <tags>` - 添加默认标签，如 `ros2,legacy`
- `--exclude <dirs>` - 排除的目录，如 `tests,build`

**例如**："执行 `/doc-organize --scan-root ./docs --default-tags ros2,rmw_dsoftbus`"

## 输出结果

命令会生成：

- **metadata.json** - 完整的文档元数据索引（JSON格式）
- **report.txt** - 人类可读的扫描报告
- **imported/** - 归档的文档副本目录

其中包含：
- ✅ 文档总数、总行数、总大小
- ✅ 标签分布统计
- ✅ 每个文档的详细信息（标题、摘要、标签等）
- ✅ 导入状态和置信度评分

## 后续步骤

整理完成后，你可以：

1. **查看报告** - 了解项目有多少文档
2. **导入知识库** - 将整理的文档导入到解决方案库
3. **建立关联** - 在文档和解决方案间建立交叉引用
4. **定期更新** - 有新文档时重新运行此命令

---

## 执行逻辑

当用户运行 `/doc-organize [options]` 时，你应该：

### 步骤 1: 检查和初始化

```bash
# 检查知识库目录是否存在
if [ ! -d "./docs/.evolving-expert" ]; then
    echo "初始化本地知识库..."
    mkdir -p ./docs/.evolving-expert/{solutions,patterns,archives/imported}
fi
```

### 步骤 2: 解析参数

从用户输入中提取：
- `--scan-root` - 扫描根目录（默认：`.`）
- `--default-tags` - 默认标签（默认：`documentation,legacy`）
- `--exclude` - 排除的目录（可选）

### 步骤 3: 运行扫描脚本

```bash
bash ./docs/.evolving-expert/organize_documents_v2.sh \
  --scan-root "$SCAN_ROOT" \
  --output-dir "./docs/.evolving-expert/archives" \
  --default-tags "$DEFAULT_TAGS"
```

### 步骤 4: 显示结果

扫描完成后，显示：
1. 扫描报告内容（`report.txt`）
2. 统计摘要（文档数、总行数、标签分布）
3. 导入的文档清单（前 10 个）

### 步骤 5: 提供后续建议

根据扫描结果建议：
- 导入知识库的命令
- 查看完整元数据的方式
- 定期更新的计划

## 使用示例

### 示例 1: 扫描整个项目
```
用户: /doc-organize
系统: 扫描 . 目录下的所有文档
结果: 显示找到的文档数量和标签分布
```

### 示例 2: 扫描特定目录
```
用户: /doc-organize --scan-root ./docs
系统: 仅扫描 ./docs 目录
结果: 显示该目录的文档统计
```

### 示例 3: 添加项目标签
```
用户: /doc-organize --default-tags "ros2,rmw_dsoftbus,v2.0"
系统: 扫描项目并为所有文档添加这些标签
结果: 显示带有项目标签的文档索引
```

---

现在，请告诉我你想要如何进行文档整理：

1. **立即扫描整个项目** - `/doc-organize`
2. **仅扫描 docs 目录** - `/doc-organize --scan-root ./docs`
3. **添加项目标签** - `/doc-organize --default-tags "ros2,rmw_dsoftbus"`
4. **查看详细帮助** - `/doc-organize --help`

我会自动执行扫描，并显示详细的整理结果！

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

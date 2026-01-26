# 文档整理和归档指南

## 特性概述

**文档整理**是新增的功能，用于将已有的代码仓库中的散落文档系统化地整理、分类、归档到知识库。

### 解决的问题

对于已使用多年的项目仓库，通常面临：

| 问题 | 表现 | 后果 |
|-----|-----|-----|
| **文档散落** | 文档分散在 docs/、README、代码注释等各个角落 | 难以发现和复用 |
| **结构混乱** | 目录命名不规范，分类不清 | 无法快速定位 |
| **缺少元数据** | 没有统一的标题、摘要、标签 | 难以检索 |
| **无法统计** | 不知道有多少文档、什么内容 | 知识库利用率低 |

**文档整理的解决方案**：
- ✅ 自动扫描并发现所有文档
- ✅ 自动提取元数据（标题、摘要、关键词）
- ✅ 自动分类和标签化
- ✅ 生成详细的统计报告
- ✅ 建立可导入知识库的索引

---

## 快速开始

### 步骤 1: 初始化（自动完成）

当你在任何项目目录开启 Claude 时，知识库会自动初始化：

```
./docs/.evolving-expert/
├── archives/          ← 文档整理的输出目录
├── solutions/         ← 解决方案存储
├── patterns/          ← 提炼的模式
└── index.json         ← 本地索引
```

### 步骤 2: 扫描和整理文档

```bash
cd /home/jiusi/M-DDS/ros2/src/ros2/rmw_dsoftbus

# 基础扫描 - 整个仓库
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --output-dir ./docs/.evolving-expert/archives
```

**系统会自动**：
1. 扫描所有文档文件 (`.md`, `.txt`, `.rst` 等)
2. 提取标题、摘要、行数等元数据
3. 根据目录和文件名自动分配标签
4. 将文档复制到 `archives/imported/` 目录
5. 生成 `metadata.json` 元数据索引
6. 生成 `report.txt` 扫描报告

### 步骤 3: 查看整理结果

```bash
# 查看扫描报告
cat ./docs/.evolving-expert/archives/report.txt

# 查看元数据 (JSON格式)
jq . ./docs/.evolving-expert/archives/metadata.json

# 生成更详细的报告
./docs/.evolving-expert/generate_archive_report.sh \
  ./docs/.evolving-expert/archives
```

### 步骤 4: 将文档导入知识库（可选）

```bash
# 批量导入所有归档文档到知识库
for doc in ./docs/.evolving-expert/archives/imported/*.md; do
    filename=$(basename "$doc" .md)
    title=$(jq -r ".documents[] | select(.import_id == \"$filename\") | .title" \
            ./docs/.evolving-expert/archives/metadata.json)
    tags=$(jq -r ".documents[] | select(.import_id == \"$filename\") | .tags | join(\",\")" \
           ./docs/.evolving-expert/archives/metadata.json)

    /home/jiusi/agent-plugins/plugins/skill-evolving-expert/skills/evolving-expert/scripts/knowledge_manager_v2.sh add \
        "$title" "$tags" "$doc"
done
```

---

## 完整使用手册

### 参数说明

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root <path>          # 扫描根目录 (默认: .)
  --output-dir <path>         # 输出目录 (默认: ./.evolving-expert/archives)
  --file-types <types>        # 文件类型 (默认: md,txt,rst)
  --exclude <dirs>            # 排除目录 (逗号分隔)
  --default-tags <tags>       # 默认标签 (逗号分隔)
```

### 常见场景

#### 场景 1: 仅扫描 docs 目录

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root ./docs \
  --exclude "tests,examples"
```

输出：只导入 `docs/` 目录下的文档

#### 场景 2: 扫描特定类型的文件

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --file-types "md,rst,adoc"
```

输出：只导入 Markdown、reStructuredText 和 AsciiDoc 文件

#### 场景 3: 添加项目特定的标签

```bash
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --default-tags "ros2,rmw_dsoftbus,v2.0"
```

输出：所有文档都会获得这些标签，便于跨项目查询

#### 场景 4: 增量扫描（仅导入新文档）

```bash
# 第一次完整扫描
./docs/.evolving-expert/organize_documents.sh --scan-root .

# 之后只扫描新添加的文件
# （检查 modified 时间戳，跳过已导入的）
```

---

## 输出详解

### metadata.json 结构

最重要的输出文件，包含所有文档的完整信息：

```json
{
  "scan": {
    "timestamp": "2026-01-26T10:45:00Z",    // 扫描时间
    "scan_root": "/path/to/project",       // 扫描根目录
    "total_files_scanned": 42,             // 扫描的总文件数
    "files_imported": 18,                  // 成功导入的文件数
    "total_size_bytes": 1024000            // 总大小
  },
  "documents": [
    {
      "import_id": "20260126_001_cmake_build_guide",  // 唯一ID
      "original_path": "docs/cmake_build_guide.md",   // 原始路径
      "title": "CMake Build Configuration",           // 自动提取的标题
      "file_size": 5240,                             // 文件大小
      "line_count": 120,                             // 行数
      "created": "2026-01-26T10:45:00Z",             // 导入时间
      "modified": "2026-01-25",                      // 最后修改时间
      "tags": ["cmake", "build", "documentation"],   // 自动分配的标签
      "summary": "Complete guide for CMake setup...", // 自动提取的摘要
      "archived_path": "imported/20260126_001_...",  // 归档后的位置
      "confidence": 0.95                             // 提取的置信度
    }
  ],
  "statistics": {
    "total_documents": 18,
    "total_lines": 3250,
    "total_size": 1024000,
    "avg_doc_size": 56889,
    "by_tag": {
      "documentation": 12,   // 有此标签的文档数
      "ros2": 10,
      "cmake": 7
    }
  }
}
```

### report.txt 示例

人类可读的扫描报告，包含：
- 扫描统计信息
- 文档清单
- 标签分布
- 最大的文档
- 归档位置和后续步骤

---

## 高级用法

### 自定义扫描规则

创建 `organize.config` 文件自定义行为：

```bash
# 复制配置模板
cp ./docs/.evolving-expert/organize.config.example \
   ./docs/.evolving-expert/organize.config
```

编辑 `organize.config` 可以自定义：

#### 1. 扫描规则
```yaml
scan:
  file_types: [md, txt, rst, adoc]
  exclude_dirs: [tests, build, node_modules, .git]
```

#### 2. 分类规则
```yaml
categorization:
  directory_tags:
    docs/api: [api, reference]
    docs/tutorials: [tutorial, guide]
```

#### 3. 标签规则
```yaml
categorization:
  filename_keywords:
    setup:
      keywords: [setup, install]
      tags: [setup, installation]
```

#### 4. 元数据提取
```yaml
metadata:
  title_sources: [h1_heading, yaml_title, filename]
  summary_method: first_paragraph
```

### 批量处理

#### 导入所有文档到知识库

```bash
#!/bin/bash
ARCHIVE_DIR="./docs/.evolving-expert/archives"

jq -r '.documents[] | "\(.import_id)|\(.title)|\(.tags | join(","))"' \
  "$ARCHIVE_DIR/metadata.json" | while IFS='|' read id title tags; do
    doc_path="$ARCHIVE_DIR/imported/${id}.md"
    if [ -f "$doc_path" ]; then
        /path/to/knowledge_manager_v2.sh add "$title" "$tags" "$doc_path"
    fi
done
```

#### 按标签分组导出

```bash
# 导出所有 "api" 标签的文档
jq '.documents[] | select(.tags[] == "api")' \
  ./docs/.evolving-expert/archives/metadata.json
```

#### 统计分析

```bash
# 统计每个标签的文档数
jq '[.documents[].tags[]] | group_by(.) | map({tag: .[0], count: length})' \
  ./docs/.evolving-expert/archives/metadata.json

# 找出最大的文档
jq '.documents | max_by(.file_size)' \
  ./docs/.evolving-expert/archives/metadata.json
```

---

## 与知识库的集成

### 文档 → 解决方案的映射

整理后的文档可以与解决方案建立关联：

```json
{
  "import_id": "20260126_001_cmake_build_guide",
  "related_solutions": [
    "20260125_234500_fix_cmake_config",
    "20260124_180000_optimize_build_time"
  ]
}
```

### 知识库查询

整理后的文档会显示在知识库统计中：

```bash
./docs/.evolving-expert/knowledge_manager_v2.sh stats

📊 知识库状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  本地解决方案: 5
  本地模式: 2
  本地文档: 18          ← 整理的文档
  全局可用: 23
```

---

## 性能建议

### 大型仓库（> 1000 个文件）

```bash
# 使用更严格的过滤条件，减少扫描范围
./docs/.evolving-expert/organize_documents.sh \
  --scan-root . \
  --exclude "tests,build,node_modules,vendor,third_party,.git,__pycache__" \
  --file-types "md,txt"
```

### 增量更新

```bash
# 保存前一次的 timestamp，仅扫描新文件
LAST_SCAN=$(stat -f%Sm ./docs/.evolving-expert/archives/metadata.json)
find . -type f -newer ./docs/.evolving-expert/archives/metadata.json
```

---

## 常见问题

**Q: 如何修改已导入文档的标签？**

A: 编辑 `metadata.json` 的 `tags` 字段，或使用 `knowledge_manager_v2.sh` 更新。

**Q: 文档的 confidence 分数是什么？**

A: 表示元数据提取的准确度（0.0-1.0）。低于 0.8 的需要人工审查。

**Q: 如何处理非英文文档？**

A: 脚本支持 UTF-8，但标题提取基于标记（H1 标题、YAML header），应在文件中用规范格式编写。

**Q: 导入后可以修改文档吗？**

A: 可以。修改 `archives/imported/` 中的文件，然后导入到知识库。原始文件保持不变。

---

## 下一步

文档整理完成后，你可以：

1. **导入知识库** - 将整理的文档导入解决方案库
2. **建立关联** - 在文档和解决方案间建立跨引用
3. **定期更新** - 定期重新扫描，保持文档库最新
4. **提炼模式** - 从文档中提炼最佳实践和设计模式

---

**下一阶段**：使用 `knowledge_manager_v2.sh` 将整理的文档导入知识库，并与解决方案建立关系。

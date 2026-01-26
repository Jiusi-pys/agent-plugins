---
description: 智能扫描、分类和组织文档到合理的目录结构
allowed-tools:
  - Bash(find,stat,wc,head,grep,mv,cp,ln,mkdir)
---

# 文档智能组织和移动

自动扫描项目中的散落文档，按照选定的分类策略整理成合理的目录结构，并支持多种命名规范。

## 🎯 核心功能

### 1. 智能文档扫描
- 🔍 递归发现所有 Markdown、文本、RST 文档
- 📍 支持指定扫描源目录
- ⏭️ 自动跳过已组织的文档，避免重复

### 2. 自动分类
根据选定的分类策略，文档会被自动放入对应的目录：

**按功能分类** (by-function) - 最灵活
```
docs/
├── api/              # API 和接口文档
├── guides/           # 使用指南和快速开始
├── architecture/     # 架构和设计文档
├── tutorials/        # 教程和示例
├── reference/        # 参考资料
├── setup/            # 安装和配置
├── deployment/       # 部署指南
├── maintenance/      # 维护文档
└── troubleshooting/  # 问题排查
```

**按开发阶段分类** (by-stage) - 最直观
```
docs/
├── setup/            # 安装和配置
├── development/      # 开发指南、架构、教程
├── deployment/       # 部署指南
├── maintenance/      # 维护文档
└── troubleshooting/  # 问题排查
```

**按标签分类** (by-tag) - 最灵活
```
docs/
├── ros2/             # ROS2 相关文档
├── cmake/            # CMake 相关文档
├── build/            # 编译相关文档
└── ...
```

### 3. 文件命名规范
- **自动编号** (auto-numbered): `01_xxx.md`, `02_yyy.md` - 推荐
- **按标题** (by-title): `xxx.md`, `yyy.md` - 保持原名
- **保持原名** (original): 完全保持原文件名

### 4. 灵活的文件操作
- **移动** (move): 直接移动文件到目标位置 - 推荐
- **复制** (copy): 复制文件，保留原位置
- **软链接** (symlink): 创建软链接（不移动实际文件）

### 5. 自动生成导航
在 `docs/README.md` 自动生成文档导航索引

## 📖 使用示例

### 最简单：一行命令按功能分类
```
/doc-organize
```

结果：文档按功能自动组织到 `docs/` 目录

### 按开发阶段分类
```
/doc-organize --strategy by-stage
```

结果：按 setup → development → deployment → maintenance 组织

### 按标签分类（如 ros2, cmake 等）
```
/doc-organize --strategy by-tag
```

### 干运行模式（预览而不实际移动）
```
/doc-organize --dry-run
```

### 完整配置示例
```
/doc-organize \
  --scan-root . \
  --output-root ./docs \
  --strategy by-function \
  --naming auto-numbered \
  --action move
```

## 🔧 参数说明

| 参数 | 说明 | 默认值 | 选项 |
|-----|------|--------|------|
| `--scan-root <path>` | 扫描的源目录 | `.` | 任意路径 |
| `--output-root <path>` | 组织后的目录 | `./docs` | 任意路径 |
| `--strategy <name>` | 分类策略 | `by-function` | `by-function`, `by-stage`, `by-tag` |
| `--naming <style>` | 命名规范 | `auto-numbered` | `auto-numbered`, `by-title`, `original` |
| `--action <op>` | 文件操作 | `move` | `move`, `copy`, `symlink` |
| `--dry-run` | 干运行模式 | 不使用 | 无值标志 |

## 📋 常见场景

### 场景 1: 项目刚接手，文档散落各处
```
/doc-organize --scan-root . --strategy by-function --dry-run
```
先预览一下会怎么组织，再决定是否执行

### 场景 2: 想按开发阶段组织文档
```
/doc-organize --strategy by-stage
```

### 场景 3: 不想移动原文件，只想看结果
```
/doc-organize --action copy
```
会在 `docs/` 中创建副本，原文件保持不变

### 场景 4: 想用自动编号便于管理
```
/doc-organize --naming auto-numbered
```
文档会被重命名为 `01_xxx.md`, `02_yyy.md` 等

## 🔄 工作流程

```
1️⃣ 运行命令
   /doc-organize [options]
        ↓
2️⃣ 扫描文档
   发现散落的文档
        ↓
3️⃣ 自动分类
   根据文件名和内容识别分类
        ↓
4️⃣ 组织和移动
   文件被移动到合理的目录结构
        ↓
5️⃣ 生成导航
   docs/README.md 自动生成目录索引
        ↓
6️⃣ 显示结果
   显示组织摘要和后续步骤
```

## ✨ 执行流程

你运行 `/doc-organize [options]` 时，系统会：

1. **验证参数** → 确保参数有效
2. **扫描源目录** → 找到所有文档
3. **识别分类** → 根据文件名和内容判断应该放在哪里
4. **执行操作** → 移动/复制/软链接文件
5. **生成导航** → 创建 README.md 索引
6. **显示结果** → 报告整理摘要

## 💡 建议

- 🔍 第一次运行时使用 `--dry-run` 预览结果
- 📁 如果不确定，使用 `--strategy by-function` 最灵活
- 📌 使用 `--naming auto-numbered` 便于管理
- 🚀 一旦组织好，可以定期运行来整理新文档

---

现在告诉我你想如何组织文档：

1. **按功能分类** - `/doc-organize --strategy by-function`
2. **按开发阶段** - `/doc-organize --strategy by-stage`
3. **按标签分类** - `/doc-organize --strategy by-tag`
4. **先预览** - `/doc-organize --dry-run`
5. **查看帮助** - `/doc-organize --help`

---
description: 智能扫描、分类和组织文档到合理的目录结构
allowed-tools:
  - Task(doc-organizer)
---

# 文档智能组织

自动扫描、理解、分类和组织项目文档，创建清晰的目录结构。

## 快速开始

### 最简单的用法
```
/doc-organize
```
按功能分类，自动编号，直接移动文件

### 先预览（推荐）
```
/doc-organize --dry-run
```
查看会如何整理，不实际移动文件

### 按开发阶段分类
```
/doc-organize --strategy by-stage
```

### 查看完整帮助
```
/doc-organize --help
```

---

## 参数说明

### 基础参数

| 参数 | 说明 | 默认值 |
|-----|------|--------|
| `--scan-root <path>` | 扫描的源目录 | `.` (当前目录) |
| `--output-root <path>` | 输出的目标目录 | `./docs` |

### 分类策略 (`--strategy`)

| 策略 | 说明 | 生成的目录 |
|-----|------|-----------|
| `by-function` | **按功能分类** (推荐) | api, guides, architecture, tutorials, reference, setup, deployment, maintenance, troubleshooting |
| `by-stage` | **按开发阶段** | setup, development, deployment, maintenance, troubleshooting |
| `by-tag` | **按标签分类** | 根据内容自动识别（ros2, cmake, build 等） |

**默认**: `by-function`

#### 详细说明

**by-function** - 最细致的分类
```
docs/
├── api/              # API 文档、接口定义
├── guides/           # 使用指南、配置说明
├── architecture/     # 架构设计、系统设计
├── tutorials/        # 教程、示例代码
├── reference/        # 参考资料、术语表
├── setup/            # 安装配置、环境要求
├── deployment/       # 部署指南、发布流程
├── maintenance/      # 维护文档、升级指南
└── troubleshooting/  # 问题排查、FAQ
```

**by-stage** - 按项目生命周期
```
docs/
├── setup/            # 环境要求、安装步骤
├── development/      # 开发流程、架构、教程、API
├── deployment/       # 发布流程、容器化
├── maintenance/      # 更新升级、迁移
└── troubleshooting/  # 调试、FAQ、错误解决
```

**by-tag** - 按技术主题
```
docs/
├── ros2/             # ROS2 相关
├── cmake/            # CMake 构建
├── build/            # 编译相关
├── api/              # API 文档
└── ...
```

### 命名规范 (`--naming`)

| 规范 | 说明 | 示例 |
|-----|------|------|
| `auto-numbered` | **自动编号** (推荐) | `01_getting_started.md`, `02_configuration.md` |
| `by-title` | **按标题命名** | `getting_started.md`, `configuration.md` |
| `original` | **保持原名** | 保持原始文件名不变 |

**默认**: `auto-numbered`

**推荐使用 auto-numbered**，因为：
- ✅ 文档自动排序
- ✅ 便于管理和查找
- ✅ 清晰的顺序

### 文件操作 (`--action`)

| 操作 | 说明 | 原文件 |
|-----|------|--------|
| `move` | **移动文件** (推荐) | 被删除 |
| `copy` | **复制文件** | 保留 |
| `symlink` | **创建软链接** | 保留 |

**默认**: `move`

**何时使用**：
- `move` - 彻底整理，删除原文件 ⭐ 推荐
- `copy` - 谨慎测试，保留原文件
- `symlink` - 保持原位置，创建引用

### 特殊选项

| 选项 | 说明 |
|-----|------|
| `--dry-run` | **干运行模式** - 预览不实际执行 ⭐ 强烈推荐首次使用 |
| `--help` | **显示帮助** - 完整的参数说明 |

---

## 完整示例

### 示例 1: 快速整理（最常用）
```
/doc-organize
```
- 扫描当前目录
- 按功能分类
- 自动编号
- 直接移动

### 示例 2: 先预览再执行
```
# 第 1 步：预览
/doc-organize --dry-run

# 第 2 步：确认无误后执行
/doc-organize
```

### 示例 3: 按开发阶段分类
```
/doc-organize --strategy by-stage
```

### 示例 4: 扫描特定目录
```
/doc-organize --scan-root ./scattered_docs --output-root ./docs
```

### 示例 5: 保留原文件（复制模式）
```
/doc-organize --action copy
```

### 示例 6: 完整配置
```
/doc-organize \
  --scan-root . \
  --output-root ./docs \
  --strategy by-function \
  --naming auto-numbered \
  --action move
```

### 示例 7: 按标签分类
```
/doc-organize --strategy by-tag
```

---

## 工作流程

```
1️⃣ 调用 doc-organizer agent
        ↓
2️⃣ Agent 扫描文档
   (使用 Glob 和 find)
        ↓
3️⃣ Agent 读取每个文档
   (使用 Read 工具深入理解内容)
        ↓
4️⃣ Agent 智能分类
   (基于实际内容，不仅是文件名)
        ↓
5️⃣ Agent 重命名文件
   (根据命名规范)
        ↓
6️⃣ Agent 移动文件
   (到对应的分类目录)
        ↓
7️⃣ Agent 生成导航
   (README.md 和 _index.json)
        ↓
8️⃣ 向用户报告结果
   (统计、分类详情、后续建议)
```

---

## 详细帮助 (`--help`)

### 参数汇总表

```
参数                      类型      默认值            说明
─────────────────────────────────────────────────────────────
--scan-root <path>       路径      .                 扫描的源目录
--output-root <path>     路径      ./docs            组织后的目录
--strategy <name>        枚举      by-function       分类策略
--naming <style>         枚举      auto-numbered     命名规范
--action <op>            枚举      move              文件操作
--dry-run                标志      false             预览模式
--help                   标志      -                 显示帮助
```

### 策略对比

| 策略 | 优点 | 缺点 | 适用场景 |
|-----|------|------|---------|
| `by-function` | 分类细致，易于查找 | 目录较多 | 功能多样的项目 |
| `by-stage` | 结构简单，符合开发流程 | 分类粗略 | 流程性强的项目 |
| `by-tag` | 灵活，按技术栈分组 | 依赖内容识别 | 跨域文档混杂 |

### 命名对比

| 规范 | 优点 | 缺点 | 示例 |
|-----|------|------|------|
| `auto-numbered` | 自动排序，便于管理 | 文件名较长 | `01_xxx.md` |
| `by-title` | 简洁 | 难以排序 | `xxx.md` |
| `original` | 最少改动 | 可能混乱 | 原文件名 |

### 操作对比

| 操作 | 优点 | 缺点 | 何时使用 |
|-----|------|------|---------|
| `move` | 彻底整理 | 无法恢复 | 确认无误后 |
| `copy` | 保留原文件 | 占用空间 | 测试阶段 |
| `symlink` | 节省空间 | 依赖原文件 | 仅需引用 |

---

## 常见用法速查

```bash
# 1. 快速整理
/doc-organize

# 2. 先预览
/doc-organize --dry-run

# 3. 按阶段分类
/doc-organize --strategy by-stage

# 4. 扫描特定目录
/doc-organize --scan-root ./src/docs

# 5. 保留原文件
/doc-organize --action copy

# 6. 使用原文件名
/doc-organize --naming original

# 7. 完整配置
/doc-organize \
  --scan-root . \
  --output-root ./docs \
  --strategy by-function \
  --naming auto-numbered \
  --action move

# 8. 帮助
/doc-organize --help
```

---

## 执行逻辑

当用户运行 `/doc-organize [options]` 时，你应该：

### 步骤 1: 解析参数

提取用户指定的参数，如果没有指定则使用默认值：
- `--scan-root` (默认: `.`)
- `--output-root` (默认: `./docs`)
- `--strategy` (默认: `by-function`)
- `--naming` (默认: `auto-numbered`)
- `--action` (默认: `move`)
- `--dry-run` (默认: `false`)

如果用户使用 `--help`，显示完整的帮助信息并退出。

### 步骤 2: 调用 doc-organizer agent

使用 Task 工具调用专门的 `doc-organizer` agent：

```
使用 doc-organizer agent 来整理文档：
- 扫描源目录: {scan-root}
- 输出目录: {output-root}
- 分类策略: {strategy}
- 命名规范: {naming}
- 文件操作: {action}
- 干运行模式: {dry-run}

请深入读取每个文档的内容，理解其主题和目的，然后智能分类和组织。
```

### 步骤 3: 显示结果

agent 完成后，显示：
- 整理统计（文档总数、分类数量）
- 分类详情（每个分类的文档列表）
- 生成的导航文件位置
- 后续建议

### 步骤 4: 提供后续步骤

建议用户：
- 查看生成的 README.md
- 检查 _index.json
- 调整分类（如有需要）

---

## 帮助信息模板

当用户使用 `--help` 时，显示：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 文档智能组织 - 完整帮助
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

用法:
  /doc-organize [选项]

快速开始:
  /doc-organize              # 默认配置快速整理
  /doc-organize --dry-run    # 预览不实际执行 ⭐ 推荐首次使用

参数:
  --scan-root <path>         扫描的源目录 (默认: .)
  --output-root <path>       输出的目标目录 (默认: ./docs)
  --strategy <name>          分类策略 (默认: by-function)
  --naming <style>           命名规范 (默认: auto-numbered)
  --action <op>              文件操作 (默认: move)
  --dry-run                  干运行模式 - 预览不实际执行
  --help                     显示此帮助信息

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

分类策略 (--strategy):

  by-function (默认) - 按功能分类 ⭐ 推荐
    docs/api/              API 和接口文档
    docs/guides/           使用指南和快速开始
    docs/architecture/     架构和设计文档
    docs/tutorials/        教程和示例
    docs/reference/        参考资料和索引
    docs/setup/            安装和配置
    docs/deployment/       部署和发布
    docs/maintenance/      维护和升级
    docs/troubleshooting/  问题排查和 FAQ

  by-stage - 按开发阶段分类
    docs/setup/            安装和配置
    docs/development/      开发指南、架构、教程
    docs/deployment/       部署指南
    docs/maintenance/      维护文档
    docs/troubleshooting/  问题排查

  by-tag - 按标签分类
    docs/ros2/             ROS2 相关文档
    docs/cmake/            CMake 相关文档
    docs/build/            编译相关文档
    (根据实际内容自动识别)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

命名规范 (--naming):

  auto-numbered (默认) - 自动编号 ⭐ 推荐
    01_getting_started.md
    02_configuration.md
    03_api_reference.md

    优点: 自动排序、便于管理
    缺点: 文件名较长

  by-title - 按标题命名
    getting_started.md
    configuration.md
    api_reference.md

    优点: 简洁
    缺点: 难以控制顺序

  original - 保持原文件名
    README.md
    docs.md
    guide.txt

    优点: 最少改动
    缺点: 可能混乱

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

文件操作 (--action):

  move (默认) - 移动文件 ⭐ 推荐
    - 文件被移动到新位置
    - 原位置不再保留
    - 最彻底的整理

    ⚠️  注意: 无法恢复，建议先用 --dry-run 预览

  copy - 复制文件
    - 在目标位置创建副本
    - 原文件保持不变
    - 可以回退

    💡 适用于: 测试阶段、不确定时

  symlink - 创建软链接
    - 创建符号链接指向原文件
    - 不占用额外空间
    - 原文件不动

    💡 适用于: 仅需引用、节省空间

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

常见用法:

  # 预览整理结果（不实际移动）
  /doc-organize --dry-run

  # 按功能分类并移动（推荐）
  /doc-organize --strategy by-function

  # 按开发阶段分类
  /doc-organize --strategy by-stage

  # 扫描特定目录
  /doc-organize --scan-root ./src/docs

  # 复制而非移动（保留原文件）
  /doc-organize --action copy

  # 使用原文件名
  /doc-organize --naming original

  # 完整配置
  /doc-organize \
    --scan-root . \
    --output-root ./documentation \
    --strategy by-stage \
    --naming auto-numbered \
    --action move

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

工作流程:

  1. doc-organizer agent 扫描源目录
  2. 读取每个文档的完整内容 ⭐
  3. 理解文档的主题和目的
  4. 智能分类（基于内容，不仅是文件名）
  5. 根据命名规范重命名
  6. 执行文件操作（move/copy/symlink）
  7. 生成导航索引 (README.md)
  8. 生成元数据 (_index.json)
  9. 报告整理结果

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

输出:

  docs/README.md          # 总导航索引
  docs/_index.json        # 元数据索引
  docs/<category>/        # 分类目录
  docs/<category>/README.md   # 分类文档列表

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

提示:

  ⭐ 首次使用时，先用 --dry-run 预览结果
  📁 不确定选哪个策略？使用 by-function 最灵活
  📌 推荐使用 auto-numbered 便于管理
  🔍 agent 会深入读取文档内容来准确分类
  💡 整理后可以定期运行来整理新文档

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

当用户请求整理文档时，你应该：

1. **解析用户提供的参数**（或使用默认值）
2. **如果用户使用 `--help`**，显示上面的完整帮助信息并退出
3. **调用 doc-organizer agent**，传递所有参数
4. **agent 会自动**：
   - 扫描文档
   - 深入读取每个文档内容
   - 理解并智能分类
   - 重命名和移动文件
   - 生成导航和索引
5. **显示结果给用户**

现在告诉我你想如何整理文档，或使用 `--help` 查看完整帮助！

---
name: auto-knowledge-loader
description: 在遇到错误、问题或技术难题时，自动从知识库加载相关的解决方案。此 skill 应该在任何问题解决尝试之前使用。
user-invocable: false
allowed-tools:
  - Read
  - Bash(jq,grep,find)
---

# 自动知识加载 Skill

**在尝试解决任何问题之前，先自动查询知识库中的已有方案。**

## 触发条件

此 skill 应该在以下情况**自动加载**：

### 1. 遇到错误
- 编译错误（CMake、make、gcc 等）
- 链接错误（undefined reference、missing library）
- 运行时错误（segmentation fault、assertion failed）
- 配置错误（missing dependency、version mismatch）

### 2. 需要实现功能
- 添加新功能前，查看是否有类似实现
- 配置新组件前，查看已有配置方案
- 集成第三方库前，查看集成经验

### 3. 用户明确询问
- "之前解决过这个问题吗？"
- "有没有类似的解决方案？"
- "这个错误怎么解决？"

## 工作流程

### 阶段 1: 问题分析

从当前上下文中提取：
- **错误信息**（如果有）
- **技术栈**（ros2, cmake, python 等）
- **问题类型**（编译、配置、运行时等）
- **关键词**（至少 2-3 个）

示例：
```
错误: CMake Error: Could not find ROS2
关键词: ["cmake", "ros2", "configuration", "error"]
```

### 阶段 2: 查询知识库

#### 本地查询

```bash
# 查询本地知识库
LOCAL_KB="./docs/.evolving-expert/index.json"

if [ -f "$LOCAL_KB" ]; then
    # 多关键词查询（OR 逻辑）
    jq --arg kw1 "cmake" --arg kw2 "ros2" '
        .solutions[] |
        select(
            .tags[] | test($kw1; "i") or
            .tags[] | test($kw2; "i") or
            .title | test($kw1; "i") or
            .title | test($kw2; "i")
        )
    ' "$LOCAL_KB"
fi
```

#### 全局查询

```bash
# 查询全局知识库
GLOBAL_KB="$HOME/.claude/knowledge-base/index.json"

if [ -f "$GLOBAL_KB" ]; then
    jq --arg kw1 "cmake" --arg kw2 "ros2" '
        .solutions[] |
        select(
            .tags[] | test($kw1; "i") or
            .tags[] | test($kw2; "i") or
            .title | test($kw1; "i") or
            .title | test($kw2; "i")
        )
    ' "$GLOBAL_KB"
fi
```

### 阶段 3: 相关度排序

按以下因素排序：
1. **标签匹配度**（匹配的标签越多，相关度越高）
2. **标题匹配度**（标题包含关键词）
3. **命中次数**（hit_count 高说明方案有效）
4. **时间新鲜度**（最近的解决方案可能更相关）

### 阶段 4: 读取和评估

对于排序后的前 3 个解决方案：
1. 使用 Read 工具读取完整内容
2. 评估是否适用于当前问题
3. 如果适用，提取关键步骤
4. 如果不适用，继续查看下一个

### 阶段 5: 应用或报告

**如果找到适用方案**：
```
✅ 找到相关解决方案！

方案: [20260125_fix_cmake_config] 修复 CMake 配置错误
来源: 本地知识库
标签: cmake, compilation, build
命中次数: 5 次

摘要:
  通过修改 CMakeLists.txt 中的 find_package 路径解决了...

建议:
  1. 检查 CMakeLists.txt 中的 CMAKE_PREFIX_PATH
  2. 确保 ROS2 环境变量已设置
  3. 重新运行 cmake ..

是否应用此方案？
```

**如果没有找到**：
```
❌ 知识库中未找到相关解决方案

已搜索:
  - 本地知识库: 0 个匹配
  - 全局知识库: 0 个匹配
  - 搜索关键词: cmake, ros2, configuration

建议:
  1. 尝试解决此问题
  2. 问题解决后，记录到知识库
  3. 使用: knowledge_manager_v2.sh add "标题" "标签" "文件"
```

## 知识库路径

此 skill 会检查以下位置：

```
本地知识库:
  - 索引: ./docs/.evolving-expert/index.json
  - 方案: ./docs/.evolving-expert/solutions/*.md
  - 模式: ./docs/.evolving-expert/patterns/*.md

全局知识库:
  - 索引: ~/.claude/knowledge-base/index.json
  - 方案: ~/.claude/knowledge-base/solutions/*.md
  - 模式: ~/.claude/knowledge-base/patterns/*.md
```

## 使用示例

### 自动触发（Claude 决定）

```
用户: 编译时出现 CMake 错误

Claude:
  1. 识别这是一个问题
  2. 自动加载 auto-knowledge-loader skill
  3. 查询知识库中关于 "cmake", "error" 的解决方案
  4. 找到相关方案
  5. 向用户展示并询问是否应用
```

### 手动触发（用户请求）

```
用户: 查询知识库中关于 ROS2 配置的解决方案

Claude:
  1. 使用 knowledge-retrieval skill
  2. 搜索 "ros2", "configuration" 相关方案
  3. 显示找到的结果
```

## 集成到工作流

### Before（没有此 skill）

```
遇到问题 → 尝试解决 → 花费时间 → 可能解决
```

### After（有此 skill）

```
遇到问题
    ↓
自动查询知识库（使用 auto-knowledge-loader）
    ↓
找到方案？
  ├─ 是 → 应用现有方案 → 快速解决 ✅
  └─ 否 → 尝试解决 → 记录到知识库 → 下次复用 ✅
```

## 性能优化

### 缓存机制

知识库索引在 SessionStart 时预加载到内存（通过环境变量）：

```bash
# SessionStart hook 设置
export KNOWLEDGE_CACHE=$(cat ./docs/.evolving-expert/index.json)
```

查询时直接使用缓存，避免重复读取文件。

### 增量搜索

```
第 1 次查询: 精确匹配（所有关键词）
    ↓ 如果找不到
第 2 次查询: 部分匹配（任意关键词）
    ↓ 如果找不到
第 3 次查询: 模糊匹配（标题相似）
```

## 后续增强

未来可以添加：
1. **语义搜索** - 使用嵌入向量匹配相似问题
2. **学习排序** - 基于用户反馈优化排序
3. **主动推荐** - 在编写代码时主动推荐最佳实践
4. **跨项目学习** - 从其他项目的解决方案中学习

---

**核心价值**：避免重复工作，积累和复用知识，提高问题解决效率。

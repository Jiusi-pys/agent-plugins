# Self-Evolving Expert Skill

## 概述

本 skill 实现专家型 sub-agent 的自我进化机制。每次问题解决后自动提取关键知识点，持久化存储，后续任务自动检索应用。

## 核心原则

1. **知识闭环**: 解决问题 → 提取知识 → 存储索引 → 检索应用
2. **渐进积累**: 单次解决方案 → 高频模式提炼 → 领域知识体系
3. **最小冗余**: 相似问题合并，保留差异点

## 工作流程

### Phase 1: 任务启动前 - 知识检索

```bash
# 检索相关历史知识
cat knowledge/index.json | jq '.solutions[] | select(.tags | contains(["关键词"]))'
```

**必须执行**：
1. 读取 `knowledge/index.json` 检索相关条目
2. 如有匹配，读取对应 solution 文件
3. 基于历史知识制定解决方案

### Phase 2: 任务执行

正常执行专家任务，记录：
- 问题描述
- 尝试的方案（含失败的）
- 最终解决方案
- 关键命令/代码

### Phase 3: 任务完成后 - 知识提取

**触发条件**（满足任一）：
- 解决了新问题
- 发现了更优方案
- 踩坑并找到原因

**提取模板**：

```markdown
## 问题摘要
{一句话描述}

## 上下文
- 环境: {OS/硬件/版本}
- 前置条件: {依赖/配置}

## 解决方案
{核心步骤，精简到可直接复用}

## 关键点
- {踩坑点1}
- {关键命令/配置}

## 标签
{tag1}, {tag2}, {tag3}
```

### Phase 4: 知识存储

```bash
# 1. 生成解决方案文件
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TOPIC="简短主题"
echo "{solution_content}" > knowledge/solutions/${TIMESTAMP}_${TOPIC}.md

# 2. 更新索引
# 读取现有索引，追加新条目
```

**索引结构**：
```json
{
  "solutions": [
    {
      "id": "20250116_153000_dsoftbus_init",
      "title": "dsoftbus 初始化失败排查",
      "tags": ["dsoftbus", "openharmony", "rk3588s", "init"],
      "file": "solutions/20250116_153000_dsoftbus_init.md",
      "created": "2025-01-16",
      "hit_count": 0
    }
  ],
  "patterns": [
    {
      "category": "dsoftbus",
      "file": "patterns/dsoftbus.md",
      "solution_refs": ["20250116_153000_dsoftbus_init"]
    }
  ]
}
```

### Phase 5: 模式提炼（周期性）

当同一 tag 下 solutions 数量 ≥ 3 时，触发模式提炼：

1. 汇总相关 solutions
2. 提取共性问题与通用解法
3. 写入 `patterns/{category}.md`
4. 更新索引中的 pattern 引用

## 检索策略

**优先级**：
1. patterns（高置信度，已验证多次）
2. solutions（单次经验，需评估适用性）
3. 无匹配时，正常推理

**检索命令**：
```bash
# 按标签检索
jq '.solutions[] | select(.tags | any(. == "dsoftbus"))' knowledge/index.json

# 按标题模糊匹配
jq '.solutions[] | select(.title | test("init"; "i"))' knowledge/index.json

# 获取高频解决方案
jq '.solutions | sort_by(-.hit_count) | .[0:5]' knowledge/index.json
```

## Sub-Agent 调用示例

主 agent 调用时：

```
Task: 解决 dsoftbus 通信问题

dispatch_agent(
  agent_name="openharmony_expert",
  task="排查 RK3588S 上 dsoftbus 节点发现失败",
  context={
    "board": "RK3588S",
    "os": "KaihongOS 4.0",
    "symptom": "LNN 回调无触发"
  }
)
```

Expert sub-agent 执行流程：
1. 检索 `tags: [dsoftbus, LNN, 节点发现]`
2. 找到历史方案则优先参考
3. 执行排查
4. 解决后提取新知识点存储

## 知识清理规则

- hit_count = 0 且 created > 90天：标记待清理
- 被 pattern 合并的 solutions：保留引用，可归档原文
- 明确过时的方案：添加 `deprecated: true` 标记

## 配置项

```json
{
  "auto_extract": true,
  "extract_threshold": "new_solution|better_solution|pitfall",
  "pattern_merge_threshold": 3,
  "knowledge_base_path": "./knowledge",
  "max_solutions_per_tag": 50
}
```

## 初始化命令

```bash
mkdir -p knowledge/{solutions,patterns}
echo '{"solutions":[],"patterns":[]}' > knowledge/index.json
```

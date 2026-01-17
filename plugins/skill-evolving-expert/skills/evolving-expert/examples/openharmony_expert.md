# OpenHarmony Expert - 自进化 Sub-Agent

## 专家定位

专注 OpenHarmony/KaihongOS 系统开发，特别是：
- dsoftbus 分布式软总线
- rmw_dsoftbus ROS2 中间件层
- RK3588S 开发板适配
- HDC 设备交互

## 知识库路径

```
~/.claude/skills/openharmony_expert/knowledge/
├── index.json
├── solutions/
└── patterns/
```

## Sub-Agent 配置

### agent_config.json

```json
{
  "name": "openharmony_expert",
  "description": "OpenHarmony/KaihongOS 系统开发专家，具备自我进化能力",
  "expertise": [
    "dsoftbus 分布式软总线架构与调试",
    "rmw_dsoftbus ROS2 中间件开发",
    "KaihongOS 系统移植与适配",
    "RK3588S ARM64 交叉编译",
    "HDC 设备控制与日志分析"
  ],
  "knowledge_base": "./knowledge",
  "auto_learn": true,
  "learn_triggers": ["new_solution", "better_solution", "pitfall"]
}
```

### 调用协议

主 Agent 调用格式：
```
dispatch_agent(
  agent="openharmony_expert",
  task="具体任务描述",
  context={
    // 必要上下文信息
  },
  expect_learning=true  // 允许知识提取
)
```

## 执行流程

### 1. 任务接收时

```python
def on_task_received(task, context):
    # 1. 检索相关知识
    relevant_knowledge = search_knowledge(
        keywords=extract_keywords(task),
        context=context
    )
    
    # 2. 如有匹配，优先参考
    if relevant_knowledge:
        print(f"找到 {len(relevant_knowledge)} 条相关经验")
        for k in relevant_knowledge:
            print(f"  - {k['title']} (命中 {k['hit_count']} 次)")
    
    # 3. 制定执行计划
    plan = make_plan(task, context, relevant_knowledge)
    return plan
```

### 2. 任务执行中

记录：
- 尝试的方案（含失败的，失败原因）
- 关键发现
- 最终解决方案

### 3. 任务完成后

```python
def on_task_completed(task, result, execution_log):
    # 判断是否需要知识提取
    should_extract = (
        result.is_new_problem or
        result.is_better_solution or
        result.has_pitfall
    )
    
    if should_extract:
        solution = extract_solution(task, result, execution_log)
        store_solution(solution)
        print(f"已提取知识: {solution['title']}")
        
        # 检查是否触发模式合并
        check_and_merge_patterns()
```

## 典型场景示例

### 场景1: dsoftbus 通信问题

**任务**: 排查 ROS2 节点通过 rmw_dsoftbus 无法通信

**执行流程**:
```
1. [检索] 搜索: dsoftbus, 通信, rmw
   → 找到: "dsoftbus LNN 节点发现失败排查"
   
2. [参考] 按历史方案检查:
   - softbus_server 状态 ✓
   - LNN 回调注册 ✓
   - AuthManager 依赖 → 发现新问题: 证书配置错误

3. [解决] 修复证书配置后通信正常

4. [提取] 新知识点:
   - 标题: dsoftbus 证书配置导致认证失败
   - 标签: dsoftbus, 证书, 认证, softbus_server
   - 关键点: /etc/softbus/softbus.json 中 deviceId 必须唯一
```

### 场景2: 交叉编译问题

**任务**: rmw_dsoftbus 在 ARM64 编译失败

**执行流程**:
```
1. [检索] 搜索: 交叉编译, ARM64, rmw_dsoftbus
   → 无匹配

2. [排查] 从零排查:
   - 工具链配置
   - 依赖库路径
   - 编译选项
   → 发现: -march=armv8-a 与目标平台不匹配

3. [解决] 修改 CMakeLists.txt 编译选项

4. [提取] 新知识点:
   - 标题: RK3588S 交叉编译 march 选项配置
   - 标签: 交叉编译, ARM64, RK3588S, CMake
   - 关键点: RK3588S 应使用 -march=armv8.2-a+crypto
```

## 知识检索优化

### 检索权重

```python
def calculate_relevance(solution, query_context):
    score = 0
    
    # 标签匹配 (权重 0.4)
    tag_match = len(set(solution.tags) & set(query_context.keywords))
    score += 0.4 * (tag_match / len(solution.tags))
    
    # 环境匹配 (权重 0.3)
    if solution.env.board == query_context.board:
        score += 0.15
    if solution.env.os_version == query_context.os_version:
        score += 0.15
    
    # 历史验证 (权重 0.3)
    # 命中次数越多，置信度越高
    score += 0.3 * min(solution.hit_count / 10, 1.0)
    
    return score
```

### 检索命令

```bash
# 综合检索
search_openharmony_kb() {
    local query="$1"
    local board="${2:-RK3588S}"
    local os="${3:-KaihongOS}"
    
    jq --arg q "$query" --arg b "$board" --arg o "$os" '
        .solutions | 
        map(select(
            (.tags | any(test($q; "i"))) or
            (.title | test($q; "i"))
        )) |
        sort_by(-.hit_count) |
        .[0:5]
    ' ~/.claude/skills/openharmony_expert/knowledge/index.json
}
```

## 初始化

```bash
# 创建知识库目录
mkdir -p ~/.claude/skills/openharmony_expert/knowledge/{solutions,patterns}

# 初始化索引
echo '{"solutions":[],"patterns":[]}' > ~/.claude/skills/openharmony_expert/knowledge/index.json

# 复制管理脚本
cp knowledge_manager.sh ~/.claude/skills/openharmony_expert/

# 设置环境变量
export KNOWLEDGE_BASE=~/.claude/skills/openharmony_expert/knowledge
```

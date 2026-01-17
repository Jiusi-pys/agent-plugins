# 知识提取提示词

## 任务完成后自动执行

当你完成一个问题的解决后，执行以下知识提取流程：

### Step 1: 判断是否需要提取

**提取条件**（满足任一即提取）：

- [ ] 解决了一个**新类型**的问题（知识库中无相似条目）
- [ ] 发现了**更优方案**（比现有方案更简洁/高效/稳定）
- [ ] 遇到**典型踩坑点**（容易犯错且不易发现原因）
- [ ] 涉及**隐性知识**（文档未明确说明但实践中必须知道）

**不提取的情况**：
- 常规操作，无特殊性
- 知识库已有高度相似的条目
- 临时性问题（如网络波动）

### Step 2: 提取关键信息

按以下结构提取：

```
【问题本质】
用一句话概括，如："dsoftbus 在 KaihongOS 上节点发现失败是因为 LNN 模块初始化顺序问题"

【最小复现条件】
- 环境: 
- 触发条件:
- 表现:

【解决方案核心】
精简到可直接复用的步骤，去除探索过程中的无效尝试

【关键命令/代码】
只保留关键的、易忘的、不易查到的

【标签】
3-5 个，用于后续检索
格式: 技术栈, 具体组件, 问题类型
示例: openharmony, dsoftbus, LNN, 初始化, 时序问题
```

### Step 3: 存储格式化

```bash
# 1. 创建解决方案文件
cat > /tmp/solution_content.md << 'EOF'
{按 solution_template.md 格式填充}
EOF

# 2. 调用知识管理脚本
./knowledge_manager.sh add "标题" "tag1,tag2,tag3" /tmp/solution_content.md
```

### Step 4: 关联检查

检查是否需要更新已有条目：

```bash
# 检索相关条目
./knowledge_manager.sh search "关键词"

# 如有高度相关条目，考虑:
# - 合并到已有条目
# - 添加为补充说明
# - 标记已有条目为 deprecated
```

---

## 模式提炼触发（周期性任务）

当执行 `./knowledge_manager.sh check-merge` 发现某标签出现 >= 3 次时：

1. 汇总该标签下所有 solutions
2. 提取共性：
   - 通用问题描述
   - 标准排查流程
   - 最佳实践配置
3. 写入 `patterns/{category}.md`
4. 原 solutions 保留，标记 `merged_to_pattern: true`

---

## 示例：dsoftbus 问题知识提取

**原始问题**：RK3588S 上 ROS2 节点通过 rmw_dsoftbus 无法互相发现

**提取结果**：

```markdown
# dsoftbus LNN 节点发现失败排查

## 问题摘要
rmw_dsoftbus 初始化后 LNN 回调未触发，节点无法互相发现

## 环境上下文
| 项目 | 值 |
|------|-----|
| 硬件 | RK3588S |
| 操作系统 | KaihongOS 4.0 |
| 相关组件版本 | dsoftbus 4.0, rmw_dsoftbus 0.1 |

## 根因分析
LNN 模块依赖 AuthManager 初始化完成，直接调用 RegNodeDeviceStateCb 时 AuthManager 未就绪

## 解决方案
1. 确认 softbus_server 已启动
   ```bash
   ps aux | grep softbus_server
   ```
2. 检查 LNN 初始化顺序
   ```cpp
   // 等待 AuthManager 就绪后再注册回调
   while (!IsAuthManagerReady()) {
       usleep(100000);
   }
   RegNodeDeviceStateCb(&g_nodeStateCb);
   ```

## 关键点
- **踩坑点**: 文档未说明 AuthManager 依赖
- **验证方法**: hilog 查看 "LNN" tag 日志

## 元信息
- **标签**: openharmony, dsoftbus, LNN, 初始化, rmw_dsoftbus
```

**存储命令**：
```bash
./knowledge_manager.sh add \
    "dsoftbus LNN 节点发现失败排查" \
    "openharmony,dsoftbus,LNN,初始化,rmw_dsoftbus" \
    /tmp/dsoftbus_lnn_solution.md
```

---
name: working-records
description: 移植工作状态记录。持久化保存工作进度、阻塞项、产出物，防止 context 丢失。任务切换或暂停时自动加载。
---

# Working Records Skill

## 概述

提供移植工作状态的持久化记录能力，解决以下问题：
- 长时间任务的上下文保持
- 多 agent 间的状态同步
- 工作中断后的恢复

## 记录格式

### 任务记录 (YAML)
```yaml
task_id: PORTING-20260118-001
library: libcurl
version: 8.5.0
source_url: https://github.com/curl/curl
target_platform: OpenHarmony 4.0
target_device: RK3588S

status: in_progress  # pending | in_progress | blocked | completed | abandoned

phases:
  - name: exploration
    status: completed
    started_at: 2026-01-18T10:00:00
    completed_at: 2026-01-18T10:30:00
    notes: "发现依赖 openssl, zlib, 均已移植"
    
  - name: diagnostics
    status: completed
    started_at: 2026-01-18T10:30:00
    completed_at: 2026-01-18T11:00:00
    grade: B
    notes: "15 处 epoll 使用，需要适配"
    
  - name: architecture
    status: in_progress
    started_at: 2026-01-18T11:00:00
    notes: "选择最小改动方案"

blockers: []

artifacts:
  - path: /home/ohos/libcurl/ohos_port.patch
    type: patch
    description: "OHOS 适配补丁"

next_steps:
  - "完成 epoll 到 poll 的替换"
  - "修改 CMakeLists.txt"

context:
  key_files:
    - lib/multi.c      # 事件循环核心
    - lib/select.c     # select/poll 封装
  key_decisions:
    - "使用 poll 替代 epoll"
    - "保持与上游同步能力"
```

## 文件位置

```
~/.claude/working-records/
├── PORTING-20260118-001.yaml
├── PORTING-20260118-002.yaml
└── index.yaml                  # 任务索引
```

## 操作命令

### 创建任务
```bash
./scripts/create_task.sh libcurl 8.5.0
```

### 更新状态
```bash
./scripts/update_task.sh PORTING-20260118-001 phase=diagnostics status=completed
```

### 查看任务
```bash
./scripts/show_task.sh PORTING-20260118-001
```

### 列出所有任务
```bash
./scripts/list_tasks.sh
```

### 恢复任务
```bash
./scripts/resume_task.sh PORTING-20260118-001
```

## 使用场景

### 场景 1: 任务中断恢复
```
用户: 继续之前 libcurl 的移植工作
Agent: [读取 working-records]
       上次进度: diagnostics 阶段已完成，正在进行 architecture 阶段
       上次决策: 使用 poll 替代 epoll
       继续执行...
```

### 场景 2: 多 agent 协作
```
Main Agent: 启动 source-explorer 分析
            [写入 working-records: exploration started]
            
source-explorer: [完成分析]
                 [写入 working-records: exploration completed, key_files=[...]]
                 
Main Agent: [读取 working-records]
            探索阶段完成，关键文件: lib/multi.c, lib/select.c
            开始诊断阶段...
```

### 场景 3: 阻塞记录
```yaml
blockers:
  - id: BLOCK-001
    type: dependency
    description: "需要先移植 nghttp2"
    created_at: 2026-01-18T12:00:00
    resolution: null
    
  - id: BLOCK-002
    type: technical
    description: "epoll_pwait 无法直接替换"
    created_at: 2026-01-18T13:00:00
    resolution: "使用 ppoll + sigmask 模拟"
```

## 最佳实践

1. **频繁保存**: 每个阶段完成后立即更新
2. **详细记录**: 关键决策必须记录理由
3. **阻塞即记**: 遇到阻塞立即记录
4. **关联上下文**: 保存关键文件和代码位置

## 集成方式

在 agent 系统提示中添加：
```
每个阶段开始前:
  - 读取 working-records 获取上下文
  
每个阶段结束后:
  - 更新 working-records 保存进度
  
遇到阻塞时:
  - 记录 blocker 并通知用户
```

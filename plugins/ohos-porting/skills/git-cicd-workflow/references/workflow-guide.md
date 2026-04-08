# Git 工作流指南

OpenHarmony 项目的层级化 Git 工作流规范。

## 层级结构

```
┌─────────────────────────────────────────────────────────────┐
│                         Project                              │
│                  (ROS2 KaihongOS 移植)                       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌────────▼────────┐
│    Track 1     │                    │    Track 2      │
│ rmw_dsoftbus   │                    │  ROS2 Core      │
└────────┬───────┘                    └─────────────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───▼───┐ ┌──▼──┐ ┌───▼───┐ ┌──▼──┐
│Stage1 │ │Stage2│ │Stage3 │ │...  │
│ Core  │ │Pub/Sub│ │Graph │ │     │
└───┬───┘ └──────┘ └───────┘ └─────┘
    │
  ┌─┴─┬────┬────┐
  │   │    │    │
┌─▼┐ ┌▼┐ ┌▼┐ ┌▼┐
│P1│ │P2│ │P3│ │..│
└──┘ └──┘ └──┘ └──┘
  │
  └──→ commit
```

---

## 层级定义

### Level 1: Phase（最小单元）

**定义**: 一个独立的、可测试的代码改动

**规模**: 1-2 小时可完成

**示例**:
- Phase 1: 实现 SessionManager 类
- Phase 2: 添加权限配置
- Phase 3: 实现单元测试

**完成标准**:
- ✅ 代码编译通过
- ✅ 单元测试通过（如有）
- ✅ 功能逻辑完整
- ✅ Phase 报告生成

**Git 操作**: **Commit**

**Commit Message**:
```
[Track/Stage/Phase] 简述 (type)

详细说明

Phase: <phase-name>
Stage: <stage-name>
Track: <track-name>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### Level 2: Stage（功能阶段）

**定义**: 多个 Phase 的集合，完成一个完整功能模块

**规模**: 3-5 个 Phases，1-2 天完成

**示例**:
- Stage 1: 核心基础设施（3 Phases）
- Stage 2: Pub/Sub 实现（4 Phases）
- Stage 3: Graph Discovery（5 Phases）

**完成标准**:
- ✅ 所有 Phase commits 完成
- ✅ 集成测试通过
- ✅ 代码审查通过
- ✅ Stage 总结生成

**Git 操作**: **Draft PR → Review → Squash Merge**

**PR 流程**:
```
1. 创建 Draft PR
   gh pr create --title "[Track/Stage] Title" --draft

2. 运行集成测试

3. 测试通过 → 转为正式 PR
   gh pr ready <pr-number>

4. Code Review

5. Review 通过 → Squash merge
   gh pr merge <pr-number> --squash
```

---

### Level 3: Track（开发线）

**定义**: 多个 Stage 的集合，完成一个大的开发目标

**规模**: 3-5 个 Stages，1-2 周完成

**示例**:
- Track 1: rmw_dsoftbus 开发（5 Stages）
- Track 2: ROS2 核心移植（4 Stages）

**完成标准**:
- ✅ 所有 Stage PRs 已 squash merge
- ✅ Track 功能完整性验证
- ✅ 文档完整（设计、实现、部署）
- ✅ Track 总结生成

**Git 操作**: **Rebase Merge**

**Merge 流程**:
```bash
# 1. Rebase to main
git checkout track1
git rebase main

# 2. Merge with --no-ff (保留 merge commit)
git checkout main
git merge track1 --no-ff -m "Merge track1: rmw_dsoftbus development"

# 3. 打标签
git tag track1-complete
git push origin main track1-complete
```

---

### Level 4: Project（项目）

**定义**: 所有 Tracks 的集合，完成整个项目目标

**Git 操作**: **Merge to main**

---

## 操作流程详解

### Phase 开发流程

```bash
# ========================================
# Phase 1: 初始化框架
# ========================================

# 1. 创建分支
git checkout -b track1/stage1/phase1

# 2. 编写代码（使用 ohos-expert）
/ohos-dev Track1/Stage1/Phase1: 初始化 rmw_dsoftbus 框架

# → Agent 会：
#   - 创建代码文件（遵循 ohos-cpp-style）
#   - 编写 BUILD.gn（参考 ohos-cross-compile）
#   - 编译验证
#   - 生成 Phase 报告

# 3. 检查报告
cat docs/progress/track1/stage1/phase1_report.md

# 4. 执行 commit（已由 agent 完成，或手动）
./scripts/git-workflow/commit_phase.sh \
  track1 stage1 phase1 \
  "初始化 rmw_dsoftbus 框架" \
  feat

# 5. 推送
git push origin track1/stage1/phase1

# ========================================
# Phase 2: Session 管理器
# ========================================

git checkout -b track1/stage1/phase2

/ohos-dev Track1/Stage1/Phase2: 实现 Session 管理器

./scripts/git-workflow/commit_phase.sh \
  track1 stage1 phase2 \
  "实现 SessionManager 类" \
  feat

git push origin track1/stage1/phase2

# ========================================
# Phase 3: 权限配置
# ========================================

# ... 类似流程 ...
```

### Stage 完成流程

```bash
# ========================================
# Stage 1 完成
# ========================================

# 1. 确认所有 Phase commits
git log --oneline --all --grep="stage1"

# 输出示例:
# abc123 [track1/stage1/phase1] 初始化框架 (feat)
# def456 [track1/stage1/phase2] 实现 SessionManager (feat)
# ghi789 [track1/stage1/phase3] 权限配置 (feat)

# 2. 合并 Phase 分支（可选）
git checkout -b track1/stage1
git merge track1/stage1/phase1
git merge track1/stage1/phase2
git merge track1/stage1/phase3

# 3. 运行集成测试
make -f Makefile.aarch64 test

# 或部署到设备测试
./scripts/deploy_and_test.sh

# 4. 生成 Stage 总结
cat > docs/progress/track1/stage1/STAGE_SUMMARY.md <<'EOF'
# Stage 1 完成总结 - 核心基础设施

## Phases
- Phase 1: init-framework (abc123)
- Phase 2: session-manager-impl (def456)
- Phase 3: permission-config-impl (ghi789)

## 测试状态
- [x] 单元测试通过
- [x] 集成测试通过
- [x] 设备验证通过

...
EOF

# 5. 创建 Draft PR
./scripts/git-workflow/create_stage_pr.sh track1 stage1

# 输出:
# ✅ Draft PR created: #10

# 6. 测试通过后转为正式 PR
gh pr ready 10

# 7. 请求 Review
gh pr edit 10 --add-reviewer <username>

# 8. Review 通过，Squash merge
gh pr merge 10 --squash --body "Stage 1: Core Infrastructure complete"

# 9. 删除分支（可选）
git branch -d track1/stage1/phase1
git branch -d track1/stage1/phase2
git branch -d track1/stage1/phase3
```

### Track 完成流程

```bash
# ========================================
# Track 1 完成
# ========================================

# 1. 确认所有 Stage PRs 已 merge
gh pr list --state merged --search "track1"

# 输出示例:
# #10  [track1/stage1] Core Infrastructure          MERGED
# #11  [track1/stage2] Pub/Sub Implementation       MERGED
# #12  [track1/stage3] Graph Discovery              MERGED

# 2. 生成 Track 总结
cat > docs/progress/track1/TRACK_SUMMARY.md <<'EOF'
# Track 1 完成总结 - rmw_dsoftbus 开发

## Stages
- Stage 1: 核心基础设施 (PR #10)
- Stage 2: Pub/Sub 实现 (PR #11)
- Stage 3: Graph Discovery (PR #12)

## 整体功能
实现了完整的 rmw_dsoftbus 中间件，支持：
- Session 管理
- Pub/Sub 通信
- Graph Discovery
- 跨设备消息传输

...
EOF

# 3. 切换到 main 并更新
git checkout main
git pull origin main

# 4. 切换到 track 分支并 rebase
git checkout track1
git rebase main

# 如果有冲突，解决后继续
git rebase --continue

# 5. 切换回 main 并 merge（保留 merge commit）
git checkout main
git merge track1 --no-ff -m "Merge track1: rmw_dsoftbus development complete

Implemented complete rmw_dsoftbus middleware with:
- Session management
- Pub/Sub communication
- Graph Discovery
- Cross-device messaging

Stages:
- Stage 1: Core Infrastructure (PR #10)
- Stage 2: Pub/Sub Implementation (PR #11)
- Stage 3: Graph Discovery (PR #12)

Track: rmw-dsoftbus-development"

# 6. 推送和打标签
git push origin main
git tag track1-complete -a -m "Track 1: rmw_dsoftbus development complete"
git push origin track1-complete

# 7. 删除远程 track 分支（可选）
git push origin --delete track1
```

---

## Commit Message 规范

### 格式

```
[Track/Stage/Phase] 简短描述（50 字符内）(type)

详细说明（可选，72 字符换行）：
- 改动点 1
- 改动点 2
- 改动点 3

Phase: <phase-name>
Stage: <stage-name>
Track: <track-name>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Type 说明

| Type | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | 添加 Publisher 实现 |
| `fix` | Bug 修复 | 修复内存泄漏 |
| `refactor` | 重构 | 重构 Session 管理 |
| `docs` | 文档 | 更新 API 文档 |
| `test` | 测试 | 添加单元测试 |
| `build` | 构建 | 更新 BUILD.gn 配置 |
| `perf` | 性能 | 优化序列化速度 |

### 示例

```
[track1/stage1/phase2] 实现 SessionManager 单例类 (feat)

使用 Meyer's Singleton 模式实现线程安全的 SessionManager。

改动：
- 新增 src/session_manager.cpp
- 新增 include/rmw_dsoftbus/session_manager.h
- 实现 initialize() 和 shutdown() 方法
- 添加 session ID 映射表

Phase: session-manager-impl
Stage: core-infrastructure
Track: rmw-dsoftbus-development

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## PR 管理规范

### Draft PR 创建

**时机**: Stage 的所有 Phase commits 完成

**Title 格式**:
```
[Track/Stage] Stage 功能描述
```

**Body 模板**:
```markdown
## Stage 概述
<简述本 Stage 完成的功能>

## Phases 列表
- [x] Phase 1: <name> (commit: <hash>)
- [x] Phase 2: <name> (commit: <hash>)
- [x] Phase 3: <name> (commit: <hash>)

## 测试状态
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 设备验证通过

## 文件改动
- 新增: <count> 个文件
- 修改: <count> 个文件
- 删除: <count> 个文件

## 下一步
<后续 Stages 计划>

Stage: <stage-name>
Track: <track-name>
```

### Draft → Ready 流程

```bash
# 1. 创建 Draft PR
gh pr create --draft --title "[track1/stage1] Core Infrastructure" \
  --body "$(cat docs/progress/track1/stage1/STAGE_SUMMARY.md)"

# 2. 运行测试
make test
./deploy_and_test.sh

# 3. 更新 PR 描述（测试结果）
gh pr edit <pr-number> --body "$(cat docs/progress/track1/stage1/STAGE_SUMMARY.md)"

# 4. 转为 Ready
gh pr ready <pr-number>

# 5. 请求 Review
gh pr edit <pr-number> --add-reviewer <username>
```

### Squash Merge（Stage 级别）

**时机**: Code Review 通过

**操作**:
```bash
gh pr merge <pr-number> --squash --body "feat: Stage <stage-number> complete

<Stage 功能总结>

Phases:
- Phase 1: <name>
- Phase 2: <name>
- Phase 3: <name>

Stage: <stage-name>
Track: <track-name>"
```

**效果**: 所有 Phase commits 合并为 1 个 commit

---

### Rebase Merge（Track 级别）

**时机**: 所有 Stage PRs 已 merge

**操作**:
```bash
# 1. 更新 main
git checkout main
git pull origin main

# 2. Rebase track 分支
git checkout track1
git rebase main
# 解决冲突（如有）
git rebase --continue

# 3. Force push（rebase 后需要）
git push origin track1 --force

# 4. Merge to main（保留 merge commit）
git checkout main
git merge track1 --no-ff -m "Merge track1: <Track 功能总结>

<详细描述>

Stages:
- Stage 1: <name> (PR #10)
- Stage 2: <name> (PR #11)
- Stage 3: <name> (PR #12)

Track: <track-name>"

# 5. 推送和打标签
git push origin main
git tag track1-complete -a -m "Track 1 complete"
git push origin track1-complete
```

**效果**: 保留每个 Stage 的 squash commit，整理成线性历史

---

## 分支命名规范

### Phase 分支

**格式**: `<track>/<stage>/<phase>`

**示例**:
```
track1/stage1/phase1
track1/stage1/phase2
rmw-dsoftbus-dev/core-infra/session-manager
```

### Stage 分支（可选）

**格式**: `<track>/<stage>`

**示例**:
```
track1/stage1
rmw-dsoftbus-dev/core-infra
```

### Track 分支

**格式**: `<track>`

**示例**:
```
track1
rmw-dsoftbus-dev
```

---

## 文档结构

### docs/progress/ 目录结构

```
docs/progress/
├── track1/                           # Track 目录
│   ├── TRACK_SUMMARY.md              # Track 总结
│   │
│   ├── stage1/                       # Stage 目录
│   │   ├── STAGE_SUMMARY.md          # Stage 总结
│   │   ├── phase1_report.md          # Phase 1 报告
│   │   ├── phase2_report.md          # Phase 2 报告
│   │   └── phase3_report.md          # Phase 3 报告
│   │
│   ├── stage2/
│   │   ├── STAGE_SUMMARY.md
│   │   ├── phase1_report.md
│   │   ├── phase2_report.md
│   │   ├── phase3_report.md
│   │   └── phase4_report.md
│   │
│   └── stage3/
│       └── ...
│
└── track2/
    └── ...
```

---

## 使用 ohos-expert 自动化

### 自动 Phase 开发

```bash
/ohos-dev Track1/Stage1/Phase1: 初始化框架
```

**Agent 会自动**:
1. ✅ 创建分支 `track1/stage1/phase1`
2. ✅ 编写代码（遵循 ohos-cpp-style）
3. ✅ 编译验证（使用 ohos-cross-compile）
4. ✅ 生成 Phase 报告
5. ✅ 执行 Git commit
6. ✅ 推送到远程

### 自动 Stage PR

**Agent 在 Stage 完成时会**:
1. ✅ 生成 Stage 总结
2. ✅ 创建 Draft PR
3. ✅ 提示运行测试
4. ✅ 指导后续操作（Ready, Review, Merge）

---

## 可视化示例

### rmw_dsoftbus 开发完整流程

```
Project: ROS2 KaihongOS 移植
│
└── Track 1: rmw_dsoftbus 开发
    │
    ├── Stage 1: 核心基础设施
    │   ├── Phase 1: init-framework             → commit abc123
    │   ├── Phase 2: session-manager-impl       → commit def456
    │   └── Phase 3: permission-config-impl     → commit ghi789
    │   └── Draft PR #10 → Review → Squash merge (commit: stage1-merge)
    │
    ├── Stage 2: Pub/Sub 实现
    │   ├── Phase 1: publisher-impl             → commit jkl012
    │   ├── Phase 2: subscriber-impl            → commit mno345
    │   ├── Phase 3: message-serialization      → commit pqr678
    │   └── Phase 4: qos-management             → commit stu901
    │   └── Draft PR #11 → Review → Squash merge (commit: stage2-merge)
    │
    └── Stage 3: Graph Discovery
        ├── Phase 1: discovery-protocol         → commit vwx234
        ├── Phase 2: cross-device-comm          → commit yza567
        ├── Phase 3: graph-cache-impl           → commit bcd890
        ├── Phase 4: liveness-tracking          → commit efg123
        └── Phase 5: integration-test           → commit hij456
        └── Draft PR #12 → Review → Squash merge (commit: stage3-merge)

    └── Rebase merge to main (commit: track1-merge)
    └── Tag: track1-complete

└── Track 2: ROS2 核心移植
    └── ...

└── Merge all Tracks to main
```

### Commit 历史示例

```bash
git log --oneline --graph

# 输出:
*   track1-merge (tag: track1-complete) Merge track1: rmw_dsoftbus development
|\
| * stage3-merge feat: Stage 3 - Graph Discovery
| * stage2-merge feat: Stage 2 - Pub/Sub Implementation
| * stage1-merge feat: Stage 1 - Core Infrastructure
|/
* main-baseline Initial commit
```

---

## 最佳实践

### ✅ DO

1. **严格遵循层级**
   - 每个 Phase 独立 commit
   - 每个 Stage 独立 PR
   - 保持层级清晰

2. **完整文档**
   - 每个 Phase 必须有报告
   - 记录问题和解决方案
   - 引用相关 Issue

3. **测试充分**
   - Phase: 单元测试
   - Stage: 集成测试
   - Track: 完整性测试

4. **Issue 优先**
   - 先搜索已知 Issue
   - 引用 Issue 编号
   - 创建新 Issue（新问题）

### ❌ DON'T

1. **不要跳过文档**
   - 每个 Phase 必须有报告

2. **不要混合层级**
   - 不要在一个 commit 中包含多个 Phase
   - 不要在一个 PR 中包含多个 Stage

3. **不要跳过测试**
   - Draft PR 必须测试通过才能 Ready

4. **不要直接 merge 到 main**
   - 必须通过 PR 流程

---

## Scripts 参考

详见: `scripts/git-workflow/README.md`

---

## Agent 参考

详见: `.claude/agents/OHOS_EXPERT_GUIDE.md`

---

**版本**: 1.0.0
**创建日期**: 2026-01-15
**适用 Agent**: ohos-expert

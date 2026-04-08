# Git Workflow Scripts

支持 Phase → Stage → Track → Project 层级 Git 工作流的自动化脚本。

## 工作流概览

```
Project (ROS2 KaihongOS 移植)
  |
  └── Track (rmw_dsoftbus 开发)
      |
      └── Stage (核心基础设施)
          |
          ├── Phase 1 → commit
          ├── Phase 2 → commit
          └── Phase 3 → commit
      → Draft PR
      → 测试通过 → 正式 PR
      → Review 通过 → Squash merge
  → Rebase merge
→ Merge to main
```

## Scripts

### 1. generate_phase_report.sh

生成 Phase 完成报告模板。

**用法**:
```bash
./scripts/git-workflow/generate_phase_report.sh <track> <stage> <phase>
```

**示例**:
```bash
./scripts/git-workflow/generate_phase_report.sh track1 stage1 phase2

# 生成文件: docs/progress/track1/stage1/phase2_report.md
```

**输出**: Phase 报告模板，需要手动填写详细内容

---

### 2. commit_phase.sh

执行 Phase commit，自动生成规范的 commit message。

**用法**:
```bash
./scripts/git-workflow/commit_phase.sh <track> <stage> <phase> <message> [type]
```

**参数**:
- `track`: Track 名称（如 track1）
- `stage`: Stage 名称（如 stage1）
- `phase`: Phase 名称（如 phase1）
- `message`: 简短描述（如 "实现 Session 管理器"）
- `type`: commit 类型（默认 feat）
  - `feat`: 新功能
  - `fix`: Bug 修复
  - `refactor`: 重构
  - `docs`: 文档
  - `test`: 测试
  - `build`: 构建配置

**示例**:
```bash
# 新功能
./scripts/git-workflow/commit_phase.sh track1 stage1 phase2 "实现 Session 管理器" feat

# Bug 修复
./scripts/git-workflow/commit_phase.sh track1 stage1 phase3 "修复权限问题" fix

# 重构
./scripts/git-workflow/commit_phase.sh track1 stage2 phase1 "重构 Publisher 实现" refactor
```

**生成的 Commit Message**:
```
[track1/stage1/phase2] 实现 Session 管理器 (feat)

Phase: phase2
Stage: stage1
Track: track1

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

### 3. create_stage_pr.sh

创建 Stage Draft PR。

**用法**:
```bash
./scripts/git-workflow/create_stage_pr.sh <track> <stage>
```

**前提条件**:
- Stage 总结报告已生成: `docs/progress/<track>/<stage>/STAGE_SUMMARY.md`
- 所有 Phase commits 已完成

**示例**:
```bash
./scripts/git-workflow/create_stage_pr.sh track1 stage1

# 创建 Draft PR，标题: [track1/stage1] <Stage Title>
```

**后续操作**:
```bash
# 1. 运行测试
make test

# 2. 测试通过，转为正式 PR
gh pr ready <pr-number>

# 3. Code review

# 4. Review 通过，Squash merge
gh pr merge <pr-number> --squash
```

---

## 完整开发流程

### Phase 开发

```bash
# 1. 创建分支
git checkout -b track1/stage1/phase2

# 2. 编写代码
# ... 开发 ...

# 3. 生成 Phase 报告
./scripts/git-workflow/generate_phase_report.sh track1 stage1 phase2

# 4. 编辑报告（填写详细内容）
vi docs/progress/track1/stage1/phase2_report.md

# 5. 执行 Phase commit
./scripts/git-workflow/commit_phase.sh track1 stage1 phase2 "实现核心功能X" feat

# 6. 推送
git push origin track1/stage1/phase2
```

### Stage 完成

```bash
# 1. 确认所有 Phase commits 完成
git log --oneline --grep="stage1"

# 2. 创建 Stage 总结
cat > docs/progress/track1/stage1/STAGE_SUMMARY.md <<EOF
# Stage 1 完成总结 - 核心基础设施

## Phases
- Phase 1: 初始化框架 (commit: abc123)
- Phase 2: Session 管理器 (commit: def456)
- Phase 3: 权限配置 (commit: ghi789)

## 测试状态
- [x] 编译通过
- [x] 单元测试通过
- [x] 设备验证通过

...
EOF

# 3. 创建 Draft PR
./scripts/git-workflow/create_stage_pr.sh track1 stage1

# 4. 测试通过后转为正式 PR
gh pr ready <pr-number>

# 5. Squash merge（Review 通过后）
gh pr merge <pr-number> --squash
```

### Track 完成

```bash
# 1. 确认所有 Stage PRs 已 merge

# 2. 生成 Track 总结
cat > docs/progress/track1/TRACK_SUMMARY.md <<EOF
# Track 1 完成总结 - rmw_dsoftbus 开发

## Stages
- Stage 1: 核心基础设施 (PR #10)
- Stage 2: Pub/Sub 实现 (PR #11)
- Stage 3: Graph Discovery (PR #12)

...
EOF

# 3. Rebase merge
git checkout main
git pull origin main
git checkout track1
git rebase main
git checkout main
git merge track1 --no-ff

# 4. 推送和打标签
git push origin main
git tag track1-complete
git push origin track1-complete
```

---

## 文档目录结构

```
docs/progress/
├── track1/
│   ├── TRACK_SUMMARY.md          # Track 总结
│   ├── stage1/
│   │   ├── STAGE_SUMMARY.md      # Stage 总结
│   │   ├── phase1_report.md      # Phase 1 报告
│   │   ├── phase2_report.md      # Phase 2 报告
│   │   └── phase3_report.md      # Phase 3 报告
│   ├── stage2/
│   │   └── ...
│   └── stage3/
│       └── ...
└── track2/
    └── ...
```

---

## Git 分支命名规范

### Phase 分支
```
<track>/<stage>/<phase>

示例:
  track1/stage1/phase1
  rmw-dsoftbus-dev/core-infra/session-manager
```

### Stage 分支（可选）
```
<track>/<stage>

示例:
  track1/stage1
  rmw-dsoftbus-dev/core-infra
```

---

## Commit Message 规范

### 格式
```
[<track>/<stage>/<phase>] <简述> (<type>)

<详细说明>

Phase: <phase-name>
Stage: <stage-name>
Track: <track-name>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Type 说明
- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 重构（不改变功能）
- `docs`: 文档更新
- `test`: 测试相关
- `build`: 构建配置
- `perf`: 性能优化

---

## PR 管理

### Draft PR → 正式 PR

```bash
# 1. 创建 Draft PR
./scripts/git-workflow/create_stage_pr.sh track1 stage1

# 2. 运行测试
make test
./deploy_and_test.sh

# 3. 测试通过，转为正式 PR
gh pr ready <pr-number>

# 4. 请求 review
gh pr edit <pr-number> --add-reviewer <username>
```

### Squash Merge（Stage 级别）

```bash
# Review 通过后
gh pr merge <pr-number> --squash --body "Squash merge: Stage 1 完成"
```

### Rebase Merge（Track 级别）

```bash
# 所有 Stage 完成后
git checkout main
git pull origin main
git checkout track1
git rebase main
git push origin track1 --force  # Rebase 后需要 force push
git checkout main
git merge track1 --no-ff -m "Merge track1: rmw_dsoftbus development"
git push origin main
```

---

## 快速参考

```bash
# Phase commit
./scripts/git-workflow/commit_phase.sh <track> <stage> <phase> "<msg>" <type>

# 生成 Phase 报告
./scripts/git-workflow/generate_phase_report.sh <track> <stage> <phase>

# 创建 Stage Draft PR
./scripts/git-workflow/create_stage_pr.sh <track> <stage>

# PR 转正式
gh pr ready <pr-number>

# Squash merge
gh pr merge <pr-number> --squash

# 列出 PRs
gh pr list

# 查看 PR 详情
gh pr view <pr-number>
```

---

**版本**: 1.0.0
**创建日期**: 2026-01-15
**适用于**: ohos-expert sub-agent

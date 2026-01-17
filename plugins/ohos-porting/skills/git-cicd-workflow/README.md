# Git CI/CD Workflow Skill

通用的层级化 Git 工作流规范，适用于任何项目。

## 概述

本 skill 提供标准化的 Git 开发流程，支持：
- ✅ Phase → Stage → Track → Project 层级管理
- ✅ 自动化 commit message 生成
- ✅ PR 管理（Draft → Review → Merge）
- ✅ 文档记录规范
- ✅ 适用于任何项目和技术栈

## 核心概念

**Phase** (最小单元):
- 1-2 小时可完成
- 独立的代码改动
- 操作：Git commit

**Stage** (功能阶段):
- 3-5 个 Phases
- 完整功能模块
- 操作：Draft PR → Squash merge

**Track** (开发线):
- 3-5 个 Stages
- 大的开发目标
- 操作：Rebase merge

**Project** (项目):
- 所有 Tracks
- 最终合并：Merge to main

## 使用方式

### 手动使用

```bash
# Phase commit
git commit -m "[track1/stage1/phase1] 实现功能X (feat)

Phase: phase1
Stage: stage1
Track: track1"

# Stage PR
gh pr create --draft --title "[track1/stage1] 功能模块"

# Squash merge
gh pr merge <pr-number> --squash
```

### 脚本自动化

```bash
# Phase commit
.claude/skills/git-cicd-workflow/scripts/commit_phase.sh \
  track1 stage1 phase1 "实现功能X" feat

# 生成 Phase 报告
.claude/skills/git-cicd-workflow/scripts/generate_phase_report.sh \
  track1 stage1 phase1

# 创建 Stage PR
.claude/skills/git-cicd-workflow/scripts/create_stage_pr.sh \
  track1 stage1
```

## 文档结构

```
docs/progress/
├── track1/
│   ├── TRACK_SUMMARY.md
│   ├── stage1/
│   │   ├── STAGE_SUMMARY.md
│   │   ├── phase1_report.md
│   │   └── phase2_report.md
│   └── stage2/
│       └── ...
└── track2/
    └── ...
```

## 详细文档

- **工作流层级**: `references/workflow-layers.md`
- **Commit 规范**: `references/commit-standards.md`
- **PR 管理**: `references/pr-management.md`
- **文档记录**: `references/documentation.md`

---

**版本**: 1.0.0
**适用范围**: 通用（所有项目）
**可被任何 Agent/Plugin 引用**

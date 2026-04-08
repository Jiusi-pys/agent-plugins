---
name: git-cicd-workflow
description: "通用的 Git CI/CD 工作流规范。适用于所有项目的层级化开发流程：Phase → Stage → Track → Project。支持自动化 commit、PR 管理、文档生成。任何需要结构化 Git 工作流的开发任务都应使用此 skill。"
---

# Git CI/CD 工作流 Skill

通用的层级化 Git 工作流规范，适用于任何项目。

## 层级结构

```
Project (项目)
  └── Track (开发线/Feature track)
      └── Stage (功能阶段/Milestone)
          └── Phase (最小单元/Task) → commit
```

## 快速参考

### Phase 完成

```bash
# 1. 开发代码
# ... 编码 ...

# 2. Git commit
git add .
git commit -m "[Track/Stage/Phase] 简述 (type)

Phase: phase-name
Stage: stage-name
Track: track-name"

# 3. 推送
git push origin track/stage/phase
```

### Stage 完成

```bash
# 1. 创建 Draft PR
gh pr create --draft --title "[Track/Stage] 功能描述"

# 2. 测试通过后转正式
gh pr ready <pr-number>

# 3. Review 通过后 Squash merge
gh pr merge <pr-number> --squash
```

### Track 完成

```bash
# Rebase merge
git checkout main
git merge track --no-ff
git tag track-complete
```

---

## 详细内容索引

### 层级定义和操作流程
见 `references/workflow-layers.md`

### Commit Message 规范
见 `references/commit-standards.md`

### PR 管理流程
见 `references/pr-management.md`

### 文档记录规范
见 `references/documentation.md`

### 自动化脚本
见 `scripts/` 目录

---

## 何时使用

**适用场景**:
- 需要结构化的开发流程
- 多人协作项目
- 需要清晰的 Git 历史
- 需要 Phase/Stage 级别的文档记录
- 需要 CI/CD 集成

**不适用场景**:
- 简单的单文件修改
- 快速原型开发
- 个人实验项目

---

## Scripts

| 脚本 | 用途 |
|------|------|
| `scripts/commit_phase.sh` | Phase commit 自动化 |
| `scripts/create_stage_pr.sh` | Stage PR 创建 |
| `scripts/generate_phase_report.sh` | Phase 报告生成 |

---

**版本**: 1.0.0
**适用范围**: 所有项目（通用 skill）

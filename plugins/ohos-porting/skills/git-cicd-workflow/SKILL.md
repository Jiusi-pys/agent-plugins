---
name: git-cicd-workflow
description: Structured Git delivery workflow for long-running engineering tracks. Use when Codex needs to sequence commits, reports, and review checkpoints for an OHOS port or related infrastructure work.
---

# Git CI/CD Workflow

Use this skill to keep large porting work legible in Git.

## Workflow

1. Break work into a track, stage, and phase.
2. Keep each commit scoped to one clear step.
3. Generate summary reports only from real command output and finished deltas.
4. Push only after local validation for the changed scope passes.

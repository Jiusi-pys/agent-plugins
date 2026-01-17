# PR 管理流程

## Stage PR 流程

### 1. 创建 Draft PR

```bash
gh pr create --draft \
  --title "[Track/Stage] 功能描述" \
  --body "$(cat docs/progress/<track>/<stage>/STAGE_SUMMARY.md)"
```

### 2. 测试验证

运行测试后更新 PR 描述。

### 3. 转为正式 PR

```bash
gh pr ready <pr-number>
```

### 4. Code Review

### 5. Squash Merge

```bash
gh pr merge <pr-number> --squash
```

## Track Merge 流程

### 1. Rebase

```bash
git checkout <track>
git rebase main
```

### 2. Merge

```bash
git checkout main
git merge <track> --no-ff
```

### 3. 打标签

```bash
git tag <track>-complete
git push origin main <track>-complete
```

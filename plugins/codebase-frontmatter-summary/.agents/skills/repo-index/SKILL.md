---
name: repo-index
description: Refresh the repository knowledge layer under .scanmeta and export dual-host guides.
---

# Repo Index

Use this skill when the repository index is missing, stale, or structurally out of date.

## Workflow

1. Run `python3 tools/repo_indexer.py refresh --root <repo>`.
2. Inspect `.scanmeta/generated/repo-map.md` and the updated sidecars.
3. Run `python3 tools/repo_indexer.py doctor --root <repo>` if the output looks inconsistent.

---
name: codebase-frontmatter-summary
description: Build an incremental repository knowledge layer with sidecar metadata, SQLite state, generated dual-host guides, and a deterministic read planner.
---

# Codebase Frontmatter Summary

Use this skill when the user wants a repository scanned and indexed for progressive agent reading.

## Workflow

1. Confirm the scan root and backend.
2. Run `python3 tools/repo_indexer.py scan --root <repo>` to inspect the current diff.
3. Run `python3 tools/repo_indexer.py refresh --root <repo>` to write `.scanmeta/` artifacts and export guides.
4. Run `python3 tools/repo_indexer.py doctor --root <repo>` if any artifact looks stale or malformed.
5. Re-run `export-guides` if only the host guide layer needs rewriting.

## Behavior

- File metadata lives in sidecars under `.scanmeta/files/`.
- Large-file section indexes live in `.scanmeta/sections/`.
- Directory summaries live in `.scanmeta/dirs/`.
- Runtime state lives in SQLite at `.scanmeta/state/index.sqlite`.
- Root `AGENTS.md`, `CLAUDE.md`, `.claude/rules/`, and `.agents/.claude skills` are exported from the generated knowledge layer.
- Markdown inline frontmatter is optional. Other file types remain sidecar-only by default.

## Entry points

- `tools/repo_indexer.py`: canonical CLI
- `skills/codebase-frontmatter-summary/scripts/scan_and_summarize.py`: compatibility wrapper
- `docs/agent-architecture.md`: design overview
- `docs/index-schemas.md`: schema details

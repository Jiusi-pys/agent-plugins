# Codebase Frontmatter Summary

This plugin implements an incremental repository knowledge compiler for Codex and Claude Code.

## Map

- `tools/repo_indexer/`: scanner, diff engine, SQLite state, sidecar writers, guide builder, read planner
- `docs/agent-architecture.md`: architecture and lifecycle
- `docs/index-schemas.md`: file, section, directory, and guide schemas
- `skills/codebase-frontmatter-summary/scripts/scan_and_summarize.py`: compatibility entrypoint
- `tests/test_repo_indexer.py`: regression coverage for add/change/remove, dirty propagation, guide refresh, and doctor

## Reading Order

1. Read `docs/agent-architecture.md`.
2. Read `docs/index-schemas.md`.
3. Read `tools/repo_indexer/cli.py` and the worker modules you need.
4. Open tests before changing indexing or export behavior.

## Guardrails

- The plugin now defaults to sidecar metadata under `.scanmeta/`; do not reintroduce blanket inline frontmatter writes.
- Treat SQLite state and JSON sidecars as generated artifacts.
- Keep root guides concise. Detailed maps belong in generated artifacts or docs.

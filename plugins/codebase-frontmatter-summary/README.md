# Codebase Frontmatter Summary

This plugin now builds an incremental repository knowledge layer for both Codex and Claude Code.

## What changed

- Source, config, test, and script files no longer get inline frontmatter by default.
- Runtime state moved into SQLite at `.scanmeta/state/index.sqlite`.
- Agent-readable knowledge moved into sidecars under `.scanmeta/files`, `.scanmeta/sections`, and `.scanmeta/dirs`.
- Generated host guides and rules now target both `AGENTS.md` and `CLAUDE.md`.
- The read order is deterministic: guides -> directory summaries -> file sidecars -> section indexes -> relevant sections -> full files.

## CLI

```bash
python3 tools/repo_indexer.py scan --root /absolute/path/to/repo
python3 tools/repo_indexer.py refresh --root /absolute/path/to/repo
python3 tools/repo_indexer.py refresh --root /absolute/path/to/repo --path src/
python3 tools/repo_indexer.py doctor --root /absolute/path/to/repo
python3 tools/repo_indexer.py export-guides --root /absolute/path/to/repo
```

The compatibility wrapper still exists at:

```bash
python3 skills/codebase-frontmatter-summary/scripts/scan_and_summarize.py --root /absolute/path/to/repo --write
```

## Output layout

```text
.scanmeta/
  state/index.sqlite
  state/pipeline.json
  runs/*.json
  files/*.json
  sections/*.json
  dirs/*.json
  generated/AGENTS.generated.md
  generated/CLAUDE.generated.md
  generated/repo-map.md
AGENTS.md
CLAUDE.md
.claude/rules/*.md
.claude/skills/repo-index/SKILL.md
.claude/skills/repo-read/SKILL.md
.agents/skills/repo-index/SKILL.md
.agents/skills/repo-read/SKILL.md
scan-manifest.json
```

## Backends

- `heuristic`: default, fully local
- `mcp`, `sdk`, `exec`, `auto`: reuse the existing Codex backend bridge

## Tests

```bash
python3 -m unittest plugins/codebase-frontmatter-summary/tests/test_repo_indexer.py
bash plugins/codebase-frontmatter-summary/examples/sample-project/verify.sh
```

## Local Codex install

Keep the repo plugin entry in `.agents/plugins/marketplace.json` for development inside this repository.

For a home-local install, sync the plugin to `~/plugins/codebase-frontmatter-summary` and keep the matching entry in `~/.agents/plugins/marketplace.json`.

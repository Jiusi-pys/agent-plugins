# Agent Architecture

This plugin now treats repository summarization as an incremental knowledge compiler, not a one-shot summarizer.

## Layers

1. Index layer
   - `scanner.py` walks the tree and classifies files.
   - `diff.py` compares the current snapshot with SQLite state.
   - `state_db.py` persists file, directory, run, and artifact records.
2. Knowledge layer
   - `file_worker.py` writes file sidecars into `.scanmeta/files/`.
   - `section_worker.py` writes large-file section indexes into `.scanmeta/sections/`.
   - `dir_worker.py` writes directory summaries into `.scanmeta/dirs/`.
   - `guide_builder.py` writes generated guides into `.scanmeta/generated/` and exports root host files.
3. Behavior layer
   - `read_planner.py` enforces the read order:
     `AGENTS/CLAUDE -> dir summary -> file frontmatter -> section index -> relevant sections -> full file`
   - `.agents/skills/` and `.claude/skills/` expose repeatable workflows.
   - `.claude/rules/` carries scoped Claude Code policy.

## Storage model

- SQLite state: `.scanmeta/state/index.sqlite`
- Pipeline metadata: `.scanmeta/state/pipeline.json`
- Run reports: `.scanmeta/runs/*.json`
- File sidecars: `.scanmeta/files/*.json`
- Section indexes: `.scanmeta/sections/*.json`
- Directory summaries: `.scanmeta/dirs/*.json`
- Generated guides: `.scanmeta/generated/*.md`
- Compatibility manifest: `scan-manifest.json`

## Incremental behavior

- `new`, `changed`, and `removed` files mark their parent directory chain dirty.
- Removed files delete their file and section sidecars plus the SQLite record.
- Directory fingerprints are built from child file hashes and child directory fingerprints.
- Dirty directories rebuild from deepest to shallowest, then regenerate guides.

## Provider boundary

- Core orchestration is deterministic Python.
- Providers only summarize files, sections, directories, and guide markdown.
- The Codex provider reuses the existing backend bridge from `skills/codebase-frontmatter-summary/scripts/codex_backends.py`.
- The heuristic provider is the default fallback and is fully local.

## CLI

- `python3 tools/repo_indexer.py scan --root <repo>`
- `python3 tools/repo_indexer.py refresh --root <repo>`
- `python3 tools/repo_indexer.py refresh --root <repo> --path src/`
- `python3 tools/repo_indexer.py doctor --root <repo>`
- `python3 tools/repo_indexer.py export-guides --root <repo>`

## Current scope

- Markdown inline frontmatter is opt-in.
- Source, config, test, and script files stay sidecar-only by default.
- The generated root guides are intentionally short; deeper maps live under `.scanmeta/generated/`.

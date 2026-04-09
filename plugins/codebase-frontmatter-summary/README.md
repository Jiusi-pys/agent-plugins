# Codebase Frontmatter Summary

This plugin scans a codebase bottom-up, adds managed frontmatter to files, and writes one `SUMMARY.md` file per directory.

## What it does

- Walks a directory tree from leaves to root.
- Generates a concise summary for each file and directory with Codex-backed or local backends.
- Inserts or refreshes a managed frontmatter block at the top of files when the format supports safe inline comments.
- Writes a directory summary that records direct child file summaries plus direct child directory summaries.

## Default behavior

- Summary file name: `SUMMARY.md`
- Default backend: `mcp`
- Traversal order: bottom-up
- Safe mode: only injects in-file frontmatter when the file can safely carry comments or metadata
- Skips symlinks and common generated directories such as `.git`, `node_modules`, `dist`, and `__pycache__`
- Auth safety: the bundled Codex backends remove `OPENAI_API_KEY` and `CODEX_API_KEY` from child process environments and are intended to use your existing Codex login session instead of direct API-key billing.

## Main entrypoint

Use the bundled script:

```bash
python3 scripts/scan_and_summarize.py --root /absolute/path/to/codebase --write --backend mcp
```

Use the SDK bridge when you want `@openai/codex-sdk` directly:

```bash
cd scripts
npm install
python3 scan_and_summarize.py --root /absolute/path/to/codebase --write --backend sdk
```

Available backends: `mcp`, `sdk`, `exec`, `auto`, `heuristic`.

Use `--unsafe-force-raw-frontmatter` if you explicitly want raw frontmatter prepended to text files that do not have a safe inline comment syntax.

## Example fixture

A deterministic sample tree is available under `examples/sample-project/`.
Use `examples/sample-project/input/` as the source fixture, then compare a generated run against `examples/sample-project/expected/` with the commands documented in `examples/sample-project/README.md`.

## Global AGENTS Rule

The global rule file `~/.codex/AGENTS.md` is configured with a frontmatter-first startup gate for this plugin.

That rule constrains discovery to:
- directory `SUMMARY.md` files first
- `codex-file-meta` frontmatter blocks in candidate files

Full file-body reads are deferred until implementation work starts, unless summaries/frontmatter are missing or an ambiguity blocks progress.

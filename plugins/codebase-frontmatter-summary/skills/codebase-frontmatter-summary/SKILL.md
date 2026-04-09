---
name: codebase-frontmatter-summary
description: Scan a codebase directory by directory, add managed frontmatter to files, and write one summary file per directory that records direct child file and directory summaries.
---

# Codebase Frontmatter Summary

Use this skill when the user wants a repository or document tree scanned bottom-up so every file gets managed frontmatter and every directory gets a generated summary document.

## Workflow

1. Confirm the scan root, the summary backend, and whether generated outputs should be written in place.
   Default summary file name is `SUMMARY.md`. Default backend is Codex MCP.
2. If using `sdk`, install the dependency in `scripts/` with `npm install`.
3. Run `scripts/scan_and_summarize.py` in preview mode first when the tree is large or risky.
4. Re-run with `--write` once the boundary and exclusions are correct.
5. Inspect a leaf directory summary and a parent directory summary to verify the roll-up behavior.

## Behavior

- Traversal is bottom-up so child directory summaries exist before parent summaries are written.
- Each directory summary records direct child files and direct child directories.
- Each file gets one managed frontmatter block that is refreshed on subsequent runs instead of duplicated.
- Safe mode only injects frontmatter into formats that support comments or inline metadata cleanly.
- Symlinks are skipped to avoid cycles.
- The bundled Codex backends remove `OPENAI_API_KEY` and `CODEX_API_KEY` from spawned environments so the workflow uses Codex auth rather than directly consuming those API keys.
- Summary backends:
  - `mcp`: Use `codex mcp-server`.
  - `sdk`: Use the bundled `@openai/codex-sdk` bridge.
  - `exec`: Use `codex exec --output-schema`.
  - `auto`: Try `mcp`, then `sdk`, then `exec`, then fall back to heuristics.
  - `heuristic`: Do not call Codex; use local summarizers only.

## Quick Start

Preview a run:

```bash
python3 scripts/scan_and_summarize.py --root /absolute/path/to/codebase --backend mcp
```

Write changes:

```bash
python3 scripts/scan_and_summarize.py --root /absolute/path/to/codebase --write --backend mcp
```

Use the Codex SDK bridge:

```bash
cd scripts
npm install
python3 scan_and_summarize.py --root /absolute/path/to/codebase --write --backend sdk
```

Change the directory summary file name:

```bash
python3 scripts/scan_and_summarize.py --root /absolute/path/to/codebase --write --summary-name DIRECTORY_SUMMARY.md
```

Force raw frontmatter into text files without a safe inline comment syntax:

```bash
python3 scripts/scan_and_summarize.py --root /absolute/path/to/codebase --write --unsafe-force-raw-frontmatter
```

## Notes

- The generated summary file itself is excluded from frontmatter injection and from the child summary list to avoid self-reference loops.
- Existing managed frontmatter from this plugin is replaced in place.
- Binary files are summarized in directory reports but are not modified.
- `mcp` and `exec` require a working Codex CLI login.
- `sdk` requires `@openai/codex-sdk` to be installed under `scripts/`.

## Files

- `scripts/scan_and_summarize.py`: Main scanner and writer.
- `scripts/codex_backends.py`: Codex MCP, SDK, and exec backends.
- `scripts/codex_sdk_bridge.mjs`: Optional Node bridge for `@openai/codex-sdk`.

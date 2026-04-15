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

Codex does not load the plugin directly from `~/plugins/`. It resolves installed plugins from the cache layout under:

```text
~/.codex/plugins/cache/<marketplace>/<plugin>/<revision>/
```

For this local marketplace, the effective paths are:

```text
~/.codex/plugins/cache/jiusi-agent-plugins/codebase-frontmatter-summary/<revision>/
~/.codex/plugins/cache/jiusi-agent-plugins/translate-web-to-chinese/<revision>/
~/.codex/plugins/cache/jiusi-agent-plugins/ohos-porting/<revision>/
```

Reinstall the marketplace and the three local plugins with:

```bash
rsync -a --delete /home/kaihong/agent-plugins/plugins/ /home/kaihong/plugins/
rsync -a /home/kaihong/agent-plugins/.agents/plugins/marketplace.json /home/kaihong/.agents/plugins/marketplace.json
```

Enable the local marketplace plugins in `~/.codex/config.toml`:

```toml
[plugins."codebase-frontmatter-summary@jiusi-agent-plugins"]
enabled = true

[plugins."translate-web-to-chinese@jiusi-agent-plugins"]
enabled = true

[plugins."ohos-porting@jiusi-agent-plugins"]
enabled = true
```

Then install each plugin into Codex's cache layout using the current revision:

```bash
rev="$(git -C /home/kaihong/agent-plugins rev-parse HEAD)"
base="$HOME/.codex/plugins/cache/jiusi-agent-plugins"
for plugin in codebase-frontmatter-summary translate-web-to-chinese ohos-porting; do
  rm -rf "$base/$plugin"
  mkdir -p "$base/$plugin/$rev"
  rsync -a --delete "$HOME/plugins/$plugin/" "$base/$plugin/$rev/"
done
```

After reinstalling, fully restart Codex CLI before checking the plugin list or invoking:

```text
$codebase-frontmatter-summary@jiusi-agent-plugins
```

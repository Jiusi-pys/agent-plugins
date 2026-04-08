---
name: translate-web-to-chinese
description: Crawl an English documentation site or linked web page tree, follow sublinks recursively, translate each page into Simplified Chinese, and preserve the source-to-Chinese relation graph in both Markdown and HTML. Use when Codex needs to mirror a documentation set or a small website into Chinese with local Codex CLI or MCP auth, and the workflow must avoid using OPENAI_API_KEY.
---

# Translate Web To Chinese

Use this skill to build a Chinese mirror of a linked English site while keeping page-level relations intact.

## Workflow

1. Confirm the crawl boundary before doing any fetches.
   Default to the entrypoint path prefix. Only widen to the full origin when the user asks for it or the site structure makes the prefix too narrow.
2. Crawl and record the source graph.
   Use `scripts/crawl_site.py` to fetch pages, save raw HTML, and write `manifest.json`, `relations.md`, and `relations.html`.
3. Expose Codex as MCP only when another local process needs it.
   Use `scripts/start_codex_mcp.py --print-config` to emit a config snippet or `--foreground` to run `codex mcp-server`.
4. Translate pages iteratively.
   Use `scripts/translate_site.py` with `--backend auto` unless the user explicitly wants a fixed backend.
5. Re-render relation reports after any manifest edits.
   Use `scripts/render_relations.py`.

## Auth Rules

- Never pass `OPENAI_API_KEY`.
- Never pass `CODEX_API_KEY`.
- Require a prior `codex login` session instead.
- Stop and ask the user to run `codex login` if the local session is missing.
- Read `references/codex-runtime.md` before changing backend selection or auth behavior.

## Backend Choice

- `auto`: Prefer this. It tries local Codex MCP first, then the SDK bridge, then `codex exec`.
- `mcp`: Force the local Codex MCP server path.
- `sdk`: Force `scripts/codex_sdk_bridge.mjs`. Use this only after `npm install @openai/codex-sdk` in `scripts/`.
- `exec`: Use the installed Codex CLI with `--output-schema` for structured page translations.
- `mock`: Use for local smoke tests when no live Codex call should be made.

The current official Codex SDK is TypeScript-based, so this skill keeps orchestration in Python and uses the Node bridge only as an optional backend.

## Quick Start

```bash
python3 scripts/crawl_site.py \
  --url https://example.com/docs/index.html \
  --output-dir /tmp/example-site/crawl

python3 scripts/translate_site.py \
  --manifest /tmp/example-site/crawl/manifest.json \
  --output-dir /tmp/example-site/zh \
  --backend auto

python3 scripts/render_relations.py \
  --manifest /tmp/example-site/zh/manifest.json \
  --output-dir /tmp/example-site/zh
```

## Output Layout

- Crawl output:
  `manifest.json`, `relations.md`, `relations.html`, and `raw/*.html`
- Chinese output:
  `manifest.json`, `relations.md`, `relations.html`, and `pages/*.md` plus `pages/*.html`

Keep the crawl manifest and the translated manifest separate so the source graph remains recoverable.

## Local Validation

Use the bundled sample site when you need a no-network smoke test:

```bash
python3 scripts/crawl_site.py \
  --url file:///Users/jiusi/Documents/agent-plugins/plugins/translate-web-to-chinese/skills/translate-web-to-chinese/assets/sample-site/index.html \
  --output-dir /tmp/sample-crawl

python3 scripts/translate_site.py --manifest /tmp/sample-crawl/manifest.json --output-dir /tmp/sample-zh --backend mock
```

## Files

- `scripts/crawl_site.py`: Crawl pages recursively and write the source graph.
- `scripts/codex_mcp_client.py`: Launch and talk to the local Codex MCP server.
- `scripts/translate_site.py`: Translate page-by-page and rewrite internal links to Chinese outputs.
- `scripts/render_relations.py`: Rebuild Markdown and HTML relation reports from a manifest.
- `scripts/start_codex_mcp.py`: Launch or describe a local `codex mcp-server`.
- `references/codex-runtime.md`: Official-doc-driven notes for backend and auth decisions.

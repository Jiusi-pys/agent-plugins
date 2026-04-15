---
name: translate-web-to-chinese
description: Crawl an English documentation site or linked web page tree, then call the single-page Chinese translator iteratively to build a Simplified Chinese mirror while preserving the page graph. Use when Codex needs multi-page site translation, not just one URL.
---
<!-- codex-file-meta: begin
relative_path: "skills/translate-web-to-chinese/SKILL.md"
language: "markdown"
summary: "Markdown document \"Translate Web To Chinese\". Use this skill for a bounded multi-page site. The page-level translation primitive lives in the sibling skill `../translate-url-to-chinese/`."
symbols: ["Translate Web To Chinese"]
generated_by: "codebase-frontmatter-summary"
codex-file-meta: end -->

# Translate Web To Chinese

Use this skill for a bounded multi-page site. The page-level translation primitive lives in the sibling skill `../translate-url-to-chinese/`.

## Workflow

1. Confirm the crawl boundary before any fetches.
   Default to the entrypoint path prefix. Only widen to the full origin when the user asks for it or the site structure demands it.
2. Crawl and record the source graph.
   Use `scripts/crawl_site.py` to fetch pages, save raw HTML, and write `manifest.json`, `relations.md`, and `relations.html`.
3. Translate the site iteratively.
   Use `scripts/translate_site.py`. It reads the crawl manifest and calls `../translate-url-to-chinese/scripts/translate_url.py` page by page.
4. Re-render relation reports after any manifest edits.
   Use `scripts/render_relations.py`.

## Auth And Runtime

- Use the Codex SDK path through the sibling single-page translator.
- Never pass `OPENAI_API_KEY`.
- Never pass `CODEX_API_KEY`.
- Require a prior `codex login` session instead.
- Read `references/codex-runtime.md` before changing SDK behavior or auth handling.

## Quick Start

```bash
python3 scripts/crawl_site.py \
  --url https://example.com/docs/index.html \
  --output-dir /tmp/example-site/crawl

python3 scripts/translate_site.py \
  --manifest /tmp/example-site/crawl/manifest.json \
  --output-dir /tmp/example-site/zh \
  --backend sdk

python3 scripts/render_relations.py \
  --manifest /tmp/example-site/zh/manifest.json \
  --output-dir /tmp/example-site/zh
```

## Output Layout

- Crawl output:
  `manifest.json`, `relations.md`, `relations.html`, and `raw/*.html`
- Chinese output:
  `manifest.json`, `relations.md`, `relations.html`, and `pages/<slug>/index.md`, `pages/<slug>/index.html`, plus `pages/<slug>/assets/*`

Keep the crawl manifest and the translated manifest separate so the source graph remains recoverable.

## Local Validation

Use the bundled sample site when you need a no-network smoke test:

```bash
python3 scripts/crawl_site.py \
  --url file:///absolute/path/to/plugins/translate-web-to-chinese/skills/translate-web-to-chinese/assets/sample-site/index.html \
  --output-dir /tmp/sample-crawl

python3 scripts/translate_site.py \
  --manifest /tmp/sample-crawl/manifest.json \
  --output-dir /tmp/sample-zh \
  --backend mock
```

## Files

- `scripts/crawl_site.py`: Crawl pages recursively and write the source graph.
- `scripts/translate_site.py`: Call the single-page translator iteratively and then rewrite internal links to Chinese outputs.
- `scripts/render_relations.py`: Rebuild Markdown and HTML relation reports from a manifest.
- `references/codex-runtime.md`: SDK and auth notes for this plugin.

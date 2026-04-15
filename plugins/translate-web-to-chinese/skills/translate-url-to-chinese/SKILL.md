---
name: translate-url-to-chinese
description: Translate a single English web page or documentation URL into Simplified Chinese Markdown or a localized HTML/CSS/JS bundle by calling the Codex SDK bridge. Use when Codex needs page-level translation for one URL, or when another workflow needs a reusable single-page translation primitive.
---
<!-- codex-file-meta: begin
relative_path: "skills/translate-url-to-chinese/SKILL.md"
language: "markdown"
summary: "Markdown document \"Translate URL To Chinese\". Use this skill when the job is a single page, not a whole site."
symbols: ["Translate URL To Chinese"]
generated_by: "codebase-frontmatter-summary"
codex-file-meta: end -->

# Translate URL To Chinese

Use this skill when the job is a single page, not a whole site.

## Workflow

1. Confirm the exact page URL and the requested output shape.
   Use Markdown when the user wants a readable Chinese doc. Use `web` or `both` when they need localized HTML plus copied CSS and JS assets.
2. Translate the page with the bundled SDK bridge.
   Run `scripts/translate_url.py`. It fetches the page unless you pass `--raw-html-file`, calls the Codex SDK bridge, writes Chinese outputs, and copies same-origin page assets for web outputs.
3. Keep auth local.
   Require an existing `codex login` session. Do not pass `OPENAI_API_KEY` or `CODEX_API_KEY`.
4. Use `mock` only for offline smoke tests.
   The normal path is `sdk`.

## Quick Start

```bash
python3 scripts/translate_url.py \
  --url https://example.com/docs/index.html \
  --output-dir /tmp/example-page-zh \
  --output-format both
```

Markdown only:

```bash
python3 scripts/translate_url.py \
  --url https://example.com/docs/index.html \
  --output-dir /tmp/example-page-md \
  --output-format markdown
```

## SDK Setup

Install the bridge dependency inside this skill before using the live SDK path:

```bash
cd scripts
npm install
```

## Local Validation

Use the bundled sample site with `mock` when no network or live Codex session should be used:

```bash
python3 scripts/translate_url.py \
  --url file:///absolute/path/to/plugins/translate-web-to-chinese/skills/translate-web-to-chinese/assets/sample-site/index.html \
  --output-dir /tmp/sample-page-zh \
  --output-format both \
  --backend mock
```

## Output Layout

- `translation.json`: machine-readable result summary
- `index.md`: Chinese Markdown when `markdown` or `both` is requested
- `index.html`: localized HTML when `web` or `both` is requested
- `assets/`: copied same-origin CSS, JS, image, and CSS-linked asset files for web output

## Files

- `scripts/translate_url.py`: page-level translator and asset copier
- `scripts/codex_sdk_bridge.mjs`: Node bridge for `@openai/codex-sdk`
- `scripts/package.json`: SDK dependency manifest

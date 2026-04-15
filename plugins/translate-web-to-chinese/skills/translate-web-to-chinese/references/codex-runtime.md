<!-- codex-file-meta: begin
relative_path: "skills/translate-web-to-chinese/references/codex-runtime.md"
language: "markdown"
summary: "Markdown document \"Codex Runtime Notes\". Use this reference when adjusting the translation backend or auth behavior."
symbols: ["Codex Runtime Notes"]
generated_by: "codebase-frontmatter-summary"
codex-file-meta: end -->

# Codex Runtime Notes

Use this reference when adjusting the translation backend or auth behavior.

## What the current OpenAI docs show

- The official Codex SDK page documents a TypeScript package: `@openai/codex-sdk`.
- The SDK can be used from local tooling through a small Node bridge while still relying on the user's `codex login` session.
- The local Codex CLI also supports `codex exec` and `codex mcp-server`, but this plugin now uses the SDK bridge as its primary path.

Official references:

- https://developers.openai.com/codex/sdk
- https://developers.openai.com/codex/noninteractive
- `codex --help`
- `codex exec --help`
- `codex mcp-server --help`

## Practical implication for this skill

- Keep the orchestration layer in Python.
- Prefer SDK-backed defaults: `gpt-5.4-mini` and `high` reasoning effort.
- Use `skills/translate-url-to-chinese/scripts/translate_url.py` as the page-level primitive.
- Use `skills/translate-web-to-chinese/scripts/translate_site.py` only as the site iterator that repeatedly invokes the single-page translator.

## Auth rule

- Do not pass `OPENAI_API_KEY`.
- Do not pass `CODEX_API_KEY`.
- Use the user's existing `codex login` session instead.
- The helper scripts strip both env vars before they launch Codex child processes or the SDK bridge.
- If the user is not logged in, stop and ask them to run `codex login`.

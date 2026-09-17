<!-- codex-file-meta: begin
relative_path: "README.md"
language: "markdown"
summary: "Markdown document \"Translate Web To Chinese Plugin\". Codex plugin for translating a single URL or a linked documentation tree into Simplified Chinese."
symbols: ["Translate Web To Chinese Plugin"]
generated_by: "codebase-frontmatter-summary"
codex-file-meta: end -->

# Translate Web To Chinese Plugin

Codex plugin for translating a single URL or a linked documentation tree into Simplified Chinese.

## Included Skill

- `translate-url-to-chinese`
- `translate-web-to-chinese`

## Notes

- The single-page layer lives under `skills/translate-url-to-chinese/`.
- The site layer lives under `skills/translate-web-to-chinese/` and calls the single-page layer iteratively.
- The skill remains Codex-oriented and does not require `OPENAI_API_KEY`.
- The default translation path is the Codex SDK bridge with model `gpt-5.4-mini` and `high` reasoning effort.

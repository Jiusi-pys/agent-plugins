# Indexing Policy

- Runtime state lives in `.scanmeta/state/index.sqlite`.
- File metadata lives in `.scanmeta/files/`.
- Large-file section indexes live in `.scanmeta/sections/`.
- Directory summaries live in `.scanmeta/dirs/`.
- Generated guides live in `.scanmeta/generated/`.
- Markdown inline frontmatter is opt-in. Source, config, test, and script files stay sidecar-only by default.

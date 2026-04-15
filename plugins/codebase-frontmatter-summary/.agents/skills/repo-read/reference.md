# Repo Read Reference

- Start with `AGENTS.md`, `CLAUDE.md`, and `.scanmeta/dirs/root.json`.
- Prefer `.scanmeta/files/*.json` over immediate full-file reads.
- Use `.scanmeta/sections/*.json` before opening large files.
- Escalate to full-file reads only for patching, exact behavior, unresolved ambiguity, or line-level reasoning.

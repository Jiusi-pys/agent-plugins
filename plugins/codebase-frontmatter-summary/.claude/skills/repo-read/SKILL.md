---
name: repo-read
description: Follow the deterministic read planner so investigation starts from summaries and escalates only when required.
---

# Repo Read

Use this skill when you need to inspect a repository without jumping into large file bodies.

## Workflow

1. Read `AGENTS.md`.
2. Read `.scanmeta/dirs/root.json` and nearest directory summaries.
3. Read `.scanmeta/files/*.json`.
4. Read `.scanmeta/sections/*.json` for large files.
5. Read full files only for patching, exact behavior, or unresolved ambiguity.

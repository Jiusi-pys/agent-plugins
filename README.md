# agent-plugins

This repository is organized around two branch roles:

- `main` is the stable upstream branch.
- `openai` is the Codex-oriented migration branch, where Claude-specific plugin content is being converted for Codex use.

The current converted output lives in `plugins/ohos-porting`.

## Converted Plugin

`plugins/ohos-porting` is the active converted plugin output in this branch. It represents the Codex-oriented porting workflow derived from the original OHOS tooling.

## Retained Codex Skills

The migration keeps these Codex skills available:

- `ohos-hdc`
- `ohos-cpp-style`
- `ohos-permission`

## Repository Notes

This branch is focused on Codex-facing migration output. Its documentation and converted artifacts should describe the openai branch as the migration destination for Codex use, not as a home for Claude plugin source-of-truth content.

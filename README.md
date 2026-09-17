# Codex plugins repository (`openai` branch)

This branch packages Codex-ready plugins from this repository under `plugins/`.

## Branch split

- `main`: Claude-oriented source material and original plugin content
- `openai`: Codex-native plugin packaging, hooks, and skill rewrites

## Available plugins

- `plugins/ohos-porting`
- `plugins/translate-web-to-chinese`
- `plugins/codebase-frontmatter-summary`

## Repo-local Codex surfaces

- `/.agents/plugins/marketplace.json`
- `/.codex/hooks.json`

## Notes

- `ohos-porting` is Linux-only and uses direct `hdc_std` or `hdc`.
- OHOS build guidance is standardized on `command-line-tools` and `openharmony_prebuilts`.
- `codebase-frontmatter-summary` scans a tree bottom-up, adds managed file frontmatter, and writes one summary file per directory.

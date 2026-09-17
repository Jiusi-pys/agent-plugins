# Codex plugins repository (`openai` branch)

This branch packages Codex-ready plugins from this repository under `plugins/`.
The Codex catalog is [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json).

## Branch split

- `main`: Claude-oriented source material and original plugin content
- `openai`: Codex-native plugin packaging, hooks, and skill rewrites

## Available plugins

| Plugin | Purpose |
| --- | --- |
| [ohos-porting](plugins/ohos-porting/README.md) | OpenHarmony porting, cross-compilation, deployment, and diagnostics |
| [translate-web-to-chinese](plugins/translate-web-to-chinese/README.md) | Translate individual pages or websites into Chinese |
| [codebase-frontmatter-summary](plugins/codebase-frontmatter-summary/README.md) | File frontmatter and bottom-up directory summaries |
| [agentic-review](plugins/agentic-review/README.md) | Risk-tiered, evidence-based code and software design review |
| [epub-editor](plugins/epub-editor/README.md) | EPUB metadata, word counts, navigation, notes, and cover editing |

Each catalog entry uses a repository-relative `./plugins/<name>` source and is available for installation. Display names and skill paths are defined in each plugin's `.codex-plugin/plugin.json`.

## Install from this repository

Clone and check out the `openai` branch, then register the checkout with Codex:

```sh
git clone --branch openai https://github.com/Jiusi-pys/agent-plugins.git
codex plugin marketplace add ./agent-plugins
```

Select the desired plugin from the `jiusi-agent-plugins` marketplace in Codex. The imported personal plugins are now included in this repository; no reference to the original user's local directories is required.

## Repo-local Codex surfaces

- `/.agents/plugins/marketplace.json`
- `/.codex/hooks.json`

## Notes

- `ohos-porting` is Linux-only and uses direct `hdc_std` or `hdc`.
- OHOS build guidance is standardized on `command-line-tools` and `openharmony_prebuilts`.
- `codebase-frontmatter-summary` scans a tree bottom-up, adds managed file frontmatter, and writes one summary file per directory.
- `agentic-review` includes a Python inventory helper and review reference documents.
- `epub-editor` requires Python with the dependencies in its `requirements.txt`; see its README for setup and tests.
- `plugins/multi-review` and `.claude-plugin/marketplace.json` are retained Claude-oriented content from the merged local history. They are not entries in the Codex catalog; the legacy Claude catalog is not the installation source for this branch.

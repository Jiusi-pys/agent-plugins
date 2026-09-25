# Codex plugins repository (`openai` branch)

This branch packages Codex-ready plugins from this repository under `plugins/`.
The Codex catalog is [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json).

## Branch split

- `main`: Claude-oriented source material and original plugin content
- `openai`: Codex-native plugin packaging, hooks, and skill rewrites

## Available plugins

| Plugin | Purpose |
| --- | --- |
| [agentic-review](plugins/agentic-review/README.md) | Risk-tiered, evidence-based code and software design review |
| [epub-editor](plugins/epub-editor/README.md) | EPUB metadata, word counts, navigation, notes, and cover editing |
| [weread-exporter](plugins/weread-exporter/README.md) | Export personally authorized WeRead books to Markdown with inline illustrations |

Each catalog entry uses a repository-relative `./plugins/<name>` source and is available for installation. The two converted personal plugins include a standard root `plugin.json` for Agent Plugins 1.0 clients and a matching `.codex-plugin/plugin.json` compatibility manifest for the Codex marketplace. Display names and skill paths are kept in sync between the manifests.

## Install from this repository

Clone and check out the `openai` branch, then register the checkout with Codex:

```sh
git clone --branch openai https://github.com/Jiusi-pys/agent-plugins.git
codex plugin marketplace add ./agent-plugins
```

Select the desired plugin from the `jiusi-agent-plugins` marketplace in Codex. The imported personal plugins are now included in this repository; no reference to the original user's local directories is required.

## Repo-local Codex surfaces

- `/.agents/plugins/marketplace.json`

## Notes

- `agentic-review` includes a Python inventory helper and review reference documents.
- `epub-editor` requires Python with the dependencies in its `requirements.txt`; see its README for setup and tests.
- Both plugins preserve their local skill instructions and supporting files while exposing the same interface metadata through the standard and Codex manifests.
- `weread-exporter` requires Python, Playwright, and a locally installed Chromium browser. It only exports books the user is authorized to read.
- `plugins/multi-review` and `.claude-plugin/marketplace.json` are retained Claude-oriented content from the merged local history. They are not entries in the Codex catalog; the legacy Claude catalog is not the installation source for this branch.

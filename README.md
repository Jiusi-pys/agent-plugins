# Codex plugins repository

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
| [book-translator](plugins/book-translator/README.md) | EPUB translation into Chinese and Classical Chinese modernization with live research agents, independent drafts, detailed notes, and full review |

Each catalog entry uses a repository-relative `./plugins/<name>` source. Plugins with portable manifests provide a standard root `plugin.json` for Agent Plugins 1.0 clients and a `.codex-plugin/plugin.json` compatibility manifest for the Codex marketplace. Display names and skill paths are kept in sync between the manifests.

## Install from this repository

Clone and check out the `openai` branch, then register the checkout with Codex:

```sh
git clone --branch openai https://github.com/Jiusi-pys/agent-plugins.git
codex plugin marketplace add ./agent-plugins
```

Select the desired plugin from the `jiusi-agent-plugins` marketplace in Codex. The imported personal plugins are now included in this repository; no reference to the original user's local directories is required.

The `openai` branch is the published Codex catalog. To try changes that are still on a feature branch, check out that branch before registering the local repository. For book-translator 0.2.1 on `codex/book-translator`:

```sh
git clone --branch codex/book-translator https://github.com/Jiusi-pys/agent-plugins.git agent-plugins-book-translator
codex plugin marketplace add ./agent-plugins-book-translator
```

A push to a feature branch does not update the `openai` catalog. See the [dependency and installation guide](plugins/book-translator/skills/book-translate/references/dependencies.md) for selecting the actual enabled EPUB editor.

## Book translation and Classical Chinese modernization

`book-translator` 0.2.1 offers two workflows, with beginner-friendly explanations and clearly marked hypothetical examples where useful:

| Input | Output | Workflow |
| --- | --- | --- |
| Foreign-language EPUB | Simplified Chinese EPUB | Verify common title/author translations online, translate chapters in parallel, then perform independent chapter and full-book review |
| Classical Chinese text, UTF-8 TXT, or Markdown | Modern Chinese Markdown with original text and detailed notes | Live primary-source research, independent candidate translations, selection based on evidence, and independent review |
| Classical Chinese EPUB | Modern Chinese EPUB with linked original text and detailed notes | The same research and review process, followed by the existing EPUB editor |

Classical Chinese translation starts with the user's actual text. No rehearsal, sample book, or prepared research dossier is required:

1. Two independent research agents per chapter locate and read the relevant original works, ancient commentaries, and alternative interpretations. They investigate wording, punctuation, allusions, historical institutions, and textual variants, recording editions, locations, quotations, and actual reading traces.
2. Two separate translators independently produce complete drafts and annotations. The assigned lead translator compares them passage by passage, selects or revises wording based on the sources, and records significant choices.
3. A dedicated chapter reviewer and a new full-book reviewer independently compare the original, translation, notes, sources, and task records. New questions return to research and revision until substantive issues are resolved or a concrete evidence/access gap is reported.

Quality determines the depth of research and revision. Classical Chinese jobs have no fixed three-round revision limit and do not reduce source checking, annotation detail, or full-text review to save time or cost. Host concurrency and access limits still apply; jobs can queue work and preserve progress for resumption. Supported alternative readings remain visible in the notes.

The plugin contains its own `translation-review` skill and does not modify or depend on `agentic-review`. Text-only Classical Chinese jobs do not require EPUB editor. EPUB workflows resolve the currently enabled `epub-editor` plugin and validate its real CLI before use.

Provide the input text or file path with a request such as:

> 将这份古文精译为现代汉语，实时派出 sub-agent 查阅对应原典和古注，详细解释《诗经》《春秋》等用典，保留原文对照、异说与出处，双稿择优并独立全文复核。质量优先，不因时间和花费减少查证。

Source snapshots and version checks make the work traceable; they do not prove that an agent actually read a source or that an interpretation is infallible. The workflow therefore also requires real research calls and independent source review. Digital-text verification and facsimile collation are reported separately.

See the [plugin README](plugins/book-translator/README.md), [Classical Chinese skill](plugins/book-translator/skills/classical-translate/SKILL.md), and [live research and selection workflow](plugins/book-translator/skills/classical-translate/references/live-research.md) for the full contract.

## Repo-local Codex surfaces

- `/.agents/plugins/marketplace.json`

## Notes

- `agentic-review` includes a Python inventory helper and review reference documents.
- `epub-editor` requires Python with the dependencies in its `requirements.txt`; see its README for setup and tests.
- Both plugins preserve their local skill instructions and supporting files while exposing the same interface metadata through the standard and Codex manifests.
- `weread-exporter` requires Python, Playwright, and a locally installed Chromium browser. It only exports books the user is authorized to read.
- `book-translator` requires real sub-agent tools, web search, local file access, and Python 3.11+ with its declared dependencies. EPUB workflows additionally require the enabled `epub-editor` plugin; text-only Classical Chinese jobs do not. Work directories retain source evidence, candidate drafts, selection records, and reviews without overwriting the original input.
- `plugins/multi-review` and `.claude-plugin/marketplace.json` are retained Claude-oriented content from the merged local history. They are not entries in the Codex catalog; the legacy Claude catalog is not the installation source for this branch.

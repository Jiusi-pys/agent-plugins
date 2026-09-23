# Jiusi Agent Plugins

Claude Code marketplace for OpenHarmony/KaihongOS software porting, evidence-gated code review, personal knowledge export, and EPUB editing.

## Available plugins

| Plugin | Contents | Documentation |
| --- | --- | --- |
| `ohos-porting` | 8-phase porting workflow, 7 agents, 14 skills, 4 commands and diagnostic hooks | [OHOS guide](plugins/ohos-porting/README.md) |
| `multi-review` | Risk routing, 6 review sensors, independent verification and a unified judge; 9 agents total | [Review guide](plugins/multi-review/README.md) |
| `weread-exporter` | Exports personally authorized WeRead books to Markdown with inline illustrations | [WeRead guide](plugins/weread-exporter/README.md) |
| `epub-editor` | Edit EPUB metadata, recount words, repair navigation and notes, and replace a user-provided cover | [EPUB guide](plugins/epub-editor/README.md) |

## Installation

Run in Claude Code, installing whichever plugins you need:

```text
/plugin marketplace add Jiusi-pys/agent-plugins
/plugin install ohos-porting@jiusi-agent-plugins
/plugin install multi-review@jiusi-agent-plugins
/plugin install weread-exporter@jiusi-agent-plugins
/plugin install epub-editor@jiusi-agent-plugins
```

The marketplace identifier is `jiusi-agent-plugins`. Add the GitHub repository or a local checkout: relative plugin sources do not work with a raw marketplace JSON URL.

```text
/ohos-porting:ohos-port libcurl
/ohos-porting:ohos-port-dev libcurl
/ohos-porting:ohos-build
/ohos-porting:ohos-deploy
/multi-review:multi-review
/multi-review:multi-review HEAD
/weread-exporter:weread-export <weread-reader-url-or-book-id>
```

## Codex marketplace

The repository also exposes Codex-ready plugins through [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json). Register a local checkout, then install `weread-exporter`:

```powershell
codex plugin marketplace add .
codex plugin add weread-exporter@jiusi-agent-plugins
```

`weread-exporter` packages the upstream Playwright exporter for personal study or backup of WeRead books that the user is authorized to read. It opens an interactive browser for the user's own login and does not bypass access restrictions.

After installing `epub-editor`, provide an EPUB file path and the changes you need, for example: “修改作者并统计字数，保留其他元数据。” The plugin creates a new EPUB and never overwrites the original.

OHOS builds require the appropriate SDK/toolchain and HDC for deployment; SSH supports remote builds. Bundled shell scripts require Bash (Git Bash or WSL on Windows). Multi-review also requires the Workflow tool; see the plugin guides for details.

## Updates and removal

```text
/plugin marketplace update jiusi-agent-plugins
/plugin update ohos-porting@jiusi-agent-plugins
/plugin update multi-review@jiusi-agent-plugins
```

Follow the client's reload or restart instructions after updating.

`auto-clean` has been removed. The catalog retains `"renames": {"auto-clean": null}` so Claude Code 2.1.193+ can remove obsolete settings entries after refreshing the marketplace. Older clients can uninstall it with `/plugin uninstall auto-clean@jiusi-agent-plugins`. Administrators must update managed settings separately.

## Development and validation

```bash
git clone https://github.com/Jiusi-pys/agent-plugins.git
cd agent-plugins
claude plugin validate .
claude plugin validate ./plugins/ohos-porting
claude plugin validate ./plugins/multi-review
claude plugin validate ./plugins/weread-exporter
claude plugin validate ./plugins/epub-editor
claude --plugin-dir ./plugins/ohos-porting
claude --plugin-dir ./plugins/weread-exporter
python -m unittest discover -s plugins/epub-editor/tests -v
```

CI runs official manifest/structure validation for the marketplace and each plugin. These checks do not exercise device deployment or review workflows.

Plugin versions live in each plugin's `.claude-plugin/plugin.json`; bump the affected version for every release. The marketplace's top-level version tracks catalog changes independently. Keep removal entries in `renames` permanently.

## Repository layout

```text
.claude-plugin/marketplace.json
.github/workflows/validate-plugins.yml
plugins/ohos-porting/
plugins/multi-review/
plugins/weread-exporter/
plugins/epub-editor/
CLAUDE.md
README.md
```

See the [official marketplace rules](https://code.claude.com/docs/en/plugin-marketplaces) for catalog fields, relative sources, migration and validation.

## License

MIT

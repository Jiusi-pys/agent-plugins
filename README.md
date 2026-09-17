# Jiusi Agent Plugins

Claude Code marketplace for OpenHarmony/KaihongOS software porting and evidence-gated code review.

## Available plugins

| Plugin | Contents | Documentation |
| --- | --- | --- |
| `ohos-porting` | 8-phase porting workflow, 7 agents, 14 skills, 4 commands and diagnostic hooks | [OHOS guide](plugins/ohos-porting/README.md) |
| `multi-review` | Risk routing, 6 review sensors, independent verification and a unified judge; 9 agents total | [Review guide](plugins/multi-review/README.md) |

## Installation

Run in Claude Code, installing whichever plugins you need:

```text
/plugin marketplace add Jiusi-pys/agent-plugins
/plugin install ohos-porting@jiusi-agent-plugins
/plugin install multi-review@jiusi-agent-plugins
```

The marketplace identifier is `jiusi-agent-plugins`. Add the GitHub repository or a local checkout: relative plugin sources do not work with a raw marketplace JSON URL.

```text
/ohos-porting:ohos-port libcurl
/ohos-porting:ohos-port-dev libcurl
/ohos-porting:ohos-build
/ohos-porting:ohos-deploy
/multi-review:multi-review
/multi-review:multi-review HEAD
```

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
claude --plugin-dir ./plugins/ohos-porting
```

CI runs official manifest/structure validation for the marketplace and each plugin. These checks do not exercise device deployment or review workflows.

Plugin versions live in each plugin's `.claude-plugin/plugin.json`; bump the affected version for every release. The marketplace's top-level version tracks catalog changes independently. Keep removal entries in `renames` permanently.

## Repository layout

```text
.claude-plugin/marketplace.json
.github/workflows/validate-plugins.yml
plugins/ohos-porting/
plugins/multi-review/
CLAUDE.md
README.md
```

See the [official marketplace rules](https://code.claude.com/docs/en/plugin-marketplaces) for catalog fields, relative sources, migration and validation.

## License

MIT

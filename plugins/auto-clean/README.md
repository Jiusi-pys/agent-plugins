# auto-clean

A Claude Code plugin for automated privacy cleanup. It removes tracking data, telemetry, session history, and performs full resets across five levels.

## Features

- **Level 1** — Reset device identifiers (`userID`, `anonymousId`, etc.)
- **Level 2** — Clear telemetry and analytics data
- **Level 3** — Clear sessions, history, `session-env`, and `session-history`
- **Level 4** — Clear OAuth account linkage and keychain credentials
- **Level 5** — Full reset of `~/.claude/` and `~/.claude.json`

## Commands

### `/init`
Manual command that performs a **Level 5 full reset** and recreates `~/.claude/settings.json` with:

```json
{
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

> **Important:** `init` deletes the entire `~/.claude/` directory. Because Claude Code stores installed plugins under `~/.claude/plugins/cache/`, running `init` will remove all active plugins including `auto-clean` itself. After running `init`, you must **reinstall and reload your plugins**:
> ```
> /plugin
> /reload-plugins
> ```

### `/clean-history`
Manual command that performs a **Level 3 cleanup**, removing:
- `history.jsonl`
- `sessions/`
- `session-history/`
- `paste-cache/`
- `shell-snapshots/`
- `session-env/`
- `file-history/`
- `debug/`

## Hooks

Both hooks run automatically when a Claude Code session ends (`Stop` event):

- **`clean.sh`** — Runs **Level 1 + Level 2** (device identifiers + telemetry)
- **`clear.sh`** — Runs **Level 2** (telemetry only)

## File Structure

```
plugins/auto-clean/
├── commands/
│   ├── init.md
│   └── clean-history.md
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       ├── clean.sh
│       └── clear.sh
├── scripts/
│   ├── init.sh
│   └── clean-history.sh
└── .claude-plugin/
    └── plugin.json
```

## License

MIT

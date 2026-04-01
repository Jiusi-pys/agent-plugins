---
description: Manual command. Performs a level 5 full reset and ensures ~/.claude/settings.json contains the env disabling non-essential traffic.
allowed-tools: Bash, Read
---

Run the manual initialization cleanup (level 5).

1. Execute the init script using Bash:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/init.sh"
   ```
2. After it completes, use the Read tool to open `~/.claude/settings.json` and confirm it contains:
   ```json
   {
     "env": {
       "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
     }
   }
   ```
3. Report the results to the user, including:
   - Level 5 completion status
   - Whether the env setting was created correctly
   - Backup directory location
   - Any warnings or errors

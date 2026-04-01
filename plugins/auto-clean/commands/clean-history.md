---
description: Manual command. Performs a level 3 cleanup of sessions, history, session-env, and session-history.
allowed-tools: Bash
---

Run the manual history cleanup (level 3).

1. Execute the clean-history script using Bash:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/clean-history.sh"
   ```
2. Report the results to the user, including:
   - Level 3 completion status
   - The scope of deleted data
   - Any warnings or errors

#!/bin/bash
# on_task_complete.sh - Send email notification when Claude Code task completes

PLUGIN_DIR="${HOME}/.claude/plugins/email-notify"
CONFIG_FILE="${HOME}/.claude-notify/config.json"

# Check if config exists and notifications are enabled
if [[ ! -f "$CONFIG_FILE" ]]; then
    exit 0
fi

# Check enabled status using python
ENABLED=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('enabled', False))" 2>/dev/null)

if [[ "$ENABLED" != "True" ]]; then
    exit 0
fi

# Send notification
python3 "${PLUGIN_DIR}/scripts/send_notification.py" "" "Claude Code task completed"

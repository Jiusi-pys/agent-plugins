---
description: Enable email notification hook. Claude Code will send email when generation completes.
allowed-tools: Bash, Read
---

# Enable Email Notifications

## Execution

### Step 1: Check Configuration

Verify configuration exists:

```bash
python3 ~/.claude/plugins/email-notify/scripts/config_manager.py status
```

If not configured, prompt user to run `/notify-config` first.

### Step 2: Enable Notifications

```bash
python3 ~/.claude/plugins/email-notify/scripts/config_manager.py enable
```

### Step 3: Output Result

```
╔═══════════════════════════════════════════════════════╗
║         Email Notifications ENABLED                   ║
╠═══════════════════════════════════════════════════════╣
║ Receiver: {receiver}                                  ║
║ Hook:     Stop event                                  ║
╚═══════════════════════════════════════════════════════╝

You will receive email when Claude Code task completes.
To disable: /notify-off
```

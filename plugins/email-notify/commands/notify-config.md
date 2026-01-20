---
description: Configure Gmail SMTP email notification. Usage: /notify-config --send <sender_gmail> --auth <app_password> --recv <receiver_email>
allowed-tools: Bash, Read, Write, Edit
---

# Email Notify Configuration

## Parameters

Parse from \$ARGUMENTS:
- `--send`: Sender Gmail address
- `--auth`: Gmail App Password (16-char, NOT login password)
- `--recv`: Receiver email address

## Execution Steps

### Step 1: Parse Arguments

Extract parameters from \$ARGUMENTS using pattern matching.

### Step 2: Validate Parameters

Verify all required parameters are provided:
- sender email format valid
- app password is 16 characters
- receiver email format valid

### Step 3: Run Setup Script

Execute Postfix Gmail SMTP configuration:

```bash
cd ~/.claude/plugins/email-notify
bash scripts/setup_postfix_gmail.sh "<sender>" "<app_password>"
```

### Step 4: Save Configuration

```bash
python3 ~/.claude/plugins/email-notify/scripts/config_manager.py save \
  --send "<sender>" \
  --auth "<app_password>" \
  --recv "<receiver>"
```

### Step 5: Output Result

```
╔═══════════════════════════════════════════════════════╗
║         Email Notify Configuration                    ║
╠═══════════════════════════════════════════════════════╣
║ Sender:   {sender}                                    ║
║ Receiver: {receiver}                                  ║
║ Status:   Configured ✓                                ║
╚═══════════════════════════════════════════════════════╝

Test email sent. Check receiver inbox.

To enable/disable:
  /notify-on   - Enable notifications
  /notify-off  - Disable notifications
```

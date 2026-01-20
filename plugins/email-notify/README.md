# Email Notify Plugin

Gmail SMTP email notification system for Claude Code. Receive email alerts when Claude Code completes generation tasks.

## Features

- **Postfix + Gmail SMTP**: Reliable email delivery via Gmail relay
- **Slash Commands**: Easy configuration and control
- **Hook Integration**: Automatic notification on task completion

## Prerequisites

1. Gmail account with 2-Step Verification enabled
2. Gmail App Password generated
3. Ubuntu/Debian system
4. sudo access

## Installation

```bash
/install email-notify
```

## Usage

### Configure

```bash
/notify-config --send your@gmail.com --auth xxxx-xxxx-xxxx-xxxx --recv notify@example.com
```

Parameters:
- `--send`: Your Gmail address (sender)
- `--auth`: Gmail App Password (16 characters, NOT your login password)
- `--recv`: Email address to receive notifications

### Enable/Disable

```bash
/notify-on   # Enable notifications
/notify-off  # Disable notifications
```

## Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to App passwords
4. Select "Other (Custom name)" -> Enter "Claude Code"
5. Copy the 16-character password

## How It Works

1. Plugin configures Postfix as local MTA with Gmail SMTP relay
2. When enabled, Stop hook triggers email notification
3. Email sent via `mail` command through Postfix -> Gmail SMTP

## Files

```
email-notify/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── notify-config.md
│   ├── notify-on.md
│   └── notify-off.md
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       └── on_task_complete.sh
├── scripts/
│   ├── setup_postfix_gmail.sh
│   ├── config_manager.py
│   └── send_notification.py
├── install.sh
└── README.md
```

## Troubleshooting

### Check Postfix status

```bash
sudo systemctl status postfix
```

### View mail logs

```bash
sudo tail -f /var/log/mail.log
```

### Test email manually

```bash
echo "Test" | mail -s "Test" your@email.com
```

## Limitations

- Gmail SMTP limit: 500 emails/day
- Requires Postfix (auto-installed on Debian/Ubuntu)
- App Password required (regular password won't work)

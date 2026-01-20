#!/usr/bin/env python3
"""
send_notification.py - Send email notification for Claude Code task completion

Usage:
    send_notification.py <receiver_email> [task_info]
    
Environment variables:
    CLAUDE_NOTIFY_RECEIVER - Override receiver email
    CLAUDE_NOTIFY_SUBJECT  - Custom subject prefix
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".claude-notify"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def send_email(receiver: str, subject: str, body: str) -> bool:
    """Send email via system mail command (Postfix)."""
    try:
        process = subprocess.Popen(
            ["mail", "-s", subject, receiver],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=body, timeout=60)
        return process.returncode == 0
    except subprocess.TimeoutExpired:
        process.kill()
        return False
    except FileNotFoundError:
        # Fallback: try sendmail directly
        try:
            message = f"Subject: {subject}\nTo: {receiver}\n\n{body}"
            process = subprocess.Popen(
                ["/usr/sbin/sendmail", "-t"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process.communicate(input=message, timeout=60)
            return process.returncode == 0
        except Exception:
            return False
    except Exception:
        return False


def format_notification(task_info: str = None) -> tuple[str, str]:
    """Format notification subject and body."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = os.uname().nodename
    
    subject_prefix = os.environ.get("CLAUDE_NOTIFY_SUBJECT", "[Claude Code]")
    
    if task_info:
        subject = f"{subject_prefix} Task Completed: {task_info[:50]}"
        body = f"""Claude Code Task Completed
{'='*40}

Task:      {task_info}
Time:      {timestamp}
Host:      {hostname}

---
Sent by email-notify plugin
"""
    else:
        subject = f"{subject_prefix} Task Completed"
        body = f"""Claude Code Task Completed
{'='*40}

Time:      {timestamp}
Host:      {hostname}

---
Sent by email-notify plugin
"""
    
    return subject, body


def main():
    config = load_config()
    
    # Check if notifications are enabled
    if not config.get("enabled", False):
        # Silent exit when disabled
        return 0
    
    # Determine receiver
    receiver = os.environ.get("CLAUDE_NOTIFY_RECEIVER")
    if not receiver and len(sys.argv) > 1:
        receiver = sys.argv[1]
    if not receiver:
        receiver = config.get("receiver")
    
    if not receiver:
        print("Error: No receiver email specified", file=sys.stderr)
        return 1
    
    # Get task info
    task_info = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Format and send
    subject, body = format_notification(task_info)
    
    if send_email(receiver, subject, body):
        print(f"Notification sent to {receiver}")
        return 0
    else:
        print(f"Failed to send notification to {receiver}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/bin/bash
set -e

CLAUDE_JSON="$HOME/.claude.json"
CLAUDE_DIR="$HOME/.claude"
BACKUP_DIR="$HOME/.claude-backup-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

# Backup key files before full reset
[ -f "$CLAUDE_DIR/CLAUDE.md" ] && cp "$CLAUDE_DIR/CLAUDE.md" "$BACKUP_DIR/" 2>/dev/null || true
[ -f "$CLAUDE_DIR/settings.json" ] && cp "$CLAUDE_DIR/settings.json" "$BACKUP_DIR/" 2>/dev/null || true
[ -d "$CLAUDE_DIR/skills" ] && cp -R "$CLAUDE_DIR/skills" "$BACKUP_DIR/" 2>/dev/null || true
[ -d "$CLAUDE_DIR/hooks" ] && cp -R "$CLAUDE_DIR/hooks" "$BACKUP_DIR/" 2>/dev/null || true

echo "[auto-clean] Backup created at $BACKUP_DIR"

# Delete macOS keychain entries for Claude Code
security delete-generic-password -s "claude-code" 2>/dev/null || true
security delete-generic-password -s "claude-code-credentials" 2>/dev/null || true
echo "[auto-clean] Keychain credentials cleared"

# Level 5: Full reset
rm -rf "$CLAUDE_DIR"
rm -f "$CLAUDE_JSON"
echo "[auto-clean] Level 5: full reset completed"

# Restore settings.json with the required env setting
mkdir -p "$CLAUDE_DIR"
python3 -c '
import json, os
out = os.path.expanduser("~/.claude/settings.json")
d = {"env": {"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}}
with open(out, "w") as f: json.dump(d, f, indent=2)
print("[auto-clean] Created settings.json with env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1")
' 2>/dev/null || echo '{"env":{"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC":"1"}}' > "$CLAUDE_DIR/settings.json"

echo "[auto-clean] Init completed successfully"

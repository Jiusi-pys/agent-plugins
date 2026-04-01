#!/bin/bash
set -e

CLAUDE_DIR="$HOME/.claude"

echo "[auto-clean] Starting clean-history (level 3)..."

# Level 3: Clear sessions and history data
rm -f "$CLAUDE_DIR/history.jsonl" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/sessions" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/session-history" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/paste-cache" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/shell-snapshots" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/session-env" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/file-history" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/debug" 2>/dev/null || true
echo "[auto-clean] Level 3: sessions, session-env, session-history, and history cleared"

echo "[auto-clean] clean-history completed successfully"

#!/bin/bash
# Stop hook: performs level 2 cleanup before the session exits.

CLAUDE_DIR="$HOME/.claude"

echo "[auto-clean] Running exit cleanup (clear / level 2)..."

# Level 2: Clear telemetry and analytics data
rm -rf "$CLAUDE_DIR/telemetry" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/statsig" 2>/dev/null || true
rm -f "$CLAUDE_DIR/stats-cache.json" 2>/dev/null || true
echo "[auto-clean] Level 2: telemetry and analytics cleared"

echo "[auto-clean] Exit cleanup (clear) completed."
exit 0

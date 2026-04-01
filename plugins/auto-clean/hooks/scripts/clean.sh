#!/bin/bash
# Stop hook: performs level 1 and level 2 cleanup before the session exits.

CLAUDE_JSON="$HOME/.claude.json"
CLAUDE_DIR="$HOME/.claude"

echo "[auto-clean] Running exit cleanup (clean / level 1+2)..."

# Level 1: Reset device identifiers
if [ -f "$CLAUDE_JSON" ]; then
    python3 -c "
import json, os
p = os.path.expanduser('~/.claude.json')
try:
    with open(p, 'r') as f: d = json.load(f)
except: d = {}
for k in ['userID', 'anonymousId', 'firstStartTime', 'claudeCodeFirstTokenDate']:
    d.pop(k, None)
with open(p, 'w') as f: json.dump(d, f, indent=2)
print('[auto-clean] Level 1: device identifiers reset')
" 2>/dev/null || echo "[auto-clean] Level 1: skipped"
fi

# Level 2: Clear telemetry and analytics data
rm -rf "$CLAUDE_DIR/telemetry" 2>/dev/null || true
rm -rf "$CLAUDE_DIR/statsig" 2>/dev/null || true
rm -f "$CLAUDE_DIR/stats-cache.json" 2>/dev/null || true
echo "[auto-clean] Level 2: telemetry and analytics cleared"

echo "[auto-clean] Exit cleanup (clean) completed."
exit 0

#!/bin/bash
set -euo pipefail

INPUT="$(cat)"
COMMAND="$(INPUT_JSON="$INPUT" python3 -c 'import json, os; print(json.loads(os.environ["INPUT_JSON"]).get("tool_input", {}).get("command", ""))')"

if ! printf '%s' "$COMMAND" | grep -Eqi '(^|[[:space:]])(hdc|hdc_std)([[:space:]]|$)|openharmony|ohos|BUILD\.gn|softbus|hilog'; then
  exit 0
fi

if printf '%s' "$COMMAND" | grep -Eqi '(/system|/vendor).*(rm|cp|mv|dd|mount)|target mount|smode'; then
  python3 -c 'import json; print(json.dumps({
    "systemMessage": "OHOS guardrail: modifying /system, /vendor, remounting partitions, or escalating device privileges requires explicit user authorization.",
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Dangerous OHOS device mutation blocked until the user explicitly authorizes it."
    }
}))'
  exit 0
fi

python3 -c 'import json; print(json.dumps({
    "systemMessage": "OHOS context: prefer the skills under plugins/ohos-porting, keep temporary artifacts under /data/local/tmp, and use direct Linux hdc_std/hdc flows."
}))'

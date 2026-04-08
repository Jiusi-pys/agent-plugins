#!/bin/bash
set -euo pipefail

INPUT="$(cat)"
INPUT_JSON="$INPUT" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["INPUT_JSON"])
command = payload.get("tool_input", {}).get("command", "")
resp = payload.get("tool_response")
if isinstance(resp, str):
    try:
        resp = json.loads(resp)
    except Exception:
        resp = {"stdout": resp, "stderr": "", "exit_code": 0}

exit_code = int(resp.get("exit_code", 0) or 0)
stdout = str(resp.get("stdout", "") or "")
stderr = str(resp.get("stderr", "") or "")
output = stdout + "\n" + stderr

if exit_code == 0:
    sys.exit(0)

hint = None
if any(token in command for token in ["build", "gn ", "ninja", "clang", "clang++", "cmake", "make"]):
    if "permission" in output.lower() or "softbus" in output.lower():
        hint = "Use $ohos-permission for permission and DSoftBus follow-up."
    else:
        hint = "Use $compile-error-analysis or $ohos-cpp-style to classify and fix the build failure."
elif any(token in command for token in ["hdc", "hdc_std", "hilog"]):
    hint = "Use $ohos-hdc or $runtime-debug to inspect the failed device interaction."

if hint:
    print(json.dumps({
        "systemMessage": hint,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": hint
        }
    }))
PY

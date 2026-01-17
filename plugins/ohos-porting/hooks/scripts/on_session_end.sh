#!/bin/bash
# Session end hook - saves working state
# This hook is called when Claude Code session ends

WORKING_DIR="${OHOS_PORTING_WORKDIR:-.ohos-porting}"

if [ -d "$WORKING_DIR" ]; then
    echo "[ohos-porting] Session ended, working state preserved in $WORKING_DIR"
fi

exit 0

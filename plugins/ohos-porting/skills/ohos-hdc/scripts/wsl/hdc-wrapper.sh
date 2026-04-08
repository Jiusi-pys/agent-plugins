#!/bin/bash
# hdc-wrapper.sh - WSL wrapper for Windows HDC
# Calls hdc.exe on Windows host via powershell.exe
#
# Usage:
#   ./hdc-wrapper.sh -t <device_id> shell ls
#   ./hdc-wrapper.sh list targets -v
#
# Environment:
#   HDC_PATH - Custom path to hdc.exe (default: hdc in PATH)
#   HDC_DEVICE - Default device ID if -t not specified

set -e

# Configuration
HDC_PATH="${HDC_PATH:-hdc}"
STAGING_DIR="/mnt/c/tmp/hdc_staging"
WIN_STAGING_DIR="C:\\tmp\\hdc_staging"

# Ensure staging directory exists
mkdir -p "$STAGING_DIR" 2>/dev/null || true

# Function: Convert WSL path to Windows path
wsl_to_win() {
    local path="$1"
    if [[ "$path" == /mnt/* ]]; then
        # /mnt/c/foo -> C:\foo
        local drive="${path:5:1}"
        local rest="${path:7}"
        echo "${drive^^}:${rest//\//\\}"
    elif [[ "$path" == /* ]]; then
        # Absolute Linux path - use wslpath
        wslpath -w "$path" 2>/dev/null || echo "$path"
    else
        # Relative path - keep as is
        echo "$path"
    fi
}

# Function: Execute HDC command via PowerShell
hdc_exec() {
    powershell.exe -NoProfile -NonInteractive -Command "$HDC_PATH $*" 2>&1 | tr -d '\r'
}

# Function: Execute HDC with proper escaping
hdc_exec_args() {
    local args=""
    for arg in "$@"; do
        # Escape single quotes for PowerShell
        arg="${arg//\'/\'\'}"
        args="$args '$arg'"
    done
    powershell.exe -NoProfile -NonInteractive -Command "$HDC_PATH $args" 2>&1 | tr -d '\r'
}

# Main execution
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [hdc_options] <command> [args...]"
    echo ""
    echo "Examples:"
    echo "  $0 list targets -v"
    echo "  $0 -t <device_id> shell ls"
    echo "  $0 -t <device_id> hilog"
    echo ""
    echo "Environment variables:"
    echo "  HDC_PATH   - Path to hdc.exe (default: hdc)"
    echo "  HDC_DEVICE - Default device ID"
    echo ""
    echo "For file transfer, use hdc-send.sh and hdc-recv.sh"
    exit 1
fi

# If HDC_DEVICE is set and -t not provided, prepend it
if [[ -n "$HDC_DEVICE" && "$1" != "-t" && "$1" != "list" && "$1" != "start" && "$1" != "kill" ]]; then
    set -- -t "$HDC_DEVICE" "$@"
fi

# Execute
hdc_exec_args "$@"

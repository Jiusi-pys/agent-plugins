#!/bin/bash
# hdc-recv.sh - Receive files from KaihongOS device to WSL via Windows staging
#
# Flow: device -> hdc file recv -> C:\tmp\hdc_staging -> WSL path
#
# Usage:
#   ./hdc-recv.sh -t <device_id> <remote_path> <local_path> [options]
#
# Options:
#   -z    Compress transfer
#   -a    Preserve timestamp
#   -k    Keep staging files (don't clean up)
#
# Examples:
#   ./hdc-recv.sh -t 7001005... /data/log/app.log ./logs/
#   ./hdc-recv.sh -t 7001005... /data/coredump ./crash/ -z

set -e

# Configuration
HDC_PATH="${HDC_PATH:-hdc}"
STAGING_DIR="/mnt/c/tmp/hdc_staging"
WIN_STAGING_DIR="C:\\tmp\\hdc_staging"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[*]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[+]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[-]${NC} $1"; }

usage() {
    echo "Usage: $0 -t <device_id> <remote_path> <local_path> [options]"
    echo ""
    echo "Options:"
    echo "  -t <id>   Device ID (required)"
    echo "  -z        Compress transfer"
    echo "  -a        Preserve timestamp"
    echo "  -k        Keep staging files"
    echo ""
    echo "Examples:"
    echo "  $0 -t 7001005... /data/log/app.log ./logs/"
    echo "  $0 -t 7001005... /data/coredump ./crash/ -z"
    exit 1
}

# Parse arguments
DEVICE_ID=""
REMOTE_PATH=""
LOCAL_PATH=""
COMPRESS=""
TIMESTAMP=""
KEEP_STAGING=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t)
            DEVICE_ID="$2"
            shift 2
            ;;
        -z)
            COMPRESS="-z"
            shift
            ;;
        -a)
            TIMESTAMP="-a"
            shift
            ;;
        -k)
            KEEP_STAGING=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "$REMOTE_PATH" ]]; then
                REMOTE_PATH="$1"
            elif [[ -z "$LOCAL_PATH" ]]; then
                LOCAL_PATH="$1"
            fi
            shift
            ;;
    esac
done

# Validate
if [[ -z "$DEVICE_ID" ]]; then
    log_error "Device ID required (-t)"
    usage
fi

if [[ -z "$REMOTE_PATH" || -z "$LOCAL_PATH" ]]; then
    log_error "Remote and local paths required"
    usage
fi

# Create staging directory
STAGE_NAME="stage_$(date +%s)_$$"
STAGE_PATH="$STAGING_DIR/$STAGE_NAME"
WIN_STAGE_PATH="$WIN_STAGING_DIR\\$STAGE_NAME"

mkdir -p "$STAGE_PATH"
log_info "Staging directory: $STAGE_PATH"

# Cleanup function
cleanup() {
    if [[ "$KEEP_STAGING" == false && -d "$STAGE_PATH" ]]; then
        rm -rf "$STAGE_PATH"
        log_info "Cleaned staging directory"
    fi
}
trap cleanup EXIT

# Build HDC command
HDC_OPTS=""
[[ -n "$COMPRESS" ]] && HDC_OPTS="$HDC_OPTS $COMPRESS"
[[ -n "$TIMESTAMP" ]] && HDC_OPTS="$HDC_OPTS $TIMESTAMP"

# Execute receive via PowerShell
log_info "Receiving from device: $DEVICE_ID:$REMOTE_PATH"
START_TIME=$(date +%s)

RESULT=$(powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$DEVICE_ID' file recv $HDC_OPTS '$REMOTE_PATH' '$WIN_STAGE_PATH'" 2>&1 | tr -d '\r')

EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    log_error "Receive failed"
    echo "$RESULT"
    exit 1
fi

log_info "Received to staging"

# Ensure local destination exists
if [[ "$LOCAL_PATH" == */ ]]; then
    # Destination is directory
    mkdir -p "$LOCAL_PATH"
else
    # Destination might be file or directory
    PARENT_DIR=$(dirname "$LOCAL_PATH")
    mkdir -p "$PARENT_DIR"
fi

# Copy from staging to WSL destination
log_info "Copying to WSL: $LOCAL_PATH"

# Find what was received
RECEIVED_ITEMS=$(ls -A "$STAGE_PATH")

if [[ -z "$RECEIVED_ITEMS" ]]; then
    log_error "No files received in staging"
    exit 1
fi

# Copy received items
for item in $STAGE_PATH/*; do
    if [[ -e "$item" ]]; then
        cp -r "$item" "$LOCAL_PATH"
    fi
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# Calculate size
SIZE=$(du -sh "$STAGE_PATH" | cut -f1)
log_ok "Received $SIZE (${ELAPSED}s)"

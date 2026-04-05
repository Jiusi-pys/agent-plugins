#!/bin/bash
# hdc-send.sh - Send files from WSL to KaihongOS device via Windows staging
#
# Flow: WSL path -> /mnt/c/tmp/hdc_staging -> hdc file send -> device
#
# Usage:
#   ./hdc-send.sh -t <device_id> <local_path> <remote_path> [options]
#
# Options:
#   -z    Compress transfer
#   -a    Preserve timestamp
#   -k    Keep staging files (don't clean up)
#
# Examples:
#   ./hdc-send.sh -t 7001005... ./build /data/local/tmp/build
#   ./hdc-send.sh -t 7001005... ./app.bin /system/bin/app -z

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
    echo "Usage: $0 -t <device_id> <local_path> <remote_path> [options]"
    echo ""
    echo "Options:"
    echo "  -t <id>   Device ID (required)"
    echo "  -z        Compress transfer"
    echo "  -a        Preserve timestamp"
    echo "  -k        Keep staging files"
    echo ""
    echo "Examples:"
    echo "  $0 -t 7001005... ./build /data/local/tmp/"
    echo "  $0 -t 7001005... ./lib/*.so /system/lib64/ -z"
    exit 1
}

# Parse arguments
DEVICE_ID=""
LOCAL_PATH=""
REMOTE_PATH=""
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
            if [[ -z "$LOCAL_PATH" ]]; then
                LOCAL_PATH="$1"
            elif [[ -z "$REMOTE_PATH" ]]; then
                REMOTE_PATH="$1"
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

if [[ -z "$LOCAL_PATH" || -z "$REMOTE_PATH" ]]; then
    log_error "Local and remote paths required"
    usage
fi

# Resolve local path
LOCAL_PATH=$(realpath "$LOCAL_PATH" 2>/dev/null || echo "$LOCAL_PATH")

if [[ ! -e "$LOCAL_PATH" ]]; then
    log_error "Local path not found: $LOCAL_PATH"
    exit 1
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

# Copy to staging
log_info "Copying to Windows staging..."
if [[ -d "$LOCAL_PATH" ]]; then
    # Directory - copy contents
    cp -r "$LOCAL_PATH" "$STAGE_PATH/"
    BASENAME=$(basename "$LOCAL_PATH")
    WIN_SRC="$WIN_STAGE_PATH\\$BASENAME"
else
    # Single file
    cp "$LOCAL_PATH" "$STAGE_PATH/"
    BASENAME=$(basename "$LOCAL_PATH")
    WIN_SRC="$WIN_STAGE_PATH\\$BASENAME"
fi

# Calculate size
SIZE=$(du -sh "$STAGE_PATH" | cut -f1)
log_info "Staged $SIZE"

# Build HDC command
HDC_OPTS=""
[[ -n "$COMPRESS" ]] && HDC_OPTS="$HDC_OPTS $COMPRESS"
[[ -n "$TIMESTAMP" ]] && HDC_OPTS="$HDC_OPTS $TIMESTAMP"

# Execute transfer via PowerShell
log_info "Transferring to device: $DEVICE_ID:$REMOTE_PATH"
START_TIME=$(date +%s)

RESULT=$(powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$DEVICE_ID' file send $HDC_OPTS '$WIN_SRC' '$REMOTE_PATH'" 2>&1 | tr -d '\r')

EXIT_CODE=$?
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

if [[ $EXIT_CODE -eq 0 ]]; then
    log_ok "Transfer complete (${ELAPSED}s)"
    echo "$RESULT"
else
    log_error "Transfer failed"
    echo "$RESULT"
    exit 1
fi

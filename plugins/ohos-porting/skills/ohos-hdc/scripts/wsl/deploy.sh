#!/bin/bash
# deploy.sh - Deploy build artifacts from WSL to KaihongOS device
#
# Flow: WSL build dir -> /mnt/c/tmp/hdc_staging -> hdc file send -> device
#
# Usage:
#   ./deploy.sh -t <device_id> [-s <source>] [-d <destination>] [options]
#
# Options:
#   -t <id>     Device ID (required, or set HDC_DEVICE env)
#   -s <path>   Source directory (default: ./build)
#   -d <path>   Device destination (default: /data/local/tmp)
#   -z          Compress transfer
#   -c          Clean destination before deploy
#   -p          Set executable permissions
#   -k          Keep staging files

set -e

# Configuration
HDC_PATH="${HDC_PATH:-hdc}"
STAGING_DIR="/mnt/c/tmp/hdc_staging"
WIN_STAGING_DIR="C:\\tmp\\hdc_staging"

# Defaults
SOURCE_DIR="./build"
DEST_DIR="/data/local/tmp"
COMPRESS=""
CLEAN=false
SET_PERMS=false
KEEP_STAGING=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[*]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[+]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[-]${NC} $1"; }
log_gray()  { echo -e "${GRAY}    $1${NC}"; }

usage() {
    echo "Usage: $0 -t <device_id> [options]"
    echo ""
    echo "Options:"
    echo "  -t <id>     Device ID (required)"
    echo "  -s <path>   Source directory (default: ./build)"
    echo "  -d <path>   Device destination (default: /data/local/tmp)"
    echo "  -z          Compress transfer"
    echo "  -c          Clean destination before deploy"
    echo "  -p          Set executable permissions"
    echo "  -k          Keep staging files"
    echo ""
    echo "Examples:"
    echo "  $0 -t 7001005... -s ./out/rk3588s -d /opt/ros2 -z -c -p"
    echo ""
    echo "Environment:"
    echo "  HDC_DEVICE  Default device ID if -t not specified"
    exit 1
}

# Parse arguments
DEVICE_ID="${HDC_DEVICE:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t) DEVICE_ID="$2"; shift 2 ;;
        -s) SOURCE_DIR="$2"; shift 2 ;;
        -d) DEST_DIR="$2"; shift 2 ;;
        -z) COMPRESS="-z"; shift ;;
        -c) CLEAN=true; shift ;;
        -p) SET_PERMS=true; shift ;;
        -k) KEEP_STAGING=true; shift ;;
        -h|--help) usage ;;
        *) shift ;;
    esac
done

# Validate
if [[ -z "$DEVICE_ID" ]]; then
    log_error "Device ID required (-t <id> or set HDC_DEVICE)"
    usage
fi

SOURCE_DIR=$(realpath "$SOURCE_DIR" 2>/dev/null || echo "$SOURCE_DIR")

if [[ ! -d "$SOURCE_DIR" ]]; then
    log_error "Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Verify device
log_info "Verifying device: $DEVICE_ID"
CHECK=$(powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$DEVICE_ID' shell echo OK" 2>&1 | tr -d '\r')

if [[ "$CHECK" != "OK" ]]; then
    log_error "Cannot connect to device"
    exit 1
fi
log_ok "Device connected"

# Calculate source size
SIZE=$(du -sh "$SOURCE_DIR" | cut -f1)
log_gray "Source: $SOURCE_DIR ($SIZE)"
log_gray "Destination: $DEVICE_ID:$DEST_DIR"

# Create staging directory
STAGE_NAME="deploy_$(date +%s)_$$"
STAGE_PATH="$STAGING_DIR/$STAGE_NAME"
WIN_STAGE_PATH="$WIN_STAGING_DIR\\$STAGE_NAME"

mkdir -p "$STAGE_PATH"

# Cleanup function
cleanup() {
    if [[ "$KEEP_STAGING" == false && -d "$STAGE_PATH" ]]; then
        rm -rf "$STAGE_PATH"
    fi
}
trap cleanup EXIT

# Copy to staging
log_info "Copying to Windows staging..."
cp -r "$SOURCE_DIR" "$STAGE_PATH/"
BASENAME=$(basename "$SOURCE_DIR")
WIN_SRC="$WIN_STAGE_PATH\\$BASENAME"

# Clean destination if requested
if [[ "$CLEAN" == true ]]; then
    log_info "Cleaning destination..."
    powershell.exe -NoProfile -NonInteractive -Command \
        "$HDC_PATH -t '$DEVICE_ID' shell 'rm -rf $DEST_DIR/*'" 2>&1 | tr -d '\r' > /dev/null
fi

# Ensure destination exists
powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$DEVICE_ID' shell 'mkdir -p $DEST_DIR'" 2>&1 | tr -d '\r' > /dev/null

# Transfer
log_info "Transferring to device..."
START_TIME=$(date +%s)

HDC_OPTS=""
[[ -n "$COMPRESS" ]] && HDC_OPTS="$COMPRESS"

RESULT=$(powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$DEVICE_ID' file send $HDC_OPTS '$WIN_SRC' '$DEST_DIR'" 2>&1 | tr -d '\r')

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

if [[ $? -ne 0 ]]; then
    log_error "Transfer failed"
    echo "$RESULT"
    exit 1
fi

log_ok "Transfer complete (${ELAPSED}s)"

# Set permissions if requested
if [[ "$SET_PERMS" == true ]]; then
    log_info "Setting permissions..."
    
    # Executables in bin/
    powershell.exe -NoProfile -NonInteractive -Command \
        "$HDC_PATH -t '$DEVICE_ID' shell 'find $DEST_DIR -path \"*/bin/*\" -type f -exec chmod 755 {} \\;'" \
        2>&1 | tr -d '\r' > /dev/null
    
    # Shell scripts
    powershell.exe -NoProfile -NonInteractive -Command \
        "$HDC_PATH -t '$DEVICE_ID' shell 'find $DEST_DIR -name \"*.sh\" -exec chmod 755 {} \\;'" \
        2>&1 | tr -d '\r' > /dev/null
    
    # Shared libraries
    powershell.exe -NoProfile -NonInteractive -Command \
        "$HDC_PATH -t '$DEVICE_ID' shell 'find $DEST_DIR -name \"*.so*\" -exec chmod 755 {} \\;'" \
        2>&1 | tr -d '\r' > /dev/null
    
    log_ok "Permissions set"
fi

log_ok "Deployed to $DEVICE_ID:$DEST_DIR"

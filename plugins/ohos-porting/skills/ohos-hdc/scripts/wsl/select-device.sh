#!/bin/bash
# select-device.sh - Interactive HDC device selector for WSL
#
# Usage:
#   DEVICE_ID=$(./select-device.sh)
#   DEVICE_ID=$(./select-device.sh --hint USB)
#   DEVICE_ID=$(./select-device.sh --first)
#
# Options:
#   --hint <pattern>  Filter devices by pattern (USB, TCP, serial prefix)
#   --first           Auto-select first available device
#   --export          Export HDC_DEVICE environment variable hint

set -e

# Configuration
HDC_PATH="${HDC_PATH:-hdc}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
HINT=""
FIRST=false
EXPORT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --hint)
            HINT="$2"
            shift 2
            ;;
        --first)
            FIRST=true
            shift
            ;;
        --export)
            EXPORT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --hint <pattern>  Filter by pattern (USB, TCP, etc.)"
            echo "  --first           Auto-select first device"
            echo "  --export          Print export command"
            echo ""
            echo "Examples:"
            echo "  DEVICE_ID=\$($0)"
            echo "  DEVICE_ID=\$($0 --hint USB --first)"
            echo "  eval \$($0 --export)"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Get device list from Windows HDC
RAW=$(powershell.exe -NoProfile -NonInteractive -Command "$HDC_PATH list targets -v" 2>&1 | tr -d '\r')

if [[ "$RAW" == *"Empty"* || -z "$RAW" ]]; then
    echo -e "${RED}No devices connected${NC}" >&2
    echo -e "Check USB connection and run: powershell.exe -Command 'hdc kill -r'" >&2
    exit 1
fi

# Parse devices into array
declare -a DEVICES
declare -a DEVICE_IDS
declare -a DEVICE_TYPES

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    
    # Parse: <id> <state> <type>
    read -r id state type <<< "$line"
    [[ -z "$id" ]] && continue
    
    # Apply hint filter
    if [[ -n "$HINT" && "$line" != *"$HINT"* ]]; then
        continue
    fi
    
    DEVICES+=("$line")
    DEVICE_IDS+=("$id")
    DEVICE_TYPES+=("${type:-Unknown}")
done <<< "$RAW"

if [[ ${#DEVICES[@]} -eq 0 ]]; then
    if [[ -n "$HINT" ]]; then
        echo -e "${YELLOW}No devices match hint '$HINT'${NC}" >&2
    else
        echo -e "${RED}No devices found${NC}" >&2
    fi
    exit 1
fi

# Select device
SELECTED_ID=""
SELECTED_TYPE=""

if [[ ${#DEVICES[@]} -eq 1 || "$FIRST" == true ]]; then
    SELECTED_ID="${DEVICE_IDS[0]}"
    SELECTED_TYPE="${DEVICE_TYPES[0]}"
    
    if [[ "$FIRST" != true ]]; then
        echo -e "${CYAN}Single device:${NC} $SELECTED_ID [$SELECTED_TYPE]" >&2
    fi
else
    # Interactive selection
    echo -e "\n${CYAN}Connected devices:${NC}" >&2
    for i in "${!DEVICES[@]}"; do
        case "${DEVICE_TYPES[$i]}" in
            USB)  color="${GREEN}" ;;
            TCP)  color="${YELLOW}" ;;
            *)    color="${NC}" ;;
        esac
        echo -e "  [$i] ${DEVICE_IDS[$i]} ${color}[${DEVICE_TYPES[$i]}]${NC}" >&2
    done
    
    echo -n -e "\nSelect device [0-$((${#DEVICES[@]}-1))]: " >&2
    read -r choice
    
    if [[ "$choice" =~ ^[0-9]+$ && "$choice" -lt ${#DEVICES[@]} ]]; then
        SELECTED_ID="${DEVICE_IDS[$choice]}"
        SELECTED_TYPE="${DEVICE_TYPES[$choice]}"
    else
        echo -e "${RED}Invalid selection${NC}" >&2
        exit 1
    fi
fi

# Verify device
echo -n -e "Verifying $SELECTED_ID..." >&2
CHECK=$(powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$SELECTED_ID' shell echo OK" 2>&1 | tr -d '\r')

if [[ "$CHECK" == "OK" ]]; then
    echo -e " ${GREEN}OK${NC}" >&2
else
    echo -e " ${YELLOW}Warning: may not be responsive${NC}" >&2
fi

# Output
if [[ "$EXPORT" == true ]]; then
    echo "export HDC_DEVICE='$SELECTED_ID'"
else
    echo "$SELECTED_ID"
fi

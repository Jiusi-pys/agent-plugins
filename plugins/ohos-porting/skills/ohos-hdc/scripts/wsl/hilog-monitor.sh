#!/bin/bash
# hilog-monitor.sh - Monitor KaihongOS device logs from WSL
#
# Usage:
#   ./hilog-monitor.sh -t <device_id> [options]
#
# Options:
#   -t <id>       Device ID (required)
#   -f <pattern>  Filter regex pattern
#   -l <level>    Log level: D/I/W/E/F
#   -g <tag>      Filter by tag
#   -o <file>     Output to file
#   -d <seconds>  Duration (0 = indefinite)
#   -c            Clear logs before starting

set -e

# Configuration
HDC_PATH="${HDC_PATH:-hdc}"

# Defaults
DEVICE_ID="${HDC_DEVICE:-}"
FILTER=""
LEVEL=""
TAG=""
OUTPUT=""
DURATION=0
CLEAR=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
NC='\033[0m'

usage() {
    echo "Usage: $0 -t <device_id> [options]"
    echo ""
    echo "Options:"
    echo "  -t <id>       Device ID (required)"
    echo "  -f <pattern>  Filter regex pattern"
    echo "  -l <level>    Log level: D(ebug)/I(nfo)/W(arn)/E(rror)/F(atal)"
    echo "  -g <tag>      Filter by tag"
    echo "  -o <file>     Output to file"
    echo "  -d <seconds>  Duration (0 = indefinite)"
    echo "  -c            Clear logs before starting"
    echo ""
    echo "Examples:"
    echo "  $0 -t 7001005... -f 'dsoftbus|rmw' -l E"
    echo "  $0 -t 7001005... -g ROS2 -o ./ros2.log -d 60 -c"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t) DEVICE_ID="$2"; shift 2 ;;
        -f) FILTER="$2"; shift 2 ;;
        -l) LEVEL="$2"; shift 2 ;;
        -g) TAG="$2"; shift 2 ;;
        -o) OUTPUT="$2"; shift 2 ;;
        -d) DURATION="$2"; shift 2 ;;
        -c) CLEAR=true; shift ;;
        -h|--help) usage ;;
        *) shift ;;
    esac
done

# Validate
if [[ -z "$DEVICE_ID" ]]; then
    echo -e "${RED}Device ID required${NC}"
    usage
fi

# Verify device
echo -e "${CYAN}[*]${NC} Connecting to $DEVICE_ID..."
CHECK=$(powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$DEVICE_ID' shell echo OK" 2>&1 | tr -d '\r')

if [[ "$CHECK" != "OK" ]]; then
    echo -e "${RED}Cannot connect to device${NC}"
    exit 1
fi

# Clear logs if requested
if [[ "$CLEAR" == true ]]; then
    echo -e "${YELLOW}[*]${NC} Clearing device logs..."
    powershell.exe -NoProfile -NonInteractive -Command \
        "$HDC_PATH -t '$DEVICE_ID' shell 'hilog -r'" 2>&1 | tr -d '\r' > /dev/null
fi

# Build grep pattern
PATTERNS=()
[[ -n "$FILTER" ]] && PATTERNS+=("$FILTER")
[[ -n "$LEVEL" ]] && PATTERNS+=("\\s${LEVEL}/")
[[ -n "$TAG" ]] && PATTERNS+=("\\s${TAG}\\s|\\[${TAG}\\]")

if [[ ${#PATTERNS[@]} -gt 0 ]]; then
    GREP_PATTERN=$(IFS='|'; echo "${PATTERNS[*]}")
else
    GREP_PATTERN="."
fi

# Display config
echo -e "${CYAN}[*]${NC} Starting hilog monitor"
echo -e "${GRAY}    Device:  $DEVICE_ID${NC}"
echo -e "${GRAY}    Filter:  $GREP_PATTERN${NC}"
[[ -n "$OUTPUT" ]] && echo -e "${GRAY}    Output:  $OUTPUT${NC}"
[[ "$DURATION" -gt 0 ]] && echo -e "${GRAY}    Duration: ${DURATION}s${NC}"
echo -e "${YELLOW}    Press Ctrl+C to stop${NC}"
echo ""

# Prepare output file
if [[ -n "$OUTPUT" ]]; then
    mkdir -p "$(dirname "$OUTPUT")" 2>/dev/null || true
    : > "$OUTPUT"
fi

# Colorize function
colorize_line() {
    local line="$1"
    local color="$NC"
    
    if [[ "$line" =~ [[:space:]]F/ ]]; then
        color="$MAGENTA"
    elif [[ "$line" =~ [[:space:]]E/ ]]; then
        color="$RED"
    elif [[ "$line" =~ [[:space:]]W/ ]]; then
        color="$YELLOW"
    elif [[ "$line" =~ [[:space:]]I/ ]]; then
        color="$NC"
    elif [[ "$line" =~ [[:space:]]D/ ]]; then
        color="$GRAY"
    fi
    
    echo -e "${color}${line}${NC}"
}

# Start monitoring
START_TIME=$(date +%s)
LINE_COUNT=0
MATCH_COUNT=0

# Trap for clean exit
cleanup() {
    ELAPSED=$(( $(date +%s) - START_TIME ))
    echo ""
    echo -e "${GREEN}[+]${NC} Processed $LINE_COUNT lines, matched $MATCH_COUNT (${ELAPSED}s)"
    [[ -n "$OUTPUT" ]] && echo -e "${GRAY}    Saved to: $OUTPUT${NC}"
}
trap cleanup EXIT INT TERM

# Main loop
powershell.exe -NoProfile -NonInteractive -Command \
    "$HDC_PATH -t '$DEVICE_ID' hilog" 2>&1 | tr -d '\r' | while IFS= read -r line; do
    
    LINE_COUNT=$((LINE_COUNT + 1))
    
    # Check duration
    if [[ "$DURATION" -gt 0 ]]; then
        ELAPSED=$(( $(date +%s) - START_TIME ))
        if [[ "$ELAPSED" -ge "$DURATION" ]]; then
            break
        fi
    fi
    
    # Apply filter
    if echo "$line" | grep -qE "$GREP_PATTERN"; then
        MATCH_COUNT=$((MATCH_COUNT + 1))
        
        # Colorize and print
        colorize_line "$line"
        
        # Save to file
        if [[ -n "$OUTPUT" ]]; then
            echo "$line" >> "$OUTPUT"
        fi
    fi
done

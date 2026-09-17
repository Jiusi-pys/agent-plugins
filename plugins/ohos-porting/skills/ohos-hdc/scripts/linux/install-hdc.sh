#!/bin/bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  install-hdc.sh [command-line-tools-root]

This script does not download or install HDC. It verifies that:
  1. the host is Linux
  2. hdc_std or hdc is already available on PATH

If you pass a command-line-tools root, it also prints a PATH export hint for
common HDC locations inside that bundle.
EOF
}

resolve_hdc() {
  if command -v hdc_std >/dev/null 2>&1; then
    command -v hdc_std
  elif command -v hdc >/dev/null 2>&1; then
    command -v hdc
  else
    return 1
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[FAIL] Linux host required" >&2
  exit 1
fi

COMMAND_LINE_TOOLS_ROOT="${1:-${OHOS_COMMAND_LINE_TOOLS:-}}"

if HDC_PATH="$(resolve_hdc)"; then
  echo "[PASS] HDC available: $HDC_PATH"
  "$HDC_PATH" version || true
  exit 0
fi

echo "[FAIL] Neither hdc_std nor hdc is available on PATH" >&2

if [[ -n "$COMMAND_LINE_TOOLS_ROOT" ]]; then
  echo
  echo "Common locations to check under $COMMAND_LINE_TOOLS_ROOT:"
  echo "  $COMMAND_LINE_TOOLS_ROOT/toolchains"
  echo "  $COMMAND_LINE_TOOLS_ROOT/sdk/toolchains"
  echo "  $COMMAND_LINE_TOOLS_ROOT/sdk/native/toolchains"
  echo
  echo "After locating the binary, add its directory to PATH and re-run this script."
fi

exit 1

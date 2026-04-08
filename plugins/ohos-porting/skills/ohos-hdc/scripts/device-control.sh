#!/bin/bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Device Control Wrapper - Linux-only interface for OHOS HDC

Usage:
  device-control.sh <hdc-args...>

Examples:
  device-control.sh list targets
  device-control.sh -t <device_id> shell "ls -la /data/local/tmp"
  device-control.sh -t <device_id> file send ./artifact /data/local/tmp/
  device-control.sh -t <device_id> hilog
EOF
}

resolve_hdc() {
  if command -v hdc_std >/dev/null 2>&1; then
    echo "hdc_std"
  elif command -v hdc >/dev/null 2>&1; then
    echo "hdc"
  else
    echo "ERROR: neither hdc_std nor hdc is available on PATH" >&2
    exit 1
  fi
}

main() {
  if [[ $# -eq 0 ]]; then
    show_help
    exit 0
  fi

  local hdc_cmd
  hdc_cmd="$(resolve_hdc)"
  exec "$hdc_cmd" "$@"
}

main "$@"

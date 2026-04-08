#!/bin/bash
set -euo pipefail

resolve_hdc() {
  if command -v hdc_std >/dev/null 2>&1; then
    echo "hdc_std"
  elif command -v hdc >/dev/null 2>&1; then
    echo "hdc"
  else
    return 1
  fi
}

show_help() {
  cat <<'EOF'
HDC Linux resolver

Usage:
  hdc-auto.sh [--platform|--hdc-path|--help]
  hdc-auto.sh <hdc-args...>
EOF
}

case "${1:-}" in
  --platform)
    echo "linux"
    exit 0
    ;;
  --hdc-path)
    resolve_hdc
    exit 0
    ;;
  -h|--help)
    show_help
    exit 0
    ;;
esac

hdc_cmd="$(resolve_hdc)" || {
  echo "ERROR: neither hdc_std nor hdc is available on PATH" >&2
  exit 1
}

exec "$hdc_cmd" "$@"

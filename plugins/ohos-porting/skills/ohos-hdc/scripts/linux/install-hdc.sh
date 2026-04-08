#!/bin/bash
set -euo pipefail

cat <<'EOF'
Install HDC on Linux by extracting the OpenHarmony command-line-tools bundle.

Expected result:
  hdc_std or hdc becomes available on PATH.

Suggested steps:
  1. Extract the Linux command-line-tools package.
  2. Add the tool binary directory to PATH.
  3. Re-open the shell and run: hdc_std version || hdc version
EOF

#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
plugin_dir=$(cd "$script_dir/../.." && pwd)
work_dir=/tmp/expected

rm -rf "$work_dir"
cp -R "$script_dir/input" "$work_dir"

python3 "$plugin_dir/skills/codebase-frontmatter-summary/scripts/scan_and_summarize.py" \
  --root "$work_dir" \
  --backend heuristic \
  --write

diff -ru "$script_dir/expected" "$work_dir"

echo "Fixture output matches expected."

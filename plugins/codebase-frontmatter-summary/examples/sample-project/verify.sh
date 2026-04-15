#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
plugin_dir=$(cd "$script_dir/../.." && pwd)
work_dir=/tmp/repo-indexer-fixture

rm -rf "$work_dir"
cp -R "$script_dir/input" "$work_dir"

python3 "$plugin_dir/tools/repo_indexer.py" refresh \
  --root "$work_dir" \
  --backend heuristic

python3 "$plugin_dir/tools/repo_indexer.py" doctor --root "$work_dir"

python3 - "$work_dir" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
expected = [
    root / ".scanmeta" / "files" / "app.py.json",
    root / ".scanmeta" / "dirs" / "root.json",
    root / ".scanmeta" / "generated" / "repo-map.md",
    root / "AGENTS.md",
    root / "CLAUDE.md",
    root / ".claude" / "rules" / "reading-policy.md",
    root / ".agents" / "skills" / "repo-index" / "SKILL.md",
]
missing = [str(path) for path in expected if not path.exists()]
if missing:
    raise SystemExit("missing expected outputs:\n" + "\n".join(missing))
print("Fixture output looks complete.")
PY

#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = PLUGIN_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from repo_indexer.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

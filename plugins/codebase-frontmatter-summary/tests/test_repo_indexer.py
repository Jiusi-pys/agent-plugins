from __future__ import annotations

import contextlib
import io
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
import json

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PLUGIN_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from repo_indexer.cli import _doctor, run_index
from repo_indexer.config import IndexerConfig
from repo_indexer.read_planner import plan_read


class RepoIndexerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "fixture"
        shutil.copytree(PLUGIN_ROOT / "examples" / "sample-project" / "input", self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _refresh(self, **kwargs):
        config = IndexerConfig(root=self.root, backend="heuristic", write=True, **kwargs)
        return run_index(config)

    def test_refresh_writes_sidecars_and_guides(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            summary = self._refresh()
        self.assertTrue((self.root / ".scanmeta" / "files" / "app.py.json").exists())
        self.assertTrue((self.root / ".scanmeta" / "dirs" / "root.json").exists())
        self.assertTrue((self.root / ".scanmeta" / "generated" / "AGENTS.generated.md").exists())
        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertTrue((self.root / "CLAUDE.md").exists())
        self.assertTrue((self.root / ".claude" / "rules" / "reading-policy.md").exists())
        self.assertIn("scan-manifest.json", summary["manifest_path"])
        root_dir = json.loads((self.root / ".scanmeta" / "dirs" / "root.json").read_text(encoding="utf-8"))
        self.assertIn("frontmatter_summary", root_dir)
        self.assertIn("app.py", root_dir["frontmatter_summary"])
        self.assertIn("Summarizing files: 0/7", stderr.getvalue())
        self.assertIn("Summarizing files: 7/7 complete", stderr.getvalue())

    def test_incremental_change_and_removed_cleanup(self) -> None:
        self._refresh()
        (self.root / "notes.txt").write_text("Updated note for incremental test.\n", encoding="utf-8")
        (self.root / "web" / "index.html").unlink()
        summary = self._refresh()
        self.assertIn("notes.txt", summary["changed_files"])
        self.assertIn("web/index.html", summary["removed_files"])
        self.assertFalse((self.root / ".scanmeta" / "files" / "web__index.html.json").exists())

    def test_directory_dirty_propagation_updates_parent_fingerprint(self) -> None:
        self._refresh()
        db_path = self.root / ".scanmeta" / "state" / "index.sqlite"
        before = _dir_fingerprint(db_path, "src")
        before_root = _dir_fingerprint(db_path, ".")
        helpers = self.root / "src" / "helpers.ts"
        helpers.write_text(helpers.read_text(encoding="utf-8") + "\nexport const EXTRA_VALUE = 3;\n", encoding="utf-8")
        self._refresh()
        after = _dir_fingerprint(db_path, "src")
        after_root = _dir_fingerprint(db_path, ".")
        self.assertNotEqual(before, after)
        self.assertNotEqual(before_root, after_root)

    def test_read_planner_escalates_for_patch_tasks(self) -> None:
        plan = plan_read(
            "patch exact line-level bug in runtime scheduler",
            [{"path": "src/runtime", "role": "implementation directory", "topics": ["runtime"], "key_files": ["src/runtime/runtime.c"]}],
            [{"path": "src/runtime/runtime.c", "summary": "Runtime scheduler.", "role": "core_impl", "tags": ["runtime"], "keywords": ["scheduler"], "exports": ["runtime_init"], "importance": "high", "token_estimate": 3000}],
        )
        self.assertIn("read_section_indexes", plan["steps"])
        self.assertIn("read_full_files", plan["steps"])
        self.assertTrue(plan["full_read_required"])

    def test_doctor_detects_corrupted_metadata(self) -> None:
        self._refresh()
        self.assertEqual(_doctor(self.root), 0)
        corrupt = self.root / ".scanmeta" / "files" / "app.py.json"
        corrupt.write_text('{"path": 1}\n', encoding="utf-8")
        self.assertEqual(_doctor(self.root), 1)


def _dir_fingerprint(db_path: Path, path: str) -> str:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT child_fingerprint FROM dirs WHERE path = ?", (path,)).fetchone()
    return row[0]


if __name__ == "__main__":
    unittest.main()

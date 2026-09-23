"""Contract tests for the Claude Code plugin and bundled exporter helpers."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins" / "weread-exporter"


def load_exporter():
    spec = importlib.util.spec_from_file_location(
        "weread_exporter", PLUGIN / "scripts" / "export_precise.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PluginContractTests(unittest.TestCase):
    def test_claude_manifest_declares_marketplace_ready_metadata(self):
        manifest = json.loads(
            (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "weread-exporter")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["repository"], "https://github.com/Jiusi-pys/weread-exporter")
        self.assertIn("weread-export", {path.name for path in (PLUGIN / "skills").iterdir()})
        self.assertFalse((PLUGIN / "plugin.json").exists())
        self.assertFalse((PLUGIN / ".codex-plugin" / "plugin.json").exists())

    def test_claude_marketplace_exposes_plugin_from_repo_relative_path(self):
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        entry = next(item for item in marketplace["plugins"] if item["name"] == "weread-exporter")
        self.assertEqual(entry["source"], "./plugins/weread-exporter")
        self.assertEqual(
            entry["description"],
            "Export personally authorized WeRead books to Markdown with inline illustrations.",
        )

    def test_exporter_pure_helpers_keep_page_order_and_image_names(self):
        exporter = load_exporter()
        self.assertEqual(exporter.split_spread([]), [[]])
        self.assertEqual(exporter.img_filename("https://example.test/figure.png", 3, 2), "ch0003_img02.png")
        body, images = exporter.render_chapter_md(
            "第一章",
            [
                {"type": "text", "text": "第一行"},
                {"type": "text", "text": "第二行。"},
                {"type": "img", "src": "https://example.test/figure.jpg"},
                {"type": "text", "text": "第三段。"},
            ],
            1,
        )
        self.assertIn("第一行第二行。", body)
        self.assertIn("![图](images/ch0001_img01.jpg)", body)
        self.assertEqual(images[0]["file"], "ch0001_img01.jpg")


if __name__ == "__main__":
    unittest.main()

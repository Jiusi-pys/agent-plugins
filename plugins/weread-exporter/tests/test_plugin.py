"""Contract tests for the dual-marketplace package and exporter helpers."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins" / "weread-exporter"


def load_exporter():
    spec = importlib.util.spec_from_file_location("weread_exporter", PLUGIN / "scripts" / "export_precise.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PluginContractTests(unittest.TestCase):
    def test_codex_and_claude_manifests_are_present(self):
        portable = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual({portable["name"], codex["name"], claude["name"]}, {"weread-exporter"})
        self.assertTrue((PLUGIN / "skills" / "weread-export" / "SKILL.md").is_file())

    def test_codex_marketplace_exposes_repo_relative_plugin(self):
        marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        entry = next(item for item in marketplace["plugins"] if item["name"] == "weread-exporter")
        self.assertEqual(entry["source"]["path"], "./plugins/weread-exporter")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")

    def test_exporter_pure_helpers_keep_page_order_and_image_names(self):
        exporter = load_exporter()
        self.assertEqual(exporter.split_spread([]), [[]])
        self.assertEqual(exporter.img_filename("https://example.test/figure.png", 3, 2), "ch0003_img02.png")
        body, images = exporter.render_chapter_md("第一章", [{"type": "text", "text": "第一行"}, {"type": "text", "text": "第二行。"}, {"type": "img", "src": "https://example.test/figure.jpg"}], 1)
        self.assertIn("第一行第二行。", body)
        self.assertIn("![图](images/ch0001_img01.jpg)", body)
        self.assertEqual(images[0]["file"], "ch0001_img01.jpg")

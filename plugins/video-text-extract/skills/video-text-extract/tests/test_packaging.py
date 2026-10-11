import json
from pathlib import Path
import re
import unittest

SKILL = Path(__file__).resolve().parents[1]
PLUGIN = SKILL.parents[1]


class PackagingTests(unittest.TestCase):
    def test_manifests_agree_and_discover_the_skill(self):
        portable = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))
        compatibility = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        for key in ['name', 'version', 'description', 'author', 'license']:
            self.assertEqual(portable[key], compatibility[key])
        interface = portable['extensions']['com.openai']['interface']
        self.assertEqual(interface, compatibility['interface'])
        self.assertLessEqual(len(interface['shortDescription']), 30)
        self.assertNotIn('skills', portable)
        skills = PLUGIN / compatibility['skills']
        self.assertTrue((skills / portable['name'] / 'SKILL.md').is_file())

    def test_documentation_and_scripts_are_contained_and_exist(self):
        for document in [SKILL / 'SKILL.md', SKILL / 'references/runtime.md']:
            source = document.read_text(encoding='utf-8')
            for reference in re.findall(r'\]\((references/[^)]+)\)', source):
                path = document.parent / reference
                self.assertTrue(path.is_file(), reference)
        for relative in ['scripts/video_extract.py', 'scripts/video_title.mjs',
                         'agents/openai.yaml', 'references/final-review.md']:
            self.assertTrue((SKILL / relative).is_file(), relative)
        for path in SKILL.rglob('*'):
            if path.is_file() and path.suffix in {'.md', '.py', '.mjs', '.yaml'}:
                self.assertNotIn('C:\\Users\\17715', path.read_text(encoding='utf-8-sig'), str(path))

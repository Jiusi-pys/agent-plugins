import json
from pathlib import Path
import re
import unittest

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parent.parent


class Packaging(unittest.TestCase):
    def test_chinese_translation_paragraphs_use_two_em_first_line_indent(self):
        translation = (PLUGIN / 'skills/book-translate/references/translation.md').read_text(encoding='utf-8')
        self.assertIn('text-indent: 2em', translation)
        self.assertIn('不得把空格或制表符插入译文文本', translation)

    def test_portable_and_compatibility_manifests_agree(self):
        main = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))
        overlay = json.loads((PLUGIN / '.codex-plugin' / 'plugin.json').read_text(encoding='utf-8'))
        for field in ('name', 'version', 'description', 'author'):
            self.assertEqual(main[field], overlay[field])
        self.assertEqual(main['extensions']['com.openai']['interface'], overlay['interface'])
        self.assertEqual(main['name'], PLUGIN.name)
        self.assertRegex(main['version'], r'^\d+\.\d+\.\d+(?:\+[\w.-]+)?$')
        self.assertFalse({'dependencies', 'mcpServers', 'skills', 'apps', 'interface'} & main.keys())

    def test_internal_reviewer_is_packaged_with_the_translator(self):
        skills = {p.parent.name for p in (PLUGIN / 'skills').glob('*/SKILL.md')}
        self.assertEqual(skills, {'book-translate', 'classical-translate', 'translation-review'})
        policy = (PLUGIN / 'skills/translation-review/agents/openai.yaml').read_text(encoding='utf-8')
        self.assertIn('allow_implicit_invocation: false', policy)
        contract = json.loads((PLUGIN / 'contracts/epub-editor.json').read_text(encoding='utf-8'))
        self.assertEqual(contract['plugin'], 'epub-editor')
        self.assertFalse((PLUGIN / 'plugins' / 'agentic-review').exists())

    def test_all_packaged_relative_markdown_links_resolve(self):
        for path in PLUGIN.rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                if '://' in link or link.startswith('#'):
                    continue
                target = (path.parent / link.split('#')[0]).resolve()
                self.assertTrue(target.is_relative_to(PLUGIN), (path, link))
                self.assertTrue(target.is_file(), (path, link))

    @unittest.skipUnless((REPO / '.agents/plugins/marketplace.json').exists(), 'catalog is not part of a standalone archive')
    def test_catalog_integrates_only_one_new_plugin(self):
        catalog = json.loads((REPO / '.agents/plugins/marketplace.json').read_text(encoding='utf-8'))
        names = [entry['name'] for entry in catalog['plugins']]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn('book-translator', names)
        self.assertNotIn('translation-review', names)
        self.assertNotIn('translator-review', names)
        entry = next(e for e in catalog['plugins'] if e['name'] == 'book-translator')
        self.assertEqual((REPO / entry['source']['path']).resolve(), PLUGIN)
        self.assertEqual(entry['policy']['installation'], 'AVAILABLE')


if __name__ == '__main__':
    unittest.main()

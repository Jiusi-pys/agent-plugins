import json
from pathlib import Path
import re
import unittest


PLUGIN = Path(__file__).resolve().parents[1]
FORMATS = ('TXT', 'EPUB', 'MOBI', 'HTML', 'Markdown', 'AZW3', 'DOCX', 'RTF', 'FB2', 'ODT')
ORIGINAL_PROMPT = (
    '帮我查看并按我的要求修改 EPUB 元数据，保留未指定字段。需要时统计字数、修复目录，'
    '并把正文注释整理为点击标记后弹窗显示翻译内容，避免阅读时跳转到注释页。封面只使用我提供的图片。'
)


class Packaging(unittest.TestCase):
    def manifest(self):
        return json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))

    def test_portable_and_compatibility_manifests_agree(self):
        portable = self.manifest()
        compat = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        for field in ('name', 'version', 'description', 'author'):
            self.assertEqual(portable[field], compat[field])
        self.assertEqual(portable['extensions']['com.openai']['interface'], compat['interface'])
        self.assertEqual(portable['name'], 'epub-editor')
        self.assertEqual(portable['version'], '0.2.2')
        self.assertEqual(compat['skills'], './skills/')
        self.assertFalse({'skills', 'interface', 'tools', 'onboarding', 'apps', 'mcpServers'} & portable.keys())

    def test_interface_preserves_identity_and_prompt_while_exposing_conversion(self):
        interface = self.manifest()['extensions']['com.openai']['interface']
        self.assertEqual(interface['displayName'], 'EPUB 编排')
        self.assertEqual(interface['brandColor'], '#167C72')
        self.assertLessEqual(len(interface['shortDescription']), 30)
        self.assertIsInstance(interface['defaultPrompt'], str)
        self.assertTrue(interface['defaultPrompt'].startswith(ORIGINAL_PROMPT))
        self.assertIn('转换', interface['defaultPrompt'][len(ORIGINAL_PROMPT):])
        self.assertIn('不承诺无损', interface['defaultPrompt'])
        for name in FORMATS:
            self.assertIn(name, self.manifest()['description'])

    def test_skill_names_and_descriptions_match_directories(self):
        paths = list((PLUGIN / 'skills').glob('*/SKILL.md'))
        self.assertEqual({p.parent.name for p in paths}, {'epub-edit', 'ebook-convert'})
        for path in paths:
            text = path.read_text(encoding='utf-8')
            frontmatter = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
            self.assertIsNotNone(frontmatter, path)
            fields = dict(re.findall(r'^([a-z_-]+):\s*(.+)$', frontmatter.group(1), re.M))
            self.assertEqual(fields['name'], path.parent.name)
            self.assertTrue(fields['description'])
            self.assertLessEqual(len(fields['description']), 1024)

    def test_relative_markdown_links_stay_in_package_and_resolve(self):
        for path in PLUGIN.rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                if '://' in link or link.startswith('#'):
                    continue
                target = (path.parent / link.split('#')[0]).resolve()
                self.assertTrue(target.is_relative_to(PLUGIN), (path, link))
                self.assertTrue(target.is_file(), (path, link))

    def test_manifest_assets_are_packaged_relative_paths(self):
        interface = self.manifest()['extensions']['com.openai']['interface']
        for field in ('composerIcon', 'logo', 'logoDark'):
            value = interface[field]
            self.assertTrue(value.startswith('./assets/'))
            target = (PLUGIN / value).resolve()
            self.assertTrue(target.is_relative_to(PLUGIN))
            self.assertTrue(target.is_file())

    def test_conversion_reference_lists_import_and_export_for_all_ten_formats(self):
        reference = PLUGIN / 'skills/ebook-convert/references/formats.md'
        self.assertTrue(reference.is_file())
        content = reference.read_text(encoding='utf-8')
        rows = [line.split('|')[1:-1] for line in content.splitlines() if line.startswith('|')]
        for name in FORMATS:
            row = next((r for r in rows if r[0].strip() == name), None)
            self.assertIsNotNone(row, name)
            self.assertGreaterEqual(len(row), 4, name)
            self.assertNotEqual(row[2].strip(), '', name)
            self.assertNotEqual(row[3].strip(), '', name)

    def test_rtf_documentation_declares_calibre_input_and_pandoc_output(self):
        content = (PLUGIN / 'skills/ebook-convert/references/formats.md').read_text(encoding='utf-8')
        row = next(line.split('|')[1:-1] for line in content.splitlines() if line.startswith('| RTF |'))
        self.assertIn('Calibre', row[2])
        self.assertIn('Pandoc', row[3])

    def test_markdown_documentation_declares_pandoc_input_and_output(self):
        content = (PLUGIN / 'skills/ebook-convert/references/formats.md').read_text(encoding='utf-8')
        row = next(line.split('|')[1:-1] for line in content.splitlines() if line.startswith('| Markdown |'))
        self.assertIn('Pandoc', row[2])
        self.assertNotIn('Calibre', row[2])
        self.assertIn('--to=epub3', row[2])
        self.assertIn('Pandoc', row[3])


if __name__ == '__main__':
    unittest.main()

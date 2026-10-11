import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / 'scripts'))
from dependencies import call_editor, resolve_editor, verify_editor

LAYOUT_HELPER = 'scripts/ebook_reading_layout.py'


class EditorCompatibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='editor version ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in ('skills/epub-edit/SKILL.md', 'scripts/epub_editor.py', 'scripts/epub_metadata.py'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture', encoding='utf-8')

    def resolve(self, version, compat_only=False, help_flags='--metadata --inspect --recount'):
        manifest = self.root / ('.codex-plugin/plugin.json' if compat_only else 'plugin.json')
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({'name': 'epub-editor', 'version': version}), encoding='utf-8')
        with patch('dependencies.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = help_flags
            run.return_value.stderr = ''
            return resolve_editor(self.root)

    def call(self, lock, inspect=False):
        source = self.root / 'source.epub'
        source.write_bytes(b'fixture')
        output = self.root / 'output.epub'
        metadata = self.root / 'metadata.json'
        metadata.write_text('{}', encoding='utf-8')
        if not inspect:
            output.write_bytes(b'fixture output')
        with patch('dependencies.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = json.dumps({'metadata': {}} if inspect else {'issues': []})
            run.return_value.stderr = ''
            call_editor(lock, source, None if inspect else output, None if inspect else metadata)
            return run.call_args.args[0]

    def test_original_01_and_new_02_cli_versions_remain_accepted(self):
        for version in ('0.1.0', '0.1.1+codex.20260927', '0.2.0', '0.2.7+codex.20261011'):
            with self.subTest(version=version):
                lock = self.resolve(version)
                self.assertEqual(lock['version'], version)
                self.assertEqual(lock['adapter'], 'epub-editor-cli-v1')

    def test_new_02_compatibility_manifest_fallback_is_accepted(self):
        lock = self.resolve('0.2.0', compat_only=True)
        self.assertIn('.codex-plugin/plugin.json', lock['files'])

    def test_untested_version_families_and_prereleases_remain_rejected(self):
        for version in ('0.0.9', '0.3.0', '1.2.0', '0.2.0-beta', '0.2', '0.2.0+invalid suffix'):
            with self.subTest(version=version):
                with self.assertRaisesRegex(ValueError, 'Untested epub-editor version'):
                    self.resolve(version)

    def test_declared_contract_names_both_tested_families(self):
        contract = json.loads((PLUGIN / 'contracts/epub-editor.json').read_text(encoding='utf-8'))
        self.assertIn('0.1.x', contract['tested_version_family'])
        self.assertIn('0.2.x', contract['tested_version_family'])
        self.assertEqual(contract['adapter'], 'epub-editor-cli-v1')
        self.assertEqual(contract['skill'], 'epub-edit')

    def test_cli_capability_detects_reading_style_from_help_not_version(self):
        lock = self.resolve('0.2.0', help_flags='--metadata --inspect --recount --reading-style {standard,preserve}')
        self.assertTrue(lock['capabilities']['reading_style'])

    def test_style_capable_editor_gets_preserve_for_editing(self):
        lock = self.resolve('0.2.1', help_flags='--metadata --inspect --recount --reading-style {standard,preserve}')
        args = self.call(lock)
        self.assertEqual(args[-2:], ['--reading-style', 'preserve'])
        self.assertIn('--metadata', args)
        self.assertIn('--recount', args)

    def test_inspect_never_receives_reading_style(self):
        lock = self.resolve('0.2.1', help_flags='--metadata --inspect --recount --reading-style {standard,preserve}')
        args = self.call(lock, inspect=True)
        self.assertEqual(args[-1], '--inspect')
        self.assertNotIn('--reading-style', args)

    def test_legacy_cli_versions_keep_original_edit_arguments(self):
        for version in ('0.1.1+codex.20260927', '0.2.0'):
            with self.subTest(version=version):
                lock = self.resolve(version)
                self.assertFalse(lock['capabilities']['reading_style'])
                args = self.call(lock)
                self.assertNotIn('--reading-style', args)
                self.assertEqual(args[-3], '--metadata')
                self.assertEqual(args[-1], '--recount')
                self.assertEqual(verify_editor(lock), (self.root / 'scripts/epub_editor.py').resolve())

    def test_similarly_named_help_option_is_not_a_reading_style_capability(self):
        lock = self.resolve('0.2.1', help_flags='--metadata --inspect --recount --reading-styles')
        self.assertFalse(lock['capabilities']['reading_style'])

    def test_optional_imported_layout_helper_is_locked_and_changes_are_rejected(self):
        helper = self.root / LAYOUT_HELPER
        helper.write_text('original helper', encoding='utf-8')
        lock = self.resolve('0.2.1')
        self.assertIn(LAYOUT_HELPER, lock['files'])
        verify_editor(lock)
        helper.write_text('changed helper', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Dependency changed'):
            verify_editor(lock)

    def test_new_helper_after_prepare_requires_new_dependency_review(self):
        lock = self.resolve('0.2.0')
        (self.root / LAYOUT_HELPER).write_text('new helper', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Incomplete dependency lock'):
            verify_editor(lock)

    def test_removed_layout_helper_is_not_silently_treated_as_legacy(self):
        helper = self.root / LAYOUT_HELPER
        helper.write_text('original helper', encoding='utf-8')
        lock = self.resolve('0.2.1')
        helper.unlink()
        with self.assertRaisesRegex(ValueError, 'Incomplete dependency lock'):
            verify_editor(lock)

    def test_legacy_lock_without_capabilities_still_uses_old_cli(self):
        lock = self.resolve('0.1.1')
        lock.pop('capabilities', None)
        self.assertNotIn('--reading-style', self.call(lock))


if __name__ == '__main__':
    unittest.main()

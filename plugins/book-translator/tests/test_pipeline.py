import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fixtures import make_epub, write_zip
import book_translate as bt
from common import load_json, save_json
from dependencies import resolve_editor
from epub_segments import parse_xml, shape

EDITOR = ROOT.parent / 'epub-editor'


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='书籍 test ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = make_epub(self.root / '原文.epub')
        self.job = self.root / '工作区'
        self.info = bt.prepare(self.source, self.job, EDITOR)
        self.profile = {
            'reader': 'beginner', 'language': 'zh-Hans', 'style': '忠实、通顺，注释帮助初学者',
            'glossary': [{'source': 'necessary', 'target': '必要'}],
            'bibliography': {'status': 'original_sample', 'title': '小论证', 'authors': ['示例作者'],
                             'sources': [], 'decision': '自编验证样本，无出版译名'},
        }
        save_json(self.job / 'profile.json', self.profile)

    def draft(self, chapter):
        # Deterministic fixture data, NOT evidence of a real agent translation.
        packet = bt.packet(self.job, chapter)
        bt.assign(self.job, chapter, 'test-translator-' + chapter, 'test-reviewer-' + chapter)
        records = []
        for segment in packet['segments']:
            records.append({'id': segment['id'], 'target': segment['source'], 'action': 'preserve',
                            'reason': '测试夹具：结构检查，不代表已翻译', 'notes': []})
        result = {'chapter': chapter, 'translator_id': 'test-translator-' + chapter,
                  'input_digest': packet['input_digest'], 'segments': records}
        save_json(self.job / 'chapters' / chapter / 'translation.json', result)
        return result

    def approve(self, chapter):
        self.draft(chapter)
        info = bt.validate_chapter(self.job, chapter, require_review=False)
        review = {'chapter': chapter, 'reviewer_id': 'test-reviewer-' + chapter,
                  'draft_digest': info['draft_digest'], 'coverage': info['coverage'],
                  'verdict': 'approved', 'findings': [], 'accuracy': 'fixture only',
                  'fluency': 'fixture only', 'annotations': 'fixture only'}
        save_json(self.job / 'chapters' / chapter / 'review.json', review)

    def approve_all(self):
        for chapter in self.info['chapters']:
            self.approve(chapter['id'])
        bt.assign_global(self.job, 'test-global-reviewer')
        packet = bt.global_packet(self.job)
        report = {'reviewer_id': 'test-global-reviewer', 'bundle_digest': packet['bundle_digest'],
                  'coverage': packet['coverage'], 'verdict': 'approved', 'findings': [],
                  'consistency': 'fixture only', 'annotations': 'fixture only'}
        save_json(self.job / 'reviews' / 'global.json', report)

    def test_content_chapters_and_non_spine_coverage(self):
        segments = load_json(self.job / 'inventory.json')['segments']
        first = next(s for s in segments if 'guarantee' in s['source'])
        second = next(s for s in segments if 'prove rain' in s['source'])
        continuation = next(s for s in segments if 'necessary without' in s['source'])
        self.assertNotEqual(first['chapter'], second['chapter'])
        self.assertEqual(second['chapter'], continuation['chapter'])
        self.assertTrue(any('original author note' in s['source'] for s in segments))
        self.assertTrue(any(s['source'] == 'A road' for s in segments))
        self.assertFalse(any('return 0' in s['source'] for s in segments))

    def test_missing_and_duplicate_segments_block_review(self):
        chapter = self.info['chapters'][0]['id']
        draft = self.draft(chapter)
        for records in (draft['segments'][:-1], draft['segments'] + [draft['segments'][0]]):
            broken = dict(draft, segments=records)
            save_json(self.job / 'chapters' / chapter / 'translation.json', broken)
            with self.assertRaises(ValueError):
                bt.validate_chapter(self.job, chapter, require_review=False)

    def test_source_tampering_is_detected(self):
        with (self.job / 'source.epub').open('ab') as stream:
            stream.write(b'tampered')
        with self.assertRaisesRegex(ValueError, 'source'):
            bt.packet(self.job, self.info['chapters'][0]['id'])

    def test_inventory_tampering_is_detected(self):
        inventory = load_json(self.job / 'inventory.json')
        inventory['segments'].pop()
        save_json(self.job / 'inventory.json', inventory)
        with self.assertRaisesRegex(ValueError, 'inventory'):
            bt.packet(self.job, self.info['chapters'][0]['id'])

    def test_translator_cannot_review_own_chapter(self):
        with self.assertRaises(ValueError):
            bt.assign(self.job, self.info['chapters'][0]['id'], 'same', 'same')

    def test_protected_markup_cannot_change(self):
        chapter = self.info['chapters'][0]['id']
        draft = self.draft(chapter)
        entry = next(s for s in draft['segments'] if 'guarantee' in s['target'])
        entry['action'] = 'translate'
        entry['target'] = entry['target'].replace('notes.xhtml#n1', 'missing.xhtml#evil')
        save_json(self.job / 'chapters' / chapter / 'translation.json', draft)
        with self.assertRaisesRegex(ValueError, 'structure'):
            bt.validate_chapter(self.job, chapter, require_review=False)

    def test_profile_change_invalidates_drafts(self):
        chapter = self.info['chapters'][0]['id']
        self.approve(chapter)
        self.profile['glossary'][0]['target'] = '必需'
        save_json(self.job / 'profile.json', self.profile)
        with self.assertRaisesRegex(ValueError, 'stale'):
            bt.validate_chapter(self.job, chapter)

    def test_edited_draft_invalidates_review(self):
        chapter = self.info['chapters'][0]['id']
        self.approve(chapter)
        path = self.job / 'chapters' / chapter / 'translation.json'
        draft = load_json(path)
        draft['segments'][0]['reason'] += ' changed'
        save_json(path, draft)
        with self.assertRaisesRegex(ValueError, 'stale'):
            bt.validate_chapter(self.job, chapter)

    def test_unresolved_review_findings_block_export(self):
        self.approve_all()
        path = self.job / 'reviews' / 'global.json'
        report = load_json(path)
        report['findings'] = [{'id': 'F1', 'status': 'open', 'evidence': 'missing negation'}]
        save_json(path, report)
        with self.assertRaises(ValueError):
            bt.finalize(self.job, self.root / '中文.epub')
        self.assertFalse((self.root / '中文.epub').exists())

    def test_global_review_requires_full_coverage_and_independence(self):
        self.approve_all()
        with self.assertRaises(ValueError):
            bt.assign_global(self.job, 'test-reviewer-' + self.info['chapters'][0]['id'])
        path = self.job / 'reviews' / 'global.json'
        report = load_json(path)
        report['coverage'].pop()
        save_json(path, report)
        with self.assertRaises(ValueError):
            bt.validate_global(self.job)

    def test_epub_editor_real_integration_preserves_assets_and_source(self):
        before = self.source.read_bytes()
        self.approve_all()
        result = bt.finalize(self.job, self.root / '中文.epub')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.source.read_bytes(), before)
        with zipfile.ZipFile(self.root / '中文.epub') as z:
            self.assertEqual(z.infolist()[0].filename, 'mimetype')
            self.assertEqual(z.read('OPS/pixel.png'), b'fixture-image-preserved-verbatim')
            opf = parse_xml(z.read('OPS/package.opf'))
            self.assertIn('小论证', ''.join(opf.itertext()))
            self.assertIn('zh-Hans', ''.join(opf.itertext()))
        with self.assertRaises(FileExistsError):
            bt.finalize(self.job, self.root / '中文.epub')

    def test_editor_exit_two_never_publishes(self):
        self.approve_all()
        with patch('dependencies.subprocess.run') as run:
            run.return_value.returncode = 2
            run.return_value.stdout = '{"issues":[{"kind":"note"}]}'
            run.return_value.stderr = ''
            with self.assertRaises(ValueError):
                bt.finalize(self.job, self.root / '中文.epub')
        self.assertFalse((self.root / '中文.epub').exists())

    def test_dependency_can_live_in_unrelated_cache_directory(self):
        other = self.root / 'independent cache' / 'epub-editor' / '0.1.0'
        shutil.copytree(EDITOR, other)
        result = resolve_editor(other)
        self.assertEqual(Path(result['root']), other.resolve())
        manifest = load_json(other / 'plugin.json')
        manifest['name'] = 'imposter'
        save_json(other / 'plugin.json', manifest)
        with self.assertRaises(ValueError):
            resolve_editor(other)

    def test_duplicate_json_keys_rejected(self):
        path = self.root / 'bad.json'
        path.write_text('{"x":1,"x":2}', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_json(path)

    def test_long_paragraph_batches_have_complete_text(self):
        src = make_epub(self.root / 'long.epub', long=True, no_nav=True)
        job = self.root / 'long-job'
        bt.prepare(src, job, EDITOR, max_chars=1000)
        inventory = load_json(job / 'inventory.json')
        self.assertTrue(all(len(s['source']) <= 1000 for s in inventory['segments']))
        long_parts = [s for s in inventory['segments'] if 'very long sentence' in s['source']]
        self.assertEqual(''.join(s['source'] for s in long_parts), 'A very long sentence. ' * 800)

    def test_zip_traversal_rejected_before_job_creation(self):
        with zipfile.ZipFile(self.source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        data['../evil'] = b'no'
        bad = self.root / 'bad.epub'
        write_zip(bad, data)
        job = self.root / 'bad-job'
        with self.assertRaises(ValueError):
            bt.prepare(bad, job, EDITOR)
        self.assertFalse(job.exists())

    def test_inline_code_protection_allows_translating_its_tail(self):
        source = parse_xml('<p>Call <code>x()</code> to continue.</p>')
        target = parse_xml('<p>调用 <code>x()</code> 以继续。</p>')
        self.assertEqual(shape(source), shape(target))
        changed = parse_xml('<p>调用 <code>y()</code> 以继续。</p>')
        self.assertNotEqual(shape(source), shape(changed))

    def test_scalar_tail_of_replaced_block_is_not_lost(self):
        with zipfile.ZipFile(self.source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        data['OPS/b.xhtml'] = data['OPS/b.xhtml'].replace(b'</p><pre>', b'</p>Text after paragraph.<pre>')
        write_zip(self.source, data)
        self.job = self.root / 'tail-job'
        self.info = bt.prepare(self.source, self.job, EDITOR)
        save_json(self.job / 'profile.json', self.profile)
        self.approve_all()
        for chapter in self.info['chapters']:
            path = self.job / 'chapters' / chapter['id'] / 'translation.json'
            draft = load_json(path)
            for record in draft['segments']:
                if record['target'] == 'Text after paragraph.':
                    record['action'] = 'translate'
                    record['target'] = '段落后的文字。'
            save_json(path, draft)
        catalog = load_json(self.job / 'inventory.json')
        assembled, _, _ = bt._assemble(self.job, catalog, self.profile, 'a' * 64)
        self.assertIn('段落后的文字。', assembled['OPS/b.xhtml'].decode())
        self.assertNotIn('Text after paragraph.', assembled['OPS/b.xhtml'].decode())

    def test_added_note_is_labeled_and_links_both_ways(self):
        for chapter in self.info['chapters']:
            self.draft(chapter['id'])
        catalog = load_json(self.job / 'inventory.json')
        segment = next(s for s in catalog['segments'] if 'prove rain' in s['source'])
        path = self.job / 'chapters' / segment['chapter'] / 'translation.json'
        draft = load_json(path)
        record = next(r for r in draft['segments'] if r['id'] == segment['id'])
        record['notes'] = [{'kind': 'example', 'text': '假设有人洒水，路也会湿。',
                            'source_quote': 'does not prove rain', 'rationale': '说明逆命题不成立', 'sources': []}]
        save_json(path, draft)
        bt.validate_chapter(self.job, segment['chapter'], require_review=False)
        data, docs, patch_data = bt._assemble(self.job, catalog, self.profile, 'b' * 64)
        note_path = next(p for p in data if p.endswith('-notes.xhtml'))
        self.assertIn('辅助案例（假设示例）', data[note_path].decode())
        self.assertIn('返回正文', data[note_path].decode())
        candidate = self.root / 'annotated.epub'
        write_zip(candidate, data)
        # Use the real editor and the same readback validator.
        metadata = self.root / 'metadata.json'
        save_json(metadata, patch_data)
        from dependencies import call_editor
        out = self.root / 'annotated-compiled.epub'
        call_editor(load_json(self.job / 'dependencies.lock.json'), candidate, out, metadata)
        bt._verify_output(out, data, docs, catalog, patch_data)

    def test_dependency_changed_after_prepare_is_rejected(self):
        other = self.root / 'cache-copy'
        shutil.copytree(EDITOR, other)
        job = self.root / 'dependency-job'
        bt.prepare(self.source, job, other)
        script = other / 'scripts' / 'epub_editor.py'
        with script.open('a', encoding='utf-8') as stream:
            stream.write('\n# changed\n')
        from dependencies import verify_editor
        with self.assertRaisesRegex(ValueError, 'changed'):
            verify_editor(load_json(job / 'dependencies.lock.json'))

    def test_epub2_without_nav_gets_real_editor_navigation(self):
        self.source = make_epub(self.root / 'old.epub', epub2=True, no_nav=True)
        self.job = self.root / 'old-job'
        self.info = bt.prepare(self.source, self.job, EDITOR)
        save_json(self.job / 'profile.json', self.profile)
        self.approve_all()
        out = self.root / 'old-zh.epub'
        bt.finalize(self.job, out)
        with zipfile.ZipFile(out) as z:
            self.assertIn('OPS/epub-editor-nav.xhtml', z.namelist())

    def test_editor_can_add_heading_ids_when_creating_navigation(self):
        self.source = make_epub(self.root / 'no-heading-ids.epub', no_nav=True)
        with zipfile.ZipFile(self.source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        data['OPS/a.xhtml'] = data['OPS/a.xhtml'].replace(b' id="one"', b'').replace(b' id="two"', b'')
        write_zip(self.source, data)
        self.job = self.root / 'no-heading-ids-job'
        self.info = bt.prepare(self.source, self.job, EDITOR)
        save_json(self.job / 'profile.json', self.profile)
        self.approve_all()
        out = self.root / 'navigation-zh.epub'
        bt.finalize(self.job, out)
        with zipfile.ZipFile(out) as z:
            body = parse_xml(z.read('OPS/a.xhtml'))
            self.assertEqual(len(body.xpath('//*[local-name()="h1"]/@id')), 2)

    def test_image_only_book_is_not_mistaken_for_full_text(self):
        with zipfile.ZipFile(self.source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        from fixtures import page
        data['OPS/a.xhtml'] = page('Scanned book', '<img src="pixel.png" alt="Page one"/>')
        data['OPS/b.xhtml'] = page('Page two', '<img src="pixel.png"/>')
        data.pop('OPS/nav.xhtml')
        data['OPS/package.opf'] = data['OPS/package.opf'].replace(b'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>', b'')
        bad = self.root / 'scan.epub'
        write_zip(bad, data)
        with self.assertRaisesRegex(ValueError, 'OCR|image-only'):
            bt.prepare(bad, self.root / 'scan-job', EDITOR)

    def test_invalid_notes_are_rejected_without_type_traceback(self):
        chapter = self.info['chapters'][0]['id']
        draft = self.draft(chapter)
        next(r for r in draft['segments'] if '<h1' in r['target'])['notes'] = 'invalid'
        save_json(self.job / 'chapters' / chapter / 'translation.json', draft)
        with self.assertRaises(ValueError):
            bt.validate_chapter(self.job, chapter, require_review=False)

    def test_long_paragraph_chunks_can_have_beginner_notes(self):
        self.source = make_epub(self.root / 'long-notes.epub', long=True, no_nav=True)
        self.job = self.root / 'long-notes-job'
        self.info = bt.prepare(self.source, self.job, EDITOR, max_chars=256)
        save_json(self.job / 'profile.json', self.profile)
        self.approve_all()
        catalog = load_json(self.job / 'inventory.json')
        segment = next(s for s in catalog['segments'] if s['parts'] > 1 and 'very long' in s['source'])
        draft_path = self.job / 'chapters' / segment['chapter'] / 'translation.json'
        draft = load_json(draft_path)
        entry = next(r for r in draft['segments'] if r['id'] == segment['id'])
        entry['notes'] = [{'kind': 'explanation', 'text': '长段落的初学者解释。',
                           'rationale': '长段落分块后仍应支持注释', 'source_quote': 'A very long sentence.'}]
        save_json(draft_path, draft)
        bt.validate_chapter(self.job, segment['chapter'], require_review=False)
        data, docs, metadata = bt._assemble(self.job, catalog, self.profile, 'long-note-test')
        body = docs['OPS/a.xhtml']
        refs = body.xpath('//*[local-name()="a" and @role="doc-noteref"]')
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].getparent().tag, '{http://www.w3.org/1999/xhtml}p')
        self.assertIn('A very long sentence.', refs[0].getparent().text)
        self.assertTrue(any('长段落的初学者解释。' in ''.join(d.itertext()) for d in docs.values()))
        output = self.root / 'long-note-assembled.epub'
        from epub_segments import write_epub
        write_epub(output, data)
        metadata_path = self.root / 'long-notes-metadata.json'
        save_json(metadata_path, metadata)
        compiled = self.root / 'long-note-compiled.epub'
        from dependencies import call_editor
        call_editor(load_json(self.job / 'dependencies.lock.json'), output, compiled, metadata_path)
        bt._verify_output(compiled, data, docs, catalog, metadata)

    def test_notes_cannot_be_attached_to_document_head(self):
        chapter = self.info['chapters'][0]['id']
        draft = self.draft(chapter)
        entry = next(r for r in draft['segments'] if r['target'] == 'Small Arguments')
        entry['notes'] = [{'kind': 'explanation', 'text': '解释', 'rationale': '测试', 'source_quote': 'Small Arguments'}]
        save_json(self.job / 'chapters' / chapter / 'translation.json', draft)
        with self.assertRaisesRegex(ValueError, 'body'):
            bt.validate_chapter(self.job, chapter, require_review=False)

    def test_original_translator_is_not_credited_as_new_chinese_translator(self):
        with zipfile.ZipFile(self.source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        data['OPS/package.opf'] = data['OPS/package.opf'].replace(b'</metadata>', b'<dc:contributor id="old-translator">Original Translator</dc:contributor><meta refines="#old-translator" property="role">trl</meta><meta id="id-kind" refines="#uid" property="identifier-type">URI</meta><meta refines="#id-kind" property="authority">test</meta></metadata>')
        write_zip(self.source, data)
        self.job = self.root / 'provenance-job'
        self.info = bt.prepare(self.source, self.job, EDITOR)
        save_json(self.job / 'profile.json', self.profile)
        self.approve_all()
        out = self.root / 'provenance-zh.epub'
        bt.finalize(self.job, out)
        with zipfile.ZipFile(out) as z:
            opf = parse_xml(z.read('OPS/package.opf'))
            self.assertEqual(opf.xpath('//*[local-name()="contributor"]/text()'), [])
            self.assertEqual(opf.xpath('//*[@refines="#id-kind"]'), [])
            self.assertIn('Original Translator', ''.join(opf.xpath('//*[local-name()="source"]/text()')))

    def test_demo_asset_is_a_valid_png(self):
        import io
        from PIL import Image
        from create_demo import create_demo
        source = create_demo(self.root / 'valid-demo')
        with zipfile.ZipFile(source) as z:
            with Image.open(io.BytesIO(z.read('OPS/pixel.png'))) as image:
                image.verify()

    def test_next_chapter_document_title_belongs_to_its_own_chapter(self):
        from create_demo import create_demo
        source = create_demo(self.root / 'title-demo')
        job = self.root / 'title-job'
        bt.prepare(source, job, EDITOR)
        segments = load_json(job / 'inventory.json')['segments']
        doc_title = next(s for s in segments if s['source'] == 'Conditions')
        heading = next(s for s in segments if 'Two: Necessary' in s['source'])
        self.assertEqual(doc_title['chapter'], heading['chapter'])

    def test_non_author_creator_is_preserved_without_breaking_author_readback(self):
        with zipfile.ZipFile(self.source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        data['OPS/package.opf'] = data['OPS/package.opf'].replace(b'</metadata>', b'<dc:creator id="artist">Original Artist</dc:creator><meta refines="#artist" property="role">ill</meta></metadata>')
        write_zip(self.source, data)
        self.job = self.root / 'artist-job'
        self.info = bt.prepare(self.source, self.job, EDITOR)
        save_json(self.job / 'profile.json', self.profile)
        self.approve_all()
        out = self.root / 'artist-zh.epub'
        result = bt.finalize(self.job, out)
        self.assertEqual(result['metadata_readback']['authors'][0]['name'], '示例作者')
        self.assertTrue(any(c['name'] == 'Original Artist' for c in result['metadata_readback']['contributors']))


if __name__ == '__main__':
    unittest.main()

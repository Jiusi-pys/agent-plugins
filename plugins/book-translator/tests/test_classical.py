"""Synthetic evidence fixtures test gates, not claims of actual historical research."""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import book_translate as bt
import classical
from common import load_json, save_json
from fixtures import make_epub


class Classical(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='古译今 test ')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / '原文.txt'
        self.source.write_text('孝子不匱，永錫爾類。\n\n其是之謂乎！\n', encoding='utf-8')
        self.job = self.root / 'job'
        self.info = bt.prepare_text(self.source, self.job)
        self.add_source()
        profile = load_json(self.job / 'profile.json')
        profile['classical']['base_edition'] = '自编测试夹具，不能作为真实考据'
        profile['bibliography'].update(status='original_sample', title='测试精译', authors=['测试作者'], decision='仅测试结构')
        save_json(self.job / 'profile.json', profile)

    def add_source(self, kind='primary_text'):
        capture = self.root / '实际获取内容.txt'
        capture.write_text('孝子不匱，永錫爾類。其是之謂乎！\n匱，竭也。', encoding='utf-8')
        metadata = {'id': 'fixture', 'work': '测试古籍', 'attribution': '测试注家',
                    'edition': '仅夹具，非真实版本', 'locator': '卷一', 'url': 'https://example.org/fixture',
                    'kind': kind, 'accessed': '2026-09-27', 'access_method': 'web', 'read_evidence': 'fixture only'}
        bt.record_source(self.job, metadata, capture)

    def draft(self, chapter='c0001'):
        packet = bt.packet(self.job, chapter)
        bt.assign(self.job, chapter, 'translator', 'reviewer-' + chapter)
        citation = {'source_id': 'fixture', 'quote': '孝子不匱，永錫爾類。', 'locator': '卷一', 'relevance': '测试对应原句'}
        records = []
        for s in packet['segments']:
            records.append({'id': s['id'], 'action': 'translate', 'target': '现代汉语译文',
                'classical': {'citations': [citation], 'reading': '核对断句、语法和古义', 'allusions': '引诗，见详注',
                              'variants': '仅测试，未声明无异文', 'status': 'verified', 'uncertainty': '仅验证契约'},
                'notes': [{'kind': 'explanation', 'category': 'allusion', 'text': '详细说明引诗的上下文及本处借用的意思。',
                           'source_quote': s['source'].strip(), 'rationale': '读者不知道出处', 'citations': [citation]}]})
        draft = {'chapter': chapter, 'translator_id': 'translator', 'input_digest': packet['input_digest'], 'segments': records}
        save_json(self.job / 'chapters' / chapter / 'translation.json', draft)
        return draft

    def checks(self):
        return [{'source_id': s['id'], 'sha256': s['sha256'], 'method': 'web', 'locator': s['locator'],
                 'conclusion': 'fixture only; not actual research'} for s in classical.read_sources(self.job)]

    def approve(self):
        self.draft()
        info = bt.validate_chapter(self.job, 'c0001', False)
        save_json(self.job / 'chapters/c0001/review.json', {'chapter': 'c0001', 'reviewer_id': 'reviewer-c0001',
            'draft_digest': info['draft_digest'], 'coverage': info['coverage'], 'verdict': 'approved', 'findings': [],
            'accuracy': 'fixture', 'fluency': 'fixture', 'annotations': 'fixture', 'source_checks': self.checks()})
        bt.assign_global(self.job, 'global')
        packet = bt.global_packet(self.job)
        save_json(self.job / 'reviews/global.json', {'reviewer_id': 'global', 'bundle_digest': packet['bundle_digest'],
            'coverage': packet['coverage'], 'verdict': 'approved', 'findings': [], 'consistency': 'fixture',
            'annotations': 'fixture', 'source_checks': self.checks()})

    def test_text_inventory_preserves_source_and_offsets(self):
        self.assertEqual(self.source.read_bytes(), (self.job / 'source.txt').read_bytes())
        source = self.source.read_bytes().decode('utf-8-sig')
        for s in bt.packet(self.job, 'c0001')['segments']:
            self.assertEqual(source[s['start']:s['end']], s['source'])

    def test_text_route_needs_no_epub_editor(self):
        self.approve()
        out = self.root / '精译.md'
        result = bt.finalize(self.job, out)
        text = out.read_text(encoding='utf-8')
        self.assertIn('孝子不匱，永錫爾類。', text)
        self.assertIn('现代汉语译文', text)
        self.assertIn('测试古籍', text)
        self.assertIn('卷一', text)
        self.assertIn('https://example.org/fixture', text)
        self.assertIn('译者注·典故', text)
        self.assertIn('### 第1段', text)
        self.assertNotIn('### s000001', text)
        self.assertEqual(result['format'], 'markdown')
        with self.assertRaises(FileExistsError):
            bt.finalize(self.job, out)

    def test_markdown_headings_split_without_blank_lines(self):
        source = self.root / 'chapters.md'
        source.write_text('# 甲篇\n甲篇原文。\n# 乙篇\n乙篇原文。', encoding='utf-8')
        result = classical.text_inventory(source)
        self.assertEqual([c['title'] for c in result['chapters']], ['甲篇', '乙篇'])
        for segment in result['segments']:
            if '乙篇原文' in segment['source']:
                self.assertEqual(segment['chapter'], 'c0002')

    def test_epub_classical_real_editor_exports_annotations_and_evidence(self):
        template = self.draft()['segments'][0]['classical']
        source = make_epub(self.root / 'epub-input.epub')
        job = self.root / 'epub-fully-reviewed'
        info = bt.prepare(source, job, ROOT.parent / 'epub-editor', mode='classical_chinese')
        save_json(job / 'profile.json', load_json(self.job / 'profile.json'))
        metadata = classical.read_sources(self.job)[0]
        bt.record_source(job, metadata, self.job / 'sources/fixture.txt')
        for chapter in info['chapters']:
            cid = chapter['id']
            bt.assign(job, cid, 'translator-' + cid, 'reviewer-' + cid)
            packet = bt.packet(job, cid)
            records = [{'id': s['id'], 'target': s['source'], 'action': 'preserve', 'reason': 'Synthetic fixture only',
                        'notes': [], 'classical': template} for s in packet['segments']]
            save_json(job / 'chapters' / cid / 'translation.json', {'chapter': cid, 'translator_id': 'translator-' + cid,
                      'input_digest': packet['input_digest'], 'segments': records})
            result = bt.validate_chapter(job, cid, False)
            save_json(job / 'chapters' / cid / 'review.json', {'chapter': cid, 'reviewer_id': 'reviewer-' + cid,
                      'draft_digest': result['draft_digest'], 'coverage': result['coverage'], 'verdict': 'approved',
                      'findings': [], 'accuracy': 'fixture', 'fluency': 'fixture', 'annotations': 'fixture',
                      'source_checks': self.checks()})
        bt.assign_global(job, 'global-fixture')
        packet = bt.global_packet(job)
        save_json(job / 'reviews/global.json', {'reviewer_id': 'global-fixture', 'bundle_digest': packet['bundle_digest'],
                  'coverage': packet['coverage'], 'verdict': 'approved', 'findings': [], 'consistency': 'fixture',
                  'annotations': 'fixture', 'source_checks': self.checks()})
        output = self.root / 'classical.epub'
        result = bt.finalize(job, output)
        self.assertEqual(result['editor']['issues'], [])
        with zipfile.ZipFile(output) as archive:
            texts = '\n'.join(archive.read(n).decode('utf-8') for n in archive.namelist() if n.endswith('.xhtml'))
            self.assertIn('原文对照', texts)
            self.assertIn('字句、用典与校勘依据', texts)
            self.assertIn('测试古籍', texts)
            self.assertIn('https://example.org/fixture', texts)

    def test_translation_without_primary_citation_is_rejected(self):
        draft = self.draft()
        draft['segments'][0]['classical']['citations'] = []
        save_json(self.job / 'chapters/c0001/translation.json', draft)
        with self.assertRaisesRegex(ValueError, 'primary'):
            bt.validate_chapter(self.job, 'c0001', False)

    def test_modern_restatement_cannot_substitute_for_primary_text(self):
        source = load_json(self.job / 'sources.json')
        source[0]['kind'] = 'modern_scholarship'
        save_json(self.job / 'sources.json', source)
        self.draft()
        with self.assertRaisesRegex(ValueError, 'primary'):
            bt.validate_chapter(self.job, 'c0001', False)

    def test_unread_or_fabricated_quote_is_rejected(self):
        draft = self.draft()
        draft['segments'][0]['notes'][0]['citations'][0] = dict(draft['segments'][0]['notes'][0]['citations'][0], quote='不存在的古文')
        save_json(self.job / 'chapters/c0001/translation.json', draft)
        with self.assertRaisesRegex(ValueError, 'quote'):
            bt.validate_chapter(self.job, 'c0001', False)

    def test_explanatory_note_needs_its_own_evidence(self):
        draft = self.draft()
        draft['segments'][0]['notes'][0].pop('citations')
        save_json(self.job / 'chapters/c0001/translation.json', draft)
        with self.assertRaisesRegex(ValueError, 'citation'):
            bt.validate_chapter(self.job, 'c0001', False)

    def test_capture_tampering_invalidates_packet(self):
        self.draft()
        (self.job / 'sources/fixture.txt').write_text('改过', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source|capture'):
            bt.packet(self.job, 'c0001')

    def test_research_metadata_change_invalidates_draft(self):
        self.draft()
        sources = load_json(self.job / 'sources.json')
        sources[0]['edition'] = '新版本'
        save_json(self.job / 'sources.json', sources)
        with self.assertRaisesRegex(ValueError, 'stale'):
            bt.validate_chapter(self.job, 'c0001', False)

    def test_unresolved_reading_blocks_delivery(self):
        draft = self.draft()
        draft['segments'][0]['classical']['status'] = 'unresolved'
        save_json(self.job / 'chapters/c0001/translation.json', draft)
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            bt.validate_chapter(self.job, 'c0001', False)

    def test_reviewer_must_independently_check_every_source(self):
        self.approve()
        path = self.job / 'chapters/c0001/review.json'
        report = load_json(path)
        report['source_checks'] = []
        save_json(path, report)
        with self.assertRaises(ValueError):
            bt.validate_chapter(self.job, 'c0001')

    def test_global_reviewer_must_check_sources_too(self):
        self.approve()
        path = self.job / 'reviews/global.json'
        report = load_json(path)
        report['source_checks'][0]['method'] = 'copied_translator_report'
        save_json(path, report)
        with self.assertRaises(ValueError):
            bt.validate_global(self.job)

    def test_mode_cannot_be_removed_from_profile(self):
        profile = load_json(self.job / 'profile.json')
        profile.pop('mode')
        save_json(self.job / 'profile.json', profile)
        with self.assertRaisesRegex(ValueError, 'mode'):
            bt.packet(self.job, 'c0001')

    def test_epub_classical_output_contains_source_comparison(self):
        source = make_epub(self.root / 'ancient.epub')
        job = self.root / 'epub-job'
        bt.prepare(source, job, ROOT.parent / 'epub-editor', mode='classical_chinese')
        catalog = load_json(job / 'inventory.json')
        profile = load_json(self.job / 'profile.json')
        save_json(job / 'profile.json', profile)
        # Assembly fixture: gate behavior is covered above; no real agent approval claimed.
        for chapter in catalog['chapters']:
            save_json(job / 'chapters' / chapter['id'] / 'translation.json', {'segments': [
                {'id': s['id'], 'target': s['source'], 'action': 'preserve', 'notes': []}
                for s in catalog['segments'] if s['chapter'] == chapter['id']]})
        data, docs, _ = bt._assemble(job, catalog, profile, 'comparison-fixture')
        self.assertTrue(any('原文对照' in ''.join(d.itertext()) for d in docs.values()))

    def test_source_id_cannot_escape_job(self):
        metadata = dict(classical.read_sources(self.job)[0], id='../escape')
        with self.assertRaises(ValueError):
            bt.record_source(self.job, metadata, self.root / '实际获取内容.txt')


if __name__ == '__main__':
    unittest.main()

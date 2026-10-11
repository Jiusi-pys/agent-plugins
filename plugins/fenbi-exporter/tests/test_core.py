"""Behavior contracts; fixtures contain synthetic personal data only."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fenbi_exporter.core import (ExportStore, asset_identity, combine_flags, course_url,
    date_selected, normalize_record, render_record, safe_name, validate_file)


class CoreTests(unittest.TestCase):
    def test_url_validation(self):
        self.assertEqual(course_url('775995'), 'https://www.fenbi.com/spa/pwa/episodes/775995')
        for bad in ['https://evil.test/775995', '../775995', 'https://www.fenbi.com.evil.test/spa/pwa/episodes/775995']:
            with self.assertRaises(ValueError):
                course_url(bad)

    def test_independent_flags_and_conflicting_evidence(self):
        for mark, star in [(True, False), (False, True), (True, True), (False, False)]:
            self.assertEqual(combine_flags({'marked': mark, 'collected': star}, {})[:2], (mark, star))
        self.assertIsNone(combine_flags({}, {})[0])
        self.assertIsNone(combine_flags({'marked': True}, {'marked': False})[0])

    def test_dates_are_inclusive_and_unknown_is_not_silently_excluded(self):
        self.assertTrue(date_selected('2026.10.11', '2026-10-11', '2026-10-11'))
        self.assertFalse(date_selected('2026-10-10T15:59:59Z', '2026-10-11', None))
        self.assertTrue(date_selected('2026-10-10T16:00:00Z', '2026-10-11', None))
        with self.assertRaises(ValueError):
            date_selected('', '2026-10-11', None)

    def test_path_names_and_signed_url_identity(self):
        for name in ['CON', '../x:y?.pdf', 'NUL.pdf', 'a' * 400]:
            result = safe_name(name)
            self.assertNotIn('/', result)
            self.assertNotIn(':', result)
            self.assertLessEqual(len(result), 70)
        self.assertEqual(asset_identity('https://files.test/a.pdf?sign=secret'), asset_identity('https://files.test/a.pdf?sign=other'))

    def test_invalid_downloads_never_pass(self):
        for data, mime in [(b'', 'application/pdf'), (b'<html>login</html>', 'application/pdf'), (b'error', 'application/pdf'), (b'body { color: red; }', 'text/css')]:
            with self.assertRaises(ValueError):
                validate_file(data, 'test.pdf', mime)
        with self.assertRaises(ValueError):
            validate_file(b'body{color:red}', 'style.css', 'text/css')
        validate_file(b'%PDF-1.7\nbody\n%%EOF', 'test.pdf', 'application/pdf')

    def test_do_not_infer_correct_user_answer(self):
        record = normalize_record({'id': 'attempt-1', 'subject': 'xingce', 'title': '练习',
            'expected_count': 1, 'questions': [{'number': 1, 'correct_answer': 'B', 'correctness': 'correct',
                'card': {'marked': False, 'collected': False}, 'blocks': []}]})
        self.assertIsNone(record['questions'][0]['user_answer'])
        self.assertTrue(any('user_answer' in x for x in record['issues']))

    def test_markdown_keeps_images_order_marks_and_material(self):
        record = normalize_record({'id': 'a', 'subject': 'xingce', 'title': '图形', 'expected_count': 1,
            'questions': [{'number': 1, 'user_answer': 'A', 'card': {'marked': True, 'collected': True},
                'blocks': [{'type': 'text', 'text': '材料一'}, {'type': 'image', 'asset': 'assets/figure.png'},
                           {'type': 'text', 'text': '题干二'}]}]})
        md = render_record(record, '../../')
        self.assertLess(md.index('材料一'), md.index('figure.png'))
        self.assertLess(md.index('figure.png'), md.index('题干二'))
        self.assertIn('不确定标注：是', md)
        self.assertIn('收藏：是', md)
        self.assertIn('../../assets/figure.png', md)

    def test_snapshots_reuse_assets_and_failed_refresh_preserves_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ExportStore(Path(tmp))
            a = store.save_asset(b'%PDF-1.7\nbody\n%%EOF', '讲义.pdf', 'application/pdf')
            self.assertEqual(a, store.save_asset(b'%PDF-1.7\nbody\n%%EOF', '别名.pdf', 'application/pdf'))
            base = {'id': 'r1', 'subject': 'xingce', 'title': 'test', 'expected_count': 0, 'questions': [], 'issues': []}
            first = store.save_record(base)
            self.assertEqual(first, store.save_record({**base, 'captured_at': 'later'}))
            second = store.save_record({**base, 'title': 'updated'})
            self.assertNotEqual(first, second)
            store.save_record({**base, 'title': 'incomplete', 'issues': ['missing image']})
            self.assertEqual(store.index['records']['xingce:r1']['current'], second)
            self.assertTrue((Path(tmp) / first).exists())
            self.assertEqual(store.verify()['status'], 'partial')
            self.assertTrue(any('incomplete' in i for i in store.verify()['issues']))

    def test_repeated_question_in_distinct_attempts_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ExportStore(Path(tmp))
            for rid in ['attempt-a', 'attempt-b']:
                store.save_record({'id': rid, 'subject': 'shenlun', 'title': '同一道题', 'questions': [], 'issues': []})
            self.assertEqual(len(store.index['records']), 2)

    def test_verify_detects_corrupt_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ExportStore(Path(tmp))
            asset = store.save_asset(b'%PDF-1.7\nbody\n%%EOF', 'a.pdf', 'application/pdf')
            (Path(tmp) / asset['path']).write_bytes(b'bad')
            self.assertEqual(store.verify()['status'], 'partial')

    def test_verify_checks_markdown_references_and_invalid_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ExportStore(tmp)
            relative = store.save_record({'id':'r', 'subject':'xingce', 'questions':[], 'issues':[]})
            md = store.path(relative).with_suffix('.md')
            md.write_text(md.read_text('utf-8') + '\n![broken](../../assets/missing.png)', 'utf-8')
            self.assertEqual(store.verify()['status'], 'partial')
            store.path(relative).write_text('{', 'utf-8')
            self.assertEqual(store.verify()['status'], 'partial')

    def test_changed_marks_get_new_snapshot_and_keep_prior_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ExportStore(tmp)
            raw = {'id':'r', 'subject':'xingce', 'questions':[{'number':1,'user_answer':'B',
                'card':{'marked':False,'collected':True}}]}
            first = store.save_record(normalize_record(raw))
            raw['questions'][0]['card']['marked'] = True
            second = store.save_record(normalize_record(raw))
            self.assertNotEqual(first, second)
            self.assertEqual(second, store.save_record(normalize_record(raw)))
            self.assertTrue(store.path(first).exists())

    def test_same_image_bytes_from_rotating_cdn_do_not_create_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ExportStore(tmp)
            raw = {'id':'r', 'subject':'xingce', 'questions':[{'number':1,'user_answer':'A',
                'card':{'marked':False,'collected':False},'blocks':[{'type':'image',
                'asset':'assets/same.png','sha256':'same','source_url':'https://cdn-a.test/img.png'}]}]}
            first = store.save_record(normalize_record(raw))
            raw['questions'][0]['blocks'][0]['source_url'] = 'https://cdn-b.test/img.png'
            self.assertEqual(first, store.save_record(normalize_record(raw)))


if __name__ == '__main__':
    unittest.main()

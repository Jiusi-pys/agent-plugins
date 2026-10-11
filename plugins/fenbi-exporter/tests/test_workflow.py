import sys
import unittest
import tempfile
import json
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fenbi_exporter.workflow import HistoryPages, dedupe_items, execute, completed_example, SolutionState


class PaginationTests(unittest.TestCase):
    def test_unloaded_flags_are_unknown_even_when_both_dom_controls_are_false(self):
        state = SolutionState()
        raw = {'issues':[], 'questions':[{'number':1,'question_id':'q1', 'card':{'marked':False,'collected':False},
            'toolbar':{'marked':False,'collected':False}, 'flag_evidence':{}}]}
        state.reconcile(raw)
        self.assertIsNone(raw['questions'][0]['card']['marked'])
        self.assertIsNone(raw['questions'][0]['card']['collected'])

    def test_flag_response_readiness_and_absent_favorite_capability(self):
        state = SolutionState()
        state.add('marked', {'code':1,'data':{'ids':['q1']}})
        raw = {'issues':[], 'questions':[{'number':1,'question_id':'q1', 'card':{'marked':False,'collected':False},
            'toolbar':{'marked':False}, 'flag_evidence':{}}]}
        self.assertFalse(state.dom_ready(raw))
        raw['questions'][0]['card']['marked'] = True
        raw['questions'][0]['toolbar']['marked'] = True
        self.assertTrue(state.dom_ready(raw))
        state.reconcile(raw)
        self.assertTrue(raw['questions'][0]['card']['marked'])
        self.assertIsNone(raw['questions'][0]['card']['collected'])

    def test_successful_empty_flags_prove_false_failed_response_does_not(self):
        state = SolutionState()
        state.add('marked', {'code':1,'data':{'ids':[]}})
        state.add('collected', {'code':0,'data':{}})
        raw = {'issues':[], 'questions':[{'number':1,'question_id':'q1','card':{'marked':False,'collected':False},'toolbar':{},'flag_evidence':{}}]}
        state.reconcile(raw)
        self.assertFalse(raw['questions'][0]['card']['marked'])
        self.assertIsNone(raw['questions'][0]['card']['collected'])

    def test_unfinished_attempt_must_not_be_opened_for_route_discovery(self):
        self.assertEqual(completed_example([{'status':0},{'status':1}]), 1)
        self.assertIsNone(completed_example([{'status':0}]))
    def test_empty_is_complete_only_after_successful_response(self):
        history = HistoryPages()
        self.assertFalse(history.complete)
        history.add({'code': 1, 'data': {'historyItems': [], 'cursor': None}})
        self.assertTrue(history.complete)

    def test_cursor_and_duplicate_records(self):
        history = HistoryPages()
        history.add({'code': 1, 'data': {'historyItems': [{'exerciseKey': 'a'}, {'exerciseKey': 'b'}], 'cursor': 'next'}})
        self.assertFalse(history.complete)
        history.add({'code': 1, 'data': {'historyItems': [{'exerciseKey': 'b'}, {'exerciseKey': 'c'}], 'cursor': None}})
        self.assertTrue(history.complete)
        self.assertEqual([x['exerciseKey'] for x in history.items], ['a', 'b', 'c'])

    def test_failed_response_does_not_imply_no_records(self):
        history = HistoryPages()
        with self.assertRaises(ValueError):
            history.add({'code': 0, 'msg': 'failed'})
        self.assertFalse(history.complete)

    def test_same_title_distinct_attempts(self):
        self.assertEqual(len(dedupe_items([{'exerciseKey': 'a', 'sheetName': 'same'}, {'exerciseKey': 'b', 'sheetName': 'same'}])), 2)

    def test_resume_retries_failed_only_and_clears_stale_pause(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(command='history', output=Path(tmp), subject='xingce', start=None, end=None,
                record_url=['https://spa.fenbi.com/ti/exam/solution/a?routecs=xingce', 'https://spa.fenbi.com/ti/exam/solution/b?routecs=xingce'], limit=None)
            with patch('fenbi_exporter.workflow.export_record', side_effect=[{'status':'complete'}, RuntimeError('temporary')]) as export:
                initial = execute(args, None)
            self.assertEqual(initial['status'], 'partial')
            manifest = Path(initial['manifest'])
            data = json.loads(manifest.read_text('utf-8'))
            data['issues'] = ['需要在独立浏览器中完成登录或访问验证']
            manifest.write_text(json.dumps(data), 'utf-8')
            resume = SimpleNamespace(command='resume', output=Path(tmp), run=initial['run_id'])
            with patch('fenbi_exporter.workflow.export_record', return_value={'status':'complete'}) as export:
                result = execute(resume, None)
                self.assertEqual(export.call_count, 1)
            self.assertEqual(result['status'], 'complete')

    def test_incomplete_discovery_exports_known_items_and_resume_rediscovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(command='history', output=Path(tmp), subject='xingce', start=None,
                end=None, record_url=[], limit=None)
            task = {'id':'a','subject':'xingce','url':'https://spa.fenbi.com/ti/exam/solution/a?routecs=xingce'}
            inventories = [([task], {'pagination_complete':False,'limited':False,'issues':['page failed']}),
                           ([], {'pagination_complete':True,'limited':False})]
            with patch('fenbi_exporter.workflow.history_inventory', side_effect=inventories), patch('fenbi_exporter.workflow.export_record', return_value={'status':'complete'}):
                first = execute(args, None)
            self.assertEqual(first['status'], 'partial')
            self.assertEqual(first['complete'], 1)
            manifest = json.loads(Path(first['manifest']).read_text('utf-8'))
            self.assertFalse(manifest['discovery_complete'])
            with patch('fenbi_exporter.workflow.history_inventory', side_effect=[([task],{'pagination_complete':True}),([],{'pagination_complete':True})]) as discovery, patch('fenbi_exporter.workflow.export_record') as export:
                resumed = execute(SimpleNamespace(command='resume', output=Path(tmp), run=first['run_id']), None)
            self.assertEqual(discovery.call_count, 2)
            self.assertEqual(export.call_count, 0)
            self.assertEqual(resumed['status'], 'complete')

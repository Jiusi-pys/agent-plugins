import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'video_extract.py'
spec = importlib.util.spec_from_file_location('video_extract', SCRIPT)
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)


class WorkflowTests(unittest.TestCase):
    def test_runtime_paths_can_be_configured_without_editing_plugin(self):
        with patch.dict(os.environ, {'VIDEO_TEXT_EXTRACT_HOME': str(self.base / 'private'),
                                    'VIDEO_TEXT_EXTRACT_CODES': str(self.base / 'native')}):
            settings = v.Settings()
        self.assertEqual(settings.home, self.base / 'private')
        self.assertEqual(settings.codes, self.base / 'native')

    def test_companion_audio_can_have_misleading_video_mime(self):
        resources = [{'id': 1, 'category': 'video'}, {'id': 2, 'category': 'video'}]
        self.assertEqual(v.validate_selection(resources, 1, 2), (resources[0], resources[1]))

    def test_title_is_used_for_final_filename(self):
        job = self.job()
        job.update(video_title='太行八陉：第四集 / 井陉？')
        final = v.publish(job, '完整正文。')
        self.assertEqual(final.name, '太行八陉：第四集 _ 井陉？.txt')

    def test_filename_handles_windows_reserved_names_and_long_titles(self):
        self.assertEqual(v.title_filename('CON. '), '_CON.txt')
        self.assertEqual(v.title_filename('a<>:"/\\|?*\n标题'), 'a__________标题.txt')
        self.assertLessEqual(len(v.title_filename('长' * 200)), 124)
        self.assertEqual(v.title_filename('...'), '未命名视频.txt')

    def test_recovery_cannot_enter_during_worker_creation(self):
        job = self.job()
        with v.FileLock(self.settings.home / '.ownership.lock'):
            v.recover_abandoned(self.settings)
        self.assertTrue(job.path.exists())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='视频提取 测试 ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.settings = v.Settings(home=self.base)

    def job(self):
        return v.Job.create(self.settings, self.base / '输出 文稿')

    def review_job(self):
        job = self.job()
        chunks = v.split_text('今天是2026年，我们不会改变原意。\n' * 60, 500)
        records = []
        for i, raw in enumerate(chunks):
            records.append({'id': i + 1, 'raw': raw, 'corrected': raw,
                            'source_sha256': v.digest(raw), 'corrected_sha256': v.digest(raw)})
        job.update(state='awaiting_review', chunks=records)
        review = {'model': 'gpt-6-luna', 'reasoning_effort': 'max',
                  'chunks': [{'id': c['id'], 'source_sha256': c['source_sha256'],
                              'corrected_sha256': c['corrected_sha256'], 'text': c['corrected'],
                              'complete': True, 'checked_numbers_negations': True} for c in records]}
        return job, review

    def test_chunking_preserves_every_character(self):
        raw = '甲乙丙。This is a sentence!\n数字123，否定不会。' * 100
        parts = v.split_text(raw, 180)
        self.assertEqual(''.join(parts), raw)
        self.assertTrue(all(0 < len(c) <= 180 for c in parts))
        self.assertEqual(v.split_text(''), [])

    def test_ambiguous_media_does_not_choose_largest(self):
        resources = [{'id': 1, 'category': 'video', 'size': 10},
                     {'id': 2, 'category': 'video', 'size': 1000}]
        self.assertIsNone(v.automatic_selection(resources))
        self.assertEqual(v.automatic_selection(resources[:1]), (1, None))
        self.assertEqual(v.automatic_selection([resources[0], {'id': 3, 'category': 'audio'}]), (1, 3))

    def test_nonmedia_and_invalid_ids_fail(self):
        with self.assertRaises(v.WorkflowError):
            v.validate_selection([{'id': 1, 'category': 'other'}], 1, None)
        with self.assertRaises(v.WorkflowError):
            v.validate_selection([{'id': 1, 'category': 'video'}], 4, None)

    def test_cleanup_stays_within_owned_root(self):
        job = self.job()
        (job.path / 'audio.wav').write_bytes(b'large media')
        user_file = self.base / 'original.txt'
        user_file.write_text('keep', encoding='utf-8')
        job.cleanup()
        self.assertFalse(job.path.exists())
        self.assertEqual(user_file.read_text(), 'keep')
        with self.assertRaises(v.WorkflowError):
            v.Job.open(self.settings, self.base)

    def test_unmarked_directory_is_never_deleted(self):
        foreign = self.settings.work_root / ('job-' + 'a' * 32)
        foreign.mkdir(parents=True)
        (foreign / 'mine.txt').write_text('user')
        v.recover_abandoned(self.settings)
        self.assertTrue((foreign / 'mine.txt').exists())

    def test_active_job_is_not_recovered(self):
        job = self.job()
        with v.FileLock(job.path / '.lock'):
            v.recover_abandoned(self.settings)
            self.assertTrue(job.path.exists())
        v.recover_abandoned(self.settings)
        self.assertFalse(job.path.exists())

    def test_missing_or_duplicate_review_chunks_are_rejected(self):
        job, review = self.review_job()
        with self.assertRaises(v.WorkflowError):
            v.validate_review(job.data, {**review, 'chunks': review['chunks'][:-1]})
        with self.assertRaises(v.WorkflowError):
            v.validate_review(job.data, {**review, 'chunks': review['chunks'] + [review['chunks'][0]]})

    def test_review_hash_and_semantic_checks_are_required(self):
        job, review = self.review_job()
        review['chunks'][0]['source_sha256'] = 'wrong'
        with self.assertRaises(v.WorkflowError):
            v.validate_review(job.data, review)
        review['chunks'][0]['source_sha256'] = job.data['chunks'][0]['source_sha256']
        review['chunks'][0]['checked_numbers_negations'] = False
        with self.assertRaises(v.WorkflowError):
            v.validate_review(job.data, review)

    def test_empty_and_obviously_abridged_review_is_rejected(self):
        job, review = self.review_job()
        for bad in ['', '概括如下']:
            review['chunks'][0]['text'] = bad
            with self.assertRaises(v.WorkflowError):
                v.validate_review(job.data, review)

    def test_merge_sorts_by_original_order(self):
        job, review = self.review_job()
        review['chunks'].reverse()
        result = v.validate_review(job.data, review)
        self.assertEqual(result, '\n\n'.join(c['corrected'].strip() for c in job.data['chunks']) + '\n')

    def test_atomic_publish_preserves_existing_file(self):
        job, review = self.review_job()
        job.update(video_title='视频标题')
        job.output_dir.mkdir(parents=True)
        final = job.output_dir / '视频标题.txt'
        final.write_text('原有文件', encoding='utf-8')
        with self.assertRaises(v.WorkflowError):
            v.publish(job, v.validate_review(job.data, review))
        self.assertEqual(final.read_text(encoding='utf-8'), '原有文件')
        self.assertEqual(list(job.output_dir.iterdir()), [final])

    def test_success_only_leaves_final_txt(self):
        job, review = self.review_job()
        job.update(video_title='中文视频标题')
        (job.path / 'raw.txt').write_text('evidence')
        final = v.publish(job, v.validate_review(job.data, review))
        job.cleanup()
        self.assertEqual([p.name for p in job.output_dir.iterdir()], ['中文视频标题.txt'])
        self.assertTrue(final.read_text(encoding='utf-8'))

    def test_failed_job_cleans_media_and_redacts_credentials(self):
        job = self.job()
        (job.path / 'video.mp4').write_bytes(b'video')
        v.fail_job(job, 'download https://host/video?token=secret failed; Cookie: topsecret')
        self.assertFalse(job.path.exists())
        error = (job.output_dir / 'error.txt').read_text(encoding='utf-8')
        self.assertNotIn('secret', error)
        self.assertEqual([p.name for p in job.output_dir.iterdir()], ['error.txt'])

    def test_local_edits_only_apply_unique_high_confidence_strings(self):
        text = '五日三行五身。不改变2026。重复，重复。'
        edits = [{'from': '五日三行五身', 'to': '吾日三省吾身', 'confidence': .99},
                 {'from': '重复', 'to': '删掉', 'confidence': .99},
                 {'from': '2026', 'to': '2027', 'confidence': .1}]
        result = v.apply_edits(text, edits)
        self.assertEqual(result, '吾日三省吾身。不改变2026。重复，重复。')

    def test_truncated_llama_response_is_rejected(self):
        with self.assertRaises(v.WorkflowError):
            v.parse_correction({'choices': [{'finish_reason': 'length',
                                           'message': {'content': '{"edits":[]}'}}]}, '原文')

    def test_invalid_json_is_not_silently_accepted(self):
        with self.assertRaises(v.WorkflowError):
            v.parse_correction({'choices': [{'finish_reason': 'stop',
                                           'message': {'content': 'not JSON'}}]}, '原文')

    def test_missing_audio_stream_fails(self):
        with self.assertRaises(v.WorkflowError):
            v.validate_audio_probe({'streams': [{'codec_type': 'video'}], 'format': {'duration': '10'}})
        v.validate_audio_probe({'streams': [{'codec_type': 'audio', 'sample_rate': '16000',
                                           'channels': 1, 'codec_name': 'pcm_s16le'}],
                                'format': {'duration': '10'}}, wav=True)

    def test_runner_failure_does_not_expose_sensitive_arguments(self):
        with v.ProcessRunner() as runner:
            with self.assertRaises(v.WorkflowError) as caught:
                runner.run([sys.executable, '-c', 'import sys; sys.exit(7)', 'token=secret'], self.base / 'log')
        self.assertNotIn('secret', str(caught.exception))

    def test_runner_closes_only_its_own_process(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.addCleanup(lambda: (unrelated.terminate(), unrelated.wait()))
        runner = v.ProcessRunner()
        owned = runner.start([sys.executable, '-c', 'import time; time.sleep(60)'], self.base / 'owned.log')
        runner.close()
        self.assertIsNotNone(owned.poll())
        self.assertIsNone(unrelated.poll())

    def test_completed_command_releases_log_handles(self):
        log = self.base / 'capture.stdout'
        with v.ProcessRunner() as runner:
            runner.run([sys.executable, '-c', 'print(123)'], log)
            log.unlink()
            log.with_name(log.name + '.stderr').unlink()
        self.assertFalse(log.exists())

    def test_cancel_interrupts_native_command_and_closes_process(self):
        cancelled = self.base / '.cancel'
        timer = threading.Timer(.3, cancelled.touch)
        timer.start()
        try:
            with v.ProcessRunner(cancelled) as runner:
                with self.assertRaisesRegex(v.WorkflowError, 'cancelled'):
                    runner.run([sys.executable, '-c', 'import time; time.sleep(60)'], self.base / 'cancel.log')
            self.assertTrue(all(process.poll() is not None for process in runner.processes))
        finally:
            timer.cancel()

    def test_gpu_headroom_uses_adapter_usage_not_only_process_budget(self):
        job = self.job()
        class FakeRunner:
            def run(self, args, log, timeout):
                log.with_name(log.name + '.stderr').write_text('')
                return 'Vulkan0: AMD Radeon RX 7900 XTX (24560 MiB, 23749 MiB free)'
        with patch.object(v, 'physical_gpu_free', return_value=3000, create=True):
            self.assertEqual(v.gpu_free(job, FakeRunner()), 3000)


if __name__ == '__main__':
    unittest.main()

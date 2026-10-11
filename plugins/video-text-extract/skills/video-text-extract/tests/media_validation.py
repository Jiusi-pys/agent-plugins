"""Opt-in localhost integration checks for cat-catch and FFmpeg (no models)."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import video_extract as v
from live_validation import QuietHandler


def main():
    with tempfile.TemporaryDirectory(prefix='视频 空格 验证 ') as temporary:
        root = Path(temporary)
        with v.ProcessRunner() as runner:
            runner.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=s=160x120:r=1',
                        '-i', str(v.Settings().codes / 'whisper.cpp/samples/jfk.wav'), '-shortest',
                        '-c:v', 'libx264', '-c:a', 'aac', str(root / 'sample.mp4')], root / 'fixture.log')
            for name, mapping in [('video.mp4', '0:v:0'), ('audio.m4a', '0:a:0')]:
                runner.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(root / 'sample.mp4'),
                            '-map', mapping, '-c', 'copy', str(root / name)], root / (name + '.log'))
            runner.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(root / 'sample.mp4'),
                        '-c', 'copy', '-hls_time', '3', '-hls_playlist_type', 'vod',
                        str(root / 'sample.m3u8')], root / 'hls.log')
        (root / 'index.html').write_text('<meta charset="utf-8"><title>页面标题</title><meta property="og:title" content="中文视频：标题测试"><video autoplay muted controls src="sample.mp4"></video>', encoding='utf-8')
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/'
        try:
            for kind in ['webpage', 'hls', 'split']:
                job = v.Job.create(v.Settings(home=root / '工作 目录'))
                try:
                    with v.ProcessRunner() as runner:
                        args = SimpleNamespace(url=base + ('index.html' if kind == 'webpage' else 'sample.m3u8'),
                                               cookies=None, storage_state=None, wait=2, click=[], resource_id=None,
                                               audio_id=None, selection_timeout=5, duration=None)
                        if kind == 'split':
                            resources = [{'id': 1, 'category': 'video', 'url': base + 'video.mp4'},
                                         {'id': 2, 'category': 'audio', 'url': base + 'audio.m4a'}]
                            v.atomic_json(job.path / 'capture.json', {'schemaVersion': 1, 'resources': resources})
                            selected, companion = resources
                        else:
                            selected, companion = v.capture(job, args, runner)
                            if kind == 'webpage':
                                assert job.data['video_title'] == '中文视频：标题测试', job.data
                                assert v.final_path(job).name == '中文视频：标题测试.txt'
                        wav = v.extract_audio(job, args, runner, selected, companion)
                        assert wav.stat().st_size > 1000
                        assert not list(job.path.glob('source-*'))
                        assert not (job.path / 'video.mkv').exists()
                        assert not (job.path / 'capture.json').exists()
                        print('MEDIA_PASS', kind, flush=True)
                finally:
                    job.cleanup()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()

"""Opt-in real-model validation. Keeps its localhost fixtures alive for Luna.

The main agent reviews the emitted job and submits finish via the installed
script. Fixtures are deleted when the worker finishes. No external website or
login state is involved.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import video_extract as v


class QuietHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args):
        pass


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['short', 'chinese', 'no-audio', 'download-failure', 'webpage', 'hls'], default='short')
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--seconds', type=float, default=180)
    parser.add_argument('--source', type=Path, help='User-provided Chinese video fixture')
    args = parser.parse_args()
    if args.kind == 'chinese' and (args.source is None or not args.source.is_file()):
        parser.error('--kind chinese requires --source pointing to an existing video')
    args.home.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='视频 验证 ', dir=args.home) as temporary:
        root = Path(temporary)
        with v.ProcessRunner() as runner:
            if args.kind == 'chinese':
                source = str(args.source.resolve())
                runner.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-i', source,
                            '-t', str(args.seconds), '-vf', 'scale=320:-2', '-c:v', 'libx264', '-preset', 'ultrafast',
                            '-crf', '30', '-c:a', 'aac', str(root / 'sample.mp4')], root / 'fixture.log')
            else:
                command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'lavfi',
                           '-i', 'color=c=black:s=320x240:r=1']
                if args.kind == 'no-audio':
                    command += ['-t', '2', '-an']
                else:
                    command += ['-i', str(v.Settings().codes / 'whisper.cpp/samples/jfk.wav'), '-shortest', '-c:a', 'aac']
                runner.run(command + ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(root / 'sample.mp4')],
                           root / 'fixture.log')
            if args.kind == 'webpage':
                (root / 'index.html').write_text('<html><body><video autoplay muted controls src="sample.mp4"></video></body></html>')
            if args.kind == 'hls':
                runner.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-i', str(root / 'sample.mp4'),
                            '-c:v', 'libx264', '-c:a', 'aac', '-hls_time', '3', '-hls_playlist_type', 'vod',
                            str(root / 'sample.m3u8')], root / 'hls.log')
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = {**os.environ, 'VIDEO_TEXT_EXTRACT_HOME': str(args.home.resolve()), 'PYTHONUTF8': '1'}
        name = 'missing.mp4' if args.kind == 'download-failure' else 'index.html' if args.kind == 'webpage' else 'sample.m3u8' if args.kind == 'hls' else 'sample.mp4'
        url = f'http://127.0.0.1:{server.server_port}/{name}'
        output = args.home / ('result-' + args.kind)
        if output.exists() and any(output.iterdir()):
            output = args.home / ('result-' + args.kind + '-' + uuid.uuid4().hex[:8])
        process = subprocess.Popen([sys.executable, str(Path(v.__file__)), 'run', url,
                                    '--output-dir', str(output), '--wait', '2'], env=env)
        try:
            code = process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=20)
            server.shutdown()
            server.server_close()
        print('LIVE_VALIDATION_EXIT', code, flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())

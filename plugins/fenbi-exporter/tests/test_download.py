import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fenbi_exporter.core import ExportStore
from fenbi_exporter.workflow import export_attachment

PDF = b'%PDF-1.7\n synthetic test document\n%%EOF'


class DownloadTests(unittest.TestCase):
    def test_real_browser_download_and_pdf_navigation(self):
        class Handler(BaseHTTPRequestHandler):
            expired_once = False
            xhr_requested = False
            def do_GET(self):
                if self.path == '/xhr.pdf' and Handler.xhr_requested:
                    self.send_response(403)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    return
                if self.path == '/xhr.pdf':
                    Handler.xhr_requested = True
                if self.path == '/expired.pdf' and not Handler.expired_once:
                    Handler.expired_once = True
                    self.send_response(403)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html>expired signature</html>')
                    return
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                if self.path == '/style.css':
                    self.send_header('Content-Type', 'text/css')
                    self.send_header('Content-Disposition', 'attachment; filename=style.css')
                    self.end_headers()
                    self.wfile.write(b'body{color:red}')
                    return
                self.send_header('Content-Type', 'application/pdf')
                if '/attachment' in self.path:
                    self.send_header('Content-Disposition', 'attachment; filename=lesson.pdf')
                self.end_headers()
                self.wfile.write(PDF)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(accept_downloads=True)
                session = SimpleNamespace(context=context)
                for mode in ['attachment', 'inline.pdf', 'popup.pdf', 'expired.pdf', 'xhr.pdf']:
                    with self.subTest(mode=mode):
                        def open_group(_b, page, *_):
                            page.set_content(f'''<link rel="stylesheet" href="http://127.0.0.1:{server.server_port}/style.css"><div class="row"><div class="title">测试课时</div><button class="downloadPDF">下载讲义</button></div>
                            <a class="material-download-modal-item" {'target="_blank"' if mode=='popup.pdf' else ''} href="http://127.0.0.1:{server.server_port}/{mode}">讲义</a>''')
                            if mode == 'xhr.pdf':
                                page.locator('.material-download-modal-item').evaluate('''e => {e.onclick=async event=>{event.preventDefault();const r=await fetch(e.href);const blob=await r.blob();await new Promise(r=>setTimeout(r,1000));const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='large.pdf';a.click();};}''')
                            return page.locator('.row')
                        item = {'id':mode,'url':'https://www.fenbi.com/spa/pwa/episodes/1','set':'主课时集',
                            'group':'科目','row':0,'lesson':'测试课时','attachment':0,'label':'讲义','course_title':'测试'}
                        from contextlib import nullcontext
                        # Large real XHR downloads may exceed Chromium's response-body buffer.
                        body = patch('playwright.sync_api.Response.body', side_effect=RuntimeError('evicted buffer')) if mode == 'xhr.pdf' else nullcontext()
                        with patch('fenbi_exporter.workflow.open_course_group', side_effect=open_group), body:
                            result = export_attachment(session, ExportStore(Path(tmp)), item)
                        self.assertEqual(result['status'], 'complete')
                        self.assertEqual((Path(tmp) / result['path']).read_bytes(), PDF)
                context.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

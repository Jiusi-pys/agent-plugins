"""Opt-in real-engine acceptance: set TEST_CALIBRE and TEST_PANDOC.

No downloads or installations occur here. The full matrix reads converted books
back as EPUB, rather than considering an exit code or file existence sufficient.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lxml import etree as E
from urllib.parse import unquote, urlsplit
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
CALIBRE = os.environ.get('TEST_CALIBRE')
PANDOC = os.environ.get('TEST_PANDOC')
FORMATS = ('txt', 'epub', 'mobi', 'html', 'md', 'azw3', 'docx', 'rtf', 'fb2', 'odt')
FIRST = '第一章中文AlphaSentinel'
SECOND = '第二章中文OmegaSentinel'
NOTE = '跨文件注释NoteSentinel'
X = 'http://www.w3.org/1999/xhtml'
O = 'http://www.idpf.org/2007/opf'
EP = 'http://www.idpf.org/2007/ops'


def fixture(path, *, linear_note=False, ordinary_note=False):
    image = io.BytesIO()
    Image.new('RGB', (31, 47), (51, 103, 157)).save(image, format='PNG')
    note_spine = '<itemref idref="notes" linear="no"/>' if linear_note else ''
    files = {
        'mimetype': b'application/epub+zip',
        'META-INF/container.xml': b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        'OPS/package.opf': f'''<package xmlns="{O}" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">urn:test:conversion</dc:identifier><dc:title>中文转换验收</dc:title><dc:creator>Test Author</dc:creator><dc:language>zh-CN</dc:language><meta property="dcterms:modified">2026-10-11T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="text/one.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="text/two.xhtml" media-type="application/xhtml+xml"/><item id="notes" href="notes.xhtml" media-type="application/xhtml+xml"/><item id="pic" href="images/sample.png" media-type="image/png"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/>{note_spine}</spine></package>'''.encode(),
        'OPS/nav.xhtml': f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>目录</title></head><body><nav epub:type="toc"><ol><li><a href="text/one.xhtml#c1">第一章</a></li><li><a href="text/two.xhtml#c2">第二章</a></li></ol></nav></body></html>'.encode(),
        'OPS/text/one.xhtml': f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>一</title></head><body><h1 id="c1">第一章</h1><p>{FIRST}</p><p><img src="../images/sample.png" alt="sample-image"/></p><p>引用<a epub:type="noteref" role="doc-noteref" href="../notes.xhtml#n1">[1]</a></p><p><a href="https://example.com/">普通外部超链接</a></p></body></html>'.encode(),
        'OPS/text/two.xhtml': f'<html xmlns="{X}"><head><title>二</title></head><body><h1 id="c2">第二章</h1><p>{SECOND}</p></body></html>'.encode(),
        'OPS/notes.xhtml': f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>注释</title></head><body><aside id="n1" epub:type="footnote" role="doc-footnote"><p>{NOTE}</p></aside></body></html>'.encode(),
        'OPS/images/sample.png': image.getvalue(),
    }
    if ordinary_note:
        files['OPS/text/one.xhtml'] = files['OPS/text/one.xhtml'].replace(b' epub:type="noteref" role="doc-noteref"', b'')
    with zipfile.ZipFile(path, 'w') as archive:
        for name, value in files.items():
            archive.writestr(name, value, compress_type=zipfile.ZIP_STORED if name == 'mimetype' else zipfile.ZIP_DEFLATED)


def body_text(path):
    from epub_editor import read_package, elements, resolve, xml
    data, opath, opf = read_package(path)
    items = {item.get('id'): item for item in elements(opf, 'item')}
    chunks = []
    for ref in elements(opf, 'itemref'):
        item = items[ref.get('idref')]
        if 'nav' not in item.get('properties', '') and item.get('media-type') == 'application/xhtml+xml':
            root = xml(data[resolve(opath, item.get('href'))[0]])
            for body in elements(root, 'body'):
                chunks.append(''.join(body.itertext()))
    return '\n'.join(chunks)


@unittest.skipUnless(CALIBRE and PANDOC, 'opt-in real engines: TEST_CALIBRE and TEST_PANDOC')
class RealConversion(unittest.TestCase):
    def setUp(self):
        from ebook_convert import convert
        self.convert = lambda source, output, **kw: convert(source, output, calibre=CALIBRE, pandoc=PANDOC, timeout=120, **kw)
        self.tmp = tempfile.TemporaryDirectory(prefix='书籍 conversion ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / '原书 input.epub'
        fixture(self.source)

    def assert_content(self, path):
        text = body_text(path)
        self.assertIn(FIRST, text, str(path))
        self.assertIn(SECOND, text, str(path))
        self.assertLess(text.index(FIRST), text.index(SECOND), str(path))

    def assert_fixture_image(self, data):
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (31, 47))
            pixel = image.convert('RGB').getpixel((15, 23))
            self.assertTrue(all(abs(a - b) <= 3 for a, b in zip(pixel, (51, 103, 157))), pixel)

    def assert_epub_fixture_image(self, path):
        from epub_editor import elements, read_package, resolve, xml
        data, opath, opf = read_package(path)
        candidates = []
        for item in elements(opf, 'item'):
            if item.get('media-type') == 'application/xhtml+xml':
                document_path = resolve(opath, item.get('href'))[0]
                for image in elements(xml(data[document_path]), 'img'):
                    target = resolve(document_path, image.get('src', ''))
                    if target and target[0] in data:
                        try:
                            with Image.open(io.BytesIO(data[target[0]])) as picture:
                                if picture.size == (31, 47):
                                    candidates.append(data[target[0]])
                        except OSError:
                            pass
        self.assertTrue(candidates, str(path))
        self.assert_fixture_image(candidates[0])

    def test_all_90_cross_format_directions_read_back(self):
        original = hashlib.sha256(self.source.read_bytes()).hexdigest()
        sources = {'epub': self.source}
        for extension in FORMATS:
            if extension != 'epub':
                target = self.root / ('source.' + extension)
                report = self.convert(self.source, target)
                self.assertEqual(report['issues'], [], report)
                sources[extension] = target

        def check_pair(source_extension, target_extension):
            target = self.root / (source_extension + '-to-' + target_extension + '.' + target_extension)
            report = self.convert(sources[source_extension], target)
            self.assertEqual(report['issues'], [], report)
            if target_extension != 'epub':
                readback = self.root / (source_extension + '-to-' + target_extension + '-readback.epub')
                report = self.convert(target, readback)
                self.assertEqual(report['issues'], [], report)
            else:
                readback = target
            self.assert_content(readback)
            return source_extension + '->' + target_extension

        verified = []
        failures = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = {pool.submit(check_pair, a, b): (a, b) for a in FORMATS for b in FORMATS if a != b}
            for future in as_completed(jobs):
                pair = jobs[future]
                try:
                    verified.append(future.result())
                except Exception as exc:
                    failures.append(str(pair) + ': ' + str(exc)[:600])
        self.assertFalse(failures, '\n'.join(failures))
        self.assertEqual(len(verified), 90)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), original)
        report_path = os.environ.get('CONVERSION_MATRIX_REPORT')
        if report_path:
            Path(report_path).write_text(json.dumps({'verified_directions': sorted(verified), 'count': 90, 'checks': ['Chinese body text', 'chapter order', 'EPUB readback', 'unchanged original']}, ensure_ascii=False, indent=2), encoding='utf-8')

    def test_images_and_non_spine_notes_survive_pandoc_outputs(self):
        for linear_note, ordinary_note in ((False, False), (True, False), (False, True)):
            with self.subTest(linear_note=linear_note, ordinary_note=ordinary_note):
                label = str(linear_note) + '-' + str(ordinary_note)
                source = self.root / ('notes-' + label + '.epub')
                fixture(source, linear_note=linear_note, ordinary_note=ordinary_note)
                for extension in ('html', 'md', 'odt'):
                    output = self.root / ('notes-' + label + '.' + extension)
                    report = self.convert(source, output)
                    self.assertEqual(report['issues'], [], report)
                    if extension == 'html':
                        document = E.HTML(output.read_bytes(), parser=E.HTMLParser(encoding='utf-8'))
                        self.assertIn(NOTE, ''.join(document.itertext()))
                        links = document.xpath('//a[normalize-space(string(.))="[1]"]/@href')
                        self.assertTrue(links, output)
                        self.assertTrue(links[0].startswith('#'), links)
                        target = links[0].split('#')[-1]
                        targets = document.xpath('//*[@id=$id]', id=target)
                        self.assertEqual(len(targets), 1)
                        self.assertIn(NOTE, ''.join(targets[0].itertext()))
                        images = document.xpath('//img/@src')
                        embedded = [value for value in images if value.startswith('data:image/')]
                        self.assertTrue(embedded)
                        self.assert_fixture_image(base64.b64decode(embedded[0].split(',', 1)[1]))
                    elif extension == 'md':
                        content = output.read_text(encoding='utf-8')
                        self.assertIn(NOTE, content)
                        image_links = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content)
                        self.assertTrue(image_links, content)
                        for link in image_links:
                            link = link.strip('<>')
                            self.assertFalse(Path(link).is_absolute(), link)
                            self.assertTrue((output.parent / link).is_file(), link)
                            self.assert_fixture_image((output.parent / unquote(link)).read_bytes())
                        rendered = self.root / ('markdown-links-' + label + '.html')
                        process = subprocess.run([PANDOC, str(output), '--from=markdown', '--to=html5', '--sandbox', '--output=' + str(rendered)], capture_output=True, timeout=120)
                        self.assertEqual(process.returncode, 0, process.stderr)
                        document = E.HTML(rendered.read_bytes(), parser=E.HTMLParser(encoding='utf-8'))
                        links = document.xpath('//a[normalize-space(string(.))="[1]"]/@href')
                        self.assertTrue(links, content)
                        self.assertTrue(links[0].startswith('#'), links)
                        targets = document.xpath('//*[@id=$id]', id=links[0].split('#')[-1])
                        self.assertEqual(len(targets), 1)
                        self.assertIn(NOTE, ''.join(targets[0].itertext()))
                    else:
                        with zipfile.ZipFile(output) as archive:
                            content = E.fromstring(archive.read('content.xml'))
                            self.assertIn(NOTE, ''.join(content.itertext()))
                            self.assertTrue(any(name.startswith('Pictures/') for name in archive.namelist()))
                            namespace = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0', 'xlink': 'http://www.w3.org/1999/xlink'}
                            links = content.xpath('//text:a[normalize-space(string(.))="[1]"]/@xlink:href', namespaces=namespace)
                            self.assertTrue(links, E.tostring(content).decode())
                            self.assertTrue(links[0].startswith('#'), links)
                            bookmarks = content.xpath('//*[@text:name=$name]', namespaces=namespace, name=links[0].lstrip('#'))
                            # Native bookmarks and an enclosing section can
                            # name the same content range. Resolve the actual
                            # bookmark, rather than counting both as positions.
                            starts = [node for node in bookmarks if E.QName(node).localname in ('bookmark', 'bookmark-start')]
                            self.assertEqual(len(starts), 1)
                            target = starts[0].getparent()
                            self.assertIn(NOTE, ''.join(target.itertext()))
                            refs = content.xpath('//*[local-name()="image"]/@xlink:href', namespaces=namespace)
                            self.assertTrue(refs)
                            self.assert_fixture_image(archive.read(refs[0]))

    def test_container_formats_keep_the_referenced_image_on_readback(self):
        for extension in ('mobi', 'azw3', 'docx', 'rtf', 'fb2'):
            with self.subTest(extension=extension):
                output = self.root / ('image.' + extension)
                self.convert(self.source, output)
                readback = self.root / ('image-' + extension + '.epub')
                self.convert(output, readback)
                self.assert_epub_fixture_image(readback)

    def test_document_note_links_point_to_content_after_round_trip(self):
        for extension in ('rtf', 'odt'):
            with self.subTest(extension=extension):
                output = self.root / ('note-roundtrip.' + extension)
                self.convert(self.source, output)
                rendered = self.root / ('note-roundtrip-' + extension + '.html')
                self.convert(output, rendered)
                document = E.HTML(rendered.read_bytes(), parser=E.HTMLParser(encoding='utf-8'))
                links = document.xpath('//a[normalize-space(string(.))="[1]"]/@href')
                self.assertTrue(links, extension)
                self.assertTrue(links[0].startswith('#'), links)
                targets = document.xpath('//*[@id=$id]', id=links[0].split('#')[-1])
                self.assertEqual(len(targets), 1, extension)
                target = targets[0]
                text = ''.join(target.itertext())
                if not text.strip():
                    # Some importers represent a native bookmark as an empty
                    # inline anchor inside the note's paragraph.
                    parent = target.getparent()
                    self.assertEqual(E.QName(parent).localname, 'p', extension)
                    text = ''.join(parent.itertext())
                self.assertIn(NOTE, text, extension)

    def test_explicit_gb18030_text_is_decoded_without_replacement(self):
        source = self.root / '编码.txt'
        source.write_bytes((FIRST + '\n\n' + SECOND).encode('gb18030'))
        output = self.root / '编码.epub'
        self.convert(source, output, input_encoding='gb18030')
        self.assert_content(output)

    def test_remote_images_and_fb2_css_do_not_make_http_requests_or_publish(self):
        hits = []

        class Handler(BaseHTTPRequestHandler):
            def parse_request(self):
                valid = super().parse_request()
                hits.append((self.command, self.path))
                return valid

            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'untrusted remote image')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = 'http://127.0.0.1:' + str(server.server_port) + '/image.png'
            source = self.root / 'remote.html'
            source.write_text('<html><body><p>正文</p><img src="' + url + '"/></body></html>', encoding='utf-8')
            output = self.root / 'blocked.epub'
            from ebook_convert import ConversionError
            with self.assertRaisesRegex(ConversionError, '(?i)remote|external'):
                self.convert(source, output)
            self.assertFalse(output.exists())
            with zipfile.ZipFile(self.source) as archive:
                entries = {name: archive.read(name) for name in archive.namelist()}
            entries['OPS/text/one.xhtml'] = entries['OPS/text/one.xhtml'].replace(b'../images/sample.png', url.encode())
            unsafe = self.root / 'remote.epub'
            with zipfile.ZipFile(unsafe, 'w') as archive:
                for name, content in entries.items():
                    archive.writestr(name, content)
            for extension in ('html', 'md', 'odt'):
                output = self.root / ('blocked.' + extension)
                with self.assertRaisesRegex(ConversionError, '(?i)remote|external'):
                    self.convert(unsafe, output)
                self.assertFalse(output.exists())
            fb2 = self.root / 'remote-stylesheet.fb2'
            fb2.write_text('<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"><stylesheet type="text/css">@import url("' + url + '");</stylesheet><body><section><p>正文</p></section></body></FictionBook>', encoding='utf-8')
            output = self.root / 'blocked-fb2.epub'
            with self.assertRaisesRegex(ConversionError, '(?i)remote|external'):
                self.convert(fb2, output)
            self.assertFalse(output.exists())
            self.assertEqual(hits, [])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_docx_cannot_read_external_synthetic_file(self):
        from ebook_convert import ConversionError
        source = self.root / 'template.docx'
        self.convert(self.source, source)
        with zipfile.ZipFile(source) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        private = self.root / 'outside-input-dir.bin'
        private.write_bytes(b'SYNTHETIC_PRIVATE_FILE_SENTINEL_72109')
        altered = 0
        for name, content in list(entries.items()):
            if name.endswith('.rels'):
                root = E.fromstring(content)
                for node in root:
                    if node.get('Type', '').endswith('/image'):
                        node.set('Target', private.as_uri())
                        node.set('TargetMode', 'External')
                        altered += 1
                entries[name] = E.tostring(root, encoding='utf-8', xml_declaration=True)
        self.assertGreater(altered, 0)
        folder = self.root / 'input-only'
        folder.mkdir()
        unsafe = folder / 'untrusted.docx'
        with zipfile.ZipFile(unsafe, 'w') as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        output = self.root / 'must-not-exist.epub'
        with self.assertRaisesRegex(ConversionError, '(?i)external|absolute|resource'):
            self.convert(unsafe, output)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()

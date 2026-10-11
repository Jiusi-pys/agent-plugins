import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from lxml import etree as E

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ebook_convert import convert, doctor, formats, ConversionError
from test_epub import book, X, EP


class Conversion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '中文 source.epub'
        book(self.source)
        self.calls = []

    def rewrite(self, action):
        with zipfile.ZipFile(self.source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        action(data)
        with zipfile.ZipFile(self.source, 'w') as z:
            for n, content in data.items():
                z.writestr(n, content)

    def fake_run(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if '--version' in args:
            return subprocess.CompletedProcess(args, 0, 'fake engine 1.0', '')
        if '--output' in args:
            dest = Path(args[args.index('--output') + 1])
        else:
            dest = Path(args[2])
        dest = Path(kwargs['cwd']) / dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.suffix == '.epub':
            book(dest)
        elif dest.suffix == '.json':
            extract = next((value for value in args if value.startswith('--extract-media=')), None)
            if extract:
                media = Path(kwargs['cwd']) / extract.split('=', 1)[1]
                media.mkdir()
                (media / 'image.png').write_bytes(b'local image')
            dest.write_text(json.dumps({'pandoc-api-version': [1, 23, 1], 'meta': {}, 'blocks': [
                {'t': 'Para', 'c': [{'t': 'Link', 'c': [['', [], []], [{'t': 'Str', 'c': '[1]'}], ['#note.id', '']]}]},
                {'t': 'Para', 'c': [{'t': 'Image', 'c': [['', [], []], [], ['rtf-media/image.png', '']]}]},
                {'t': 'Div', 'c': [['note.id', [], []], [{'t': 'Para', 'c': [{'t': 'Str', 'c': 'NoteContent'}]}]]}]}), encoding='utf-8')
        elif dest.suffix in ('.mobi', '.azw3'):
            data = bytearray(150)
            data[60:68] = b'BOOKMOBI'
            data[76:78] = (1).to_bytes(2, 'big')
            data[78:82] = (90).to_bytes(4, 'big')
            data[106:110] = b'MOBI'
            dest.write_bytes(data)
        elif dest.suffix == '.docx':
            with zipfile.ZipFile(dest, 'w') as z:
                z.writestr('[Content_Types].xml', '<Types/>')
                z.writestr('word/document.xml', '<document><body><p>正文</p></body></document>')
        elif dest.suffix == '.odt':
            with zipfile.ZipFile(dest, 'w') as z:
                z.writestr('mimetype', 'application/vnd.oasis.opendocument.text')
                z.writestr('content.xml', '<document-content><body><p>正文</p></body></document-content>')
        elif dest.suffix == '.fb2':
            dest.write_text('<FictionBook><body><section><p>正文</p></section></body></FictionBook>', encoding='utf-8')
        elif dest.suffix == '.rtf':
            dest.write_text(r'{\rtf1 正文}', encoding='utf-8')
        elif dest.suffix in ('.html', '.htm'):
            dest.write_text('<!doctype html><html><head><title>书</title></head><body><h1 id="chapter">第一章</h1><p>正文</p></body></html>', encoding='utf-8')
        elif dest.suffix == '.md':
            assets_arg = next(a for a in args if a.startswith('--extract-media='))
            assets = Path(kwargs['cwd']) / assets_arg.split('=', 1)[1]
            assets.mkdir()
            (assets / 'image.png').write_bytes(b'image')
            dest.write_text(f'# 第一章\n\n正文 ![插图](<{assets.name}/image.png>)', encoding='utf-8')
        else:
            dest.write_text('第一章\n正文', encoding='utf-8')
        return subprocess.CompletedProcess(args, 0, 'engine log', '')

    def perform(self, extension, source=None, run=None):
        output = self.root / ('结果 book.' + extension)
        with patch('ebook_convert.subprocess.run', side_effect=run or self.fake_run):
            result = convert(source or self.source, output, calibre=sys.executable, pandoc=sys.executable)
        return output, result

    def test_formats_cover_ten_kinds_and_aliases(self):
        report = formats()
        expected = {'txt', 'epub', 'mobi', 'html', 'markdown', 'azw3', 'docx', 'rtf', 'fb2', 'odt'}
        self.assertEqual(set(report['input']), expected)
        self.assertEqual(set(report['output']), expected)
        self.assertEqual(report['aliases']['htm'], 'html')
        self.assertEqual(report['aliases']['md'], 'markdown')

    def test_all_output_routes(self):
        for extension in ('txt', 'mobi', 'html', 'md', 'azw3', 'docx', 'rtf', 'fb2', 'odt'):
            with self.subTest(extension=extension):
                output, report = self.perform(extension)
                self.assertTrue(output.exists())
                self.assertEqual(report['issues'], [])
                self.assertEqual(report['output'], str(output.resolve()))
                args, opts = self.calls[-1]
                self.assertFalse(opts.get('shell', False))
                self.assertGreater(opts['timeout'], 0)
                if extension in ('html', 'md', 'odt', 'rtf'):
                    self.assertIn('--sandbox', args)
                    self.assertIn('--fail-if-warnings', args)
                if extension == 'html':
                    self.assertIn('--standalone', args)
                    self.assertIn('--embed-resources', args)

    def test_epub_copy_is_identical_without_engine_or_editor(self):
        output = self.root / 'copy.epub'
        with patch('ebook_convert.subprocess.run') as run:
            report = convert(self.source, output)
        self.assertEqual(output.read_bytes(), self.source.read_bytes())
        self.assertEqual(report['engines'], [])
        run.assert_not_called()

    def test_markdown_input_uses_pandoc_to_preserve_native_attributes(self):
        source = self.root / 'input.markdown'
        content = '# 标题\n[]{#n1}\n::: {#note}\n正文\n:::\n'
        source.write_text(content, encoding='utf-8')
        _, report = self.perform('epub', source)
        args = self.calls[0][0]
        self.assertIn('--from=markdown', args)
        self.assertIn('--to=epub3', args)
        self.assertIn('--sandbox', args)
        self.assertIn('--fail-if-warnings', args)
        self.assertEqual(report['engines'][0]['name'], 'pandoc')
        self.assertEqual(report['input_format'], 'markdown')
        self.assertEqual(source.read_text(encoding='utf-8'), content)

    def test_html_alias(self):
        source = self.root / 'input.htm'
        source.write_text('<html><body><p>正文</p></body></html>', encoding='utf-8')
        _, report = self.perform('txt', source)
        self.assertEqual(report['input_format'], 'html')

    def test_original_input_is_unchanged(self):
        before = self.source.read_bytes()
        self.perform('mobi')
        self.assertEqual(self.source.read_bytes(), before)

    def test_existing_output_and_source_output_refused(self):
        with self.assertRaises((ConversionError, ValueError)):
            convert(self.source, self.source)
        out = self.root / 'existing.txt'
        out.write_bytes(b'keep')
        with self.assertRaises((ConversionError, FileExistsError)):
            convert(self.source, out, calibre=sys.executable)
        self.assertEqual(out.read_bytes(), b'keep')

    def test_missing_engine_never_creates_output(self):
        out = self.root / 'missing.mobi'
        with patch('ebook_convert._find_engine', return_value=None):
            with self.assertRaises(ConversionError):
                convert(self.source, out)
        self.assertFalse(out.exists())

    def test_unsupported_extension_and_missing_source(self):
        with self.assertRaises(ConversionError):
            convert(self.source, self.root / 'out.pdf')
        with self.assertRaises((ConversionError, FileNotFoundError)):
            convert(self.root / 'missing.txt', self.root / 'out.epub')

    def test_timeout_nonzero_empty_and_corrupt_outputs_fail(self):
        def bad(args, **opts):
            dest = Path(opts['cwd']) / (args[args.index('--output') + 1] if '--output' in args else args[2])
            dest.write_bytes(b'corrupt')
            return subprocess.CompletedProcess(args, 0, '', '')
        for run in (subprocess.TimeoutExpired(['fake'], 1), subprocess.CompletedProcess([], 1, '', 'failed'),
                    subprocess.CompletedProcess([], 0, '', ''), bad):
            with self.subTest(run=run), patch('ebook_convert.subprocess.run', side_effect=run if callable(run) or isinstance(run, Exception) else None, return_value=run if not callable(run) else None):
                out = self.root / 'failed.epub'
                source = self.root / 'text.txt'
                source.write_text('正文', encoding='utf-8')
                with self.assertRaises(ConversionError):
                    convert(source, out, calibre=sys.executable)
                self.assertFalse(out.exists())

    def test_pandoc_warning_fails_without_publish(self):
        def warning(args, **opts):
            result = self.fake_run(args, **opts)
            result.stderr = '[WARNING] Could not fetch resource'
            return result
        with self.assertRaises(ConversionError):
            self.perform('md', run=warning)
        self.assertFalse((self.root / '结果 book.md').exists())
        self.assertFalse((self.root / '结果 book_assets').exists())

    def test_markdown_assets_are_relative_complete_and_source_independent(self):
        out, report = self.perform('md')
        self.assertEqual(report['assets'], [str((self.root / '结果 book_assets').resolve())])
        self.assertIn('结果 book_assets/image.png', out.read_text(encoding='utf-8'))
        self.assertTrue((self.root / '结果 book_assets/image.png').is_file())
        self.assertNotIn('Temporary', out.read_text(encoding='utf-8'))

    def test_assets_conflict_preserves_existing_directory(self):
        assets = self.root / '结果 book_assets'
        assets.mkdir()
        (assets / 'keep').write_bytes(b'keep')
        with self.assertRaises((ConversionError, FileExistsError)):
            self.perform('md')
        self.assertEqual((assets / 'keep').read_bytes(), b'keep')

    def test_local_markdown_image_is_staged_with_content(self):
        source = self.root / 'input.md'
        source.write_text('# 书\n\n正文 image.png\n![图](image.png)\n![引用][pic]\n\n[pic]: image.png\n\n`![代码](image.png)`\n```md\n![代码块](image.png)\n```\n', encoding='utf-8')
        (self.root / 'image.png').write_bytes(b'local image')
        def run(args, **opts):
            staged = Path(args[1])
            self.assertTrue((staged.parent / 'image.png').exists())
            text = staged.read_text(encoding='utf-8')
            self.assertEqual(text.count('data:image/png;base64,bG9jYWwgaW1hZ2U='), 2)
            self.assertIn('正文 image.png', text)
            self.assertIn('`![代码](image.png)`', text)
            self.assertIn('![代码块](image.png)', text)
            return self.fake_run(args, **opts)
        self.perform('epub', source, run)

    def test_raw_svg_image_in_markdown_is_embedded_for_sandbox(self):
        source = self.root / 'svg.md'
        source.write_text('# Cover\n\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><image xlink:href="cover_image.jpg"/></svg>\n', encoding='utf-8')
        (self.root / 'cover_image.jpg').write_bytes(b'local image')
        def run(args, **opts):
            text = Path(args[1]).read_text(encoding='utf-8')
            self.assertIn('xlink:href="data:image/jpeg;base64,bG9jYWwgaW1hZ2U="', text)
            return self.fake_run(args, **opts)
        self.perform('epub', source, run)

    def test_text_staging_keeps_newlines_without_windows_double_conversion(self):
        source = self.root / 'linebreaks.txt'
        source.write_text('第一行\n\n第二行\n', encoding='utf-8')
        def run(args, **opts):
            self.assertEqual(Path(args[1]).read_text(encoding='utf-8'), source.read_text(encoding='utf-8'))
            return self.fake_run(args, **opts)
        self.perform('epub', source, run)

    def test_ordinary_link_to_marked_nonspine_note_is_normalized(self):
        def change(data):
            data['OPS/package.opf'] = data['OPS/package.opf'].replace(b'<itemref idref="n"/>', b'')
            data['OPS/text/c.xhtml'] = data['OPS/text/c.xhtml'].replace(b'epub:type="noteref" ', b'')
            data['OPS/notes.xhtml'] = data['OPS/notes.xhtml'].replace(b'<p id="n1">', b'<p id="n1" role="doc-footnote">')
        self.rewrite(change)
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as archive:
                root = E.fromstring(archive.read('OPS/package.opf'))
                self.assertTrue(root.xpath('//*[local-name()="itemref" and @idref="n"]'))
            return self.fake_run(args, **opts)
        self.perform('html', run=run)

    def test_paragraph_and_legacy_named_anchors_become_preserved_containers(self):
        def change(data):
            data['OPS/text/c.xhtml'] = data['OPS/text/c.xhtml'].replace(b'</body>', b'<a href="#legacy">Go</a><a name="legacy"></a></body>')
        self.rewrite(change)
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as archive:
                note = E.fromstring(archive.read('OPS/notes.xhtml'))
                target = note.xpath('//*[@id="n1"]')[0]
                self.assertEqual(E.QName(target).localname, 'div')
                self.assertEqual(''.join(target.itertext()), '注释的内容')
                chapter = E.fromstring(archive.read('OPS/text/c.xhtml'))
                legacy = chapter.xpath('//*[@id="legacy"]')[0]
                self.assertEqual(E.QName(legacy).localname, 'span')
            return self.fake_run(args, **opts)
        self.perform('html', run=run)

    def test_zip_normalization_aliases_rejected_before_engine(self):
        for alias in ('OPS/text/./c.xhtml', 'OPS/text//c.xhtml', 'OPS/text/c.xhtml.', 'OPS/text/c.xhtml ', 'OPS/text/CON.xhtml'):
            with self.subTest(alias=alias):
                book(self.source)
                self.rewrite(lambda data: data.update({alias: b'<html><body>replacement</body></html>'}))
                with patch('ebook_convert.subprocess.run') as run:
                    with self.assertRaises(ConversionError):
                        convert(self.source, self.root / 'alias.txt', calibre=sys.executable)
                run.assert_not_called()

    def test_fb2_external_css_and_broken_binary_images_rejected_before_engine(self):
        for index, fragment in enumerate(('<stylesheet type="text/css">@import url(http://127.0.0.1:9/external.css);</stylesheet>',
                         '<image xmlns:l="http://www.w3.org/1999/xlink" l:href="file:///outside.png"/>',
                         '<image xmlns:l="http://www.w3.org/1999/xlink" l:href="#missing"/>')):
            with self.subTest(fragment=fragment):
                source = self.root / 'input.fb2'
                source.write_text('<FictionBook>' + fragment + '<body><section><p>正文</p></section></body></FictionBook>', encoding='utf-8')
                calls = []
                def run(args, **kwargs):
                    calls.append(args)
                    return self.fake_run(args, **kwargs)
                with patch('ebook_convert.subprocess.run', side_effect=run):
                    with self.assertRaises(ConversionError):
                        convert(source, self.root / ('fb2-' + str(index) + '.epub'), calibre=sys.executable)
                self.assertEqual(calls, [])

    def test_fb2_embedded_binary_image_is_allowed(self):
        source = self.root / 'input.fb2'
        source.write_text('<FictionBook xmlns:l="http://www.w3.org/1999/xlink"><body><section><image l:href="#image"/><p>正文</p></section></body><binary id="image" content-type="image/png">bG9jYWwgaW1hZ2U=</binary></FictionBook>', encoding='utf-8')
        self.perform('epub', source)

    def test_docx_odt_resource_validation_runs_before_engine(self):
        packages = {
            'docx': {'[Content_Types].xml': '<Types/>', 'word/document.xml': '<document><body/></document>',
                     'word/_rels/document.xml.rels': '<Relationships><Relationship Id="r" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" TargetMode="External" Target="file:///outside.png"/></Relationships>'},
            'odt': {'mimetype': 'application/vnd.oasis.opendocument.text',
                    'content.xml': '<document-content xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:xlink="http://www.w3.org/1999/xlink"><body><draw:image xlink:href="http://127.0.0.1:9/outside.png"/></body></document-content>'},
        }
        for kind, data in packages.items():
            with self.subTest(kind=kind):
                source = self.root / ('container.' + kind)
                with zipfile.ZipFile(source, 'w') as archive:
                    for name, content in data.items():
                        archive.writestr(name, content)
                calls = []
                def run(args, **kwargs):
                    calls.append(args)
                    return self.fake_run(args, **kwargs)
                with patch('ebook_convert.subprocess.run', side_effect=run):
                    with self.assertRaises(ConversionError):
                        convert(source, self.root / (kind + '.epub'), calibre=sys.executable)
                self.assertEqual(calls, [])

    def test_html_markdown_remote_and_outside_resources_refused(self):
        cases = {
            'md': ('![图](https://127.0.0.1:9/image.png)', '![图](../private.png)',
                   '![图][x]\n\n[x]: https://127.0.0.1:9/image.png'),
            'html': ('<img src="https://127.0.0.1:9/image.png">', '<img src="../private.png">',
                     '<iframe src="https://127.0.0.1:9"></iframe>', '<p onclick="evil()">正文</p>'),
        }
        for suffix, texts in cases.items():
            for content in texts:
                with self.subTest(content=content):
                    source = self.root / ('unsafe.' + suffix)
                    source.write_text(content, encoding='utf-8')
                    with patch('ebook_convert.subprocess.run') as run:
                        with self.assertRaises(ConversionError):
                            convert(source, self.root / 'unsafe.epub', calibre=sys.executable)
                    run.assert_not_called()

    def test_plain_remote_hyperlink_is_allowed(self):
        source = self.root / 'links.html'
        source.write_text('<a href="https://example.org/book">参考资料</a><p>正文</p>', encoding='utf-8')
        self.perform('epub', source)

    def test_epub_script_remote_resource_and_zip_symlink_refused(self):
        for fragment in (b'<script>evil()</script>', b'<img src="https://127.0.0.1:9/x.png"/>', b'<p onclick="evil()">x</p>'):
            book(self.source)
            self.rewrite(lambda d: d.update({'OPS/text/c.xhtml': d['OPS/text/c.xhtml'].replace(b'</body>', fragment+b'</body>')}))
            with patch('ebook_convert.subprocess.run') as run:
                with self.assertRaises(ConversionError):
                    convert(self.source, self.root / 'unsafe.mobi', calibre=sys.executable)
            run.assert_not_called()
        book(self.source)
        with zipfile.ZipFile(self.source, 'a') as z:
            info = zipfile.ZipInfo('OPS/link')
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            z.writestr(info, '../private')
        with self.assertRaises(ConversionError):
            self.perform('txt')

    def test_nonspine_notes_and_non_linear_docs_normalized_only_for_pandoc(self):
        self.rewrite(lambda d: d.update({'OPS/package.opf': d['OPS/package.opf'].replace(b'<itemref idref="n"/>', b'')}))
        before = self.source.read_bytes()
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as z:
                opf = E.fromstring(z.read('OPS/package.opf'))
                self.assertTrue(opf.xpath('//*[local-name()="itemref" and @idref="n"]'))
                body = E.fromstring(z.read('OPS/text/c.xhtml'))
                self.assertFalse(body.xpath('//*[@role="doc-noteref"]'))
                self.assertNotIn(b'epub:type="noteref"', z.read('OPS/text/c.xhtml'))
                self.assertNotIn(b'epub:type="footnote"', z.read('OPS/notes.xhtml'))
            return self.fake_run(args, **opts)
        _, report = self.perform('html', run=run)
        self.assertTrue(report['warnings'])
        self.assertEqual(self.source.read_bytes(), before)

    def test_aside_note_target_becomes_div_with_same_anchor(self):
        self.rewrite(lambda d: d.update({'OPS/notes.xhtml': d['OPS/notes.xhtml'].replace(b'<p id="n1">', b'<aside id="n1" epub:type="footnote" role="doc-footnote" xmlns:epub="'+EP.encode()+b'">').replace(b'</p>', b'</aside>')}))
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as z:
                root = E.fromstring(z.read('OPS/notes.xhtml'))
                target = root.xpath('//*[@id="n1"]')[0]
                self.assertEqual(E.QName(target).localname, 'div')
                self.assertEqual(''.join(target.itertext()), '注释的内容')
            return self.fake_run(args, **opts)
        self.perform('html', run=run)

    def test_calibre_unnamespaced_note_types_are_removed(self):
        self.rewrite(lambda data: data.update({'OPS/notes.xhtml': data['OPS/notes.xhtml'].replace(b'<p id="n1">', b'<aside id="n1" type="footnote" role="doc-footnote">').replace(b'</p>', b'</aside>')}))
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as archive:
                root = E.fromstring(archive.read('OPS/notes.xhtml'))
                target = root.xpath('//*[@id="n1"]')[0]
                self.assertEqual(E.QName(target).localname, 'div')
                self.assertIsNone(target.get('type'))
            return self.fake_run(args, **opts)
        self.perform('html', run=run)

    def test_inline_svg_becomes_self_contained_manifest_image_for_pandoc(self):
        def change(data):
            data['OPS/text/c.xhtml'] = data['OPS/text/c.xhtml'].replace(b'</body>', b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 31 47"><image xlink:href="../cover.jpg" width="31" height="47"/><rect x="0" y="0" width="1" height="1"/></svg></body>')
            data['OPS/cover.jpg'] = b'local image'
            data['OPS/package.opf'] = data['OPS/package.opf'].replace(b'</manifest>', b'<item id="cover" href="cover.jpg" media-type="image/jpeg"/></manifest>')
        self.rewrite(change)
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as archive:
                root = E.fromstring(archive.read('OPS/text/c.xhtml'))
                self.assertFalse(root.xpath('//*[local-name()="svg"]'))
                images = root.xpath('//*[local-name()="img"]')
                self.assertEqual(len(images), 1)
                opf = E.fromstring(archive.read('OPS/package.opf'))
                item = opf.xpath('//*[local-name()="item" and @media-type="image/svg+xml"]')[0]
                svg = E.fromstring(archive.read('OPS/' + item.get('href')))
                image = svg.xpath('//*[local-name()="image"]')[0]
                self.assertEqual(image.get('{http://www.w3.org/1999/xlink}href'), 'data:image/jpeg;base64,bG9jYWwgaW1hZ2U=')
            return self.fake_run(args, **opts)
        self.perform('md', run=run)

    def test_simple_svg_cover_retains_original_raster_resource(self):
        def change(data):
            data['OPS/text/c.xhtml'] = data['OPS/text/c.xhtml'].replace(b'</body>', b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 31 47"><image xlink:href="../cover.jpg" width="31" height="47"/></svg></body>')
            data['OPS/cover.jpg'] = b'local image'
            data['OPS/package.opf'] = data['OPS/package.opf'].replace(b'</manifest>', b'<item id="cover" href="cover.jpg" media-type="image/jpeg"/></manifest>')
        self.rewrite(change)
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as archive:
                root = E.fromstring(archive.read('OPS/text/c.xhtml'))
                image = root.xpath('//*[local-name()="img"]')[0]
                self.assertEqual(image.get('src'), '../cover.jpg')
            return self.fake_run(args, **opts)
        self.perform('html', run=run)

    def test_rtf_output_adds_native_bookmark_ranges_around_target_content(self):
        def run(args, **opts):
            if '--from=json' in args:
                ast = json.loads(Path(args[1]).read_text(encoding='utf-8'))
                serialized = json.dumps(ast)
                self.assertIn('bkmkstart book_anchor_', serialized)
                self.assertIn('bkmkend book_anchor_', serialized)
                self.assertIn('NoteContent', serialized)
                self.assertIn('data:image/png;base64,bG9jYWwgaW1hZ2U=', serialized)
                self.assertNotIn('#note.id', serialized)
            return self.fake_run(args, **opts)
        self.perform('rtf', run=run)
        self.assertTrue(any('--to=json' in args for args, _ in self.calls))
        self.assertTrue(any('--from=json' in args for args, _ in self.calls))

    def test_odt_output_adds_native_bookmark_ranges_inside_named_note_section(self):
        text = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
        def run(args, **opts):
            result = self.fake_run(args, **opts)
            candidate = Path(args[args.index('--output') + 1])
            with zipfile.ZipFile(candidate, 'w') as archive:
                archive.writestr('mimetype', 'application/vnd.oasis.opendocument.text')
                archive.writestr('content.xml', '<document-content xmlns:text="' + text + '"><body><text:section text:name="note.id"><text:p>NoteContent</text:p></text:section></body></document-content>')
            return result
        output, _ = self.perform('odt', run=run)
        with zipfile.ZipFile(output) as archive:
            root = E.fromstring(archive.read('content.xml'))
            start = root.xpath('//*[local-name()="bookmark-start"]')[0]
            self.assertEqual(start.get('{' + text + '}name'), 'note.id')
            self.assertIn('NoteContent', ''.join(start.getparent().itertext()))
            self.assertTrue(root.xpath('//*[local-name()="bookmark-end"]'))

    def test_empty_imported_bookmark_anchor_retains_following_paragraph_content(self):
        self.rewrite(lambda data: data.update({'OPS/notes.xhtml': data['OPS/notes.xhtml'].replace(b'<p id="n1">', b'<p><a id="n1"/>')}))
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as archive:
                root = E.fromstring(archive.read('OPS/notes.xhtml'))
                target = root.xpath('//*[@id="n1"]')[0]
                self.assertIn('注释的内容', ''.join(target.itertext()))
            return self.fake_run(args, **opts)
        self.perform('html', run=run)

    def test_non_linear_note_spine_item_becomes_linear(self):
        self.rewrite(lambda d: d.update({'OPS/package.opf': d['OPS/package.opf'].replace(b'<itemref idref="n"/>', b'<itemref idref="n" linear="no"/>')}))
        def run(args, **opts):
            with zipfile.ZipFile(args[1]) as z:
                root = E.fromstring(z.read('OPS/package.opf'))
                target = root.xpath('//*[local-name()="itemref" and @idref="n"]')[0]
                self.assertNotEqual(target.get('linear'), 'no')
            return self.fake_run(args, **opts)
        self.perform('odt', run=run)

    def test_local_html_resource_named_input_is_not_overwritten(self):
        source = self.root / 'book.html'
        source.write_text('<h1>RootBook</h1><a href="input.html">Second chapter</a>', encoding='utf-8')
        (self.root / 'input.html').write_text('<h1>OtherChapter</h1>', encoding='utf-8')
        def run(args, **opts):
            staged = Path(args[1])
            self.assertIn('RootBook', staged.read_text(encoding='utf-8'))
            self.assertIn('OtherChapter', (staged.parent / 'input.html').read_text(encoding='utf-8'))
            return self.fake_run(args, **opts)
        self.perform('epub', source, run)

    def test_malformed_xhtml_becomes_json_error(self):
        self.rewrite(lambda d: d.update({'OPS/text/c.xhtml': b'<html><body><p>broken</body></html>'}))
        script = Path(__file__).resolve().parents[1] / 'scripts/ebook_convert.py'
        result = subprocess.run([sys.executable, str(script), str(self.source), str(self.root/'out.txt')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)['issues'])

    def test_output_race_preserves_other_writer_and_rolls_back_assets(self):
        output = self.root / '结果 book.md'
        def run(args, **opts):
            result = self.fake_run(args, **opts)
            output.write_bytes(b'other writer')
            return result
        with self.assertRaises(ConversionError):
            self.perform('md', run=run)
        self.assertEqual(output.read_bytes(), b'other writer')
        self.assertFalse((self.root / '结果 book_assets').exists())

    def test_missing_markdown_image_is_not_published(self):
        def run(args, **opts):
            result = self.fake_run(args, **opts)
            dest = Path(args[args.index('--output')+1])
            dest.write_text('![image](missing_assets/image.png)', encoding='utf-8')
            return result
        with self.assertRaises(ConversionError):
            self.perform('md', run=run)
        self.assertFalse((self.root / '结果 book.md').exists())

    def test_css_import_remote_resource_is_refused_before_engine(self):
        source = self.root / 'styled.html'
        source.write_text('<html><head><link rel="stylesheet" href="book.css"></head><body>正文</body></html>', encoding='utf-8')
        (self.root / 'book.css').write_text('@import "http://127.0.0.1:9/private.css";', encoding='utf-8')
        with patch('ebook_convert.subprocess.run') as run:
            with self.assertRaises(ConversionError):
                convert(source, self.root / 'style.epub', calibre=sys.executable)
        run.assert_not_called()

    def test_dangling_output_symlink_is_refused_without_following(self):
        output = self.root / 'link.epub'
        target = self.root / 'not-requested.epub'
        original_resolve = Path.resolve
        def resolve(path, *args, **kwargs):
            return target if path == output else original_resolve(path, *args, **kwargs)
        with patch.object(Path, 'resolve', resolve), patch.object(Path, 'is_symlink', lambda path: path == output):
            with self.assertRaises(ConversionError):
                convert(self.source, output)
        self.assertFalse(target.exists())

    def test_cli_invalid_option_is_json_error(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/ebook_convert.py'
        result = subprocess.run([sys.executable, str(script), '--timeout=fast'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)['issues'])

    def test_corrupt_html_and_truncated_rtf_not_published(self):
        def bad(args, **opts):
            dest = Path(args[args.index('--output') + 1])
            dest.write_bytes(b'{\\rtf1 unclosed' if dest.suffix == '.rtf' else b'not an HTML document')
            return subprocess.CompletedProcess(args, 0, '', '')
        for extension in ('html', 'rtf'):
            with self.subTest(extension=extension):
                with self.assertRaises(ConversionError):
                    self.perform(extension, run=bad)
                self.assertFalse((self.root / ('结果 book.' + extension)).exists())

    def test_broken_note_and_duplicate_basename_fail(self):
        self.rewrite(lambda d: d.update({'OPS/text/c.xhtml': d['OPS/text/c.xhtml'].replace(b'#n1', b'#missing')}))
        with self.assertRaises(ConversionError):
            self.perform('html')
        book(self.source)
        def duplicate(d):
            d['OPS/other/c.xhtml'] = d['OPS/text/c.xhtml']
            d['OPS/package.opf'] = d['OPS/package.opf'].replace(b'</manifest>', b'<item id="other" href="other/c.xhtml" media-type="application/xhtml+xml"/></manifest>').replace(b'</spine>', b'<itemref idref="other"/></spine>')
        self.rewrite(duplicate)
        with self.assertRaises(ConversionError):
            self.perform('html')

    def test_encoding_is_strict_and_explicit_legacy_input_works(self):
        source = self.root / 'legacy.txt'
        source.write_bytes('第一章 中文正文'.encode('gb18030'))
        out = self.root / 'legacy.epub'
        with self.assertRaises(ConversionError):
            convert(source, out, calibre=sys.executable)
        with patch('ebook_convert.subprocess.run', side_effect=self.fake_run):
            convert(source, out, calibre=sys.executable, input_encoding='gb18030')
        self.assertTrue(out.exists())

    def test_doctor_missing_and_available_engines(self):
        with patch('ebook_convert._find_engine', return_value=None):
            report = doctor()
        self.assertFalse(report['calibre']['available'])
        self.assertTrue(report['issues'])
        with patch('ebook_convert.subprocess.run', side_effect=self.fake_run):
            report = doctor(calibre=sys.executable, pandoc=sys.executable)
        self.assertTrue(report['calibre']['available'])
        self.assertIn('fake', report['pandoc']['version'])

    def test_cli_formats_and_json_failure(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/ebook_convert.py'
        result = subprocess.run([sys.executable, str(script), '--formats'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['input']), 10)
        result = subprocess.run([sys.executable, str(script), str(self.source), str(self.root/'bad.pdf')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)['issues'])


if __name__ == '__main__':
    unittest.main()

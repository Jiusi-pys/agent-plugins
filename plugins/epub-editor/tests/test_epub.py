import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from lxml import etree as E

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from epub_editor import edit

X = 'http://www.w3.org/1999/xhtml'
EP = 'http://www.idpf.org/2007/ops'
O = 'http://www.idpf.org/2007/opf'

def book(path, broken=False, ambiguous=False, version='3.0'):
    opf = f'''<package xmlns="{O}" version="{version}" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">test</dc:identifier><dc:title>Test</dc:title><dc:language>zh</dc:language></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c" href="text/c.xhtml" media-type="application/xhtml+xml"/><item id="n" href="notes.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c"/><itemref idref="n"/></spine></package>'''
    href = 'text/c.xhtml#missing' if broken else 'text/c.xhtml#chapter'
    files = {
        'mimetype': 'application/epub+zip',
        'META-INF/container.xml': '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        'OPS/package.opf': opf,
        'OPS/nav.xhtml': f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>目录</title></head><body><nav epub:type="toc"><ol><li><a href="{href}">第一章</a></li></ol></nav></body></html>',
        'OPS/text/c.xhtml': f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>正文</title></head><body><h1 id="chapter">第一章</h1><p>正文<a epub:type="noteref" href="../notes.xhtml#n1">[1]</a></p>' + ('<h2 id="another">第一章</h2>' if ambiguous else '') + '</body></html>',
        'OPS/notes.xhtml': f'<html xmlns="{X}"><head><title>注释</title></head><body><p id="n1">注释的内容</p></body></html>',
        'OPS/untouched.bin': b'unchanged',
    }
    with zipfile.ZipFile(path, 'w') as z:
        for name, value in files.items(): z.writestr(name, value)

class Editing(unittest.TestCase):
    def rewrite(self, transform):
        with zipfile.ZipFile(self.src) as z: data = {n:z.read(n) for n in z.namelist()}
        transform(data)
        with zipfile.ZipFile(self.src, 'w') as z:
            for n,v in data.items(): z.writestr(n,v)

    def test_legacy_note_reference_class(self):
        book(self.src)
        self.rewrite(lambda d: d.update({'OPS/text/c.xhtml': d['OPS/text/c.xhtml'].replace(b'epub:type="noteref"', b'class="noteref"')}))
        self.assertEqual(edit(self.src,self.out)['notes'], 1)

    def test_epub2_ncx_becomes_nested_epub3_navigation(self):
        book(self.src, version='2.0')
        def change(d):
            del d['OPS/nav.xhtml']
            d['OPS/package.opf'] = d['OPS/package.opf'].replace(b'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>', b'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
            d['OPS/toc.ncx'] = b'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap><navPoint id="a"><navLabel><text>One</text></navLabel><content src="text/c.xhtml#chapter"/></navPoint></navMap></ncx>'
        self.rewrite(change)
        edit(self.src,self.out)
        self.assertEqual(self.read('OPS/package.opf').get('version'),'3.0')
        self.assertEqual(self.read('OPS/epub-editor-nav.xhtml').xpath('//*[local-name()="a"]')[0].get('href'),'text/c.xhtml#chapter')

    def test_existing_cover_page_points_to_replacement(self):
        book(self.src)
        def change(d):
            d['OPS/package.opf'] = d['OPS/package.opf'].replace(b'</manifest>',b'<item id="old" href="old.png" media-type="image/png" properties="cover-image"/></manifest>')
            d['OPS/text/c.xhtml'] = d['OPS/text/c.xhtml'].replace(b'<body>',b'<body><img src="../old.png" alt="old"/>')
            d['OPS/old.png']=b'old cover resource'
        self.rewrite(change)
        cover=self.root/'cover.png'
        Image.new('RGB',(20,30),'red').save(cover)
        edit(self.src,self.out,cover)
        self.assertEqual(self.read('OPS/text/c.xhtml').xpath('//*[local-name()="img"]')[0].get('src'),'../epub-editor-cover.jpg')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src, self.out = self.root/'source.epub', self.root/'out.epub'

    def read(self, name):
        with zipfile.ZipFile(self.out) as z: return E.fromstring(z.read(name))

    def test_cross_file_note_and_archive_integrity(self):
        book(self.src)
        before = self.src.read_bytes()
        report = edit(self.src, self.out)
        self.assertEqual(report['notes'], 1)
        note = self.read('OPS/notes.xhtml').xpath('//*[@id="n1"]')[0]
        self.assertEqual(note.get('{'+EP+'}type'), 'footnote')
        self.assertEqual(self.src.read_bytes(), before)
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(z.infolist()[0].filename, 'mimetype')
            self.assertEqual(z.infolist()[0].compress_type, zipfile.ZIP_STORED)
            self.assertEqual(z.read('OPS/untouched.bin'), b'unchanged')

    def test_repair_unique_heading(self):
        book(self.src, broken=True)
        report = edit(self.src, self.out)
        self.assertEqual(report['toc_repaired'], 1)
        self.assertEqual(self.read('OPS/nav.xhtml').xpath('//*[local-name()="a"]')[0].get('href'), 'text/c.xhtml#chapter')

    def test_ambiguous_heading_is_reported_not_guessed(self):
        book(self.src, broken=True, ambiguous=True)
        report = edit(self.src, self.out)
        self.assertTrue(report['issues'])
        self.assertEqual(report['toc_repaired'], 0)

    def test_cover_requires_user_file_and_updates_package(self):
        book(self.src)
        cover = self.root/'cover.jpg'
        Image.new('RGB', (32, 48), 'blue').save(cover)
        report = edit(self.src, self.out, cover=cover)
        self.assertTrue(report['cover_replaced'])
        opf = self.read('OPS/package.opf')
        covers = opf.xpath('//*[local-name()="item" and @properties="cover-image"]')
        self.assertEqual(len(covers), 1)
        with zipfile.ZipFile(self.out) as z:
            self.assertIn('OPS/'+covers[0].get('href'), z.namelist())

    def test_no_cover_preserves_package_cover_state(self):
        book(self.src)
        report = edit(self.src, self.out)
        self.assertFalse(report['cover_replaced'])
        self.assertFalse(self.read('OPS/package.opf').xpath('//*[@properties="cover-image"]'))

    def test_refuses_overwrite_and_source_as_output(self):
        book(self.src)
        with self.assertRaises(ValueError): edit(self.src, self.src)
        self.out.write_bytes(b'existing')
        with self.assertRaises(FileExistsError): edit(self.src, self.out)
        self.assertEqual(self.out.read_bytes(), b'existing')

    def test_invalid_cover_does_not_publish_output(self):
        book(self.src)
        cover = self.root/'bad.png'
        cover.write_text('not an image')
        with self.assertRaises(ValueError): edit(self.src, self.out, cover=cover)
        self.assertFalse(self.out.exists())

    def test_rejects_zip_traversal(self):
        book(self.src)
        with zipfile.ZipFile(self.src, 'a') as z: z.writestr('../escape', 'bad')
        with self.assertRaises(ValueError): edit(self.src, self.out)
        self.assertFalse(self.out.exists())

if __name__ == '__main__': unittest.main()

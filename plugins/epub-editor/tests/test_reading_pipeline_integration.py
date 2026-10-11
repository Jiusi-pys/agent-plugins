"""Opt-in real conversion -> standard layout -> export acceptance."""
import hashlib
import io
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
import zipfile

from lxml import etree as E
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ebook_convert import convert
from epub_editor import edit, elements, read_package, resolve, xml

CALIBRE = os.environ.get('TEST_CALIBRE')
PANDOC = os.environ.get('TEST_PANDOC')


@unittest.skipUnless(CALIBRE and PANDOC, 'opt-in real engines: TEST_CALIBRE and TEST_PANDOC')
class ReadingPipeline(unittest.TestCase):
    def test_html_to_standard_epub_and_export_preserves_image_notes_and_captions(self):
        with tempfile.TemporaryDirectory(prefix='编排流程 ') as scratch:
            root = Path(scratch)
            image = root / 'image.png'
            Image.new('RGB', (31, 47), (51, 103, 157)).save(image)
            source = root / 'original.html'
            source.write_text('''<!DOCTYPE html><html lang="zh-CN" xmlns:epub="http://www.idpf.org/2007/ops"><head><meta charset="utf-8"><title>流程验收</title></head><body><h1>第一章</h1><p>正文PipelineSentinel<a epub:type="noteref" role="doc-noteref" href="#n1">[1]</a>。</p><figure><p><img src="image.png" alt="原始替代文本"/></p><figcaption class="caption"><p>图 1 CaptionSentinel 原始图注。</p><p class="source">来源：SourceSentinel 自制测试图。</p></figcaption></figure><aside id="n1" epub:type="footnote" role="doc-footnote"><p>注释NotePipelineSentinel。</p></aside></body></html>''', encoding='utf-8')
            original = hashlib.sha256(source.read_bytes()).hexdigest()
            staged = root / 'stage.epub'
            conversion = convert(source, staged, calibre=CALIBRE, pandoc=PANDOC)
            self.assertEqual(conversion['issues'], [], conversion)
            staged_bytes, _, staged_opf = read_package(staged)
            staged_images = {name:value for name,value in staged_bytes.items() if name.endswith('.png')}
            self.assertTrue(staged_images)
            standard = root / 'standard.epub'
            layout = edit(staged, standard)
            self.assertEqual(layout['issues'], [], layout)
            self.assertEqual(layout['notes'], 1)
            data, opath, opf = read_package(standard)
            docs = {resolve(opath,item.get('href'))[0]:xml(data[resolve(opath,item.get('href'))[0]])
                    for item in elements(opf,'item') if item.get('media-type') == 'application/xhtml+xml'}
            ref_pairs = [(path,a) for path,doc in docs.items() for a in elements(doc,'a') if a.get('role') == 'doc-noteref']
            self.assertEqual(len(ref_pairs),1)
            ref_path, ref = ref_pairs[0]
            self.assertEqual(E.QName(ref.getparent()).localname,'sup')
            serialized = '\n'.join(E.tostring(doc).decode('utf-8') for doc in docs.values())
            self.assertRegex(serialized,r'font-size:\s*0\.75em')
            target = resolve(ref_path,ref.get('href'))
            matches = docs[target[0]].xpath('//*[@id=$id]',id=target[1])
            self.assertEqual(len(matches),1)
            self.assertIn('NotePipelineSentinel',''.join(matches[0].itertext()))
            captions = [caption for doc in docs.values() for caption in elements(doc,'figcaption')]
            self.assertEqual(len(captions),1)
            self.assertIn('CaptionSentinel',''.join(captions[0].itertext()))
            self.assertIn('SourceSentinel',''.join(captions[0].itertext()))
            self.assertEqual(list(captions[0].getparent())[-1],captions[0])
            self.assertFalse([node for doc in docs.values() for node in doc.xpath('//*[local-name()="p"]/*[local-name()="figure" or local-name()="p"]')])
            for name,value in staged_images.items():
                self.assertEqual(data[name],value)
                with Image.open(io.BytesIO(value)) as picture:
                    self.assertEqual(picture.size,(31,47))
            final = root / 'final.html'
            exported = convert(standard,final,calibre=CALIBRE,pandoc=PANDOC)
            self.assertEqual(exported['issues'],[],exported)
            final_doc = E.HTML(final.read_bytes(),parser=E.HTMLParser(encoding='utf-8'))
            final_text = ''.join(final_doc.itertext())
            for marker in ('PipelineSentinel','NotePipelineSentinel','CaptionSentinel','SourceSentinel'):
                self.assertIn(marker,final_text)
            self.assertTrue(final_doc.xpath('//img[starts-with(@src,"data:image/")]'))
            links = final_doc.xpath('//a[normalize-space(string(.))="[1]"]/@href')
            self.assertEqual(len(links),1)
            target_id = links[0].split('#')[-1]
            self.assertEqual(len(final_doc.xpath('//*[@id=$id]',id=target_id)),1)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original)


if __name__ == '__main__':
    unittest.main()

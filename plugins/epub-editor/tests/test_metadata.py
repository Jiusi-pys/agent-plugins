import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from lxml import etree as E

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_epub import book, O, X, EP
from epub_editor import edit

DC = 'http://purl.org/dc/elements/1.1/'
NS = {'o': O, 'dc': DC}


class MetadataEditing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src, self.out = self.root/'in.epub', self.root/'out.epub'
        book(self.src)

    def opf(self, path=None):
        with zipfile.ZipFile(path or self.out) as z:
            return E.fromstring(z.read('OPS/package.opf'))

    def modify(self, action):
        with zipfile.ZipFile(self.src) as z:
            data = {name:z.read(name) for name in z.namelist()}
        action(data)
        with zipfile.ZipFile(self.src, 'w') as z:
            for name, value in data.items(): z.writestr(name,value)

    def test_common_fields_roles_and_primary_identifier(self):
        report = edit(self.src, self.out, metadata_patch={
            'title':'新书 & <名称>', 'subtitle':'副标题',
            'authors':[{'name':'张三','sort_as':'Zhang, San'}, '李四'],
            'contributors':[{'name':'王五','role':'translator'}],
            'publisher':'测试出版社', 'published_date':'2024-02-29',
            'languages':['zh-CN','en'], 'subjects':['小说','文学'],
            'description':'第一行\n第二行', 'rights':'版权所有',
            'isbn':'978-0-306-40615-7', 'edition':'修订版',
            'series':{'name':'测试丛书','position':2.5},
            'page_count':320, 'word_count':123456,
        }, metadata_only=True)
        opf = self.opf()
        self.assertEqual(opf.xpath('o:metadata/dc:title/text()',namespaces=NS), ['新书 & <名称>','副标题'])
        self.assertEqual(opf.xpath('o:metadata/dc:creator/text()',namespaces=NS), ['张三','李四'])
        self.assertEqual(opf.xpath('o:metadata/dc:language/text()',namespaces=NS), ['zh-CN','en'])
        self.assertEqual(opf.xpath('o:metadata/dc:identifier[@id="uid"]/text()',namespaces=NS), ['test'])
        self.assertIn('9780306406157',opf.xpath('o:metadata/dc:identifier/text()',namespaces=NS))
        self.assertEqual(opf.xpath('o:metadata/o:meta[@property="role"]/text()',namespaces=NS),['aut','aut','trl'])
        self.assertEqual(report['metadata']['after']['word_count'],123456)
        self.assertEqual(report['metadata']['after']['page_count'],320)
        self.assertEqual(report['metadata']['after']['series'],{'name':'测试丛书','position':2.5})

    def test_metadata_only_preserves_content_and_unknown_fields(self):
        self.modify(lambda d:d.update({'OPS/package.opf':d['OPS/package.opf'].replace(b'</metadata>',b'<meta name="vendor:keep" content="yes"/></metadata>')}))
        original = self.src.read_bytes()
        with zipfile.ZipFile(self.src) as z: before = {n:z.read(n) for n in z.namelist()}
        edit(self.src,self.out,metadata_patch={'title':'Only title'},metadata_only=True)
        self.assertEqual(self.src.read_bytes(),original)
        with zipfile.ZipFile(self.out) as z:
            for n,v in before.items():
                if n != 'OPS/package.opf': self.assertEqual(z.read(n),v,n)
        self.assertTrue(self.opf().xpath('o:metadata/o:meta[@name="vendor:keep"]',namespaces=NS))

    def test_subtitle_deletion_preserves_main_title_and_has_no_dangling_refines(self):
        edit(self.src,self.out,metadata_patch={'subtitle':'To remove','authors':['A']},metadata_only=True)
        third = self.root/'third.epub'
        edit(self.out,third,metadata_patch={'subtitle':None,'authors':['B']},metadata_only=True)
        opf=self.opf(third)
        self.assertEqual(opf.xpath('o:metadata/dc:title/text()',namespaces=NS),['Test'])
        ids=set(opf.xpath('//@id'))
        self.assertTrue(all(v[1:] in ids for v in opf.xpath('//@refines') if v.startswith('#')))

    def test_recount_chinese_english_and_excluded_notes(self):
        content=f'''<html xmlns="{X}" xmlns:epub="{EP}"><head><title>不计</title></head><body><nav epub:type="toc">不计</nav><p>中文 Hello world 123<a epub:type="noteref" href="../notes.xhtml#n1">99</a></p><p>𠀀 don't co-operate</p><script>not counted</script><p hidden="hidden">不计</p></body></html>'''
        self.modify(lambda d:d.update({'OPS/text/c.xhtml':content.encode()}))
        report=edit(self.src,self.out,recount=True,metadata_only=True)
        self.assertEqual(report['statistics']['word_count'],8)
        self.assertEqual(report['statistics']['cjk_characters'],3)
        self.assertEqual(report['statistics']['other_words'],5)
        self.assertEqual(report['metadata']['after']['word_count'],8)
        self.assertIn('cjk',report['metadata']['after']['word_count_method'])

    def test_invalid_metadata_leaves_no_output(self):
        invalid=[{'title':''},{'languages':[]},{'languages':['x']},{'word_count':True},{'word_count':-1},
                 {'page_count':0},{'published_date':'2023-02-29'}, {'isbn':'9780306406158'},
                 {'mispelled_title':'oops'},{'contributors':[{'name':'X','role':'made-up'}]},
                 {'series':{'name':'S','position':float('nan')}}, {'title':'bad\x00title'}]
        for patch in invalid:
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError): edit(self.src,self.out,metadata_patch=patch,metadata_only=True)
                self.assertFalse(self.out.exists())

    def test_manual_and_automatic_word_count_conflict(self):
        with self.assertRaises(ValueError): edit(self.src,self.out,metadata_patch={'word_count':100},recount=True)
        self.assertFalse(self.out.exists())

    def test_existing_schema_prefix_is_not_overwritten(self):
        self.modify(lambda d:d.update({'OPS/package.opf':d['OPS/package.opf'].replace(b'version="3.0"',b'version="3.0" prefix="schema: https://example.org/other/ s: https://schema.org/"').replace(b'</metadata>',b'<meta property="s:wordCount">5</meta><meta property="schema:keep">keep</meta></metadata>')}))
        report=edit(self.src,self.out,metadata_patch={'word_count':12},metadata_only=True)
        self.assertIn('schema: https://example.org/other/',self.opf().get('prefix'))
        self.assertEqual(self.opf().xpath('o:metadata/o:meta[@property="s:wordCount"]/text()',namespaces=NS),['12'])
        self.assertEqual(report['metadata']['before']['word_count'],5)

    def test_primary_isbn_update_keeps_unique_identifier_reference(self):
        self.modify(lambda d:d.update({'OPS/package.opf':d['OPS/package.opf'].replace(b'>test</dc:identifier>',b'>urn:isbn:9780306406157</dc:identifier>')}))
        edit(self.src,self.out,metadata_patch={'isbn':'9781861972712'},metadata_only=True)
        self.assertEqual(self.opf().xpath('o:metadata/dc:identifier[@id="uid"]/text()',namespaces=NS),['urn:isbn:9781861972712'])
        with self.assertRaises(ValueError): edit(self.src,self.root/'remove.epub',metadata_patch={'isbn':None},metadata_only=True)

    def test_cli_inspect_and_edit(self):
        script=Path(__file__).resolve().parents[1]/'scripts'/'epub_editor.py'
        patch=self.root/'metadata.json'
        patch.write_text(json.dumps({'title':'CLI title','word_count':0}),encoding='utf-8-sig')
        done=subprocess.run([sys.executable,str(script),str(self.src),str(self.out),'--metadata',str(patch),'--metadata-only'],capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stderr)
        done=subprocess.run([sys.executable,str(script),str(self.out),'--inspect'],capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stderr)
        metadata=json.loads(done.stdout)['metadata']
        self.assertEqual(metadata['title'],'CLI title')
        self.assertEqual(metadata['word_count'],0)

    def test_epub2_full_edit_preserves_metadata_and_creates_navigation(self):
        book(self.src,version='2.0')
        report=edit(self.src,self.out,metadata_patch={'title':'新版','authors':['作者'],'word_count':12})
        self.assertEqual(report['metadata']['after']['title'],'新版')
        self.assertEqual(report['notes'],1)
        self.assertEqual(self.opf().get('version'),'3.0')

    def test_secondary_identifier_patch_and_clear_leave_primary_unchanged(self):
        edit(self.src,self.out,metadata_patch={'identifiers':{'DOI':'10.1234/example','ASIN':'B012345678'},'subjects':['A'],'edition':'First','page_count':24},metadata_only=True)
        final=self.root/'cleared.epub'
        report=edit(self.out,final,metadata_patch={'identifiers':{'DOI':None},'subjects':[],'edition':None,'page_count':None},metadata_only=True)
        actual=report['metadata']['after']
        self.assertEqual(actual['subjects'],[])
        self.assertIsNone(actual['edition'])
        self.assertIsNone(actual['page_count'])
        self.assertEqual({i['scheme'] for i in actual['identifiers']},{'UNKNOWN','ASIN'})
        self.assertEqual(self.opf(final).get('unique-identifier'),'uid')

    def test_repeated_patch_is_idempotent_without_duplicate_fields(self):
        patch={'title':'Stable','subtitle':'Sub','authors':['A'],'series':{'name':'S','position':1},'word_count':100,'isbn':'9780306406157'}
        edit(self.src,self.out,metadata_patch=patch,metadata_only=True)
        final=self.root/'again.epub'
        report=edit(self.out,final,metadata_patch=patch,metadata_only=True)
        self.assertEqual(report['metadata']['changed'],[])
        self.assertEqual(len(self.opf(final).xpath('o:metadata/dc:creator',namespaces=NS)),1)

    def test_count_ignores_non_linear_resources_and_counts_each_document_once(self):
        def change(data):
            data['OPS/package.opf']=data['OPS/package.opf'].replace(b'<itemref idref="n"/>',b'<itemref idref="n" linear="no"/><itemref idref="c"/>')
            data['OPS/text/c.xhtml']=f'<html xmlns="{X}"><body><p>Hello<b>world</b>!</p><p>next</p></body></html>'.encode()
        self.modify(change)
        report=edit(self.src,self.out,recount=True,metadata_only=True)
        self.assertEqual(report['statistics']['word_count'],2)

    def test_removed_person_also_removes_link_refinements(self):
        def change(data):
            data['OPS/package.opf']=data['OPS/package.opf'].replace(b'</metadata>',b'<dc:creator id="old-author">Old</dc:creator><link refines="#old-author" href="https://example.org/author" rel="record"/></metadata>')
        self.modify(change)
        edit(self.src,self.out,metadata_patch={'authors':['New']},metadata_only=True)
        self.assertFalse(self.opf().xpath('//*[@refines="#old-author"]'))

    def test_full_mode_synchronizes_ncx_unique_id_when_primary_isbn_changes(self):
        def change(data):
            data['OPS/package.opf']=data['OPS/package.opf'].replace(b'>test</dc:identifier>',b'>urn:isbn:9780306406157</dc:identifier>').replace(b'</manifest>',b'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>')
            data['OPS/toc.ncx']=b'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="urn:isbn:9780306406157"/></head><docTitle><text>Test</text></docTitle><navMap/></ncx>'
        self.modify(change)
        edit(self.src,self.out,metadata_patch={'isbn':'9781861972712','title':'New title'})
        with zipfile.ZipFile(self.out) as z: ncx=E.fromstring(z.read('OPS/toc.ncx'))
        self.assertEqual(ncx.xpath('//*[local-name()="meta" and @name="dtb:uid"]')[0].get('content'),'urn:isbn:9781861972712')
        self.assertEqual(ncx.xpath('//*[local-name()="docTitle"]/*[local-name()="text"]/text()'),['New title'])
        with self.assertRaises(ValueError):
            edit(self.src,self.root/'metadata-only-ncx.epub',metadata_patch={'isbn':'9781861972712'},metadata_only=True)
        self.assertFalse((self.root/'metadata-only-ncx.epub').exists())


if __name__ == '__main__': unittest.main()

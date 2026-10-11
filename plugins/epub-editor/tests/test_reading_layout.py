"""EPUB structure tests; reader popup interactions require separate reader tests."""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from lxml import etree as E

from test_epub import book, X, EP

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from epub_editor import edit

TYPE = '{' + EP + '}type'
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'epub_editor.py'


class ReadingLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src, self.out = self.root / 'source.epub', self.root / 'out.epub'
        book(self.src)

    def rewrite(self, transform):
        with zipfile.ZipFile(self.src) as z:
            data = {name: z.read(name) for name in z.namelist()}
        transform(data)
        with zipfile.ZipFile(self.src, 'w') as z:
            for name, value in data.items():
                z.writestr(name, value)

    def body(self, content):
        def change(data):
            data['OPS/text/c.xhtml'] = (
                f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>正文</title></head>'
                f'<body><h1 id="chapter">第一章</h1>{content}</body></html>'
            ).encode()
        self.rewrite(change)

    def read(self, name='OPS/text/c.xhtml', path=None):
        with zipfile.ZipFile(path or self.out) as z:
            return E.fromstring(z.read(name))

    def styles(self, root):
        return root.xpath('//*[local-name()="style" and @data-epub-editor="reading-layout"]')

    def marker(self, root):
        return root.xpath('//*[local-name()="a" and @role="doc-noteref"]')[0]

    def assert_marker_once(self, ref):
        supers = [n for n in list(ref.iterancestors()) + list(ref.iter())
                  if isinstance(n.tag, str) and E.QName(n).localname == 'sup']
        self.assertEqual(len(supers), 1)
        self.assertIn('epub-editor-note-sup', supers[0].get('class', '').split())
        self.assertIn('epub-editor-note-marker', ref.get('class', '').split())
        for node in [ref, supers[0]]:
            self.assertNotIn('font-size', node.get('style', '').lower())
            self.assertNotIn('vertical-align', node.get('style', '').lower())

    def test_default_standard_has_one_small_sup_and_resolvable_target(self):
        self.body('<p>正文<a id="ref" epub:type="noteref" href="../notes.xhtml#n1">[1]</a>尾文</p>')
        report = edit(self.src, self.out)
        root = self.read()
        ref = self.marker(root)
        self.assert_marker_once(ref)
        self.assertEqual(ref.get('id'), 'ref')
        self.assertEqual(ref.get('href'), '../notes.xhtml#n1')
        self.assertEqual(ref.get(TYPE), 'noteref')
        self.assertEqual(''.join(root.xpath('//*[local-name()="p"]')[0].itertext()), '正文[1]尾文')
        css = ''.join(self.styles(root)[0].itertext())
        self.assertIn('0.75em', css)
        self.assertIn('focus-visible', css)
        self.assertNotIn('display:none', css.replace(' ', ''))
        self.assertFalse(root.xpath('//*[local-name()="script" or local-name()="button"]'))
        self.assertEqual(report['reading_layout']['mode'], 'standard')
        self.assertEqual(report['reading_layout']['popup_behavior'], 'reader-dependent')
        self.assertEqual(report['reading_layout']['note_markers'], 1)
        self.assertEqual(report['issues'], [])

    def test_existing_sup_and_inline_scale_apply_only_once(self):
        samples = [
            '<sup style="font-size:.5em;vertical-align:super;color:red"><a epub:type="noteref" href="../notes.xhtml#n1">1</a></sup>',
            '<a epub:type="noteref" href="../notes.xhtml#n1"><sup style="font-size:.6em;vertical-align:super">1</sup></a>',
            '<a epub:type="noteref" href="../notes.xhtml#n1" style="font-size:.5em!important;vertical-align:super;color:red">1</a>',
            '<sup><sup><a epub:type="noteref" href="../notes.xhtml#n1">1</a></sup></sup>',
        ]
        for index, content in enumerate(samples):
            with self.subTest(content=content):
                book(self.src)
                self.body('<p>正文' + content + '尾</p>')
                output = self.root / f'sup-{index}.epub'
                edit(self.src, output)
                ref = self.marker(self.read(path=output))
                self.assert_marker_once(ref)
                self.assertEqual(''.join(ref.itertext()), '1')
                if 'color:red' in content:
                    ancestors = list(ref.iterancestors())
                    self.assertTrue(any('color:red' in n.get('style', '') for n in [ref] + ancestors))

    def test_shared_sup_preserves_other_text_and_its_style(self):
        self.body('<p>A<sup id="shared" class="original" style="font-size:.6em;vertical-align:super;color:red">'
                  'before<em><a epub:type="noteref" href="../notes.xhtml#n1">1</a></em>after</sup>Z</p>')
        edit(self.src, self.out)
        root = self.read()
        self.assert_marker_once(self.marker(root))
        paragraph = root.xpath('//*[local-name()="p"]')[0]
        self.assertEqual(''.join(paragraph.itertext()), 'Abefore1afterZ')
        others = [n for n in root.xpath('//*[local-name()="sup"]')
                  if 'epub-editor-note-sup' not in n.get('class', '').split()]
        self.assertEqual([''.join(n.itertext()) for n in others], ['before', 'after'])
        self.assertTrue(all(n.get('style') == 'font-size:.6em;vertical-align:super;color:red' for n in others))
        self.assertEqual(len(root.xpath('//*[@id="shared"]')), 1)

    def test_reference_inline_branches_do_not_compound_scale_or_raise(self):
        samples = [
            '<sup><span style="font-size:.5em;vertical-align:super;color:blue"><a epub:type="noteref" href="../notes.xhtml#n1">1</a></span></sup>',
            '<a epub:type="noteref" href="../notes.xhtml#n1"><span style="font-size:.5em;vertical-align:super;color:blue">1</span></a>',
            '<a epub:type="noteref" href="../notes.xhtml#n1">[<sup style="font-size:.5em;vertical-align:super">1</sup>]</a>',
        ]
        for index, content in enumerate(samples):
            with self.subTest(content=content):
                book(self.src)
                self.body('<p>正文' + content + '</p>')
                output = self.root / f'branches-{index}.epub'
                edit(self.src, output)
                root = self.read(path=output)
                anchor = self.marker(root)
                self.assert_marker_once(anchor)
                sup = next(n for n in list(anchor.iterancestors()) + list(anchor.iter())
                           if E.QName(n).localname == 'sup')
                self.assertIn(anchor, sup.iterdescendants())
                for node in sup.iterdescendants():
                    self.assertNotIn('font-size', node.get('style', ''))
                    self.assertNotIn('vertical-align', node.get('style', ''))
                if 'color:blue' in content:
                    self.assertTrue(any('color:blue' in n.get('style', '') for n in sup.iter()))
                css = ''.join(self.styles(root)[0].itertext())
                self.assertIn('.epub-editor-note-neutral', css)

    def test_multiple_references_in_shared_sup_keep_non_reference_styles(self):
        self.body('<p><sup style="font-size:.6em;vertical-align:super">start'
                  '<a epub:type="noteref" href="../notes.xhtml#n1">1</a>middle'
                  '<a epub:type="noteref" href="../notes.xhtml#n1">2</a>end</sup></p>')
        edit(self.src, self.out)
        root = self.read()
        self.assertEqual(''.join(root.xpath('//*[local-name()="p"]')[0].itertext()), 'start1middle2end')
        anchors = root.xpath('//*[@role="doc-noteref"]')
        self.assertEqual(len(anchors), 2)
        for anchor in anchors:
            self.assert_marker_once(anchor)
        ordinary = [n for n in root.xpath('//*[local-name()="sup"]')
                    if 'epub-editor-note-sup' not in n.get('class', '').split()]
        self.assertEqual([''.join(n.itertext()) for n in ordinary], ['start', 'middle', 'end'])
        self.assertTrue(all(n.get('style') == 'font-size:.6em;vertical-align:super' for n in ordinary))

    def test_font_shorthand_cannot_override_standard_marker_scale(self):
        self.body('<p id="ordinary" style="font:italic 1.2em serif;color:red">普通正文</p>'
                  '<p><sup style="font:italic .6em/0 serif!important;color:red">before'
                  '<a epub:type="noteref" href="../notes.xhtml#n1" style="font:italic .5em/0 serif!important;color:green">'
                  '<span style="font:italic .5em/0 serif!important;color:blue">1</span></a>after</sup></p>')
        report = edit(self.src, self.out)
        root = self.read()
        anchor = self.marker(root)
        self.assert_marker_once(anchor)
        sup = next(n for n in anchor.iterancestors() if E.QName(n).localname == 'sup')
        for node in sup.iter():
            self.assertNotIn('font:', node.get('style', ''))
        self.assertTrue(any('color:blue' in n.get('style', '') for n in sup.iter()))
        self.assertEqual(root.xpath('//*[@id="ordinary"]')[0].get('style'), 'font:italic 1.2em serif;color:red')
        ordinary = [n for n in root.xpath('//*[local-name()="sup"]')
                    if 'epub-editor-note-sup' not in n.get('class', '').split()]
        self.assertTrue(all(n.get('style') == 'font:italic .6em/0 serif!important;color:red' for n in ordinary))
        self.assertTrue(any(w['kind'] == 'font' for w in report['reading_layout']['warnings']))

    def test_caption_font_shorthand_is_scoped_to_caption_presentation(self):
        self.add_image()
        self.body('<p id="ordinary" style="font:italic 1.2em serif">普通正文</p>'
                  '<figure><img src="../img/picture.png"/><figcaption style="font:italic .5em/0 serif!important;color:red">'
                  '<p id="caption" style="font:italic .5em/0 serif!important;color:blue">原图注</p></figcaption></figure>')
        report = edit(self.src, self.out)
        root = self.read()
        caption = root.xpath('//*[local-name()="figcaption"]')[0]
        self.assertNotIn('font:', caption.get('style', ''))
        self.assertNotIn('font:', root.xpath('//*[@id="caption"]')[0].get('style', ''))
        self.assertIn('color:blue', root.xpath('//*[@id="caption"]')[0].get('style', ''))
        self.assertEqual(root.xpath('//*[@id="ordinary"]')[0].get('style'), 'font:italic 1.2em serif')
        self.assertTrue(any(w['kind'] == 'font' for w in report['reading_layout']['warnings']))

    def test_ordinary_numbers_links_and_unresolved_refs_are_not_restyled(self):
        self.body('<p>123<a href="#chapter">4</a><a epub:type="noteref" href="../notes.xhtml#absent">5</a></p>')
        report = edit(self.src, self.out)
        root = self.read()
        self.assertFalse(root.xpath('//*[local-name()="sup"]'))
        self.assertFalse(self.styles(root))
        self.assertEqual(report['reading_layout']['note_markers'], 0)
        self.assertTrue(report['issues'])

    def test_non_spine_note_targets_get_footnote_role_without_hiding_content(self):
        self.rewrite(lambda d: d.update({'OPS/package.opf': d['OPS/package.opf'].replace(b'<itemref idref="n"/>', b'')}))
        edit(self.src, self.out)
        note = self.read('OPS/notes.xhtml').xpath('//*[@id="n1"]')[0]
        self.assertEqual(note.get(TYPE), 'footnote')
        self.assertEqual(note.get('role'), 'doc-footnote')
        self.assertEqual(''.join(note.itertext()), '注释的内容')
        self.assertFalse(note.get('hidden'))

    def test_navigation_links_to_notes_are_not_body_note_references(self):
        def change(data):
            data['OPS/nav.xhtml'] = data['OPS/nav.xhtml'].replace(
                b'</ol>', '<li><a href="notes.xhtml#n1">注释</a></li></ol>'.encode())
            data['OPS/notes.xhtml'] = data['OPS/notes.xhtml'].replace(
                b'<p id="n1">', f'<p xmlns:epub="{EP}" id="n1" epub:type="footnote">'.encode())
        self.rewrite(change)
        self.body('<p>正文<a epub:type="noteref" href="../notes.xhtml#n1">1</a></p>'
                  '<nav epub:type="toc"><a href="../notes.xhtml#n1">正文内目录</a></nav>')
        report = edit(self.src, self.out)
        self.assertEqual(report['notes'], 1)
        self.assertEqual(report['reading_layout']['note_markers'], 1)
        self.assertFalse(self.read('OPS/nav.xhtml').xpath('//*[@role="doc-noteref"]'))
        embedded = self.read().xpath('//*[local-name()="nav"]')[0]
        self.assertFalse(embedded.xpath('.//*[@role="doc-noteref"]'))

    def test_endnotes_collection_keeps_content_semantics_without_individual_aria_roles(self):
        def change(data):
            data['OPS/notes.xhtml'] = (
                f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>注释</title></head><body>'
                '<section epub:type="endnotes"><ol><li id="n1" role="doc-endnote">原注一</li>'
                '<li id="n2" epub:type="endnote" role="doc-footnote">原注二</li></ol></section>'
                '</body></html>'
            ).encode()
        self.rewrite(change)
        self.body('<p><a href="../notes.xhtml#n1">1</a><a epub:type="noteref" href="../notes.xhtml#n2">2</a></p>')
        report = edit(self.src, self.out)
        notes = self.read('OPS/notes.xhtml')
        section = notes.xpath('//*[local-name()="section"]')[0]
        self.assertEqual(section.get('role'), 'doc-endnotes')
        self.assertIsNone(notes.xpath('//*[local-name()="ol"]')[0].get('role'))
        for target in notes.xpath('//*[local-name()="li"]'):
            self.assertNotIn(target.get('role'), ('doc-footnote', 'doc-endnote'))
        self.assertEqual(notes.xpath('//*[@id="n1"]')[0].get(TYPE), 'footnote')
        self.assertEqual(notes.xpath('//*[@id="n2"]')[0].get(TYPE), 'endnote')
        self.assertNotIn('endnote', notes.xpath('//*[@id="n1"]')[0].get(TYPE, '').split())
        self.assertEqual(report['notes'], 2)
        self.assertEqual(len(self.read().xpath('//*[local-name()="a" and @role="doc-noteref"]')), 2)

    def test_endnotes_keep_legal_footnote_types_and_normalize_legacy_role_only_entries(self):
        self.rewrite(lambda d: d.update({'OPS/notes.xhtml': (
            f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>注释</title></head><body>'
            '<section epub:type="endnotes"><ol><li id="n1" epub:type="footnote" role="doc-footnote">原脚注</li>'
            '<li id="n2" role="doc-endnote">旧端注</li><li id="n3">仅引用目标</li></ol></section>'
            '</body></html>').encode()}))
        self.body('<p><a epub:type="noteref" href="../notes.xhtml#n1">1</a>'
                  '<a epub:type="noteref" href="../notes.xhtml#n3">3</a></p>')
        edit(self.src, self.out)
        root = self.read('OPS/notes.xhtml')
        for identifier in ('n1', 'n2', 'n3'):
            target = root.xpath('//*[@id=$id]', id=identifier)[0]
            self.assertIn('footnote', target.get(TYPE, '').split())
            self.assertNotIn(target.get('role'), ('doc-footnote', 'doc-endnote'))
            self.assertNotIn('endnote', target.get(TYPE, '').split())

    def test_endnotes_role_requires_a_container_and_list(self):
        self.rewrite(lambda d: d.update({'OPS/notes.xhtml': (
            f'<html xmlns="{X}" xmlns:epub="{EP}"><head><title>注释</title></head><body>'
            '<section epub:type="endnotes" role="doc-endnotes"><p id="n1" epub:type="endnote">原注</p></section>'
            '<ol epub:type="endnotes" role="doc-endnotes"><li id="n2">第二注</li></ol>'
            '</body></html>').encode()}))
        edit(self.src, self.out)
        notes = self.read('OPS/notes.xhtml')
        collections = notes.xpath('//*[@role="doc-endnotes"]')
        self.assertTrue(all(E.QName(n).localname not in ('ol', 'ul') and n.xpath('.//*[local-name()="ol" or local-name()="ul"]') for n in collections))
        self.assertEqual(notes.xpath('//*[@id="n1"]')[0].get(TYPE), 'endnote')

    def add_image(self):
        def change(data):
            data['OPS/package.opf'] = data['OPS/package.opf'].replace(b'</manifest>', b'<item id="picture" href="img/picture.png" media-type="image/png"/></manifest>')
            data['OPS/img/picture.png'] = b'original image bytes'
        self.rewrite(change)

    def test_explicit_caption_and_credit_form_figure_in_original_order(self):
        self.add_image()
        self.body('<p id="image-paragraph"><img id="picture" src="../img/picture.png" alt="原图"/></p>'
                  '<p id="caption" class="caption">图一：原说明<a id="image-ref" epub:type="noteref" href="../notes.xhtml#n1">1</a>。<em>尾注</em></p>'
                  '<p id="source" class="source">来源：<a href="https://example.com">原来源</a>。</p><p>后文</p>')
        with zipfile.ZipFile(self.src) as z:
            before = ''.join(E.fromstring(z.read('OPS/text/c.xhtml')).xpath('//*[local-name()="body"]')[0].itertext())
        report = edit(self.src, self.out)
        root = self.read()
        figures = root.xpath('//*[local-name()="figure"]')
        self.assertEqual(len(figures), 1)
        figure = figures[0]
        self.assertEqual(E.QName(figure[-1]).localname, 'figcaption')
        captions = figure.xpath('./*[local-name()="figcaption"]')
        self.assertEqual(len(captions), 1)
        self.assertEqual([p.get('id') for p in captions[0]], ['caption', 'source'])
        self.assertTrue(all(E.QName(p).localname == 'p' for p in captions[0]))
        credit = root.xpath('//*[@epub:type="credit"]', namespaces={'epub': EP})
        self.assertEqual(len(credit), 1)
        self.assertEqual(E.QName(credit[0]).localname, 'span')
        self.assertEqual(credit[0].getparent().get('id'), 'source')
        self.assertEqual(''.join(credit[0].itertext()), '来源：原来源。')
        self.assert_marker_once(root.xpath('//*[@id="image-ref"]')[0])
        self.assertFalse(root.xpath('//*[local-name()="p"]/*[local-name()="p" or local-name()="figure"]'))
        self.assertEqual(''.join(root.xpath('//*[local-name()="body"]')[0].itertext()), before)
        self.assertEqual(root.xpath('//*[@id="picture"]')[0].get('src'), '../img/picture.png')
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(z.read('OPS/img/picture.png'), b'original image bytes')
        css = ''.join(self.styles(root)[0].itertext())
        self.assertIn('0.85em', css)
        self.assertIn('text-indent:0', css.replace(' ', ''))
        self.assertEqual(report['reading_layout']['figures'], 1)
        self.assertEqual(report['reading_layout']['captions'], 1)
        self.assertEqual(report['reading_layout']['credits'], 1)

    def test_existing_figcaption_paragraphs_and_text_tail_are_not_nested_or_lost(self):
        self.add_image()
        self.body('<figure id="f"><figcaption id="caption">前<span id="word">中</span>尾<p id="existing-p">既有段</p></figcaption>'
                  '<img src="../img/picture.png" alt="原图"/></figure><p><a href="#word">指向图注</a></p>')
        edit(self.src, self.out)
        root = self.read()
        figure = root.xpath('//*[@id="f"]')[0]
        self.assertEqual(E.QName(figure[-1]).localname, 'figcaption')
        caption = root.xpath('//*[@id="caption"]')[0]
        self.assertEqual(''.join(caption.itertext()), '前中尾既有段')
        self.assertEqual(len(root.xpath('//*[@id="existing-p"]')), 1)
        self.assertEqual(E.QName(root.xpath('//*[@id="existing-p"]')[0].getparent()).localname, 'figcaption')
        self.assertFalse(root.xpath('//*[local-name()="p"]/*[local-name()="p"]'))
        self.assertEqual(root.xpath('//*[local-name()="a"]')[0].get('href'), '#word')

    def test_caption_non_phrasing_flow_elements_remain_outside_paragraphs(self):
        self.add_image()
        self.body('<figure><img src="../img/picture.png"/><figcaption id="caption">前文'
                  '<address id="address">原来源</address><hr id="separator"/>'
                  '<article id="description"><p id="description-p">长描述</p></article>'
                  '<custom-flow id="custom"><p>未知块</p></custom-flow>尾文</figcaption></figure>')
        edit(self.src, self.out)
        root = self.read()
        caption = root.xpath('//*[@id="caption"]')[0]
        for identifier in ('address', 'separator', 'description', 'custom'):
            self.assertEqual(root.xpath('//*[@id=$id]', id=identifier)[0].getparent(), caption)
        self.assertFalse(root.xpath('//*[local-name()="p"]//*[local-name()="address" or local-name()="article" or local-name()="hr" or local-name()="p"]'))
        self.assertEqual(''.join(caption.itertext()), '前文原来源长描述未知块尾文')

    def test_explicit_credit_paragraph_retains_id_and_uses_phrasing_span(self):
        self.add_image()
        self.body('<figure><img src="../img/picture.png"/><figcaption><p>说明</p>'
                  '<p id="credit" epub:type="credit">来源<a href="https://example.com">站点</a>尾</p></figcaption></figure>')
        edit(self.src, self.out)
        root = self.read()
        paragraph = root.xpath('//*[@id="credit"]')[0]
        self.assertEqual(E.QName(paragraph).localname, 'p')
        self.assertNotIn('credit', paragraph.get(TYPE, '').split())
        self.assertEqual(paragraph[0].get(TYPE), 'credit')
        self.assertEqual(E.QName(paragraph[0]).localname, 'span')
        self.assertEqual(''.join(paragraph.itertext()), '来源站点尾')

    def test_explicit_source_span_marks_only_the_source_phrase(self):
        self.add_image()
        self.body('<figure><img src="../img/picture.png"/><figcaption><p id="caption">图注文字'
                  '<span id="source" class="source">来源<a href="https://example.com">原站点</a>尾</span>'
                  '后续图注</p></figcaption></figure>')
        report = edit(self.src, self.out)
        root = self.read()
        paragraph = root.xpath('//*[@id="caption"]')[0]
        span = root.xpath('//*[@id="source"]')[0]
        self.assertEqual(span.get(TYPE), 'credit')
        self.assertEqual(E.QName(span).localname, 'span')
        self.assertEqual(span.getparent(), paragraph)
        self.assertIsNone(paragraph.get(TYPE))
        self.assertEqual(''.join(paragraph.itertext()), '图注文字来源原站点尾后续图注')
        self.assertEqual(report['reading_layout']['credits'], 1)

    def test_ordinary_neighbors_inline_and_cover_images_are_not_guessed(self):
        self.add_image()
        self.body('<p id="picture-p"><img src="../img/picture.png"/></p><p id="ordinary">普通正文不是图注</p>'
                  '<p id="inline">行内<img src="../img/picture.png"/>正文</p>'
                  '<section epub:type="cover"><img src="../img/picture.png"/><p class="caption">封面标题</p></section>')
        report = edit(self.src, self.out)
        root = self.read()
        self.assertFalse(root.xpath('//*[local-name()="figure" or local-name()="figcaption"]'))
        self.assertEqual(E.QName(root.xpath('//*[@id="picture-p"]')[0]).localname, 'p')
        self.assertEqual(root.xpath('//*[@id="ordinary"]')[0].getparent(), root.xpath('//*[local-name()="body"]')[0])
        self.assertEqual(''.join(root.xpath('//*[@id="inline"]')[0].itertext()), '行内正文')
        self.assertEqual(report['issues'], [])
        self.assertTrue(report['reading_layout']['warnings'])

    def test_cover_resource_does_not_exclude_other_illustrations_in_same_document(self):
        self.add_image()
        def change(data):
            data['OPS/package.opf'] = data['OPS/package.opf'].replace(
                b'</manifest>', b'<item id="cover" href="img/cover.png" media-type="image/png" properties="cover-image"/></manifest>')
            data['OPS/img/cover.png'] = b'original cover bytes'
        self.rewrite(change)
        self.body('<section epub:type="cover"><img id="cover" src="../img/cover.png"/><p class="caption">封面</p></section>'
                  '<p id="standalone-cover"><img src="../img/cover.png"/></p><p class="caption">另一个封面引用</p>'
                  '<p id="ordinary-image"><img src="../img/picture.png"/></p><p id="ordinary-caption" class="caption">正文插图</p>')
        report = edit(self.src, self.out)
        root = self.read()
        self.assertEqual(len(root.xpath('//*[local-name()="figure"]')), 1)
        self.assertEqual(E.QName(root.xpath('//*[@id="ordinary-image"]')[0]).localname, 'figure')
        self.assertEqual(E.QName(root.xpath('//*[@id="ordinary-caption"]')[0].getparent()).localname, 'figcaption')
        self.assertEqual(E.QName(root.xpath('//*[@id="standalone-cover"]')[0]).localname, 'p')
        cover_section = root.xpath('//*[@epub:type="cover"]', namespaces={'epub': EP})[0]
        self.assertFalse(cover_section.xpath('.//*[local-name()="figure" or local-name()="figcaption"]'))
        self.assertEqual(report['reading_layout']['figures'], 1)
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(z.read('OPS/img/cover.png'), b'original cover bytes')

    def test_cover_guide_fragment_excludes_only_its_target_in_shared_document(self):
        self.add_image()
        def change(data):
            data['OPS/package.opf'] = data['OPS/package.opf'].replace(
                b'</manifest>', b'<item id="cover" href="img/cover.png" media-type="image/png"/></manifest>')
            data['OPS/package.opf'] = data['OPS/package.opf'].replace(
                b'</package>', b'<guide><reference type="cover" href="text/c.xhtml#cover-front"/></guide></package>')
            data['OPS/img/cover.png'] = b'original cover bytes'
        self.rewrite(change)
        self.body('<section id="cover-front"><p><img src="../img/cover.png"/></p><p class="caption">封面</p></section>'
                  '<p id="ordinary-image"><img src="../img/picture.png"/></p><p id="ordinary-caption" class="caption">正文插图</p>')
        report = edit(self.src, self.out)
        root = self.read()
        self.assertEqual(len(root.xpath('//*[local-name()="figure"]')), 1)
        self.assertEqual(E.QName(root.xpath('//*[@id="ordinary-image"]')[0]).localname, 'figure')
        cover = root.xpath('//*[@id="cover-front"]')[0]
        self.assertFalse(cover.xpath('.//*[local-name()="figure" or local-name()="figcaption"]'))
        self.assertEqual(''.join(cover.itertext()), '封面')
        self.assertEqual(report['reading_layout']['figures'], 1)

    def test_unassociated_source_or_caption_is_not_moved(self):
        self.add_image()
        self.body('<p><img src="../img/picture.png"/></p><p>隔开的正文</p>'
                  '<p id="caption" class="caption">不能猜测归属</p><p id="source" class="source">不能猜测来源</p>')
        edit(self.src, self.out)
        root = self.read()
        self.assertFalse(root.xpath('//*[local-name()="figure" or local-name()="figcaption"]'))
        self.assertEqual(E.QName(root.xpath('//*[@id="caption"]')[0].getparent()).localname, 'body')

    def test_meaningful_image_tail_is_not_reclassified_as_caption(self):
        self.add_image()
        self.body('<p id="image"><img src="../img/picture.png"/></p>这是普通正文'
                  '<p id="caption" class="caption">显式图注</p>')
        report = edit(self.src, self.out)
        root = self.read()
        self.assertFalse(root.xpath('//*[local-name()="figure" or local-name()="figcaption"]'))
        self.assertEqual(root.xpath('//*[@id="image"]')[0].tail, '这是普通正文')
        self.assertEqual(E.QName(root.xpath('//*[@id="caption"]')[0].getparent()).localname, 'body')
        self.assertTrue(report['reading_layout']['warnings'])
        self.assertEqual(report['issues'], [])

    def test_multiple_captions_with_prose_tails_keep_original_content_order(self):
        self.add_image()
        self.body('<figure id="figure"><img src="../img/picture.png"/>'
                  '<figcaption id="c1">图注一</figcaption>中间正文'
                  '<figcaption id="c2">图注二</figcaption>末尾正文</figure>')
        report = edit(self.src, self.out)
        figure = self.read().xpath('//*[@id="figure"]')[0]
        self.assertEqual(''.join(figure.itertext()), '图注一中间正文图注二末尾正文')
        self.assertEqual(figure.xpath('//*[@id="c1"]')[0].tail, '中间正文')
        self.assertEqual(figure.xpath('//*[@id="c2"]')[0].tail, '末尾正文')
        self.assertEqual(len(figure.xpath('./*[local-name()="figcaption"]')), 2)
        self.assertTrue(report['reading_layout']['warnings'])
        self.assertEqual(report['issues'], [])

    def test_source_after_intervening_prose_is_not_moved_into_caption(self):
        self.add_image()
        self.body('<p><img src="../img/picture.png"/></p><p class="caption">图注</p>正文间隔'
                  '<p id="source" class="source">独立来源段</p>')
        edit(self.src, self.out)
        root = self.read()
        source = root.xpath('//*[@id="source"]')[0]
        self.assertEqual(E.QName(source.getparent()).localname, 'body')
        self.assertEqual(''.join(root.xpath('//*[local-name()="body"]')[0].itertext()), '第一章图注正文间隔独立来源段')

    def test_caption_reordering_does_not_reorder_unassociated_figure_prose(self):
        self.add_image()
        self.body('<figure id="f"><figcaption id="caption">图注</figcaption>前文'
                  '<img src="../img/picture.png"/>后文</figure>')
        report = edit(self.src, self.out)
        figure = self.read().xpath('//*[@id="f"]')[0]
        self.assertEqual(''.join(figure.itertext()), '图注前文后文')
        self.assertTrue(report['reading_layout']['warnings'])

    def test_metadata_only_preserves_all_non_opf_bytes_and_skips_layout(self):
        self.add_image()
        self.body('<p><img src="../img/picture.png"/></p><p class="caption">图注</p>')
        with zipfile.ZipFile(self.src) as z:
            before = {n: z.read(n) for n in z.namelist() if n != 'OPS/package.opf'}
        report = edit(self.src, self.out, None, {'title': '新版'}, False, True)
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual({n: z.read(n) for n in z.namelist() if n != 'OPS/package.opf'}, before)
        self.assertFalse(report['reading_layout']['applied'])
        self.assertEqual(report['reading_layout']['note_markers'], 0)

    def test_preserve_retains_layout_and_legacy_six_positional_arguments(self):
        self.add_image()
        self.body('<p><img src="../img/picture.png"/></p><p class="caption">图注</p>'
                  '<p><a epub:type="noteref" href="../notes.xhtml#n1">1</a></p>')
        report = edit(self.src, self.out, None, None, False, False, reading_style='preserve')
        root = self.read()
        self.assertFalse(root.xpath('//*[local-name()="sup" or local-name()="figure" or local-name()="figcaption"]'))
        self.assertFalse(self.styles(root))
        self.assertEqual(report['notes'], 1)
        self.assertEqual(report['reading_layout']['mode'], 'preserve')
        self.assertFalse(report['reading_layout']['applied'])

    def test_repeat_edit_has_identical_document_layout_and_single_style(self):
        self.add_image()
        self.body('<p><img src="../img/picture.png"/></p><p class="caption">图注'
                  '<a epub:type="noteref" href="../notes.xhtml#n1">1</a></p><p class="source">来源</p>')
        edit(self.src, self.out)
        second = self.root / 'second.epub'
        edit(self.out, second)
        with zipfile.ZipFile(self.out) as a, zipfile.ZipFile(second) as b:
            self.assertEqual(a.read('OPS/text/c.xhtml'), b.read('OPS/text/c.xhtml'))
            self.assertEqual(a.read('OPS/notes.xhtml'), b.read('OPS/notes.xhtml'))
        root = self.read(path=second)
        self.assertEqual(len(self.styles(root)), 1)
        self.assertEqual(len(root.xpath('//*[local-name()="figcaption"]')), 1)
        self.assert_marker_once(self.marker(root))

    def test_invalid_reading_style_fails_without_publishing(self):
        with self.assertRaises(ValueError):
            edit(self.src, self.out, reading_style='floating')
        self.assertFalse(self.out.exists())

    def test_cli_standard_and_preserve_publish_json_layout_reports(self):
        for mode in ('standard', 'preserve'):
            with self.subTest(mode=mode):
                output = self.root / f'cli-{mode}.epub'
                result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(self.src), str(output),
                                         '--reading-style', mode], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['reading_layout']['mode'], mode)
                self.assertTrue(output.exists())


if __name__ == '__main__':
    unittest.main()

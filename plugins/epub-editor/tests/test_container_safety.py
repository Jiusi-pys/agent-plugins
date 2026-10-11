import html
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ebook_container_safety import validate_container_resources


REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
REL_TYPE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
ODF = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'xlink': 'http://www.w3.org/1999/xlink',
}


def relationships(target, *, relation='image', mode=None):
    attrs = ' Id="r1" Type="' + REL_TYPE + relation + '" Target="' + html.escape(target, quote=True) + '"'
    if mode is not None:
        attrs += ' TargetMode="' + mode + '"'
    return ('<Relationships xmlns="' + REL + '"><Relationship' + attrs + '/></Relationships>').encode()


def docx(target='media/picture.png', **kw):
    return {
        '[Content_Types].xml': b'<Types/>',
        'word/document.xml': b'<document><body/></document>',
        'word/_rels/document.xml.rels': relationships(target, **kw),
        'word/media/picture.png': b'synthetic image',
    }


def odt(content, *, document='content.xml'):
    namespaces = ' '.join('xmlns:' + name + '="' + uri + '"' for name, uri in ODF.items())
    return {
        'mimetype': b'application/vnd.oasis.opendocument.text',
        document: ('<office:document-content ' + namespaces + '><office:body>' + content + '</office:body></office:document-content>').encode(),
        'Pictures/picture.png': b'synthetic image',
        'Fonts/font.ttf': b'synthetic font',
    }


class ContainerResources(unittest.TestCase):
    def test_docx_contained_images_and_package_root_relationships_are_accepted(self):
        data = docx()
        data['_rels/.rels'] = relationships('word/document.xml', relation='officeDocument')
        validate_container_resources(data, 'docx')

    def test_docx_valid_parent_reference_remains_inside_package(self):
        data = docx('../media/picture.png')
        data['word/headers/_rels/header1.xml.rels'] = data.pop('word/_rels/document.xml.rels')
        data['word/headers/header1.xml'] = b'<header/>'
        validate_container_resources(data, 'docx')

    def test_docx_external_file_cannot_read_synthetic_payload_outside_input(self):
        with tempfile.TemporaryDirectory(prefix='container resource ') as temporary:
            root = Path(temporary)
            (root / 'input').mkdir()
            private = root / 'private-payload.bin'
            private.write_bytes(b'SYNTHETIC PRIVATE PAYLOAD - test fixture only')
            data = docx(private.as_uri(), mode='External')
            with patch('builtins.open', side_effect=AssertionError('validator must not open files')):
                with self.assertRaises(ValueError):
                    validate_container_resources(data, 'docx')
            self.assertEqual(private.read_bytes(), b'SYNTHETIC PRIVATE PAYLOAD - test fixture only')

    def test_docx_external_images_are_rejected_even_when_target_exists(self):
        for target in ('media/picture.png', 'https://example.invalid/picture.png', 'mailto:a@example.invalid'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_container_resources(docx(target, mode='External'), 'docx')

    def test_docx_absolute_and_windows_paths_are_rejected(self):
        for target in ('/word/media/picture.png', 'C:/private.bin', r'C:\private.bin',
                       r'\\server\share\private.bin', '//server/share/private.bin',
                       'file:///C:/private.bin', '%2fword/media/picture.png', 'media%5cpicture.png'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_container_resources(docx(target), 'docx')

    def test_docx_encoded_and_plain_traversal_are_rejected(self):
        for target in ('../../private.bin', '%2e%2e/%2e%2e/private.bin',
                       '%252e%252e/%252e%252e/private.bin', 'media/picture.png?file=private'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_container_resources(docx(target), 'docx')

    def test_docx_missing_internal_resource_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_container_resources(docx('media/missing.png'), 'docx')

    def test_docx_scans_all_relationship_files(self):
        data = docx()
        data['word/_rels/header1.xml.rels'] = relationships('file:///synthetic-private.bin', mode='External')
        data['word/header1.xml'] = b'<header/>'
        with self.assertRaises(ValueError):
            validate_container_resources(data, 'docx')

    def test_docx_normal_http_https_and_mailto_hyperlinks_are_accepted(self):
        for target in ('http://example.invalid/chapter', 'https://example.invalid/chapter?q=1#note',
                       'mailto:reader@example.invalid'):
            with self.subTest(target=target):
                validate_container_resources(docx(target, relation='hyperlink', mode='External'), 'docx')

    def test_docx_file_hyperlinks_and_unknown_external_types_are_rejected(self):
        for relation in ('hyperlink', 'image', 'font', 'hyperlinkish'):
            with self.subTest(relation=relation), self.assertRaises(ValueError):
                validate_container_resources(docx('file:///synthetic-private.bin', relation=relation, mode='External'), 'docx')

    def test_docx_relationship_target_can_use_percent_encoded_package_filename(self):
        data = docx('media/picture%20one.png')
        data['word/media/picture one.png'] = data.pop('word/media/picture.png')
        validate_container_resources(data, 'docx')

    def test_entities_are_rejected_without_loading_external_data(self):
        for declaration in ('<!DOCTYPE document [<!ENTITY leak SYSTEM "file:///synthetic-private.bin">]>',
                            '<!DOCTYPE document [<!ENTITY leak "internal">]>'):
            for use in ('', '&leak;'):
                for encoding in ('utf-8', 'utf-16'):
                    with self.subTest(declaration=declaration, use=use, encoding=encoding):
                        data = docx()
                        data['word/document.xml'] = (declaration + '<document><body>' + use + '</body></document>').encode(encoding)
                        with self.assertRaises(ValueError):
                            validate_container_resources(data, 'docx')

    def test_odt_embedded_images_fonts_and_object_packages_are_accepted(self):
        data = odt('<draw:image xlink:href="Pictures/picture.png"/><svg:font-face-uri xlink:href="Fonts/font.ttf"/><draw:object xlink:href="./Object 1"/>')
        data['Object 1/content.xml'] = b'<document/>'
        validate_container_resources(data, 'odt')

    def test_odt_remote_absolute_and_missing_images_are_rejected(self):
        for target in ('https://example.invalid/picture.png', 'file:///synthetic-private.bin',
                       '../private.bin', '%2e%2e/private.bin', '/Pictures/picture.png', 'Pictures/missing.png'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_container_resources(odt('<draw:image xlink:href="' + target + '"/>'), 'odt')

    def test_odt_styles_xml_external_fonts_are_rejected(self):
        data = odt('<text:p>正文</text:p>')
        data.update(odt('<svg:font-face-uri xlink:href="file:///synthetic-private-font.ttf"/>', document='styles.xml'))
        with self.assertRaises(ValueError):
            validate_container_resources(data, 'odt')

    def test_odt_normal_hyperlinks_remain_accepted(self):
        for target in ('https://example.invalid/#note', 'http://example.invalid/', 'mailto:reader@example.invalid', '#chapter'):
            with self.subTest(target=target):
                validate_container_resources(odt('<text:a xlink:href="' + target + '">普通链接</text:a>'), 'odt')

    def test_odt_other_external_resources_and_file_hyperlinks_are_rejected(self):
        for tag in ('text:section-source', 'draw:plugin', 'draw:object', 'text:a'):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                validate_container_resources(odt('<' + tag + ' xlink:href="file:///synthetic-private.bin"/>'), 'odt')

    def test_xml_base_cannot_redirect_contained_resources(self):
        for kind, data in (('docx', docx()), ('odt', odt('<draw:image xlink:href="Pictures/picture.png"/>'))):
            name = 'word/_rels/document.xml.rels' if kind == 'docx' else 'content.xml'
            data[name] = data[name].replace(b'>', b' xml:base="file:///outside/">', 1)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_container_resources(data, kind)

    def test_invalid_xml_and_unsupported_kinds_raise_value_error(self):
        for kind, name, data in (('docx', 'word/document.xml', docx()), ('odt', 'content.xml', odt(''))):
            data[name] = b'<not-closed'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_container_resources(data, kind)
        with self.assertRaises(ValueError):
            validate_container_resources({}, 'epub')


if __name__ == '__main__':
    unittest.main()

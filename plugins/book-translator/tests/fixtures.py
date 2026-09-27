"""Original tiny EPUB fixtures. No third-party book content."""
from pathlib import Path
import zipfile

X = 'http://www.w3.org/1999/xhtml'
EP = 'http://www.idpf.org/2007/ops'


def page(title, body):
    return (f'<html xmlns="{X}" xmlns:epub="{EP}" lang="en"><head>'
            f'<title>{title}</title></head><body>{body}</body></html>').encode()


def make_epub(path, *, no_nav=False, long=False, epub2=False):
    path = Path(path)
    version = '2.0' if epub2 else '3.0'
    nav_item = '' if no_nav else '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    data = {
        'mimetype': b'application/epub+zip',
        'META-INF/container.xml': b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        'OPS/package.opf': f'''<package xmlns="http://www.idpf.org/2007/opf" version="{version}" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Small Arguments</dc:title><dc:creator>Example Author</dc:creator><dc:identifier id="uid">urn:sample:arguments</dc:identifier><dc:language>en</dc:language></metadata><manifest>
          <item id="b" href="b.xhtml" media-type="application/xhtml+xml"/>
          <item id="a" href="a.xhtml" media-type="application/xhtml+xml"/>
          <item id="notes" href="notes.xhtml" media-type="application/xhtml+xml"/>{nav_item}
          <item id="image" href="pixel.png" media-type="image/png"/>
        </manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>'''.encode(),
        'OPS/b.xhtml': page('Continuation', '<p id="p3">A condition can be necessary without being sufficient.</p><pre>if (x &lt; 2) return 0;</pre>'),
        'OPS/a.xhtml': page('Small Arguments', '<h1 id="one">One: Reasons</h1><p id="p1">A <em>reason</em> supports a claim; it does not guarantee it.<a epub:type="noteref" href="notes.xhtml#n1">1</a></p><h1 id="two">Two: Conditions</h1><p id="p2">If it rains, the road is wet. A wet road does not prove rain.</p><img src="pixel.png" alt="A road"/>' + ('<p>' + ('A very long sentence. ' * 800) + '</p>' if long else '')),
        'OPS/notes.xhtml': page('Original notes', '<aside id="n1" epub:type="footnote"><p>This is an original author note.</p></aside>'),
        'OPS/pixel.png': b'fixture-image-preserved-verbatim',
    }
    if not no_nav:
        data['OPS/nav.xhtml'] = page('Contents', '<nav epub:type="toc"><ol><li><a href="a.xhtml#one">One: Reasons</a></li><li><a href="a.xhtml#two">Two: Conditions</a></li></ol></nav>')
    write_zip(path, data)
    return path


def write_zip(path, data):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype', data['mimetype'], compress_type=zipfile.ZIP_STORED)
        for name, content in data.items():
            if name != 'mimetype':
                z.writestr(name, content)

"""Create an original two-chapter book for REAL agent smoke testing."""
import argparse
import io
from pathlib import Path
from PIL import Image
from fixtures import page, write_zip


def create_demo(directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source = directory / 'Small Arguments.epub'
    pixel = io.BytesIO()
    Image.new('RGB', (1, 1), (30, 45, 70)).save(pixel, format='PNG')
    data = {
        'mimetype': b'application/epub+zip',
        'META-INF/container.xml': b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        'OPS/package.opf': b'''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Small Arguments</dc:title><dc:creator>Example Author</dc:creator><dc:identifier id="uid">urn:original-demo:small-arguments</dc:identifier><dc:language>en</dc:language><dc:description>An original demonstration written for this plugin test.</dc:description></metadata><manifest><item id="a" href="reasons.xhtml" media-type="application/xhtml+xml"/><item id="b" href="conditions.xhtml" media-type="application/xhtml+xml"/><item id="image" href="pixel.png" media-type="image/png"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>''',
        'OPS/reasons.xhtml': page('Small Arguments', '''<h1 id="reasons">One: Reasons and Certainty</h1>
<p id="reason">A <em>reason</em> can support a claim without guaranteeing that the claim is true. Treating support as proof would hide the possibility of error.</p>
<p id="doubt">To doubt a claim is not necessarily to reject it. A person may suspend judgment while looking for better evidence.<a epub:type="noteref" href="#author-note">1</a></p>
<aside id="author-note" epub:type="footnote"><p>The distinction concerns what we are justified in believing, not merely what we happen to believe.</p></aside>
<p id="context">In the next chapter, the same caution will apply to conditions: a fact may matter without being enough by itself.</p>'''),
        'OPS/conditions.xhtml': page('Conditions', '''<h1 id="conditions">Two: Necessary and Sufficient Conditions</h1>
<p id="rain">If it rains, the road is wet. Even if this conditional is true, observing a wet road does not prove that it rained.</p>
<p id="necessary">A condition is necessary when the result cannot occur without it. It is sufficient when its presence guarantees the result. One condition can be necessary without being sufficient.</p>
<p id="only">Saying that a person may enter only if they have a ticket makes having a ticket necessary for entry. It does not promise entry to every ticket holder.</p>
<p id="scope">These claims concern the stated rules. Changing the rules or the background assumptions may change which conditions are necessary or sufficient.</p>
<figure><img src="pixel.png" alt="A tiny decorative square"/><figcaption>A decorative image, unrelated to the logical argument.</figcaption></figure>'''),
        'OPS/pixel.png': pixel.getvalue(),
    }
    write_zip(source, data)
    return source


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    print(create_demo(parser.parse_args().directory))

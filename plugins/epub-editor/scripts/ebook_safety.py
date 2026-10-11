"""Bounded, passive input validation for the ebook conversion adapter."""
import base64
import io
import json
import posixpath
import re
import stat
import zipfile
from pathlib import Path
from urllib.parse import unquote, unquote_to_bytes, urlsplit

from lxml import etree as E, html
from epub_editor import read_package, xml, elements, local, resolve, TYPE
from ebook_container_safety import validate_container_resources

MAX_FILE = 128 * 1024**2
MAX_EXPANDED = 256 * 1024**2
ACTIVE_TAGS = {'script', 'iframe', 'object', 'embed', 'applet', 'form', 'base'}
NOTE_TYPES = {'noteref', 'footnote', 'endnote', 'rearnote', 'footnotes', 'rearnotes', 'endnotes'}
NOTE_ROLES = {'doc-noteref', 'doc-footnote', 'doc-endnote', 'doc-endnotes'}


class UnsafeBook(ValueError):
    pass


def checked_zip(path):
    if Path(path).stat().st_size > MAX_FILE:
        raise UnsafeBook('Archive exceeds 128 MiB')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) > 10000 or len(names) != len(set(names)):
            raise UnsafeBook('Too many or duplicate ZIP entries')
        if sum(entry.file_size for entry in entries) > MAX_EXPANDED:
            raise UnsafeBook('Expanded archive exceeds 256 MiB')
        folded = set()
        for entry in entries:
            name = entry.filename
            components = name[:-1].split('/') if entry.is_dir() else name.split('/')
            if (entry.file_size > 32 * 1024**2 or name.startswith('/') or '\\' in name
                    or ':' in name or any(part in ('', '.', '..') for part in components)
                    or any(part.endswith((' ', '.')) or re.search(r'[\x00-\x1f<>"|?*]', part)
                           or re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)
                           for part in components)):
                raise UnsafeBook('Unsafe ZIP path: ' + name)
            if name.casefold() in folded:
                raise UnsafeBook('Case-colliding ZIP paths: ' + name)
            folded.add(name.casefold())
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise UnsafeBook('ZIP symlinks are unsupported: ' + name)
            if entry.flag_bits & 1:
                raise UnsafeBook('Encrypted ZIP entry: ' + name)
        return {entry.filename: archive.read(entry) for entry in entries if not entry.is_dir()}


def data_image(url, depth=0):
    if depth > 16:
        raise UnsafeBook('Image data URI nesting exceeds limits')
    match = re.fullmatch(r'data:(image/(?:png|jpeg|gif|webp|bmp|svg\+xml))(;base64)?,(.*)', url, re.I | re.S)
    if not match:
        raise UnsafeBook('Only image data URIs are accepted')
    try:
        content = base64.b64decode(match[3], validate=True) if match[2] else unquote_to_bytes(match[3])
    except Exception as exc:
        raise UnsafeBook('Invalid image data URI') from exc
    if not content or len(content) > 32 * 1024**2:
        raise UnsafeBook('Empty or oversized image data URI')
    if match[1].lower() == 'image/svg+xml':
        def embedded(value):
            if value.startswith('#'):
                return
            if value.startswith('data:'):
                data_image(value, depth + 1)
                return
            raise UnsafeBook('SVG data URI has an external resource')
        check_markup(xml(content), embedded)


def check_css(content, resource):
    css = re.sub(r'/\*.*?\*/', '', content, flags=re.S)
    if re.search(r'(?:expression\s*\(|javascript\s*:|@(?:charset|namespace)\s+url)', css, re.I):
        raise UnsafeBook('Active CSS is unsupported')
    # Escaped CSS identifiers could hide URL/import expressions from validation.
    if '\\' in css:
        raise UnsafeBook('Escaped CSS requires explicit normalization before conversion')
    pattern = r'url\(\s*(?:"([^"\n]*)"|\'([^\'\n]*)\'|([^\s)]+))\s*\)'
    for match in re.finditer(pattern, css, re.I):
        resource(next(value for value in match.groups() if value is not None))
    if re.search(r'url\s*\(', re.sub(pattern, '', css, flags=re.I), re.I):
        raise UnsafeBook('Malformed CSS URL')
    for match in re.finditer(r'@import\s+([^;]+)', css, re.I):
        target = match[1].strip()
        if target.lower().startswith('url('):
            continue
        quoted = re.match(r'["\']([^"\']+)["\']', target)
        if not quoted:
            raise UnsafeBook('Unrecognized CSS import')
        resource(quoted[1])


def check_markup(root, resource, *, hyperlinks=None):
    for node in root.iter():
        tag = local(node).lower()
        if tag in ACTIVE_TAGS:
            raise UnsafeBook('Active book element is unsupported: ' + tag)
        for key, value in node.attrib.items():
            attr = key.rsplit('}', 1)[-1].rsplit(':', 1)[-1].lower()
            compact = re.sub(r'[\x00-\x20]', '', value).lower()
            if attr.startswith('on') or compact.startswith(('javascript:', 'vbscript:')):
                raise UnsafeBook('Active book attribute is unsupported: ' + attr)
            if attr == 'srcset':
                raise UnsafeBook('srcset requires explicit normalization before conversion')
            if attr == 'style':
                check_css(value, resource)
            if attr in ('src', 'poster', 'data', 'background'):
                resource(value)
            elif attr == 'href':
                if tag == 'a':
                    if compact.startswith('data:'):
                        raise UnsafeBook('Data URI hyperlinks are unsupported')
                    if hyperlinks:
                        hyperlinks(value)
                elif tag in ('link', 'image', 'use', 'feimage'):
                    if tag == 'link' and node.get('rel', '').lower() not in ('stylesheet', 'icon'):
                        raise UnsafeBook('Unsupported linked resource')
                    resource(value)
        if tag == 'style':
            check_css(''.join(node.itertext()), resource)


def markup_root(content):
    return html.document_fromstring(content)


def _without_code(content):
    # Preserve offsets so resource substitutions never alter prose or code.
    def mask(match):
        return ''.join('\n' if token == '\n' else ' ' for token in match[0])
    content = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', mask, content)
    return re.sub(r'(`+)[^`]*\1', mask, content)


def _markdown_image_targets(content):
    """Return each image URL and exact source replacement span."""
    text = _without_code(content)
    definitions = {}
    target = r'(<[^>\n]+>|(?:\\ |[^\s)])+)'
    for match in re.finditer(r'(?m)^\s{0,3}\[([^\]\n]+)\]:\s*' + target, text):
        definitions[' '.join(match[1].lower().split())] = match[2].strip('<>').replace('\\ ', ' ')
    inline = re.compile(r'(?<!\\)!\[([^\]\n]*)\]\(\s*' + target + r'(?:\s+["\'][^\n]*["\'])?\s*\)')
    found = []
    spans = []
    for match in inline.finditer(text):
        found.append((match[2].strip('<>').replace('\\ ', ' '), match.span(2), None))
        spans.append(match.span())
    reference = re.compile(r'(?<!\\)!\[([^\]\n]*)\](?:\[([^\]\n]*)\])?')
    for match in reference.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue
        key = ' '.join((match[2] or match[1]).lower().split())
        if key not in definitions:
            raise UnsafeBook('Unresolved or unsupported Markdown image reference: ' + key)
        found.append((definitions[key], match.span(), match[1]))
    return found


def markdown_images(content):
    return [url for url, _, _ in _markdown_image_targets(content)]


def embed_markdown_images(path):
    """Embed validated local image targets for Pandoc's pure sandbox reader."""
    path = Path(path)
    content = path.read_text(encoding='utf-8')
    media_types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                   '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp', '.svg': 'image/svg+xml'}

    def embedded(url):
        parsed = urlsplit(url)
        if parsed.scheme == 'data':
            data_image(url)
            return url
        resource = (path.parent / unquote(parsed.path)).resolve()
        if parsed.scheme or parsed.netloc or not resource.is_relative_to(path.parent.resolve()) or not resource.is_file():
            raise UnsafeBook('Invalid staged Markdown image: ' + url)
        media_type = media_types.get(resource.suffix.lower())
        if not media_type:
            raise UnsafeBook('Unsupported Markdown image type: ' + resource.suffix)
        uri = 'data:' + media_type + ';base64,' + base64.b64encode(resource.read_bytes()).decode('ascii')
        data_image(uri)
        return uri

    replacements = []
    for url, (start, end), alt in _markdown_image_targets(content):
        uri = embedded(url)
        replacements.append((start, end, '<' + uri + '>' if alt is None else '![' + alt + '](<' + uri + '>)'))
    masked = _without_code(content)
    for tag in re.finditer(r'<(?:img|image)\b[^>]*>', masked, re.I):
        attr = re.search(r'\b(?:src|(?:[\w.-]+:)?href)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag[0], re.I)
        if attr:
            group = next(index for index in (1, 2, 3) if attr[index] is not None)
            start, end = attr.span(group)
            replacements.append((tag.start() + start, tag.start() + end, embedded(attr[group])))
    for start, end, replacement in sorted(replacements, reverse=True):
        content = content[:start] + replacement + content[end:]
    path.write_text(content, encoding='utf-8', newline='\n')


def stage_text(source, target, encoding, kind):
    """Copy only resources referenced inside the input directory to private staging."""
    source = Path(source).resolve()
    base = source.parent
    target.parent.mkdir(parents=True, exist_ok=True)
    visited = set()
    total = source.stat().st_size
    if total > MAX_FILE:
        raise UnsafeBook('Text input exceeds 128 MiB')

    def read_text(path):
        try:
            return path.read_bytes().decode(encoding if encoding != 'utf-8' else 'utf-8-sig', errors='strict').replace('\r\n', '\n').replace('\r', '\n')
        except (UnicodeError, LookupError) as exc:
            raise UnsafeBook('Cannot decode input using ' + encoding + '; specify --input-encoding') from exc

    def copy_file(path):
        nonlocal total
        path = path.resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise UnsafeBook('Resource is missing or outside input directory: ' + str(path))
        rel = path.relative_to(base)
        if rel in visited:
            return
        visited.add(rel)
        total += path.stat().st_size
        if len(visited) > 10000 or total > MAX_EXPANDED or path.stat().st_size > 32 * 1024**2:
            raise UnsafeBook('Local input resources exceed limits')
        destination = target.parent / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        suffix = path.suffix.lower()
        if suffix == '.css':
            content = read_text(path)
            check_css(content, lambda url: resource(path, url))
            destination.write_text(content, encoding='utf-8', newline='\n')
        elif suffix in ('.html', '.htm', '.xhtml', '.svg'):
            content = read_text(path)
            root = xml(content.encode('utf-8')) if suffix == '.svg' else markup_root(content)
            check_markup(root, lambda url: resource(path, url), hyperlinks=lambda url: hyperlink(path, url))
            destination.write_text(content, encoding='utf-8', newline='\n')
        else:
            destination.write_bytes(path.read_bytes())

    def resource(current, url):
        if url.startswith('#'):
            return
        parsed = urlsplit(url.strip())
        if parsed.scheme == 'data':
            data_image(url)
            return
        if parsed.scheme or parsed.netloc or parsed.query or '\\' in unquote(parsed.path):
            raise UnsafeBook('Remote or absolute resource is unsupported: ' + url)
        if not parsed.path or parsed.path.startswith('/'):
            raise UnsafeBook('Invalid local resource: ' + url)
        copy_file(current.parent / unquote(parsed.path))

    def hyperlink(current, url):
        parsed = urlsplit(url)
        if parsed.scheme in ('http', 'https', 'mailto', 'tel') or (not parsed.path and parsed.fragment):
            return
        if parsed.scheme or parsed.netloc:
            raise UnsafeBook('Unsupported hyperlink scheme: ' + url)
        if parsed.path:
            resource(current, url)

    content = read_text(source)
    if kind == 'html':
        check_markup(markup_root(content), lambda url: resource(source, url), hyperlinks=lambda url: hyperlink(source, url))
    elif kind == 'markdown':
        for url in markdown_images(content):
            resource(source, url)
        check_markup(markup_root(_without_code(content)), lambda url: resource(source, url), hyperlinks=lambda url: hyperlink(source, url))
    target.write_text(content, encoding='utf-8', newline='\n')


def inspect_epub(path):
    checked_zip(path)
    data, package_path, opf = read_package(path)
    manifest = elements(opf, 'manifest')
    spine = elements(opf, 'spine')
    if len(manifest) != 1 or len(spine) != 1:
        raise UnsafeBook('EPUB must contain one manifest and spine')
    docs = {}
    items = {}
    for item in elements(manifest[0], 'item'):
        item_id = item.get('id')
        target = resolve(package_path, item.get('href', ''))
        if not item_id or item_id in items or not target or target[0] not in data:
            raise UnsafeBook('Broken or duplicate EPUB manifest item')
        if 'scripted' in item.get('properties', '').split():
            raise UnsafeBook('Scripted EPUB is unsupported')
        items[item_id] = (target[0], item)
        if item.get('media-type') in ('application/xhtml+xml', 'image/svg+xml'):
            docs[target[0]] = xml(data[target[0]])
            root = docs[target[0]]
            if item.get('media-type') == 'application/xhtml+xml' and (local(root) != 'html' or not elements(root, 'body')):
                raise UnsafeBook('Invalid EPUB XHTML document: ' + target[0])
    for ref in elements(spine[0], 'itemref'):
        if ref.get('idref') not in items:
            raise UnsafeBook('Broken EPUB spine reference')
    if not elements(spine[0], 'itemref'):
        raise UnsafeBook('EPUB has an empty spine')

    def resource(current, url):
        if url.startswith('#'):
            return
        if urlsplit(url).scheme == 'data':
            data_image(url)
            return
        target = resolve(current, url)
        if not target or target[0] not in data:
            raise UnsafeBook('Remote or missing EPUB resource: ' + url)

    for current, root in docs.items():
        check_markup(root, lambda url: resource(current, url))
    for current, content in data.items():
        if current.lower().endswith('.css'):
            check_css(content.decode('utf-8-sig'), lambda url: resource(current, url))
    return data, package_path, opf, docs, items


def pandoc_epub(source, output):
    data, package_path, opf, docs, items = inspect_epub(source)
    basenames = set()
    changed = False
    xhtml = '{http://www.w3.org/1999/xhtml}'
    media_types = {path: item.get('media-type') for path, item in items.values()}

    def self_contained_svg(root, current, ancestry=()):
        if current in ancestry:
            raise UnsafeBook('Recursive SVG image resource: ' + current)
        for node in root.iter():
            for key, value in list(node.attrib.items()):
                attribute = key.rsplit('}', 1)[-1].rsplit(':', 1)[-1]
                if attribute not in ('href', 'src') or value.startswith(('#', 'data:')):
                    continue
                target = resolve(current, value)
                if local(node) not in ('image', 'feImage') or not target or target[0] not in data or target[1]:
                    raise UnsafeBook('SVG resource cannot be embedded safely: ' + value)
                name = target[0]
                content = data[name]
                media_type = media_types.get(name)
                if media_type == 'image/svg+xml':
                    nested = xml(content)
                    self_contained_svg(nested, name, (*ancestry, current))
                    content = E.tostring(nested, encoding='utf-8')
                uri = 'data:' + (media_type or '') + ';base64,' + base64.b64encode(content).decode('ascii')
                data_image(uri)
                node.set(key, uri)
        data_image('data:image/svg+xml;base64,' + base64.b64encode(E.tostring(root, encoding='utf-8')).decode('ascii'))

    serial = 0
    def simple_raster_svg(svg, current):
        if len(svg) != 1 or local(svg[0]) != 'image' or len(svg[0]):
            return None
        child = svg[0]
        root_attributes = {'version', 'width', 'height', 'viewBox', 'preserveAspectRatio', 'id', 'aria-label'}
        image_attributes = {'href', 'width', 'height', 'x', 'y', 'preserveAspectRatio'}
        if (any(key.rsplit('}', 1)[-1] not in root_attributes for key in svg.attrib)
                or any(key.rsplit('}', 1)[-1] not in image_attributes for key in child.attrib)):
            return None
        try:
            if any(float(child.get(key, '0').rstrip('%')) != 0 for key in ('x', 'y')):
                return None
            viewbox = [float(number) for number in svg.get('viewBox', '0 0 1 1').split()]
            if len(viewbox) != 4 or viewbox[:2] != [0, 0]:
                return None
        except ValueError:
            return None
        url = child.get('{http://www.w3.org/1999/xlink}href') or child.get('href')
        if not url:
            return None
        target = resolve(current, url)
        if target and media_types.get(target[0]) in ('image/png', 'image/jpeg'):
            return url
        if url.startswith(('data:image/png;', 'data:image/jpeg;')):
            return url
        return None

    for current, root in list(docs.items()):
        if local(root) == 'svg':
            self_contained_svg(root, current)
            changed = True
            continue
        for svg in list(root.xpath('//*[local-name()="svg"]')):
            raster = simple_raster_svg(svg, current)
            if raster:
                image = E.Element(xhtml + 'img', src=raster, alt=svg.get('aria-label', ''))
                if svg.get('id'):
                    image.set('id', svg.get('id'))
                image.tail = svg.tail
                svg.getparent().replace(svg, image)
                changed = True
                continue
            self_contained_svg(svg, current)
            while True:
                serial += 1
                identifier = 'conversion-inline-svg-' + str(serial)
                name = posixpath.join(posixpath.dirname(package_path), identifier + '.svg')
                if name not in data and identifier not in items:
                    break
            data[name] = E.tostring(svg, encoding='utf-8', xml_declaration=True)
            manifest = elements(opf, 'manifest')[0]
            item = E.SubElement(manifest, '{http://www.idpf.org/2007/opf}item', id=identifier,
                                href=posixpath.relpath(name, posixpath.dirname(package_path)),
                                attrib={'media-type': 'image/svg+xml'})
            items[identifier] = (name, item)
            image = E.Element(xhtml + 'img', src=posixpath.relpath(name, posixpath.dirname(current)))
            image.set('alt', svg.get('aria-label', '') or ''.join(svg.xpath('.//*[local-name()="title"]/text()')))
            if svg.get('id'):
                image.set('id', svg.get('id'))
            image.tail = svg.tail
            svg.getparent().replace(svg, image)
            changed = True
    for path, root in docs.items():
        if not path.lower().endswith(('.xhtml', '.html', '.htm')):
            continue
        basename = posixpath.basename(path)
        if basename in basenames:
            raise UnsafeBook('Pandoc anchor collision: duplicate XHTML basename ' + basename)
        basenames.add(basename)
        for node in list(root.iter()):
            if local(node) == 'a' and node.get('name'):
                name = node.attrib.pop('name')
                if node.get('id') and node.get('id') != name:
                    alias = E.Element(xhtml + 'span', id=name)
                    node.addprevious(alias)
                else:
                    node.set('id', name)
                changed = True
        ids = root.xpath('//@id')
        if len(ids) != len(set(ids)):
            raise UnsafeBook('Duplicate EPUB anchors: ' + path)
    spine = elements(opf, 'spine')[0]
    spine_ids = {ref.get('idref') for ref in elements(spine, 'itemref')}
    by_path = {path: (key, item) for key, (path, item) in items.items()}
    def note_target(node):
        return (bool(set((node.get(TYPE, '') + ' ' + node.get('type', '')).split()) & (NOTE_TYPES - {'noteref'}))
                or node.get('role') in NOTE_ROLES - {'doc-noteref'}
                or bool(set(node.get('class', '').split()) & {'footnote', 'endnote', 'rearnote'}))
    note_ids = {(path, node.get('id')) for path, root in docs.items() for node in root.iter()
                if node.get('id') and any(note_target(ancestor) for ancestor in [node, *node.iterancestors()])}
    references = set()
    for current, root in docs.items():
        for node in root.iter():
            types = set((node.get(TYPE, '') + ' ' + node.get('type', '')).split())
            role = node.get('role', '')
            is_ref = 'noteref' in types or role == 'doc-noteref' or any(c in ('noteref', 'footnote-ref', 'endnote-ref') for c in node.get('class', '').split()) or node.get('rel') == 'footnote'
            target = resolve(current, node.get('href', '')) if local(node) == 'a' and node.get('href') else None
            if target and target[0] in docs and target[1]:
                matches = docs[target[0]].xpath('//*[@id=$id]', id=target[1])
                if len(matches) != 1:
                    raise UnsafeBook('Missing or ambiguous EPUB link target: ' + node.get('href', ''))
                references.add(target)
                is_ref = is_ref or target in note_ids
            if is_ref:
                if not target or target[0] not in docs or not target[1]:
                    raise UnsafeBook('Unresolved EPUB note reference: ' + node.get('href', ''))
                matches = docs[target[0]].xpath('//*[@id=$id]', id=target[1])
                if len(matches) != 1:
                    raise UnsafeBook('Missing or ambiguous EPUB note target: ' + node.get('href', ''))
                if local(matches[0]) == 'aside':
                    matches[0].tag = xhtml + 'div'
                    changed = True
                item_id, item = by_path[target[0]]
                if item_id not in spine_ids:
                    E.SubElement(spine, '{http://www.idpf.org/2007/opf}itemref', idref=item_id)
                    spine_ids.add(item_id)
                    changed = True
            if types & NOTE_TYPES:
                if local(node) == 'aside':
                    node.tag = xhtml + 'div'
                for attribute in (TYPE, 'type'):
                    remaining = set(node.get(attribute, '').split()) - NOTE_TYPES
                    if remaining:
                        node.set(attribute, ' '.join(sorted(remaining)))
                    else:
                        node.attrib.pop(attribute, None)
                changed = True
            if role in NOTE_ROLES:
                node.attrib.pop('role', None)
                changed = True
            if is_ref:
                node.attrib.pop('rel', None)
                node.set('class', ' '.join(c for c in node.get('class', '').split() if c not in ('noteref', 'footnote-ref', 'endnote-ref')))
    # Pandoc drops paragraph IDs and legacy empty a/name anchors. Preserve each
    # in an ordinary div/span in this private copy, keeping its actual content.
    preserved = {'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    blocks = {'p', 'aside', 'section', 'article', 'header', 'footer', 'main', 'nav',
              'blockquote', 'pre', 'address', 'figure', 'figcaption', 'ul', 'ol', 'dl', 'table'}
    structural = {'body', 'li', 'dt', 'dd', 'td', 'th'}
    inline = {'a', 'b', 'i', 'em', 'strong', 'small', 'sup', 'sub', 'code', 'img',
              'br', 'u', 's', 'strike', 'mark', 'q', 'abbr', 'cite', 'time'}
    for current, root in docs.items():
        if not current.lower().endswith(('.xhtml', '.html', '.htm')):
            continue
        for node in list(root.iter()):
            anchor = node.get('id')
            tag = local(node)
            if not anchor or tag in preserved:
                continue
            if tag == 'a' and not node.get('href'):
                node.tag = xhtml + 'span'
                if not len(node) and not node.text and local(node.getparent()) == 'p':
                    # Native RTF/ODT bookmarks import as empty inline anchors.
                    # Their paragraph remainder is the actual target content.
                    node.text, node.tail = node.tail, None
                    for following in list(node.itersiblings()):
                        node.append(following)
            elif tag in structural:
                wrapper = E.Element(xhtml + 'div', id=anchor)
                wrapper.text, node.text = node.text, None
                for child in list(node):
                    wrapper.append(child)
                node.append(wrapper)
                node.attrib.pop('id')
            elif tag in blocks or tag in inline:
                wrapper = E.Element(xhtml + ('div' if tag in blocks else 'span'), id=anchor)
                wrapper.tail, node.tail = node.tail, None
                node.attrib.pop('id')
                parent = node.getparent()
                parent.replace(node, wrapper)
                wrapper.append(node)
            elif (current, anchor) in references:
                raise UnsafeBook('Pandoc cannot safely preserve anchor on ' + tag + ': ' + anchor)
            else:
                continue
            changed = True
    for ref in elements(spine, 'itemref'):
        if ref.get('linear') == 'no':
            ref.attrib.pop('linear', None)
            changed = True
    if changed:
        for name, root in docs.items():
            data[name] = E.tostring(root, encoding='utf-8', xml_declaration=True)
        data[package_path] = E.tostring(opf, encoding='utf-8', xml_declaration=True)
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('mimetype', data['mimetype'], compress_type=zipfile.ZIP_STORED)
        for name, content in data.items():
            if name != 'mimetype':
                archive.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)
    return changed


def rtf_ast_bookmarks(path):
    """Add native RTF bookmark ranges to a trusted Pandoc-generated AST."""
    path = Path(path)
    if path.stat().st_size > MAX_FILE:
        raise UnsafeBook('Pandoc AST exceeds limits')
    document = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict) or not isinstance(document.get('blocks'), list) or not document.get('pandoc-api-version'):
        raise UnsafeBook('Invalid Pandoc JSON document')
    attribute_indexes = {'Div': 0, 'Span': 0, 'Link': 0, 'Image': 0, 'Code': 0,
                         'CodeBlock': 0, 'Table': 0, 'Figure': 0, 'Header': 1}
    inline_types = {'Span', 'Link', 'Image', 'Code'}

    def attribute(node):
        if not isinstance(node, dict) or node.get('t') not in attribute_indexes:
            return None
        values = node.get('c')
        index = attribute_indexes[node['t']]
        if not isinstance(values, list) or len(values) <= index:
            raise UnsafeBook('Malformed Pandoc attribute node')
        attr = values[index]
        if not isinstance(attr, list) or len(attr) != 3 or not isinstance(attr[0], str):
            raise UnsafeBook('Malformed Pandoc attribute')
        return attr

    identities = {}
    media = path.parent / 'rtf-media'
    media_files = validate_assets(media)
    image_types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                   '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp', '.svg': 'image/svg+xml'}
    def collect(value):
        if isinstance(value, dict):
            attr = attribute(value)
            if attr and attr[0]:
                if attr[0] in identities:
                    raise UnsafeBook('Duplicate Pandoc anchor: ' + attr[0])
                identities[attr[0]] = 'book_anchor_' + str(len(identities) + 1)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(document['blocks'])

    def transform(value):
        if isinstance(value, list):
            return [transform(child) for child in value]
        if not isinstance(value, dict):
            return value
        if value.get('t') == 'Link':
            target = value['c'][2][0]
            if target.startswith('#'):
                identity = unquote(target[1:])
                if identity not in identities:
                    raise UnsafeBook('Unresolved RTF bookmark link: ' + target)
                value['c'][2][0] = '#' + identities[identity]
        if value.get('t') == 'Image':
            url = value['c'][2][0]
            if url.startswith('data:'):
                data_image(url)
            else:
                parsed = urlsplit(url)
                resource = (path.parent / unquote(parsed.path)).resolve()
                media_type = image_types.get(resource.suffix.lower())
                if parsed.scheme or parsed.netloc or resource not in media_files or not media_type:
                    raise UnsafeBook('Unresolved RTF image resource: ' + url)
                uri = 'data:' + media_type + ';base64,' + base64.b64encode(resource.read_bytes()).decode('ascii')
                data_image(uri)
                value['c'][2][0] = uri
        attr = attribute(value)
        identity = identities.get(attr[0]) if attr else None
        if identity:
            attr[0] = ''
        value = {key: transform(child) for key, child in value.items()}
        if not identity:
            return value
        raw = 'RawInline' if value['t'] in inline_types else 'RawBlock'
        start = {'t': raw, 'c': ['rtf', '{\\*\\bkmkstart ' + identity + '}']}
        end = {'t': raw, 'c': ['rtf', '{\\*\\bkmkend ' + identity + '}']}
        return {'t': 'Span' if raw == 'RawInline' else 'Div', 'c': [['', [], []], [start, value, end]]}
    document['blocks'] = transform(document['blocks'])
    path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8', newline='\n')


def odt_bookmarks(path):
    """Preserve Pandoc's named sections as native ODF bookmark ranges."""
    data = checked_zip(path)
    validate_container_resources(data, 'odt')
    root = xml(data['content.xml'])
    text = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
    existing = set(root.xpath('//*[local-name()="bookmark" or local-name()="bookmark-start"]/@*[local-name()="name"]'))
    changed = False
    for section in root.iter(text + 'section'):
        name = section.get(text + 'name')
        if not name or name in existing:
            continue
        paragraphs = [node for node in section.iter() if node.tag in (text + 'p', text + 'h')]
        if not paragraphs:
            paragraphs = [E.SubElement(section, text + 'p')]
        start = E.Element(text + 'bookmark-start', attrib={text + 'name': name})
        start.tail, paragraphs[0].text = paragraphs[0].text, None
        paragraphs[0].insert(0, start)
        E.SubElement(paragraphs[-1], text + 'bookmark-end', attrib={text + 'name': name})
        existing.add(name)
        changed = True
    if changed:
        data['content.xml'] = E.tostring(root, encoding='utf-8', xml_declaration=True)
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('mimetype', data['mimetype'], compress_type=zipfile.ZIP_STORED)
            for name, content in data.items():
                if name != 'mimetype':
                    archive.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)


def validate_file(path, kind):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0 or path.stat().st_size > MAX_FILE:
        raise UnsafeBook('Engine did not produce a nonempty bounded output: ' + str(path))
    if kind == 'epub':
        inspect_epub(path)
    elif kind in ('docx', 'odt'):
        data = checked_zip(path)
        validate_container_resources(data, kind)
        if kind == 'docx':
            if '[Content_Types].xml' not in data or 'word/document.xml' not in data:
                raise UnsafeBook('Invalid DOCX package')
            root = xml(data['word/document.xml'])
        else:
            if data.get('mimetype') != b'application/vnd.oasis.opendocument.text' or 'content.xml' not in data:
                raise UnsafeBook('Invalid ODT package')
            root = xml(data['content.xml'])
        if not elements(root, 'body'):
            raise UnsafeBook('Output document has no body')
    elif kind in ('mobi', 'azw3'):
        data = path.read_bytes()
        if len(data) < 86 or data[60:68] != b'BOOKMOBI':
            raise UnsafeBook('Invalid MOBI/AZW3 header')
        count = int.from_bytes(data[76:78], 'big')
        offset = int.from_bytes(data[78:82], 'big')
        if count < 1 or 78 + 8 * count > len(data) or offset < 78 + 8 * count or data[offset+16:offset+20] != b'MOBI':
            raise UnsafeBook('Invalid MOBI/AZW3 record structure')
    elif kind == 'fb2':
        root = xml(path.read_bytes())
        if local(root) != 'FictionBook':
            raise UnsafeBook('Invalid FB2 root')
        binaries = {}
        for node in elements(root, 'binary'):
            key = node.get('id')
            if not key or key in binaries:
                raise UnsafeBook('Missing or duplicate FB2 binary ID')
            binaries[key] = node

        def binary_resource(url):
            if urlsplit(url).scheme == 'data':
                data_image(url)
                return
            if not url.startswith('#') or unquote(url[1:]) not in binaries:
                raise UnsafeBook('External or missing FB2 binary resource: ' + url)
            binary = binaries[unquote(url[1:])]
            content = re.sub(r'\s+', '', ''.join(binary.itertext()))
            data_image('data:' + binary.get('content-type', '') + ';base64,' + content)
        check_markup(root, binary_resource)
        for node in elements(root, 'stylesheet'):
            if node.get('type', 'text/css').lower() != 'text/css':
                raise UnsafeBook('Unsupported FB2 stylesheet type')
            check_css(''.join(node.itertext()), binary_resource)
    elif kind == 'rtf':
        content = path.read_bytes().strip()
        if not content.startswith(b'{\\rtf'):
            raise UnsafeBook('Invalid RTF header')
        depth, index = 0, 0
        while index < len(content):
            token = content[index]
            if token == 92:
                if content[index+1:index+2] in (b'{', b'}', b'\\'):
                    index += 2
                    continue
                binary = re.match(rb'\\bin([0-9]+) ?', content[index:])
                if binary:
                    index += len(binary[0]) + int(binary[1])
                    if index > len(content):
                        raise UnsafeBook('Truncated RTF binary data')
                    continue
            elif token == 123:
                depth += 1
            elif token == 125:
                depth -= 1
                if depth < 0:
                    raise UnsafeBook('Unbalanced RTF groups')
            index += 1
        if depth != 0:
            raise UnsafeBook('Unclosed RTF groups')
    elif kind in ('html', 'markdown', 'txt'):
        content = path.read_text(encoding='utf-8-sig', errors='strict')
        if not content.strip():
            raise UnsafeBook('Empty text output')
        if kind == 'html':
            if not re.search(r'<html(?:\s|>)', content, re.I) or not re.search(r'<body(?:\s|>)', content, re.I):
                raise UnsafeBook('HTML output is not a standalone document')
            root = markup_root(content)
            def embedded(url):
                if not url.startswith('#'):
                    data_image(url)
            check_markup(root, embedded)
            ids = set(root.xpath('//@id'))
            for url in root.xpath('//a/@href'):
                if url.startswith('#') and unquote(url[1:]) not in ids:
                    raise UnsafeBook('Unresolved HTML output anchor: ' + url)
            if not root.xpath('//body'):
                raise UnsafeBook('HTML output has no body')


def validate_assets(root):
    root = Path(root)
    if not root.exists():
        return []
    if not root.is_dir() or root.is_symlink():
        raise UnsafeBook('Unsafe extracted media directory')
    files = []
    total = 0
    for path in root.rglob('*'):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise UnsafeBook('Unsafe extracted media path')
        if path.is_file():
            total += path.stat().st_size
            if len(files) >= 10000 or total > MAX_EXPANDED or path.stat().st_size > 32 * 1024**2:
                raise UnsafeBook('Extracted media exceeds limits')
            files.append(path)
    return files

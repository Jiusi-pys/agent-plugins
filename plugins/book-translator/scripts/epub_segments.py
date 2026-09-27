"""Loss-accounted EPUB text inventory and safe reconstruction primitives."""
from pathlib import Path
import posixpath
import re
import zipfile
from urllib.parse import unquote, urlsplit
from lxml import etree as E

from common import digest

X = 'http://www.w3.org/1999/xhtml'
O = 'http://www.idpf.org/2007/opf'
DC = 'http://purl.org/dc/elements/1.1/'
EP = 'http://www.idpf.org/2007/ops'
TYPE = '{' + EP + '}type'
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
BLOCKS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'dt', 'dd', 'td', 'th', 'caption', 'figcaption', 'blockquote', 'address'}
PROTECTED = {'script', 'style', 'pre', 'code', 'math', 'svg'}
TRANSLATABLE_ATTRS = {'alt', 'title', 'aria-label'}


def local(node):
    return E.QName(node).localname if isinstance(node.tag, str) else ''


def parse_xml(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    root = E.fromstring(data, E.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, remove_blank_text=False))
    if any(isinstance(n, E._Entity) for n in root.iter()):
        raise ValueError('Unsupported XML entities')
    return root


def nodes(root, name):
    return [n for n in root.iter() if local(n) == name]


def resolve(base, href):
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or parts.query:
        return None
    path = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(parts.path))) if parts.path else base
    if path.startswith(('../', '/')) or '\\' in path or ':' in path:
        raise ValueError('Unsafe resource path: ' + href)
    return path, unquote(parts.fragment)


def read_epub(source):
    source = Path(source)
    if source.stat().st_size > 128 * 1024**2:
        raise ValueError('EPUB exceeds 128 MiB')
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        names = [i.filename for i in entries]
        if len(entries) > 10000 or len(names) != len(set(names)) or sum(i.file_size for i in entries) > 256 * 1024**2:
            raise ValueError('Duplicate or oversized ZIP archive')
        for item in entries:
            if (item.file_size > 32 * 1024**2 or item.flag_bits & 1 or item.filename.startswith('/')
                    or any(p in ('..', '.') for p in item.filename.split('/'))
                    or '\\' in item.filename or ':' in item.filename or ((item.external_attr >> 16) & 0o170000) == 0o120000):
                raise ValueError('Unsafe ZIP entry: ' + item.filename)
        data = {i.filename: archive.read(i) for i in entries if not i.is_dir()}
    if data.get('mimetype') != b'application/epub+zip':
        raise ValueError('Not an EPUB archive')
    if {'META-INF/encryption.xml', 'META-INF/signatures.xml'} & data.keys():
        raise ValueError('Encrypted/signed EPUB unsupported')
    roots = nodes(parse_xml(data['META-INF/container.xml']), 'rootfile')
    if len(roots) != 1:
        raise ValueError('Multiple/missing EPUB renditions')
    opath = roots[0].get('full-path')
    if opath not in data:
        raise ValueError('Missing package document')
    opf = parse_xml(data[opath])
    if any(n.get('property') == 'rendition:layout' and n.text == 'pre-paginated' for n in nodes(opf, 'meta')):
        raise ValueError('Fixed-layout EPUB needs an explicit content/OCR workflow')
    return data, opath, opf


def shape(node):
    """Ignore translated text, but require the original element/attribute skeleton."""
    if not isinstance(node.tag, str):
        return ('comment', node.text)
    attrs = tuple(sorted((k, v) for k, v in node.attrib.items() if k not in TRANSLATABLE_ATTRS))
    if local(node) in PROTECTED:
        return ('protected', E.tostring(node, method='c14n', with_comments=True).decode())
    # Existing attributes may be translated but cannot silently disappear.
    translated_attrs = tuple(sorted(k for k in node.attrib if k in TRANSLATABLE_ATTRS))
    return node.tag, attrs, translated_attrs, tuple(shape(child) for child in node)


def split_text(text, maximum):
    remaining = text
    while len(remaining) > maximum:
        candidates = [m.end() for m in re.finditer(r'[.!?。！？;；]\s+|\s+', remaining[:maximum])]
        end = candidates[-1] if candidates else maximum
        yield remaining[:end]
        remaining = remaining[end:]
    if remaining:
        yield remaining


def locator(node):
    indices = []
    while node.getparent() is not None:
        parent = node.getparent()
        indices.append(parent.index(node))
        node = parent
    return list(reversed(indices))


def locate(root, indices):
    for index in indices:
        root = root[index]
    return root


def note_container(node, kind):
    """Put chunk notes at the end of their prose block, never in head/attributes."""
    if kind == 'tail':
        node = node.getparent()
    if node is None or kind not in ('xml', 'text', 'tail'):
        raise ValueError('Notes require body prose')
    lineage = [node, *node.iterancestors()]
    if (not any(n.tag == '{' + X + '}body' for n in lineage)
            or any(local(n) in PROTECTED | {'nav'} for n in lineage)):
        raise ValueError('Notes require body prose outside protected/navigation content')
    return next(n for n in lineage if local(n) in BLOCKS | {'body'})


def inventory(source, max_chars=6000):
    if not 256 <= max_chars <= 24000:
        raise ValueError('max_chars must be between 256 and 24000')
    data, opath, opf = read_epub(source)
    items = nodes(opf, 'item')
    by_id, item_paths, docs = {}, {}, {}
    for item in items:
        ident = item.get('id')
        if not ident or ident in by_id:
            raise ValueError('Duplicate/missing manifest id')
        by_id[ident] = item
        target = resolve(opath, item.get('href', ''))
        if not target or target[0] not in data:
            raise ValueError('Missing/nonlocal manifest resource')
        path = target[0]
        if path in item_paths:
            raise ValueError('Duplicate manifest resource')
        item_paths[path] = item
        mime = item.get('media-type', '')
        if mime in ('application/xhtml+xml', 'application/x-dtbncx+xml'):
            docs[path] = parse_xml(data[path])
        elif mime in ('text/html', 'text/plain', 'application/pdf', 'image/svg+xml'):
            raise ValueError('Unsupported potentially textual resource: ' + path)
    order = []
    for ref in nodes(opf, 'itemref'):
        item = by_id.get(ref.get('idref'))
        if item is None:
            raise ValueError('Broken spine reference')
        path = resolve(opath, item.get('href'))[0]
        if item.get('media-type') != 'application/xhtml+xml':
            raise ValueError('Unsupported spine content: ' + path)
        if path in order:
            raise ValueError('Repeated spine resource requires explicit handling')
        if 'nav' not in item.get('properties', '').split() and ref.get('linear') != 'no':
            order.append(path)
    if not order:
        raise ValueError('No readable spine')
    prose_found = False
    excluded = PROTECTED | {'nav', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    for path in order:
        for body in nodes(docs[path], 'body'):
            for node in body.iter():
                if (node.text and node.text.strip() and not any(local(a) in excluded for a in [node, *node.iterancestors()])):
                    prose_found = True
                if (node.tail and node.tail.strip() and not any(local(a) in excluded for a in node.iterancestors())):
                    prose_found = True
    if not prose_found:
        raise ValueError('No readable body prose; image-only books require OCR')
    for path, root in docs.items():
        ids = [n.get('id') for n in root.iter() if n.get('id')]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate XML IDs: ' + path)
        if any(local(n) == 'svg' and any(local(t) == 'text' and ''.join(t.itertext()).strip() for t in n.iter()) for n in root.iter()):
            raise ValueError('SVG text needs explicit translation handling: ' + path)
    # Use top-level TOC boundaries; a chapter may continue across spine files.
    boundaries = {}
    has_nav = any('nav' in item.get('properties', '').split() for item in items)
    for path, item in item_paths.items():
        root = docs.get(path)
        if root is None:
            continue
        links = []
        if 'nav' in item.get('properties', '').split():
            for nav in nodes(root, 'nav'):
                if 'toc' not in nav.get(TYPE, '').split():
                    continue
                links += [(a.get('href', ''), ''.join(a.itertext())) for a in nav.xpath('./*[local-name()="ol"]/*[local-name()="li"]/*[local-name()="a"]')]
        elif item.get('media-type') == 'application/x-dtbncx+xml' and not has_nav:
            for navmap in nodes(root, 'navMap'):
                for point in navmap:
                    contents, labels = nodes(point, 'content'), nodes(point, 'navLabel')
                    if contents and labels:
                        links.append((contents[0].get('src', ''), ''.join(labels[0].itertext())))
        for href, label in links:
            target = resolve(path, href)
            if not target or target[0] not in order:
                raise ValueError('TOC target is not readable spine: ' + href)
            dest = docs[target[0]]
            matches = dest.xpath('//*[@id=$id]', id=target[1]) if target[1] else [next(iter(nodes(dest, 'body')), dest)]
            if len(matches) != 1:
                raise ValueError('Ambiguous/broken TOC boundary: ' + href)
            key = (target[0], tuple(locator(matches[0])))
            if key in boundaries and boundaries[key] != label:
                raise ValueError('Conflicting TOC chapter boundary')
            boundaries[key] = label.strip()
    if not boundaries:
        for path in order:
            headings = nodes(docs[path], 'h1') or nodes(docs[path], 'h2')
            for heading in headings:
                boundaries[path, tuple(locator(heading))] = ''.join(heading.itertext()).strip()
    chapters, segments, protections = [], [], []
    current = None
    def new_chapter(title, kind):
        chapter = {'id': f'c{len(chapters)+1:04d}', 'title': title, 'kind': kind}
        chapters.append(chapter)
        return chapter['id']
    for path in order + [p for p in docs if p not in order]:
        root = docs[path]
        if path not in order:
            current = new_chapter(path, 'auxiliary')
        path_boundaries = {loc: label for (p, loc), label in boundaries.items() if p == path}
        first_boundary = True
        if current is None:
            current = new_chapter(next(iter(path_boundaries.values()), path), 'chapter')
        elif path in order and path_boundaries:
            # A document beginning a new chapter owns its own head/title.
            # If real body content precedes the boundary it is a continuation.
            before_body_content = False
            for node in root.iter():
                if tuple(locator(node)) in path_boundaries:
                    if not before_body_content:
                        current = new_chapter(path_boundaries[tuple(locator(node))], 'chapter')
                    break
                in_body = local(node) == 'body' or any(local(a) == 'body' for a in node.iterancestors())
                if in_body and node.text and node.text.strip() and local(node) not in PROTECTED:
                    before_body_content = True
        def emit(node, kind, value, attribute=None):
            if not value or not value.strip():
                return
            chunks = list(split_text(value, max_chars)) if kind != 'xml' else [value]
            for part, chunk in enumerate(chunks):
                segments.append({'id': f's{len(segments)+1:06d}', 'chapter': current, 'file': path,
                                 'locator': locator(node), 'kind': kind, 'attribute': attribute,
                                 'part': part, 'parts': len(chunks), 'source': chunk})
        def walk(node):
            nonlocal current, first_boundary
            if not isinstance(node.tag, str):
                return
            loc = tuple(locator(node))
            if loc in path_boundaries:
                # The initial document title belongs to its first chapter.
                if not (first_boundary and not any(s['chapter'] == current and s['kind'] == 'xml' for s in segments)):
                    current = new_chapter(path_boundaries[loc], 'chapter')
                else:
                    next(c for c in chapters if c['id'] == current)['title'] = path_boundaries[loc]
                first_boundary = False
            name = local(node)
            if name in PROTECTED:
                protections.append({'file': path, 'locator': locator(node), 'kind': name, 'digest': digest(E.tostring(node, with_tail=False))})
                return
            fragment = E.tostring(node, encoding='unicode', with_tail=False)
            descendant_boundary = any(tuple(locator(n)) in path_boundaries for n in node.iterdescendants() if isinstance(n.tag, str))
            # Navigation remains scalar so nested entries never consume chapter bodies.
            in_nav = any(local(a) == 'nav' for a in node.iterancestors())
            if name in BLOCKS and len(fragment) <= max_chars and not descendant_boundary and not in_nav:
                if ''.join(node.itertext()).strip() or any(n.get('alt') for n in node.iter()):
                    emit(node, 'xml', fragment)
                    return
            for attr in sorted(TRANSLATABLE_ATTRS):
                emit(node, 'attribute', node.get(attr), attr)
            emit(node, 'text', node.text)
            for child in node:
                walk(child)
                emit(child, 'tail', child.tail)
        walk(root)
    chapters = [c for c in chapters if any(s['chapter'] == c['id'] for s in segments)]
    if not segments:
        raise ValueError('No translatable text; image-only books require OCR')
    original = {}
    for node in opf.iter():
        if isinstance(node.tag, str) and node.tag.startswith('{' + DC + '}'):
            key, value = local(node), ''.join(node.itertext())
            if key in original:
                if not isinstance(original[key], list):
                    original[key] = [original[key]]
                original[key].append(value)
            else:
                original[key] = value
    return {'schema': 1, 'package': opath, 'chapters': chapters, 'segments': segments,
            'original_metadata': original, 'resources': {p: digest(v) for p, v in data.items()},
            'text_resources': list(docs), 'protected': protections, 'max_chars': max_chars}


def validate_target(segment, record):
    target = record.get('target')
    if not isinstance(target, str) or not target.strip():
        raise ValueError('Empty translation: ' + segment['id'])
    if len(target) > max(24000, len(segment['source']) * 8):
        raise ValueError('Unbounded translation: ' + segment['id'])
    action = record.get('action')
    if action == 'preserve':
        if target != segment['source'] or not isinstance(record.get('reason'), str) or not record['reason'].strip():
            raise ValueError('Preservation needs exact source and an explicit reason')
    elif action != 'translate':
        raise ValueError('Expected translate/preserve action')
    if segment['kind'] == 'xml':
        source_node, target_node = parse_xml(segment['source']), parse_xml(target)
        if shape(source_node) != shape(target_node):
            raise ValueError('Protected structure changed: ' + segment['id'])
    notes = record.get('notes', [])
    if not isinstance(notes, list) or not all(isinstance(n, dict) for n in notes):
        raise ValueError('Notes must be a list of objects')
    for note in notes:
        if segment['kind'] not in ('xml', 'text', 'tail') or note.get('kind') not in ('explanation', 'example'):
            raise ValueError('Notes require body prose and an explicit kind')
        for field in ('text', 'rationale', 'source_quote'):
            if not isinstance(note.get(field), str) or not note[field].strip():
                raise ValueError('Incomplete translator note: ' + field)
        source_text = ''.join(parse_xml(segment['source']).itertext()) if segment['kind'] == 'xml' else segment['source']
        if note['source_quote'] not in source_text:
            raise ValueError('Note has no matching source evidence')
        if len(note['text']) > 4000:
            raise ValueError('Translator note exceeds 4000 characters')
        if not isinstance(note.get('sources', []), list):
            raise ValueError('Note sources must be a list')


def write_epub(path, data):
    with Path(path).open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('mimetype', data['mimetype'], compress_type=zipfile.ZIP_STORED)
            for name, content in data.items():
                if name != 'mimetype':
                    archive.writestr(name, content)

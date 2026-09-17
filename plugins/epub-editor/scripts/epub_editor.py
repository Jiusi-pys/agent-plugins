"""Conservative EPUB editing. Never execute book scripts or overwrite input/output."""
import argparse
import io
import json
import posixpath as P
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from lxml import etree as E
from PIL import Image
from epub_metadata import PackageMetadata, validate_patch, count_text, CUSTOM

X = 'http://www.w3.org/1999/xhtml'
EP = 'http://www.idpf.org/2007/ops'
O = 'http://www.idpf.org/2007/opf'
TYPE = '{' + EP + '}type'

def xml(data):
    parser = E.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    root = E.fromstring(data, parser)
    if any(isinstance(n, E._Entity) for n in root.iter()):
        raise ValueError('Unsupported XML entities; expand these explicitly before editing')
    return root

def local(node):
    return E.QName(node).localname if isinstance(node.tag, str) else ''

def elements(root, name):
    return [n for n in root.iter() if local(n) == name]

def text(node):
    return ' '.join(''.join(node.itertext()).split())

def resolve(base, href):
    u = urlsplit(href)
    if u.scheme or u.netloc or u.query:
        return None
    path = P.normpath(P.join(P.dirname(base), unquote(u.path))) if u.path else base
    if path.startswith('../') or path.startswith('/') or '\\' in path:
        return None
    return path, unquote(u.fragment)

def relative(base, target, fragment=''):
    return quote(P.relpath(target, P.dirname(base)), safe='/') + ('#' + quote(fragment, safe='') if fragment else '')

def add(root, namespace, tag, **attrs):
    return E.SubElement(root, '{'+namespace+'}'+tag, attrs)

def read_package(source):
    source = Path(source).resolve()
    if source.stat().st_size > 128 * 1024**2:
        raise ValueError('EPUB exceeds 128 MiB')
    with zipfile.ZipFile(source) as z:
        entries = z.infolist()
        names = [i.filename for i in entries]
        if len(entries) > 10000 or len(names) != len(set(names)):
            raise ValueError('Too many or duplicate ZIP entries')
        if sum(i.file_size for i in entries) > 256 * 1024**2:
            raise ValueError('Expanded archive exceeds 256 MiB')
        for i in entries:
            if i.file_size > 32 * 1024**2 or i.filename.startswith('/') or '\\' in i.filename or '..' in i.filename.split('/') or ':' in i.filename:
                raise ValueError('Unsafe ZIP entry: '+i.filename)
        data = {i.filename: z.read(i) for i in entries if not i.is_dir()}
    if data.get('mimetype') != b'application/epub+zip':
        raise ValueError('Not an EPUB archive')
    if 'META-INF/encryption.xml' in data or 'META-INF/signatures.xml' in data:
        raise ValueError('Encrypted or signed EPUB requires separate handling')
    container = xml(data['META-INF/container.xml'])
    roots = elements(container, 'rootfile')
    if len(roots) != 1:
        raise ValueError('Expected one EPUB rendition')
    opath = roots[0].get('full-path')
    opf = xml(data[opath])
    return data, opath, opf


def inspect_metadata(source):
    _, _, opf = read_package(source)
    return {'metadata': PackageMetadata(opf).snapshot(), 'epub_version': opf.get('version')}


def edit(source, output, cover=None, metadata_patch=None, recount=False, metadata_only=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError('Input and output must differ')
    if output.exists():
        raise FileExistsError(output)
    patch = validate_patch(metadata_patch if metadata_patch is not None else {})
    if recount and 'word_count' in patch:
        raise ValueError('Choose manual word_count or --recount, not both')
    if metadata_only and cover is not None:
        raise ValueError('--metadata-only cannot be combined with --cover')
    data, opath, opf = read_package(source)
    if metadata_only and not opf.get('version', '').startswith('3'):
        raise ValueError('--metadata-only requires EPUB 3; use normal editing to upgrade EPUB 2 navigation first')
    metadata_before = PackageMetadata(opf).snapshot()
    manifest, metadata, spine = [elements(opf, n)[0] for n in ('manifest', 'metadata', 'spine')]
    items = elements(manifest, 'item')
    docs = {}
    for item in items:
        target = resolve(opath, item.get('href', ''))
        if not target or target[0] not in data:
            raise ValueError('Missing/local manifest resource: '+str(item.get('href')))
        if item.get('media-type') in ('application/xhtml+xml', 'application/x-dtbncx+xml'):
            docs[target[0]] = xml(data[target[0]])
    report = {'toc_repaired': 0, 'notes': 0, 'cover_replaced': False, 'issues': []}
    by_id = {i.get('id'): i for i in items}
    body_paths = []
    count_paths = []
    for ref in elements(spine, 'itemref'):
        item = by_id.get(ref.get('idref'))
        if item is None:
            raise ValueError('Broken spine reference')
        path = resolve(opath, item.get('href'))[0]
        if path in docs:
            body_paths.append(path)
            if ref.get('linear') != 'no' and 'nav' not in item.get('properties', '').split():
                count_paths.append(path)

    def target_node(base, href):
        target = resolve(base, href)
        if not target or target[0] not in docs: return None
        if not target[1]: return docs[target[0]]
        matches = docs[target[0]].xpath('//*[@id=$id]', id=target[1])
        return matches[0] if len(matches) == 1 else None

    def fresh_id(root, prefix):
        ids = {n.get('id') for n in root.iter()}
        candidate, index = prefix, 1
        while candidate in ids:
            candidate = prefix+'-'+str(index)
            index += 1
        return candidate

    def repair(base, link, attribute, label):
        href = link.get(attribute, '')
        if target_node(base, href) is not None: return
        target = resolve(base, href)
        scope = [target[0]] if target and target[0] in body_paths else body_paths
        candidates = [(p, n) for p in scope for n in docs[p].iter()
                      if local(n) in ('h1','h2','h3','h4','h5','h6') and text(n) == label]
        if len(candidates) != 1:
            report['issues'].append({'kind': 'toc', 'file': base, 'href': href, 'reason': 'No unique heading match'})
            return
        p, n = candidates[0]
        if not n.get('id'): n.set('id', fresh_id(docs[p], 'epub-editor-heading'))
        link.set(attribute, relative(base, p, n.get('id')))
        report['toc_repaired'] += 1

    if not metadata_only:
        nav_item = next((i for i in items if 'nav' in i.get('properties', '').split()), None)
        ncx_item = next((i for i in items if i.get('media-type') == 'application/x-dtbncx+xml'), None)
        if ncx_item is not None:
            p = resolve(opath, ncx_item.get('href'))[0]
            for point in elements(docs[p], 'navPoint'):
                labels, contents = elements(point, 'navLabel'), elements(point, 'content')
                if labels and contents: repair(p, contents[0], 'src', text(labels[0]))
        if nav_item is None:
            nav_path = P.join(P.dirname(opath), 'epub-editor-nav.xhtml')
            if nav_path in data: raise ValueError('Generated navigation path already exists')
            nav = E.Element('{'+X+'}html', nsmap={None:X, 'epub':EP})
            add(add(nav, X, 'head'), X, 'title').text = '目录'
            nav_section = add(add(nav, X, 'body'), X, 'nav')
            nav_section.set(TYPE, 'toc')
            listing = add(nav_section, X, 'ol')
            if ncx_item is not None:
                np = resolve(opath, ncx_item.get('href'))[0]
                def copy_points(parent, dest):
                    for point in parent:
                        if local(point) != 'navPoint': continue
                        labels, contents = elements(point, 'navLabel'), elements(point, 'content')
                        if not labels or not contents: continue
                        li = add(dest, X, 'li')
                        target = resolve(np, contents[0].get('src', ''))
                        if target: add(li, X, 'a', href=relative(nav_path, *target)).text = text(labels[0])
                        if any(local(c) == 'navPoint' for c in point): copy_points(point, add(li, X, 'ol'))
                for navmap in elements(docs[np], 'navMap'): copy_points(navmap, listing)
            else:
                for p in body_paths:
                    headings = [n for n in docs[p].iter() if local(n) in ('h1','h2','h3')]
                    if not headings:
                        titles = elements(docs[p], 'title')
                        add(add(listing, X, 'li'), X, 'a', href=relative(nav_path, p)).text = text(titles[0]) if titles else P.basename(p)
                    for n in headings:
                        if not n.get('id'): n.set('id', fresh_id(docs[p], 'epub-editor-heading'))
                        add(add(listing, X, 'li'), X, 'a', href=relative(nav_path, p, n.get('id'))).text = text(n)
            docs[nav_path] = nav
            nav_item = add(manifest, O, 'item', id=fresh_id(opf, 'epub-editor-nav'), href=relative(opath, nav_path), **{'media-type':'application/xhtml+xml', 'properties':'nav'})
        nav_path = resolve(opath, nav_item.get('href'))[0]
        for section in elements(docs[nav_path], 'nav'):
            if 'toc' in section.get(TYPE, '').split():
                for a in elements(section, 'a'): repair(nav_path, a, 'href', text(a))

        for p, root in list(docs.items()):
            for a in elements(root, 'a'):
                dest = target_node(p, a.get('href', ''))
                is_ref = ('noteref' in a.get(TYPE, '').split() or a.get('role') == 'doc-noteref'
                          or bool(set(a.get('class', '').split()) & {'noteref','footnote-ref','endnote-ref'})
                          or 'footnote' in a.get('rel', '').split())
                is_note = dest is not None and (set(dest.get(TYPE, '').split()) & {'footnote','endnote'} or dest.get('role') in ('doc-footnote','doc-endnote'))
                if not is_ref and not is_note: continue
                if dest is None or not resolve(p, a.get('href', ''))[1]:
                    report['issues'].append({'kind':'note', 'file':p, 'href':a.get('href'), 'reason':'Missing or ambiguous note target'})
                    continue
                a.set(TYPE, ' '.join(dict.fromkeys(a.get(TYPE, '').split()+['noteref'])))
                a.set('role', 'doc-noteref')
                if not set(dest.get(TYPE, '').split()) & {'footnote','endnote'}:
                    dest.set(TYPE, ' '.join(dest.get(TYPE, '').split()+['footnote']))
                report['notes'] += 1

        if cover is not None:
            try:
                with Image.open(cover) as im:
                    if im.format not in ('JPEG','PNG') or im.width * im.height > 40_000_000:
                        raise ValueError('Provide a JPEG or PNG cover under 40 megapixels')
                    im.load()
                    buf = io.BytesIO()
                    im.convert('RGB').save(buf, format='JPEG', quality=95)
            except Exception as exc:
                raise ValueError('Invalid user-provided cover: '+str(exc)) from exc
            image_path = P.join(P.dirname(opath), 'epub-editor-cover.jpg')
            index = 1
            while image_path in data:
                image_path = P.join(P.dirname(opath), f'epub-editor-cover-{index}.jpg')
                index += 1
            data[image_path] = buf.getvalue()
            old_ids = {n.get('content') for n in elements(metadata, 'meta') if n.get('name') == 'cover'}
            old_paths = set()
            for item in elements(manifest, 'item'):
                props = item.get('properties', '').split()
                if 'cover-image' in props or item.get('id') in old_ids:
                    old_paths.add(resolve(opath, item.get('href'))[0])
                    props = [t for t in props if t != 'cover-image']
                    if props: item.set('properties', ' '.join(props))
                    else: item.attrib.pop('properties', None)
            replacements = 0
            for p, root in docs.items():
                for node in root.iter():
                    if local(node) not in ('img', 'image'): continue
                    for attr in ('src','href','{http://www.w3.org/1999/xlink}href'):
                        if node.get(attr) and resolve(p, node.get(attr)) and resolve(p, node.get(attr))[0] in old_paths:
                            node.set(attr, relative(p, image_path))
                            replacements += 1
            cover_id = fresh_id(opf, 'epub-editor-cover')
            add(manifest, O, 'item', id=cover_id, href=relative(opath, image_path), **{'media-type':'image/jpeg','properties':'cover-image'})
            for meta in list(elements(metadata, 'meta')):
                if meta.get('name') == 'cover': metadata.remove(meta)
            add(metadata, O, 'meta', name='cover', content=cover_id)
            if not replacements:
                page = P.join(P.dirname(opath), 'epub-editor-cover.xhtml')
                if page in data: raise ValueError('Generated cover page path already exists')
                root = E.Element('{'+X+'}html', nsmap={None:X})
                add(add(root, X, 'head'), X, 'title').text = '封面'
                add(add(root, X, 'body'), X, 'img', src=relative(page, image_path), alt='封面', style='max-width:100%;height:auto')
                docs[page] = root
                page_id = fresh_id(opf, 'epub-editor-cover-page')
                add(manifest, O, 'item', id=page_id, href=relative(opath, page), **{'media-type':'application/xhtml+xml'})
                ref = E.Element('{'+O+'}itemref', idref=page_id, linear='no')
                spine.insert(0, ref)
            report['cover_replaced'] = True

    package_metadata = PackageMetadata(opf)
    statistics = count_text(docs, count_paths, resolve) if recount else None
    if statistics is not None:
        patch['word_count'] = statistics['word_count']
        report['statistics'] = statistics
    package_metadata.apply(patch)
    if statistics is not None:
        package_metadata.extension(CUSTOM, 'word-count-method', statistics['method'])
    metadata_after = package_metadata.snapshot()
    primary_before = next((i['value'] for i in metadata_before['identifiers'] if i['primary']), None)
    primary_after = next((i['value'] for i in metadata_after['identifiers'] if i['primary']), None)
    for root in docs.values():
        if local(root) != 'ncx': continue
        if metadata_only and primary_before != primary_after:
            raise ValueError('Changing the primary identifier also requires updating NCX; omit --metadata-only')
        if not metadata_only:
            if primary_before != primary_after:
                for meta in elements(root, 'meta'):
                    if meta.get('name') == 'dtb:uid': meta.set('content', primary_after)
            if metadata_before['title'] != metadata_after['title']:
                for title in elements(root, 'docTitle'):
                    for node in elements(title, 'text'): node.text = metadata_after['title']
    report['metadata'] = {'before': metadata_before, 'after': metadata_after,
                          'changed': [key for key in metadata_after if metadata_before.get(key) != metadata_after[key]]}
    opf.set('version', '3.0')
    for meta in list(elements(metadata, 'meta')):
        if meta.get('property') == 'dcterms:modified': metadata.remove(meta)
    add(metadata, O, 'meta', property='dcterms:modified').text = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if metadata_only: docs = {}
    docs[opath] = opf
    for p, root in docs.items():
        data[p] = E.tostring(root, encoding='utf-8', xml_declaration=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr('mimetype', data.pop('mimetype'), compress_type=zipfile.ZIP_STORED)
                for p, value in data.items(): z.writestr(p, value)
    except Exception:
        if created: output.unlink(missing_ok=True)
        raise
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--cover', type=Path, help='User supplied JPEG/PNG; omitted means preserve cover')
    parser.add_argument('--metadata', type=Path, help='UTF-8 JSON metadata patch; omitted fields are preserved')
    parser.add_argument('--metadata-only', action='store_true', help='EPUB 3: preserve every resource except the OPF package')
    parser.add_argument('--recount', action='store_true', help='Recalculate CJK characters + other words in linear body text')
    parser.add_argument('--inspect', action='store_true', help='Read metadata without writing an EPUB')
    args = parser.parse_args()
    if args.inspect and (args.output or args.cover or args.metadata or args.recount or args.metadata_only):
        parser.error('--inspect cannot be combined with editing arguments')
    if not args.inspect and args.output is None:
        parser.error('output is required unless --inspect is used')
    try:
        if args.inspect:
            print(json.dumps(inspect_metadata(args.input), ensure_ascii=True, indent=2))
            return
        patch = None
        if args.metadata:
            if args.metadata.stat().st_size > 2 * 1024**2:
                raise ValueError('Metadata JSON exceeds 2 MiB')
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result: raise ValueError('Duplicate metadata JSON key: '+key)
                    result[key] = value
                return result
            patch = json.loads(args.metadata.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs)
        report = edit(args.input, args.output, args.cover, patch, args.recount, args.metadata_only)
    except (ValueError, OSError, KeyError, E.XMLSyntaxError, zipfile.BadZipFile) as exc:
        parser.exit(1, str(exc)+'\n')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if report['issues']: parser.exit(2)

if __name__ == '__main__': main()

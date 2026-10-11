"""Conservative EPUB presentation. Reader interaction stays the reader's responsibility."""
from lxml import etree as E

X = 'http://www.w3.org/1999/xhtml'
EP = 'http://www.idpf.org/2007/ops'
TYPE = '{' + EP + '}type'

STYLE = '''/* Scoped EPUB reading presentation; no script or hidden note content. */
sup.epub-editor-note-sup {font-size:0.75em !important;vertical-align:super !important;line-height:0 !important;}
a.epub-editor-note-marker {font-size:1em !important;vertical-align:baseline !important;line-height:inherit !important;}
.epub-editor-note-neutral {font-size:inherit !important;vertical-align:baseline !important;line-height:inherit !important;}
a.epub-editor-note-marker:focus-visible {outline:2px solid currentColor;outline-offset:2px;}
figure.epub-editor-figure {text-indent:0;}
figure.epub-editor-figure > figcaption.epub-editor-caption {font-size:0.85em !important;text-indent:0 !important;}
figcaption.epub-editor-caption > p {font-size:inherit !important;text-indent:0 !important;}
'''

CAPTION_CLASSES = {'caption', 'figcaption', 'image-caption', 'figure-caption', 'illustration-caption'}
CREDIT_CLASSES = {'source', 'credit', 'credits', 'image-source', 'figure-source', 'fig-source'}
PHRASING = {'a', 'abbr', 'audio', 'b', 'bdi', 'bdo', 'br', 'button', 'canvas',
            'cite', 'code', 'data', 'datalist', 'del', 'dfn', 'em', 'embed', 'i',
            'iframe', 'img', 'input', 'ins', 'kbd', 'label', 'map', 'mark', 'math',
            'meter', 'noscript', 'object', 'output', 'picture', 'progress', 'q',
            'ruby', 's', 'samp', 'script', 'select', 'slot', 'small', 'span',
            'strong', 'sub', 'sup', 'svg', 'template', 'textarea', 'time', 'u',
            'var', 'video', 'wbr'}


def local(node):
    return E.QName(node).localname if isinstance(node.tag, str) else ''


def tokens(node, attribute):
    return node.get(attribute, '').split()


def add_class(node, value):
    node.set('class', ' '.join(dict.fromkeys(tokens(node, 'class') + [value])))


def remove_tokens(node, attribute, values):
    remaining = [v for v in tokens(node, attribute) if v not in values]
    if remaining:
        node.set(attribute, ' '.join(remaining))
    else:
        node.attrib.pop(attribute, None)


def endnotes_collection(node):
    return 'endnotes' in tokens(node, TYPE) or node.get('role') == 'doc-endnotes'


def in_endnotes(node):
    return any(endnotes_collection(n) for n in node.iterancestors())


def report(mode, applied=False):
    return {'mode': mode, 'applied': applied, 'note_markers': 0, 'figures': 0,
            'captions': 0, 'credits': 0, 'warnings': [], 'popup_behavior': 'reader-dependent'}


def _warning(result, path, kind, reason, node=None):
    item = {'kind': kind, 'file': path, 'reason': reason}
    if node is not None and node.get('id'):
        item['id'] = node.get('id')
    result['warnings'].append(item)


def _strip_style(node, properties):
    """Remove only presentation properties being standardized, keeping other declarations."""
    properties = set(properties)
    if 'font-size' in properties:
        properties.add('font')
    declarations, removed_font = [], False
    for declaration in node.get('style', '').split(';'):
        key, separator, _ = declaration.partition(':')
        property_name = key.strip().lower()
        if separator and property_name == 'font' and property_name in properties:
            removed_font = True
        if declaration.strip() and (not separator or property_name not in properties):
            declarations.append(declaration.strip())
    if declarations:
        node.set('style', ';'.join(declarations))
    else:
        node.attrib.pop('style', None)
    return removed_font


def _shallow(node, keep_id=True):
    result = E.Element(node.tag, dict(node.attrib), nsmap=node.nsmap)
    if not keep_id:
        result.attrib.pop('id', None)
    return result


def _meaningful(node):
    return bool(node.get('id') or len(node) or (node.text and node.text.strip()))


def _split_around(node, anchor):
    """Partition a shared superscript without flattening its other inline content.

    Only the anchor's branch is copied for normalization. Before/after branches keep
    their original classes and inline styles; IDs stay unique on the first branch.
    """
    if node is anchor:
        return None, anchor, None
    before, middle, after = _shallow(node), _shallow(node, False), _shallow(node, False)
    before.text = node.text
    branch = next(c for c in node if c is anchor or anchor in c.iterdescendants())
    passed = False
    for child in list(node):
        if child is branch:
            tail, child.tail = child.tail, None
            left, center, right = _split_around(child, anchor)
            if left is not None:
                before.append(left)
            middle.append(center)
            if right is not None:
                after.append(right)
                right.tail = tail
            else:
                after.text = tail
            passed = True
        elif passed:
            after.append(child)
        else:
            before.append(child)
    if not _meaningful(before):
        if before.text:
            middle.text = before.text
        before = None
        if node.get('id'):
            middle.set('id', node.get('id'))
    if not _meaningful(after):
        if after.text:
            middle.tail = (middle.tail or '') + after.text
        after = None
    return before, middle, after


def _only_reference(node, anchor):
    if ''.join(node.itertext()).strip() != ''.join(anchor.itertext()).strip():
        return False
    return not any(local(n) == 'a' and n is not anchor for n in node.iter())


def _normalize_marker(anchor):
    removed_font = False
    # A shared superscript can contain unrelated text. Split only its reference
    # branch, rather than changing the font size or vertical position of that text.
    supers = [n for n in anchor.iterancestors() if local(n) == 'sup']
    shared = next((n for n in reversed(supers) if not _only_reference(n, anchor)), None)
    if shared is not None:
        parent, index, tail = shared.getparent(), shared.getparent().index(shared), shared.tail
        shared.tail = None
        before, center, after = _split_around(shared, anchor)
        parent.remove(shared)
        segments = [n for n in (before, center, after) if n is not None]
        for offset, segment in enumerate(segments):
            parent.insert(index + offset, segment)
        segments[-1].tail = (segments[-1].tail or '') + (tail or '')
    ancestors = [n for n in anchor.iterancestors() if local(n) == 'sup']
    if ancestors:
        sup = ancestors[-1]
    elif (len(anchor) == 1 and local(anchor[0]) == 'sup'
          and not (anchor.text or '').strip() and not (anchor[0].tail or '').strip()):
        # Reuse a > sup as sup > a. The whole reference then has one effective
        # font size, including any text outside its former inner inline spans.
        parent, index, tail = anchor.getparent(), anchor.getparent().index(anchor), anchor.tail
        sup = anchor[0]
        leading, trailing = anchor.text, sup.tail
        anchor.remove(sup)
        anchor.text = (leading or '') + (sup.text or '')
        sup.text = None
        for child in list(sup):
            sup.remove(child)
            anchor.append(child)
        if len(anchor):
            anchor[-1].tail = (anchor[-1].tail or '') + (trailing or '')
        else:
            anchor.text += trailing or ''
        anchor.tail, sup.tail = None, tail
        parent.remove(anchor)
        sup.append(anchor)
        parent.insert(index, sup)
    else:
        parent, index, tail = anchor.getparent(), anchor.getparent().index(anchor), anchor.tail
        anchor.tail = None
        parent.remove(anchor)
        sup = E.Element('{' + X + '}sup')
        sup.append(anchor)
        sup.tail = tail
        parent.insert(index, sup)
    # Dedicated inline branches also receive neutral presentation. Resetting
    # only the a/sup misses an existing scaled or raised span between them.
    for node in sup.iterdescendants():
        if not isinstance(node.tag, str):
            continue
        removed_font = _strip_style(node, {'font-size', 'vertical-align', 'line-height'}) or removed_font
        if local(node) == 'sup':
            node.tag = '{' + X + '}span'
            remove_tokens(node, 'class', {'epub-editor-note-sup'})
        if node is not anchor:
            add_class(node, 'epub-editor-note-neutral')
    removed_font = _strip_style(sup, {'font-size', 'vertical-align', 'line-height'}) or removed_font
    removed_font = _strip_style(anchor, {'font-size', 'vertical-align', 'line-height'}) or removed_font
    add_class(sup, 'epub-editor-note-sup')
    add_class(anchor, 'epub-editor-note-marker')
    return removed_font


def _normalize_notes(root, result, path):
    for node in list(root.iter()):
        if not isinstance(node.tag, str):
            continue
        if (node.get('role') in ('doc-footnote', 'doc-endnote')
                and not set(tokens(node, TYPE)) & {'footnote', 'endnote'}):
            # EPUB SSV footnote covers both endnotes and footnotes. Keep that
            # portable content semantic while removing inappropriate ARIA item
            # roles inside doc-endnotes collections; never invent endnote.
            node.set(TYPE, ' '.join(tokens(node, TYPE) + ['footnote']))
        if endnotes_collection(node):
            has_list = any(local(n) in ('ol', 'ul') for n in node.iterdescendants())
            if local(node) not in ('ol', 'ul') and has_list:
                node.set('role', 'doc-endnotes')
            elif node.get('role') == 'doc-endnotes':
                node.attrib.pop('role')
                _warning(result, path, 'endnotes', 'Collection role requires a container with a list', node)
        if in_endnotes(node):
            if node.get('role') in ('doc-footnote', 'doc-endnote'):
                node.attrib.pop('role')
        elif 'endnote' in tokens(node, TYPE) or node.get('role') == 'doc-endnote':
            if node.get('role') in ('doc-footnote', 'doc-endnote'):
                node.attrib.pop('role')
        elif 'footnote' in tokens(node, TYPE):
            node.set('role', 'doc-footnote')


def _caption(node):
    return local(node) == 'figcaption' or bool(set(tokens(node, 'class')) & CAPTION_CLASSES)


def _credit(node):
    return 'credit' in tokens(node, TYPE) or bool(set(tokens(node, 'class')) & CREDIT_CLASSES)


def _cover(node, path, cover_paths, cover_nodes):
    return (path in cover_paths
            or any('cover' in tokens(n, TYPE) for n in [node] + list(node.iterancestors()))
            or any(n in cover_nodes for n in list(node.iter()) + list(node.iterancestors())))


def _image_only(node, references):
    if local(node) not in ('p', 'div', 'img'):
        return False
    images = [n for n in node.iter() if local(n) == 'img']
    if len(images) != 1:
        return False
    # Image-associated note markers may have text. Ordinary prose and links do
    # not make an illustration standalone merely because it contains an image.
    for n in node.iter():
        if n.text and n.text.strip() and not any(n is a or a in n.iterancestors() for a in references):
            return False
        if n is not node and n.tail and n.tail.strip():
            return False
        if n is not node and isinstance(n.tag, str) and not _phrasing(n):
            return False
    return True


def _phrasing(node):
    # Transparent/unknown flow containers cannot safely be inserted into p.
    # Preserve them in place; embedded SVG and MathML are phrasing roots even
    # though their internal vocabulary is not the HTML phrasing vocabulary.
    if local(node) in ('svg', 'math'):
        return True
    return (local(node) in PHRASING
            and all(_phrasing(c) for c in node if isinstance(c.tag, str)))


def _paragraphs(caption):
    original = list(caption)
    leading = caption.text
    caption.text = None
    for node in original:
        caption.remove(node)
    current = None
    if leading is not None:
        if leading.strip():
            current = E.SubElement(caption, '{' + X + '}p')
            current.text = leading
        else:
            caption.text = leading
    for node in original:
        if not _phrasing(node):
            current = None
            caption.append(node)
            # Meaningful tail text must also be retained in a reader-compatible p.
            if node.tail and node.tail.strip():
                trailing, node.tail = node.tail, None
                current = E.SubElement(caption, '{' + X + '}p')
                current.text = trailing
        else:
            if current is None:
                current = E.SubElement(caption, '{' + X + '}p')
            current.append(node)


def _normalize_credit(paragraph):
    for span in [n for n in paragraph.iter() if local(n) == 'span' and _credit(n)]:
        span.set(TYPE, ' '.join(dict.fromkeys(tokens(span, TYPE) + ['credit'])))
    existing = [n for n in paragraph.iter() if local(n) == 'span' and 'credit' in tokens(n, TYPE)]
    if existing:
        remove_tokens(paragraph, TYPE, {'credit'})
        return len(existing)
    if not _credit(paragraph):
        return 0
    remove_tokens(paragraph, TYPE, {'credit'})
    span = E.Element('{' + X + '}span')
    span.set(TYPE, 'credit')
    span.text, paragraph.text = paragraph.text, None
    for child in list(paragraph):
        paragraph.remove(child)
        span.append(child)
    paragraph.append(span)
    return 1


def _normalize_figure(figure, result, path):
    captions = [n for n in figure if local(n) == 'figcaption']
    if not captions:
        _warning(result, path, 'caption', 'Illustration has no explicit caption; no text was invented', figure)
        return False
    if len(captions) != 1:
        _warning(result, path, 'caption', 'Multiple caption containers are ambiguous; original content order was retained', figure)
        return False
    caption = captions[0]
    if figure[-1] is not caption:
        outside_text = (figure.text or '').strip() or any(
            (node.tail or '').strip() or (node is not caption and ''.join(node.itertext()).strip())
            for node in figure)
        if outside_text:
            _warning(result, path, 'caption', 'Figure contains unassociated prose; original content order was retained', figure)
            return False
        figure.remove(caption)
        figure.append(caption)
    _paragraphs(caption)
    add_class(figure, 'epub-editor-figure')
    add_class(caption, 'epub-editor-caption')
    removed_font = _strip_style(caption, {'font-size', 'text-indent'})
    for paragraph in caption.iter():
        if local(paragraph) == 'p':
            removed_font = _strip_style(paragraph, {'font-size', 'text-indent'}) or removed_font
            result['credits'] += _normalize_credit(paragraph)
    if removed_font:
        _warning(result, path, 'font', 'Removed caption font shorthand to apply standard relative size; independent styles were retained', caption)
    result['figures'] += 1
    result['captions'] += 1
    return True


def _normalize_images(root, references, result, path, cover_paths, cover_nodes):
    styled = False
    for figure in [n for n in root.iter() if local(n) == 'figure']:
        if not _cover(figure, path, cover_paths, cover_nodes):
            styled = _normalize_figure(figure, result, path) or styled
    candidates = [n for n in root.iter() if _image_only(n, references)]
    # Prefer the existing image paragraph/container, rather than its nested img.
    candidates = [n for n in candidates if not any(p in candidates for p in n.iterancestors())]
    for image in candidates:
        if _cover(image, path, cover_paths, cover_nodes) or any(local(p) in ('figure', 'figcaption') for p in image.iterancestors()):
            continue
        if (image.tail or '').strip():
            _warning(result, path, 'caption', 'Prose separates the illustration and caption; original structure was retained', image)
            continue
        parent = image.getparent()
        if parent is None or local(parent) in ('p', 'a', 'span', 'sup'):
            continue
        index = parent.index(image)
        caption = parent[index + 1] if index + 1 < len(parent) else None
        if caption is None or local(caption) != 'p' or not _caption(caption):
            _warning(result, path, 'caption', 'No adjacent explicitly marked caption; illustration was left in place', image)
            continue
        source = parent[index + 2] if index + 2 < len(parent) else None
        source = source if source is not None and local(source) == 'p' and _credit(source) else None
        if source is not None and (caption.tail or '').strip():
            _warning(result, path, 'credit', 'Prose separates the caption and source; source paragraph was retained', source)
            source = None
        # Changing an image-only p/div into figure preserves its ID and avoids
        # invalid p > figure. A direct img requires a new flow container.
        if local(image) == 'img':
            figure = E.Element('{' + X + '}figure')
            parent.remove(image)
            parent.insert(index, figure)
            figure.append(image)
            between, image.tail = image.tail, None
        else:
            figure = image
            figure.tag = '{' + X + '}figure'
            between, figure.tail = figure.tail, None
        fc = E.SubElement(figure, '{' + X + '}figcaption')
        fc.text = between
        last = source if source is not None else caption
        figure.tail, last.tail = last.tail, None
        parent.remove(caption)
        fc.append(caption)
        if source is not None:
            parent.remove(source)
            fc.append(source)
        styled = _normalize_figure(figure, result, path) or styled
    return styled


def _install_style(root):
    heads = [n for n in root if local(n) == 'head']
    head = heads[0] if heads else E.Element('{' + X + '}head')
    if not heads:
        root.insert(0, head)
    styles = root.xpath('//*[local-name()="style" and @data-epub-editor="reading-layout"]')
    if styles:
        style = styles[0]
        for extra in styles[1:]:
            extra.getparent().remove(extra)
    else:
        style = E.SubElement(head, '{' + X + '}style', {'type': 'text/css', 'data-epub-editor': 'reading-layout'})
    style.text = STYLE


def apply(docs, references, cover_paths=(), cover_nodes=()):
    """Normalize parsed XHTML and validated references in place; never touch images."""
    result = report('standard', applied=True)
    by_path = {}
    for path, anchor in references:
        by_path.setdefault(path, []).append(anchor)
    for path, root in docs.items():
        if local(root) != 'html':
            continue
        _normalize_notes(root, result, path)
        anchors = by_path.get(path, [])
        for anchor in anchors:
            if _normalize_marker(anchor):
                _warning(result, path, 'font', 'Removed reference font shorthand to apply one relative superscript; independent styles were retained', anchor)
            result['note_markers'] += 1
        figures = _normalize_images(root, anchors, result, path, set(cover_paths), set(cover_nodes))
        if anchors or figures:
            _install_style(root)
    return result

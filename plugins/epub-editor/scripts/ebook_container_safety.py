"""Passive resource validation for already bounded, unpacked DOCX/ODT packages.

The validator uses package bytes only: it neither opens filesystem resources nor
fetches URLs. Run it before handing an input container to a conversion engine,
and before publishing a generated container.
"""
import posixpath
import re
from urllib.parse import unquote, urlsplit

from lxml import etree as E


REL_HYPERLINKS = {
    'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
    'http://purl.oclc.org/ooxml/officeDocument/relationships/hyperlink',
}
ODF_TEXT = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
ODF_DRAW = 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0'
ODF_MANIFEST = 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'
SVG = 'http://www.w3.org/2000/svg'
XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'


class UnsafeContainer(ValueError):
    """A container resource may escape its package or has no package target."""


def _xml(content, name):
    parser = E.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        root = E.fromstring(content, parser)
    except (E.XMLSyntaxError, ValueError, TypeError) as exc:
        raise UnsafeContainer('Invalid container XML: ' + name) from exc
    # Reject declarations as well as used entities, including UTF-16 documents.
    # No OOXML/ODF resource part needs a DTD or an entity declaration.
    if root.getroottree().docinfo.doctype or any(isinstance(node, E._Entity) for node in root.iter()):
        raise UnsafeContainer('XML entities/DTD are unsupported: ' + name)
    for node in root.iter():
        if isinstance(node.tag, str) and node.get(XML_BASE):
            raise UnsafeContainer('XML base redirects are unsupported: ' + name)
    return root


def _url(value, current):
    if (not isinstance(value, str) or value != value.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise UnsafeContainer('Invalid container resource URL in ' + current)
    if re.search(r'%(?![0-9a-fA-F]{2})', value):
        raise UnsafeContainer('Malformed encoded resource URL in ' + current)
    try:
        return urlsplit(value)
    except ValueError as exc:
        raise UnsafeContainer('Invalid container resource URL in ' + current) from exc


def _resource(value, current, data, *, allow_directory=False):
    url = _url(value, current)
    if url.scheme or url.netloc or url.query:
        raise UnsafeContainer('External container resource: ' + value + ' in ' + current)
    path = unquote(url.path)
    if unquote(path) != path:
        raise UnsafeContainer('Repeatedly encoded container resource: ' + value)
    if (path.startswith('/') or '\\' in path or ':' in path
            or any(ord(char) < 32 or ord(char) == 127 for char in path)):
        raise UnsafeContainer('Absolute or unsafe container resource: ' + value)
    if not path and not url.fragment:
        raise UnsafeContainer('Empty container resource in ' + current)
    target = posixpath.normpath(posixpath.join(posixpath.dirname(current), path)) if path else current
    if target == '..' or target.startswith('../') or target.startswith('/'):
        raise UnsafeContainer('Container resource escapes package: ' + value)
    if target in data:
        return target
    if allow_directory and any(name.startswith(target.rstrip('/') + '/') for name in data):
        return target
    raise UnsafeContainer('Missing package resource: ' + value + ' in ' + current)


def _hyperlink(value, current, data):
    url = _url(value, current)
    if url.scheme.lower() in ('http', 'https') and url.netloc:
        return
    if url.scheme.lower() == 'mailto' and url.path and not url.netloc:
        return
    # A file:// hyperlink can also be dereferenced by importers; normal external
    # web/mail links are the only external relationship targets we permit.
    _resource(value, current, data)


def _relationship_owner(name):
    parent, filename = posixpath.split(name)
    if name == '_rels/.rels':
        return ''
    if posixpath.basename(parent) != '_rels' or not filename.endswith('.rels'):
        raise UnsafeContainer('Invalid relationship part path: ' + name)
    return posixpath.join(posixpath.dirname(parent), filename[:-5])


def _docx_relationships(name, root, data):
    owner = _relationship_owner(name)
    seen = set()
    for node in root.iter():
        if not isinstance(node.tag, str) or E.QName(node).localname != 'Relationship':
            continue
        identity, relation, target = node.get('Id'), node.get('Type'), node.get('Target')
        if not identity or identity in seen or not relation or target is None:
            raise UnsafeContainer('Malformed or duplicate DOCX relationship in ' + name)
        seen.add(identity)
        mode = node.get('TargetMode', 'Internal')
        if mode not in ('Internal', 'External'):
            raise UnsafeContainer('Unknown DOCX relationship mode in ' + name)
        if relation in REL_HYPERLINKS:
            _hyperlink(target, owner, data)
        else:
            if mode == 'External':
                raise UnsafeContainer('External DOCX resource relationship: ' + target)
            _resource(target, owner, data)


def _markup_resources(name, root, data, *, kind):
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        tag = E.QName(node)
        is_hyperlink = (tag.namespace == ODF_TEXT and tag.localname == 'a'
                        or tag.namespace == ODF_DRAW and tag.localname in ('a', 'area-rectangle', 'area-circle', 'area-polygon')
                        or tag.namespace == SVG and tag.localname == 'a')
        directory = tag.namespace == ODF_DRAW and tag.localname == 'object'
        for attr, value in node.attrib.items():
            attr_name = E.QName(attr)
            if attr_name.localname in ('href', 'src'):
                if is_hyperlink:
                    _hyperlink(value, name, data)
                else:
                    _resource(value, name, data, allow_directory=directory)
            elif kind == 'odt' and attr_name.namespace == ODF_MANIFEST and attr_name.localname == 'full-path':
                if value == '/':
                    continue  # ODF manifest's one permitted package-root marker.
                # Manifest locations are always relative to the package root,
                # unlike resource references within embedded object documents.
                _resource(value, '', data, allow_directory=value.endswith('/'))


def validate_container_resources(data, kind):
    """Validate DOCX/ODT resource references in checked_zip's dict[str, bytes].

    Raises UnsafeContainer (a ValueError) for external resources, unsafe/missing
    package targets, malformed XML or XML entity declarations. HTTP(S)/mailto
    hyperlinks are retained; resource relationships are always package-local.
    """
    if kind not in ('docx', 'odt'):
        raise UnsafeContainer('Unsupported resource container: ' + str(kind))
    for name, content in data.items():
        lowered = name.lower()
        if not lowered.endswith(('.xml', '.rels', '.svg')):
            continue
        root = _xml(content, name)
        if kind == 'docx' and lowered.endswith('.rels'):
            _docx_relationships(name, root, data)
        elif kind == 'odt' or lowered.endswith('.svg'):
            _markup_resources(name, root, data, kind=kind)

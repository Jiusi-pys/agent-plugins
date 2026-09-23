"""EPUB package metadata patching and reproducible text statistics."""
import math
import re
import unicodedata
from datetime import date
from lxml import etree as E

DC = 'http://purl.org/dc/elements/1.1/'
OPF = 'http://www.idpf.org/2007/opf'
EPUB = 'http://www.idpf.org/2007/ops'
SCHEMA = 'https://schema.org/'
CUSTOM = 'urn:epub-editor:metadata:'
COUNT_METHOD = 'cjk-character-plus-other-word-v1; linear-spine; marked-nonbody-excluded'
ROLES = {'author':'aut', 'translator':'trl', 'editor':'edt', 'illustrator':'ill',
         'narrator':'nrt', 'compiler':'com', 'photographer':'pht', 'other':'ctb'}
SCALARS = {'publisher':'publisher', 'published_date':'date', 'description':'description',
           'rights':'rights', 'source':'source', 'coverage':'coverage',
           'book_type':'type', 'format':'format'}
EXTENSIONS = {'edition':(SCHEMA,'bookEdition'), 'page_count':(SCHEMA,'numberOfPages'),
              'word_count':(SCHEMA,'wordCount')}
FIELDS = set(SCALARS) | set(EXTENSIONS) | {'title','subtitle','authors','contributors',
          'languages','subjects','isbn','identifiers','series'}


def nodes(root, ns, name):
    return root.findall('{'+ns+'}'+name)


def clean(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 100000:
        raise ValueError(f'{field}: expected nonempty text (maximum 100000 characters)')
    if any(not (c in '\t\n\r' or '\x20' <= c <= '\ud7ff' or '\ue000' <= c <= '\ufffd' or '\U00010000' <= c <= '\U0010ffff') for c in value):
        raise ValueError(f'{field}: invalid XML character')
    return value.strip()


def isbn_value(value):
    value = clean(value, 'isbn').removeprefix('urn:isbn:')
    value = re.sub(r'[\s-]', '', value).upper()
    valid = False
    if re.fullmatch(r'\d{9}[\dX]', value):
        valid = sum((10-i) * (10 if c == 'X' else int(c)) for i,c in enumerate(value)) % 11 == 0
    elif re.fullmatch(r'97[89]\d{10}', value):
        valid = sum(int(c) * (1 if i % 2 == 0 else 3) for i,c in enumerate(value)) % 10 == 0
    if not valid: raise ValueError('isbn: invalid ISBN-10/ISBN-13 checksum or format')
    return value


def validate_patch(patch):
    if not isinstance(patch, dict): raise ValueError('Metadata must be a JSON object')
    unknown = set(patch)-FIELDS
    if unknown: raise ValueError('Unknown metadata fields: '+', '.join(sorted(unknown)))
    result = dict(patch)
    for field, value in patch.items():
        if field in SCALARS or field in ('title','subtitle','edition'):
            if value is None and field != 'title': continue
            result[field] = clean(value, field)
        elif field in ('authors','contributors','languages','subjects'):
            if not isinstance(value, list) or len(value) > 1000:
                raise ValueError(f'{field}: expected a list of at most 1000 items; use [] to clear')
            if field == 'languages' and not value: raise ValueError('languages cannot be empty')
            normalized = []
            for item in value:
                if field in ('languages','subjects'):
                    item = clean(item, field)
                    if field == 'languages' and not re.fullmatch(r'(?:[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*|[ixIX](?:-[A-Za-z0-9]{1,8})+)',item):
                        raise ValueError('languages: expected a BCP 47 language tag')
                else:
                    if field == 'authors' and isinstance(item,str): item = {'name':item}
                    if not isinstance(item,dict) or set(item)-{'name','sort_as','role'}:
                        raise ValueError(f'{field}: expected name, optional sort_as, and contributor role')
                    item = dict(item)
                    item['name'] = clean(item.get('name'),field)
                    role = item.get('role','author' if field == 'authors' else 'other')
                    if not isinstance(role,str): raise ValueError('Invalid contributor role')
                    role = ROLES.get(role,role)
                    if role not in ROLES.values() or (field == 'authors' and role != 'aut'):
                        raise ValueError('Unsupported contributor role: '+role)
                    item['role'] = role
                    if 'sort_as' in item: item['sort_as'] = clean(item['sort_as'],'sort_as')
                if item not in normalized: normalized.append(item)
            result[field] = normalized
        elif field in ('word_count','page_count'):
            if value is not None and (type(value) is not int or value < (1 if field == 'page_count' else 0)):
                raise ValueError(f'{field}: expected a {"positive" if field == "page_count" else "nonnegative"} integer or null')
        elif field == 'isbn':
            if value is not None: result[field] = isbn_value(value)
        elif field == 'series':
            if value is None: continue
            if not isinstance(value,dict) or set(value)-{'name','position'}:
                raise ValueError('series: expected name and optional position')
            value = dict(value)
            value['name'] = clean(value.get('name'),'series.name')
            if 'position' in value and (type(value['position']) not in (int,float) or (type(value['position']) is float and not math.isfinite(value['position'])) or value['position'] < 0):
                raise ValueError('series.position: expected finite nonnegative number')
            result[field] = value
        elif field == 'identifiers':
            if not isinstance(value,dict): raise ValueError('identifiers: expected a scheme-to-value object')
            normalized = {}
            for scheme, ident in value.items():
                scheme = clean(scheme,'identifier scheme').upper()
                if not re.fullmatch(r'[A-Z][A-Z0-9_-]{0,31}',scheme) or scheme in normalized:
                    raise ValueError('Invalid or duplicate identifier scheme')
                normalized[scheme] = (isbn_value(ident) if scheme == 'ISBN' else clean(ident,'identifier')) if ident is not None else None
            if 'ISBN' in normalized and 'isbn' in patch:
                raise ValueError('Use isbn or identifiers.ISBN, not both')
            result[field] = normalized
    if result.get('published_date') is not None:
        value = result['published_date']
        if not re.fullmatch(r'\d{4}(?:-\d{2}){0,2}',value):
            raise ValueError('published_date: use YYYY, YYYY-MM or YYYY-MM-DD')
        date.fromisoformat(value + ('-01-01' if len(value)==4 else '-01' if len(value)==7 else ''))
    return result


class PackageMetadata:
    def __init__(self, package):
        self.package = package
        self.root = package.find('{'+OPF+'}metadata')
        if self.root is None: raise ValueError('Missing OPF metadata')

    def fresh_id(self, base):
        ids = {n.get('id') for n in self.package.iter()}
        candidate, index = base, 1
        while candidate in ids:
            candidate, index = base+'-'+str(index), index+1
        return candidate

    def new(self, ns, name, value=None, **attrs):
        node = E.SubElement(self.root,'{'+ns+'}'+name,attrs)
        if value is not None: node.text = str(value)
        return node

    def refine(self, node, prop, value, **attrs):
        if not node.get('id'): node.set('id',self.fresh_id('epub-editor-'+E.QName(node).localname))
        for old in self.refinements(node,prop): self.remove(old)
        return self.new(OPF,'meta',value,refines='#'+node.get('id'),property=prop,**attrs)

    def refinements(self,node,prop=None):
        if not node.get('id'): return []
        candidates = nodes(self.root,OPF,'meta') + (nodes(self.root,OPF,'link') if prop is None else [])
        return [m for m in candidates if m.get('refines') == '#'+node.get('id') and (prop is None or m.get('property') == prop)]

    def refinement(self,node,prop):
        found = self.refinements(node,prop)
        return found[0].text if found else None

    def remove(self,node):
        # Remove the whole refinement chain, without touching unrelated vendor data.
        pending = [node]
        visited = set()
        while pending:
            current = pending.pop()
            if current in visited: continue
            visited.add(current)
            pending.extend(self.refinements(current))
        for current in visited:
            if current.getparent() is self.root: self.root.remove(current)

    def role(self,node):
        return self.refinement(node,'role') or node.get('{'+OPF+'}role') or ('aut' if E.QName(node).localname=='creator' else 'ctb')

    def prefixes(self):
        return dict(re.findall(r'([A-Za-z][\w.-]*):\s+(\S+)',self.package.get('prefix','')))

    def property_iri(self,value):
        prefix,sep,name = value.partition(':')
        if not sep: return value
        # schema is a reserved EPUB prefix; an explicit mapping takes precedence.
        base = self.prefixes().get(prefix,SCHEMA if prefix=='schema' else '')
        if base == 'http://schema.org/': base = SCHEMA
        return base+name if base else value

    def extended(self,iri):
        return [m for m in nodes(self.root,OPF,'meta') if not m.get('refines') and self.property_iri(m.get('property','')) == iri]

    def extension(self,base,name,value):
        matches = self.extended(base+name)
        prop = matches[0].get('property') if matches else None
        for m in matches: self.remove(m)
        if value is None: return
        if prop is None:
            prefixes = self.prefixes()
            prefix = next((p for p,b in prefixes.items() if b == base or (base==SCHEMA and b=='http://schema.org/')),None)
            if prefix is None:
                seed = 'schema' if base==SCHEMA else 'epubedit'
                prefix, index = seed, 1
                while prefix in prefixes:
                    prefix, index = seed+str(index), index+1
                original = self.package.get('prefix','').strip()
                self.package.set('prefix',(original+' '+prefix+': '+base).strip())
            prop = prefix+':'+name
        self.new(OPF,'meta',value,property=prop)

    def scheme(self,node):
        legacy = node.get('{'+OPF+'}scheme')
        if legacy: return legacy.upper()
        scheme = self.refinement(node,'identifier-type')
        if scheme in ('15','02'): return 'ISBN'
        if scheme: return scheme.upper()
        value = node.text or ''
        if value.lower().startswith('urn:isbn:'): return 'ISBN'
        if value.lower().startswith('urn:uuid:'): return 'UUID'
        if value.lower().startswith(('urn:doi:','https://doi.org/')): return 'DOI'
        try:
            isbn_value(value)
            return 'ISBN'
        except ValueError: return 'UNKNOWN'

    def identifier(self,scheme,value):
        matches = [n for n in nodes(self.root,DC,'identifier') if self.scheme(n)==scheme]
        primary = next((n for n in matches if n.get('id')==self.package.get('unique-identifier')),None)
        if primary is not None and value is None:
            raise ValueError('Cannot remove the package unique identifier')
        keep = primary if primary is not None else (matches[0] if matches else None)
        for old in matches:
            if old is not keep or value is None: self.remove(old)
        if value is None: return
        if keep is None: keep = self.new(DC,'identifier')
        old_value = keep.text or ''
        keep.text = ('urn:isbn:'+value) if scheme=='ISBN' and old_value.lower().startswith('urn:isbn:') else value
        keep.attrib.pop('{'+OPF+'}scheme',None)
        if scheme=='ISBN': self.refine(keep,'identifier-type','15' if len(value)==13 else '02',scheme='onix:codelist5')
        else: self.refine(keep,'identifier-type',scheme)

    def series_nodes(self):
        return [m for m in nodes(self.root,OPF,'meta') if m.get('property')=='belongs-to-collection' and self.refinement(m,'collection-type')=='series']

    def snapshot(self):
        titles = nodes(self.root,DC,'title')
        main = next((n for n in titles if self.refinement(n,'title-type')=='main'),None)
        if main is None: main = next((n for n in titles if self.refinement(n,'title-type')!='subtitle'),None)
        subtitles = [n.text for n in titles if self.refinement(n,'title-type')=='subtitle']
        result = {'title':main.text if main is not None else None,'subtitle':subtitles[0] if subtitles else None}
        for field,tag in SCALARS.items():
            found = nodes(self.root,DC,tag)
            result[field] = found[0].text if found else None
        for field,tag in (('languages','language'),('subjects','subject')):
            result[field] = [n.text for n in nodes(self.root,DC,tag)]
        result['authors'],result['contributors'] = [],[]
        for node in nodes(self.root,DC,'creator')+nodes(self.root,DC,'contributor'):
            person = {'name':node.text,'role':self.role(node)}
            sort_as = self.refinement(node,'file-as') or node.get('{'+OPF+'}file-as')
            if sort_as: person['sort_as'] = sort_as
            result['authors' if E.QName(node).localname=='creator' and self.role(node)=='aut' else 'contributors'].append(person)
        result['identifiers'] = [{'scheme':self.scheme(n),'value':n.text,'primary':n.get('id')==self.package.get('unique-identifier')} for n in nodes(self.root,DC,'identifier')]
        for field,(base,name) in EXTENSIONS.items():
            found = self.extended(base+name)
            value = found[0].text if found else None
            if value is not None and field.endswith('_count'):
                try: value = int(value)
                except (ValueError,TypeError): pass
            result[field] = value
        found = self.extended(CUSTOM+'word-count-method')
        result['word_count_method'] = found[0].text if found else None
        result['series'] = None
        found = self.series_nodes()
        if found:
            result['series'] = {'name':found[0].text}
            pos = self.refinement(found[0],'group-position')
            if pos:
                try: pos = float(pos)
                except ValueError: pass
                result['series']['position'] = pos
        return result

    def apply(self,patch):
        for field in ('title','subtitle'):
            if field not in patch: continue
            titles = nodes(self.root,DC,'title')
            matches = [n for n in titles if self.refinement(n,'title-type') == ('main' if field=='title' else 'subtitle')]
            if field=='title' and not matches:
                matches = [n for n in titles if self.refinement(n,'title-type')!='subtitle'][:1]
            value = patch[field]
            if value is None:
                for n in matches: self.remove(n)
                continue
            node = matches[0] if matches else self.new(DC,'title')
            node.text = value
            for n in matches[1:]: self.remove(n)
            self.refine(node,'title-type','main' if field=='title' else 'subtitle')
            if field=='title':
                # Reading systems use the first dc:title as the main title.
                first = nodes(self.root,DC,'title')[0]
                if first is not node:
                    index = self.root.index(first)
                    self.root.remove(node)
                    self.root.insert(index,node)
        for field,tag in SCALARS.items():
            if field not in patch: continue
            matches = nodes(self.root,DC,tag)
            value = patch[field]
            if value is None:
                for n in matches: self.remove(n)
            else:
                node = matches[0] if matches else self.new(DC,tag)
                node.text = value
                for n in matches[1:]: self.remove(n)
        for field,tag in (('languages','language'),('subjects','subject')):
            if field in patch:
                for n in nodes(self.root,DC,tag): self.remove(n)
                for value in patch[field]: self.new(DC,tag,value)
        for field,tag in (('authors','creator'),('contributors','contributor')):
            if field not in patch: continue
            # Preserve creators with explicitly non-author roles when editing authors.
            remove = [n for n in nodes(self.root,DC,tag) if field!='authors' or self.role(n)=='aut']
            if field=='contributors': remove += [n for n in nodes(self.root,DC,'creator') if self.role(n)!='aut']
            for n in remove: self.remove(n)
            for value in patch[field]:
                n = self.new(DC,tag,value['name'])
                self.refine(n,'role',value['role'],scheme='marc:relators')
                if value.get('sort_as'): self.refine(n,'file-as',value['sort_as'])
        for scheme,value in patch.get('identifiers',{}).items(): self.identifier(scheme,value)
        if 'isbn' in patch: self.identifier('ISBN',patch['isbn'])
        for field,(base,name) in EXTENSIONS.items():
            if field in patch: self.extension(base,name,patch[field])
        if 'word_count' in patch:
            self.extension(CUSTOM,'word-count-method','user-supplied' if patch['word_count'] is not None else None)
        if 'series' in patch:
            for n in self.series_nodes(): self.remove(n)
            # Clear legacy series values to avoid conflicting displays in Calibre.
            for n in list(nodes(self.root,OPF,'meta')):
                if n.get('name') in ('calibre:series','calibre:series_index'): self.remove(n)
            value = patch['series']
            if value is not None:
                n = self.new(OPF,'meta',value['name'],property='belongs-to-collection')
                self.refine(n,'collection-type','series')
                if 'position' in value: self.refine(n,'group-position',value['position'])


def count_text(docs, body_paths, resolve):
    """Count encoded text, not CSS layout: external stylesheets are not evaluated."""
    skipped = {'toc','cover','titlepage','copyright-page','frontmatter','backmatter',
               'footnote','endnote','rearnotes','bibliography','index'}
    def semantics(n): return set(n.get('{'+EPUB+'}type','').split())
    def name(n): return E.QName(n).localname if isinstance(n.tag,str) else ''
    targets = set()
    for path,root in docs.items():
        for n in root.iter():
            if name(n)=='a' and ('noteref' in semantics(n) or n.get('role')=='doc-noteref'
                    or set(n.get('class','').split()) & {'noteref','footnote-ref','endnote-ref'} or 'footnote' in n.get('rel','').split()):
                target = resolve(path,n.get('href',''))
                if target and target[1]: targets.add(target)
    counts = {'word_count':0,'cjk_characters':0,'other_words':0,'character_count':0,'method':COUNT_METHOD}
    blocks = {'p','div','section','article','li','td','th','br','h1','h2','h3','h4','h5','h6','blockquote','pre'}
    for path in dict.fromkeys(body_paths):
        root = docs.get(path)
        if root is None: continue
        bodies = [n for n in root.iter() if name(n)=='body']
        for body in bodies:
            pieces = []
            def walk(n):
                tag = name(n)
                if not tag or tag in ('script','style','nav','svg','math') or semantics(n)&skipped or 'noteref' in semantics(n) or n.get('role') in ('doc-noteref','doc-footnote','doc-endnote') or (path,n.get('id')) in targets or n.get('hidden') is not None or n.get('aria-hidden')=='true' or re.search(r'display\s*:\s*none|visibility\s*:\s*hidden',n.get('style',''),re.I):
                    return
                if tag=='a' and (set(n.get('class','').split()) & {'noteref','footnote-ref','endnote-ref'} or 'footnote' in n.get('rel','').split()): return
                if tag in blocks: pieces.append(' ')
                if n.text: pieces.append(n.text)
                for child in n:
                    walk(child)
                    if child.tail: pieces.append(child.tail)
                if tag in blocks: pieces.append(' ')
            walk(body)
            text = ''.join(pieces)
            counts['character_count'] += sum(not c.isspace() for c in text)
            in_word = False
            for i,c in enumerate(text):
                number = ord(c)
                cjk = 0x3400<=number<=0x4DBF or 0x4E00<=number<=0x9FFF or 0xF900<=number<=0xFAFF or 0x20000<=number<=0x2FA1F or 0x30000<=number<=0x323AF
                if cjk:
                    counts['cjk_characters'] += 1
                    in_word = False
                elif unicodedata.category(c)[0] in ('L','N'):
                    if not in_word: counts['other_words'] += 1
                    in_word = True
                elif unicodedata.category(c)[0]=='M' and in_word: pass
                elif c in "'-’" and in_word and i+1<len(text) and unicodedata.category(text[i+1])[0] in ('L','N'): pass
                else: in_word = False
    counts['word_count'] = counts['cjk_characters']+counts['other_words']
    return counts

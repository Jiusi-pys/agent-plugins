"""Classical-Chinese evidence bookkeeping; actual research is performed by host agents."""
from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from common import digest, file_digest, load_json, save_json, require_text, exact_coverage

MODE = 'classical_chinese'
SOURCE_KINDS = {'primary_text', 'ancient_commentary', 'modern_scholarship'}
READ_METHODS = {'web', 'http', 'browser', 'local_scan'}
NOTE_LABELS = {'allusion': '典故', 'lexical': '字词', 'institution': '制度',
               'textual': '校勘与异说', 'grammar': '语法', 'context': '背景'}


def profile_defaults():
    return {'mode': MODE, 'classical': {'base_edition': '', 'parallel_original': True}}


def validate_profile(profile):
    details = profile.get('classical', {})
    require_text(details.get('base_edition'), 'classical base edition and limitations')
    if details.get('parallel_original') is not True:
        raise ValueError('Classical precision mode retains original-text comparison')


def text_inventory(source, max_chars=6000):
    source = Path(source)
    if source.suffix.lower() not in ('.txt', '.md') or source.stat().st_size > 16 * 1024**2:
        raise ValueError('Use UTF-8 .txt/.md up to 16 MiB')
    if not 256 <= max_chars <= 24000:
        raise ValueError('max_chars must be between 256 and 24000')
    text = source.read_bytes().decode('utf-8-sig')
    if not text.strip() or '\x00' in text:
        raise ValueError('Empty or binary text input')
    chapters, segments = [], []
    for match in re.finditer(r'\S[\s\S]*?(?=\r?\n[ \t]*\r?\n|\r?\n(?=#{1,2}\s)|\Z)', text):
        value = match.group()
        heading = re.match(r'^#{1,2}\s+([^\r\n]+)', value)
        if not chapters or heading:
            chapters.append({'id': f'c{len(chapters)+1:04d}', 'title': heading.group(1) if heading else source.stem, 'kind': 'chapter'})
        parts = (len(value) + max_chars - 1) // max_chars
        for part in range(parts):
            start = match.start() + part * max_chars
            end = min(match.end(), start + max_chars)
            chunk = text[start:end]
            if not chunk.strip():
                continue
            segments.append({'id': f's{len(segments)+1:06d}', 'chapter': chapters[-1]['id'],
                             'kind': 'text', 'source': chunk, 'start': start, 'end': end,
                             'part': part, 'parts': parts, 'file': 'source.txt', 'locator': [], 'attribute': None})
    # Every non-whitespace character must have exactly one segment owner.
    normalize = lambda value: re.sub(r'\s+', '', value)
    if normalize(''.join(s['source'] for s in segments)) != normalize(text):
        raise ValueError('Text inventory is incomplete')
    return {'schema': 1, 'chapters': chapters, 'segments': segments, 'input_format': 'text',
            'original_metadata': {'title': source.stem}, 'resources': {}, 'text_resources': [], 'max_chars': max_chars}


def source_metadata(metadata):
    result = {}
    for key in ('id', 'work', 'attribution', 'edition', 'locator', 'accessed', 'read_evidence'):
        result[key] = require_text(metadata.get(key), 'source ' + key)
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', result['id']):
        raise ValueError('Unsafe source id')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', result['accessed']):
        raise ValueError('Source accessed date must be YYYY-MM-DD')
    result['kind'], result['access_method'] = metadata.get('kind'), metadata.get('access_method')
    if result['kind'] not in SOURCE_KINDS or result['access_method'] not in READ_METHODS:
        raise ValueError('Source requires an actual reading method and source kind')
    url = metadata.get('url')
    if url:
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Invalid source URL')
        result['url'] = url
    else:
        result['local_reference'] = require_text(metadata.get('local_reference'), 'local scan reference')
    return result


def read_sources(job):
    job = Path(job).resolve()
    path = job / 'sources.json'
    if not path.exists():
        return []
    records = load_json(path)
    if not isinstance(records, list):
        raise ValueError('Expected source list')
    seen = set()
    for record in records:
        valid = source_metadata(record)
        ident = valid['id']
        if ident in seen:
            raise ValueError('Duplicate source id')
        seen.add(ident)
        capture = (job / 'sources' / (ident + '.txt')).resolve(strict=True)
        if not capture.is_relative_to(job) or capture.stat().st_size > 16 * 1024**2:
            raise ValueError('Invalid source capture path or size')
        if file_digest(capture) != record.get('sha256'):
            raise ValueError('Changed source capture: ' + ident)
        if not capture.read_text(encoding='utf-8').strip():
            raise ValueError('Empty source capture')
    return records


def record_source(job, metadata, capture):
    job = Path(job).resolve(strict=True)
    records = read_sources(job)
    record = source_metadata(metadata)
    if any(s['id'] == record['id'] for s in records):
        raise ValueError('Source id already recorded; use a new id for a new edition/capture')
    capture = Path(capture)
    if capture.stat().st_size > 16 * 1024**2:
        raise ValueError('Source capture exceeds 16 MiB')
    text = require_text(capture.read_text(encoding='utf-8-sig'), 'actual source capture')
    target = job / 'sources' / (record['id'] + '.txt')
    target.parent.mkdir(exist_ok=True)
    if not target.parent.resolve().is_relative_to(job):
        raise ValueError('Source directory escapes job')
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
    record['sha256'] = file_digest(target)
    save_json(job / 'sources.json', [*records, record])
    return record


def citations(job, items, sources, primary=False):
    if not isinstance(items, list) or not items or not all(isinstance(c, dict) for c in items):
        raise ValueError('Missing primary citation' if primary else 'Missing note citation')
    by_id = {s['id']: s for s in sources}
    used = set()
    normalize = lambda text: re.sub(r'\s+', '', text)
    for item in items:
        source = by_id.get(item.get('source_id'))
        if source is None:
            raise ValueError('Unknown citation source')
        for field in ('quote', 'locator', 'relevance'):
            require_text(item.get(field), 'citation ' + field)
        text = (Path(job) / 'sources' / (source['id'] + '.txt')).read_text(encoding='utf-8')
        if normalize(item['quote']) not in normalize(text):
            raise ValueError('Citation quote is absent from captured source')
        used.add(source['id'])
    if primary and not any(by_id[i]['kind'] in ('primary_text', 'ancient_commentary') for i in used):
        raise ValueError('A primary text or ancient commentary citation is required')
    return used


def validate_record(job, segment, record, sources):
    verification = record.get('classical')
    if not isinstance(verification, dict):
        raise ValueError('Missing classical verification')
    for field in ('reading', 'allusions', 'variants', 'uncertainty'):
        require_text(verification.get(field), 'classical ' + field)
    if verification.get('status') not in ('verified', 'disputed'):
        raise ValueError('Classical reading is unresolved')
    used = citations(job, verification.get('citations'), sources, primary=True)
    if verification['status'] == 'disputed':
        require_text(verification.get('alternatives'), 'documented alternative readings')
        if not any(n.get('category') == 'textual' for n in record.get('notes', [])):
            raise ValueError('Disputed reading must be disclosed in a textual note')
    for note in record.get('notes', []):
        if note['kind'] == 'example':
            if note.get('citations'):
                used |= citations(job, note['citations'], sources)
            continue
        if note.get('category') not in NOTE_LABELS:
            raise ValueError('Classical note needs an explicit category')
        used |= citations(job, note.get('citations'), sources, primary=note['category'] in ('allusion', 'textual'))
    return used


def check_review(report, used, sources):
    checks = report.get('source_checks')
    if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
        raise ValueError('Missing independent source_checks')
    exact_coverage([c.get('source_id') for c in checks], sorted(used))
    by_id = {s['id']: s for s in sources}
    for check in checks:
        if check.get('method') not in READ_METHODS or check.get('sha256') != by_id[check['source_id']]['sha256']:
            raise ValueError('Source review must identify the current source and actual reading method')
        require_text(check.get('locator'), 'source review locator')
        require_text(check.get('conclusion'), 'independent source review conclusion')


def citation_text(citation, sources):
    source = next(s for s in sources if s['id'] == citation['source_id'])
    edition = source['edition'].rstrip().rstrip('。')
    relevance = citation['relevance'].rstrip().rstrip('。')
    return (f"《{source['work']}》；{source['attribution']}；{citation['locator']}；版本：{edition}。"
            f"核对原文：『{citation['quote']}』。此处依据：{relevance}。")


def modern_text(segment):
    if segment['kind'] == 'xml':
        from epub_segments import parse_xml
        return ''.join(parse_xml(segment['source']).itertext())
    return segment['source']


def render_markdown(job, catalog, profile, sources):
    def safe(text):
        # Keep source text visible without interpreting its HTML/Markdown as embeds.
        value = escape(text, quote=False)
        return re.sub(r'([\\`*_[\]{}])', r'\\\1', value)
    lines = ['# ' + safe(profile['bibliography']['title']), '',
             '古文精译 · 原文对照与详注', '', '底本与校勘范围：' + safe(profile['classical']['base_edition']), '']
    by_id = {s['id']: s for s in catalog['segments']}
    paragraph = 0
    for chapter in catalog['chapters']:
        lines += ['## ' + safe(chapter['title']), '']
        draft = load_json(Path(job) / 'chapters' / chapter['id'] / 'translation.json')
        records = {r['id']: r for r in draft['segments']}
        for ident, segment in by_id.items():
            if segment['chapter'] != chapter['id']:
                continue
            record = records[ident]
            paragraph += 1
            lines += [f'### 第{paragraph}段', '', '**原文**', '',
                      '\n'.join('> ' + safe(line) for line in segment['source'].splitlines()), '',
                      '**现代文**', '', safe(record['target']), '', '**详注与校读**', '']
            for note in record.get('notes', []):
                label = '辅助案例（假设示例）' if note['kind'] == 'example' else '译者注·' + NOTE_LABELS[note['category']]
                lines += ['- ' + label + '：' + safe(note['text'])]
                for citation in note.get('citations', []):
                    lines += ['  ' + safe(citation_text(citation, sources))]
            verify = record['classical']
            for label, key in (('字句与断句', 'reading'), ('用典核验', 'allusions'), ('异文与取舍', 'variants'), ('不确定性', 'uncertainty')):
                lines += ['', label + '：' + safe(verify[key])]
            if verify.get('alternatives'):
                lines += ['', '异说：' + safe(verify['alternatives'])]
            for citation in verify['citations']:
                lines += ['', safe(citation_text(citation, sources))]
            lines += ['']
    lines += ['## 实查文献', '']
    for source in sources:
        lines += ['- ' + safe(f"《{source['work']}》；{source['attribution']}；{source['locator']}；{source['edition']}"),
                  '  访问日期：' + source['accessed'] + '；核验范围：' + safe(source['read_evidence'])]
        if source.get('url'):
            # Encode delimiter characters so a source URL cannot inject Markdown.
            url = source['url'].replace(' ', '%20').replace('(', '%28').replace(')', '%29').replace('<', '%3C').replace('>', '%3E')
            lines += ['  [原典页面](' + url + ')']
        else:
            lines += ['  本地图版：' + safe(source['local_reference'])]
    return '\n'.join(lines) + '\n'

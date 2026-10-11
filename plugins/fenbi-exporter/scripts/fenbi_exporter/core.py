"""Pure data contracts, immutable snapshots and verified local assets."""
from __future__ import annotations
import copy
import hashlib
import json
import mimetypes
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

SCHEMA = 1
CST = timezone(timedelta(hours=8))
SECRET = re.compile(r'(sign|token|auth|cookie|credential|key|ticket|secret)', re.I)


def now():
    return datetime.now(CST).isoformat(timespec='seconds')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def redact_url(url):
    p = urlsplit(str(url))
    return urlunsplit((p.scheme, p.netloc, p.path,
        urlencode([(k, v) for k, v in parse_qsl(p.query) if not SECRET.search(k)]), ''))


def asset_identity(url):
    return digest(redact_url(url).encode())


def course_url(value):
    value = str(value).strip()
    if value.isdigit():
        return 'https://www.fenbi.com/spa/pwa/episodes/' + value
    p = urlsplit(value)
    if p.scheme != 'https' or p.netloc not in ('fenbi.com', 'www.fenbi.com') or not re.fullmatch(r'/spa/pwa/episodes/\d+/?', p.path):
        raise ValueError('请提供粉笔课程链接或数字课程 ID')
    return 'https://www.fenbi.com' + p.path.rstrip('/')


def safe_name(value, limit=70):
    original = str(value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', original).strip(' .') or 'unnamed'
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', value, re.I):
        value = '_' + value
    if len(value) > limit:
        suffix = Path(value).suffix[:10]
        value = value[:limit-len(suffix)-9] + '-' + digest(original.encode())[:8] + suffix
    return value


def date_selected(value, start=None, end=None):
    if not start and not end:
        return True
    match = re.search(r'\d{4}[.-]\d{2}[.-]\d{2}', str(value))
    if not match:
        raise ValueError('记录日期不可识别，不能静默排除')
    if 'T' in str(value):
        day = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if day.tzinfo:
            day = day.astimezone(CST)
        day = day.date().isoformat()
    else:
        day = match.group().replace('.', '-')
    return (not start or day >= start) and (not end or day <= end)


def combine_flags(card, toolbar):
    flags, issues = [], []
    for name in ('marked', 'collected'):
        values = [x[name] for x in (card, toolbar) if isinstance(x.get(name), bool)]
        if not values or len(set(values)) > 1:
            flags.append(None)
            issues.append(name + (': conflicting evidence' if values else ': unknown'))
        else:
            flags.append(values[0])
    return flags[0], flags[1], issues


def normalize_record(raw):
    record = copy.deepcopy(raw)
    record.update(schema_version=SCHEMA, captured_at=raw.get('captured_at', now()))
    record.setdefault('issues', [])
    record.setdefault('questions', [])
    for q in record['questions']:
        mark, star, issues = combine_flags(q.get('card', {}), q.get('toolbar', {}))
        q.update(uncertain_marked=mark, favorited=star, flag_issues=issues)
        q.setdefault('user_answer', None)
        q.setdefault('blocks', [])
        record['issues'].extend(f"question {q['number']}: {x}" for x in issues)
        if q['user_answer'] is None and q.get('correctness') != 'unanswered':
            record['issues'].append(f"question {q['number']}: user_answer unavailable")
    expected = record.get('expected_count')
    if expected is not None and expected != len(record['questions']):
        record['issues'].append(f"question count mismatch: expected {expected}, extracted {len(record['questions'])}")
    if not record['questions'] and expected != 0:
        record['issues'].append('no questions extracted')
    record['issues'] = list(dict.fromkeys(record['issues']))
    record['status'] = 'partial' if record['issues'] else 'complete'
    return record


def validate_file(data, filename, mime=''):
    if not data:
        raise ValueError('empty download')
    head = data[:1024].lstrip().lower()
    if head.startswith((b'<!doctype html', b'<html', b'{"error', b'{"code')) or mime.split(';')[0] in ('text/html', 'application/json'):
        raise ValueError('download contains an error/login document')
    ext = Path(filename).suffix.lower()
    if mime.split(';')[0] in ('text/css','application/javascript','text/javascript') or ext in ('.css','.js','.html','.htm'):
        raise ValueError('download is a web application resource, not an attachment')
    if ext == '.pdf' or mime.split(';')[0] == 'application/pdf':
        if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-4096:]:
            raise ValueError('invalid or truncated PDF')
    if ext == '.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('invalid PNG')
    if ext in ('.jpg', '.jpeg') and not data.startswith(b'\xff\xd8'):
        raise ValueError('invalid JPEG')
    if ext in ('.zip', '.docx', '.xlsx', '.pptx'):
        import io, zipfile
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if z.testzip():
                    raise ValueError('corrupt archive')
        except zipfile.BadZipFile as exc:
            raise ValueError('invalid archive') from exc


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.partial-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))


def render_blocks(blocks, prefix=''):
    out = []
    for block in blocks:
        kind = block.get('type')
        if kind == 'image':
            asset = block.get('asset')
            out.append(f"![{block.get('alt', '图片')}]({prefix}{asset})" if asset else '**[图片未保存]**')
        elif kind == 'heading':
            out.append('#### ' + block.get('text', ''))
        else:
            out.append(block.get('text', ''))
    return '\n\n'.join(out)


def render_record(record, prefix='../../'):
    yn = {True: '是', False: '否', None: '未知'}
    lines = [f"# {record.get('title', record['id'])}", '',
        f"记录：{record['id']} · {record.get('subject', '')}",
        f"来源：{record.get('source_url', '')}",
        f"采集时间：{record.get('captured_at', '')}（标注与收藏为采集时状态）", '',
        record.get('summary', ''), '']
    if record.get('issues'):
        lines += ['## 待核对项', '', *['- ' + i for i in record['issues']], '']
    for q in record.get('questions', []):
        lines += [f"## 第 {q['number']} 题", '',
            f"不确定标注：{yn[q.get('uncertain_marked')]} · 收藏：{yn[q.get('favorited')]}", '',
            f"我的答案：{q.get('user_answer') if q.get('user_answer') is not None else '未取得'}", '',
            render_blocks(q.get('blocks', []), prefix), '']
    return '\n'.join(lines)


class ExportStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        index_path = self.root / 'index.json'
        self.index = json.loads(index_path.read_text('utf-8')) if index_path.exists() else {
            'schema_version': SCHEMA, 'assets': {}, 'records': {}, 'courses': {}}
        self.index.setdefault('image_sources', {})
        # Upgrade old local snapshots without fetching identical immutable image resources again.
        for entry in self.index['records'].values():
            latest = self.path(entry['latest'])
            if latest.exists():
                try:
                    old = json.loads(latest.read_text('utf-8'))
                except (ValueError, OSError):
                    continue  # verify reports damaged snapshots; other records remain usable.
                for question in old.get('questions', []):
                    for block in question.get('blocks', []):
                        if block.get('method') == 'original' and block.get('source_url') and block.get('sha256'):
                            self.index['image_sources'][asset_identity(block['source_url'])] = block['sha256']

    def path(self, relative):
        result = (self.root / relative).resolve()
        if not result.is_relative_to(self.root):
            raise ValueError('output path escapes root')
        return result

    def flush(self):
        write_json(self.root / 'index.json', self.index)
        lines = ['# 粉笔导出索引', '', '## 做题记录', '']
        for entry in self.index['records'].values():
            current = entry.get('current') or entry.get('latest')
            if current:
                lines.append(f"- [{entry['title']}]({current[:-5]}.md) — {entry['status']}")
        lines += ['', '## 课程资料', '']
        for cid, entry in self.index['courses'].items():
            lines.append(f"- [{entry.get('title', cid)}](courses/{cid}/index.md)")
        atomic_write(self.root / 'index.md', '\n'.join(lines).encode('utf-8'))

    def save_asset(self, data, filename, mime=''):
        validate_file(data, filename, mime)
        sha = digest(data)
        old = self.index['assets'].get(sha)
        if old and self.path(old['path']).exists() and digest(self.path(old['path']).read_bytes()) == sha:
            return old
        extension = Path(filename).suffix.lower()
        if not re.fullmatch(r'\.[a-z0-9]{1,8}', extension):
            extension = mimetypes.guess_extension(mime.split(';')[0]) or '.bin'
        relative = 'assets/' + sha + extension
        atomic_write(self.path(relative), data)
        asset = {'path': relative, 'sha256': sha, 'size': len(data), 'mime': mime.split(';')[0]}
        self.index['assets'][sha] = asset
        self.flush()
        return asset

    def save_record(self, record):
        record = copy.deepcopy(record)
        record.setdefault('schema_version', SCHEMA)
        record.setdefault('issues', [])
        content = copy.deepcopy(record)
        for key in ('captured_at', 'run_id'):
            content.pop(key, None)
        for question in content.get('questions', []):
            for block in question.get('blocks', []):
                if block.get('type') == 'image' and block.get('sha256') and block.get('asset'):
                    # CDN rotation is provenance, not a content change. Keep the observed
                    # source in the saved snapshot, but compare the verified local bytes.
                    block.pop('source_url', None)
        version = digest(json.dumps(content, sort_keys=True, ensure_ascii=False).encode())[:20]
        key = record['subject'] + ':' + record['id']
        folder = safe_name(record['subject'] + '-' + record['id'], 80)
        relative = f'snapshots/{folder}/{version}.json'
        target = self.path(relative)
        if not target.exists():
            write_json(target, record)
            atomic_write(target.with_suffix('.md'), render_record(record).encode('utf-8'))
        entry = self.index['records'].setdefault(key, {'versions': []})
        if relative not in entry['versions']:
            entry['versions'].append(relative)
        entry.update(title=record.get('title', key), latest=relative, last_checked_at=now(),
            status='partial' if record['issues'] else 'complete')
        if not record['issues']:
            entry['current'] = relative
        self.flush()
        return relative

    def verify(self):
        issues = []
        for sha, asset in self.index['assets'].items():
            path = self.path(asset['path'])
            if not path.exists():
                issues.append('missing/corrupt asset: ' + asset['path'])
                continue
            data = path.read_bytes()
            if digest(data) != sha or len(data) != asset['size']:
                issues.append('missing/corrupt asset: ' + asset['path'])
            try:
                validate_file(data, path.name, asset.get('mime', ''))
            except ValueError:
                issues.append('invalid file content: ' + asset['path'])
        for entry in self.index['records'].values():
            if entry.get('status') != 'complete':
                issues.append('incomplete latest record: ' + entry['latest'])
            for relative in entry['versions']:
                path = self.path(relative)
                if not path.exists() or not path.with_suffix('.md').exists():
                    issues.append('missing snapshot: ' + relative)
                    continue
                try:
                    record = json.loads(path.read_text('utf-8'))
                except (ValueError, OSError):
                    issues.append('invalid snapshot: ' + relative)
                    continue
                for link in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', path.with_suffix('.md').read_text('utf-8')):
                    target = (path.parent / link).resolve()
                    if not target.is_relative_to(self.root) or not target.is_file():
                        issues.append('broken Markdown image reference: ' + relative)
                for q in record.get('questions', []):
                    for b in q.get('blocks', []):
                        if b.get('type') == 'image' and (not b.get('asset') or not self.path(b['asset']).exists()):
                            issues.append('missing image: ' + relative)
        for course in self.index['courses'].values():
            for versions in course['attachments'].values():
                for version in versions:
                    path = self.path(version['path'])
                    if not path.exists() or digest(path.read_bytes()) != version['asset']['sha256']:
                        issues.append('missing/corrupt course file: ' + version['path'])
        return {'status': 'partial' if issues else 'complete', 'issues': issues,
            'records': len(self.index['records']), 'assets': len(self.index['assets'])}

"""Read-only UI traversal, passive response observation and export orchestration."""
from __future__ import annotations
import base64
import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit, urljoin, unquote
from .browser import AccessRequired, HISTORY, CATALOG, record_url
from .core import (CST, ExportStore, asset_identity, atomic_write, course_url, date_selected, digest,
    normalize_record, now, redact_url, safe_name, write_json)

EXTRACT = Path(__file__).with_name('extract.js').read_text('utf-8')


def dedupe_items(items):
    unique = {}
    for item in items:
        key = item.get('exerciseKey')
        if not key:
            raise ValueError('历史记录缺少作答标识')
        unique[key] = item
    return list(unique.values())


def completed_example(items):
    return next((i for i, item in enumerate(items) if item.get('status') == 1), None)


class HistoryPages:
    def __init__(self):
        self.items = []
        self.complete = False
        self.cursor = None
        self.responses = 0
        self.error = None

    def add(self, value):
        if value.get('code') != 1 or not isinstance(value.get('data', {}).get('historyItems'), list):
            raise ValueError('历史列表响应无效')
        data = value['data']
        if 'cursor' not in data:
            raise ValueError('历史列表缺少结束游标')
        self.items = dedupe_items(self.items + data['historyItems'])
        self.cursor = data['cursor']
        self.complete = self.cursor is None or self.cursor == ''
        self.responses += 1

    def observe(self, response):
        # This endpoint and schema were observed through the user's own history UI.
        # We listen only; pagination is still performed by the page, with its own auth.
        if urlsplit(response.url).path.endswith('/getExerciseBriefHistory'):
            try:
                self.add(response.json())
            except Exception:
                self.error = '历史列表请求失败或格式已改变'


class SolutionState:
    """Observe the page's own state requests; an unhydrated unchecked icon is not false."""
    ROUTES = {'/combine/mark/getMark':'marked', '/combine/collect/getCollect':'collected',
              '/combine/note/getNote':'notes', '/combine/question/getMeta':'meta'}

    def __init__(self):
        self.started, self.finished, self.failed = set(), set(), set()
        self.values = {}

    def requested(self, request):
        slot = self.ROUTES.get(urlsplit(request.url).path)
        if slot:
            self.started.add(slot)

    def add(self, slot, value):
        self.started.add(slot)
        self.finished.add(slot)
        data = value.get('data')
        valid = value.get('code') == 1 and isinstance(data, dict)
        if slot in ('marked', 'collected'):
            valid = valid and isinstance(data.get('ids'), list) and all(isinstance(x, str) for x in data['ids'])
        if valid:
            self.values[slot] = set(data['ids']) if slot in ('marked','collected') else data
        else:
            self.failed.add(slot)

    def received(self, response):
        slot = self.ROUTES.get(urlsplit(response.url).path)
        if slot:
            try:
                self.add(slot, response.json())
            except Exception:
                self.finished.add(slot)
                self.failed.add(slot)

    def request_failed(self, request):
        slot = self.ROUTES.get(urlsplit(request.url).path)
        if slot:
            self.finished.add(slot)
            self.failed.add(slot)

    def dom_ready(self, raw):
        for q in raw['questions']:
            for slot in ('marked', 'collected'):
                if slot not in self.values or slot in self.failed:
                    continue
                qid = q.get('question_id')
                expected = qid in self.values[slot]
                states = [v[slot] for v in (q.get('card',{}), q.get('toolbar',{})) if isinstance(v.get(slot), bool)]
                if not qid or not states or any(x != expected for x in states):
                    return False
        return True

    def reconcile(self, raw, required=()):
        for q in raw['questions']:
            evidence = q.setdefault('flag_evidence', {})
            evidence['response_states'] = {}
            for slot in ('marked', 'collected'):
                known = slot in self.values and slot not in self.failed and bool(q.get('question_id'))
                expected = q.get('question_id') in self.values[slot] if known else None
                states = [v[slot] for v in (q.get('card',{}), q.get('toolbar',{})) if isinstance(v.get(slot), bool)]
                matched = known and bool(states) and all(x == expected for x in states)
                reason = None if matched else ('状态请求失败' if slot in self.failed else
                    '页面未提供或尚未加载该状态' if not known else '响应与页面状态未一致')
                evidence['response_states'][slot] = {'confirmed':matched,'expected':expected,'reason':reason}
                if not matched:
                    q.setdefault('card', {})[slot] = None
                    q.setdefault('toolbar', {})[slot] = None
                    raw['issues'].append(f"question {q['number']}: {slot}: {reason}")
        for slot in set(required) | self.started:
            if slot not in ('marked','collected') and (slot not in self.values or slot in self.failed):
                raw['issues'].append(slot + ': 页面数据加载未确认')


def wait_until(page, predicate, timeout=45000):
    end = time.monotonic() + timeout / 1000
    while time.monotonic() < end:
        if predicate():
            return
        page.wait_for_timeout(250)
    raise RuntimeError('等待页面内容超时')


def wait_for_solution(page, timeout=30000):
    page.wait_for_url('**/ti/exam/solution/**', wait_until='domcontentloaded', timeout=timeout)


def history_inventory(browser, subject, category, start=None, end=None, limit=None):
    page = browser.context.new_page()
    pages = HistoryPages()
    page.on('response', pages.observe)
    try:
        if subject == 'xingce':
            browser.goto(HISTORY, page)
            wait_until(page, lambda: pages.responses or pages.error)
            browser.check(page)
            if category != '练习':
                pages = HistoryPages()
                # Install a fresh collector; the old one is harmless and local to this page.
                page.on('response', pages.observe)
                page.get_by_text(category, exact=True).click()
                wait_until(page, lambda: pages.responses or pages.error)
        else:
            browser.goto(CATALOG, page)
            page.get_by_text('申论', exact=True).last.wait_for(timeout=45000)
            # Selecting a subject changes navigation only; it does not start an exercise.
            page.get_by_text('申论', exact=True).last.click()
            page.get_by_text('全部', exact=True).wait_for(timeout=30000)
            page.get_by_text('全部', exact=True).click()
            wait_until(page, lambda: pages.responses or pages.error)
            if category != '练习批改':
                pages = HistoryPages()
                page.on('response', pages.observe)
                page.get_by_text(category, exact=True).click()
                wait_until(page, lambda: pages.responses or pages.error)
        if pages.error:
            raise RuntimeError(pages.error)
        template = None
        listing_url = page.url
        truncated = False
        inventory_issues = []
        stagnation = 0
        while not pages.complete:
            if limit and len(pages.items) >= limit:
                truncated = True
                break
            before = (len(pages.items), pages.responses, pages.cursor)
            page.evaluate('''() => {window.scrollTo(0,document.body.scrollHeight);
              for(const e of document.querySelectorAll('main,article,section,div'))
                if(e.scrollHeight>e.clientHeight+100 && ['auto','scroll'].includes(getComputedStyle(e).overflowY)) e.scrollTop=e.scrollHeight;}''')
            try:
                wait_until(page, lambda: pages.responses != before[1] or pages.error, 10000)
            except RuntimeError:
                stagnation += 1
                if stagnation >= 3:
                    inventory_issues.append('历史分页未确认结束；已保存已发现记录，请恢复任务重试')
                    break
            browser.check(page)
            if pages.error:
                inventory_issues.append(pages.error)
                break
            if (len(pages.items), pages.responses, pages.cursor) != before:
                stagnation = 0
        selected = []
        # Derive a URL template only after a real row has established its route.
        # Enumerate before navigation so returning to the list cannot reset its category/cursor.
        example = completed_example(pages.items)
        if example is not None:
            selector = '.list-detail-item .item-info-title' if subject == 'xingce' else 'h5.list-item-title'
            page.locator(selector).nth(example).click()
            wait_for_solution(page)
            template = record_url(page.url)
            if urlsplit(template).path.rsplit('/', 1)[-1] != pages.items[example]['exerciseKey']:
                raise RuntimeError('列表与详情标识不一致，停止推断链接')
        for item in pages.items:
            dt = datetime.fromtimestamp(item['updatedTime'] / 1000, CST).isoformat() if item.get('updatedTime') else ''
            if date_selected(dt, start, end):
                readable = item.get('status') == 1
                if not template and readable:
                    raise RuntimeError('无法取得历史详情链接模板')
                p = urlsplit(template or listing_url)
                url = urlunsplit((p.scheme, p.netloc, p.path.rsplit('/', 1)[0] + '/' + item['exerciseKey'], p.query, '')) if readable else listing_url
                selected.append({'url': url, 'id': item['exerciseKey'], 'subject': subject, 'category': category,
                    'date': dt, 'list_metadata': item, 'readable': readable})
        if limit and len(selected) > limit:
            selected = selected[:limit]
            truncated = True
        return selected, {'subject': subject, 'category': category, 'discovered': len(pages.items),
            'pagination_complete': pages.complete, 'response_pages': pages.responses,
            'limited': truncated, 'issues': inventory_issues}
    finally:
        page.close()


def fetch_asset(browser, url, referer, filename):
    if url.startswith('data:'):
        header, payload = url.split(',', 1)
        mime = header[5:].split(';')[0]
        return (base64.b64decode(payload) if ';base64' in header else unquote(payload).encode()), mime
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname:
        raise ValueError('不支持的图片地址')
    for attempt in range(3):
        try:
            response = browser.context.request.get(url, headers={'Referer': referer}, timeout=45000)
            if response.status in (401, 403):
                raise ValueError('附件地址失效或无权访问')
            if not response.ok:
                raise RuntimeError('附件请求失败')
            data, mime = response.body(), response.headers.get('content-type', '')
            return data, mime
        except ValueError:
            raise
        except Exception:
            if attempt == 2:
                raise RuntimeError('附件请求失败（已重试）') from None
            browser.page.wait_for_timeout(500 * (attempt + 1))


def export_record(browser, store, item):
    if item.get('readable') is False:
        record = normalize_record({'id':item['id'], 'subject':item['subject'], 'source_url':item['url'],
            'title':item['list_metadata'].get('sheetName',item['id']), 'list_metadata':item['list_metadata'],
            'date':item.get('date'), 'questions':[], 'issues':['未完成或状态未识别：已保留列表信息，未进入答题页']})
        return {'status':'partial','snapshot':store.save_record(record),'questions':0,'issues':record['issues']}
    page = browser.context.new_page()
    state = SolutionState()
    page.on('request', state.requested)
    page.on('response', state.received)
    page.on('requestfailed', state.request_failed)
    try:
        browser.goto(record_url(item['url']), page)
        page.locator('app-ti').first.wait_for(state='attached', timeout=60000)
        page.locator('.answer-btn').first.wait_for(state='attached', timeout=30000)
        browser.check(page)
        # Render lazy content without modifying answers or toggles.
        page.locator('app-ti').last.scroll_into_view_if_needed()
        page.wait_for_timeout(700)
        raw = page.evaluate(EXTRACT)
        required = {slot for q in raw['questions'] for slot in ('marked','collected') if slot in q.get('toolbar',{})}
        if any(s['id'].startswith('section-note-') for q in raw['questions'] for s in q.get('sections',[])):
            required.add('notes')
        try:
            wait_until(page, lambda: (required | state.started) <= state.finished, 45000)
            wait_until(page, lambda: state.dom_ready(page.evaluate(EXTRACT)), 10000)
        except RuntimeError:
            pass  # Missing or inconsistent evidence must become unknown, never unchecked/false.
        browser.check(page)
        raw = page.evaluate(EXTRACT)
        state.reconcile(raw, required)
        raw.update(id=item.get('id') or urlsplit(page.url).path.rsplit('/', 1)[-1],
            subject=item['subject'], source_url=redact_url(page.url), category=item.get('category'),
            date=item.get('date'), list_metadata=item.get('list_metadata', {}))
        record = normalize_record(raw)
        for question in record['questions']:
            for block in question['blocks']:
                if block.get('type') != 'image':
                    continue
                source = block.pop('src', None)
                selector = block.pop('capture_selector', None)
                try:
                    if source and not source.startswith('blob:'):
                        url = urljoin(page.url, source)
                        filename = Path(urlsplit(url).path).name or 'image.png'
                        sha = store.index['image_sources'].get(asset_identity(url))
                        asset = store.index['assets'].get(sha)
                        if not asset or not store.path(asset['path']).exists() or digest(store.path(asset['path']).read_bytes()) != sha:
                            data, mime = fetch_asset(browser, url, page.url, filename)
                            asset = store.save_asset(data, filename, mime)
                            store.index['image_sources'][asset_identity(url)] = asset['sha256']
                        block.update(asset=asset['path'], sha256=asset['sha256'], source_url=redact_url(url), method='original')
                    else:
                        raise ValueError('rendered-only image')
                except Exception:
                    try:
                        element = page.locator(selector) if selector else None
                        if not element or not element.count():
                            raise ValueError('missing rendered image')
                        if source and not element.evaluate('(e)=>e.tagName!=="IMG" || (e.complete&&e.naturalWidth>0)'):
                            raise ValueError('image did not load')
                        data = element.screenshot(timeout=12000)
                        asset = store.save_asset(data, 'capture.png', 'image/png')
                        block.update(asset=asset['path'], sha256=asset['sha256'], method='rendered_capture')
                    except Exception:
                        record['issues'].append(f"question {question['number']}: missing image")
            # Preserve a visual reference for per-character essay grading.
            answer_selector = question.pop('answer_capture_selector', None)
            if question.get('grading') and answer_selector:
                try:
                    data = page.locator(answer_selector).screenshot(timeout=12000)
                    asset = store.save_asset(data, 'grading.png', 'image/png')
                    question['blocks'].append({'type': 'image', 'asset': asset['path'], 'alt': '本人作答与批改原貌', 'method': 'rendered_capture'})
                except Exception:
                    record['issues'].append(f"question {question['number']}: grading capture unavailable")
        record['status'] = 'partial' if record['issues'] else 'complete'
        path = store.save_record(record)
        return {'status': record['status'], 'snapshot': path, 'questions': len(record['questions']), 'issues': record['issues']}
    except Exception:
        if not page.is_closed():
            browser.check(page)
        raise
    finally:
        if not page.is_closed():
            page.close()


def load_course_rows(page, expected, timeout=15000):
    """Scroll the lesson list until its rendered count agrees with the group header."""
    rows = page.locator('.episode-wrapper:has(> .title-wrapper .title[title])')
    while rows.count() < expected:
        before = rows.count()
        if before:
            rows.last.scroll_into_view_if_needed()
            rows.last.hover()
            page.mouse.wheel(0, 1900)
        try:
            wait_until(page, lambda: rows.count() > before, timeout)
        except RuntimeError:
            raise RuntimeError(f'课时加载不完整：页面显示 {expected} 节，已加载 {rows.count()} 节') from None
    if rows.count() != expected:
        raise RuntimeError('课时数量与科目标题不一致，不能确认列表完整')
    return rows


def open_course_group(browser, page, url, set_name, group):
    browser.goto(url, page)
    page.locator('.left .name').first.wait_for(timeout=45000)
    if set_name != '主课时集':
        page.locator('.group > button').filter(has_not_text='课时筛选').click()
        page.locator('.group .list-wrapper-c > span').filter(has_text=re.compile('^'+re.escape(set_name)+'$')).click()
    header = page.locator('.left .name').filter(has_text=re.compile('^' + re.escape(group) + '$'))
    header.click()
    count_text = header.locator('xpath=../..').locator('.right').inner_text()
    count = re.search(r'(\d+)\s*节', count_text)
    if not count:
        raise RuntimeError('科目课时总数无法识别，不能确认列表完整')
    return load_course_rows(page, int(count.group(1)))


def course_inventory(browser, url, limit=None, group_filter=None, lesson_filter=None):
    page = browser.context.new_page()
    tasks = []
    try:
        browser.goto(url, page)
        page.locator('.left .name').first.wait_for(timeout=45000)
        title = page.locator('h5').first.inner_text()
        page.locator('.group > button').filter(has_not_text='课时筛选').click()
        # The dropdown selector is discovered from its rendered button/menu, not an API.
        sets = page.locator('.group .list-wrapper-c > span').all_text_contents()
        if not sets:
            raise ValueError('课时集菜单无法识别，不能保证完整遍历')
        page.locator('.group > button').filter(has_not_text='课时筛选').click()
        sets = list(dict.fromkeys(['主课时集'] + sets))
        for set_name in sets:
            if set_name != '主课时集':
                page.locator('.group > button').filter(has_not_text='课时筛选').click()
                page.locator('.group .list-wrapper-c > span').filter(has_text=re.compile('^'+re.escape(set_name)+'$')).click()
            groups = page.locator('.left .name').all_text_contents()
            for group in groups:
                if group_filter and group.strip() != group_filter:
                    continue
                rows = open_course_group(browser, page, url, set_name, group.strip())
                for i in range(rows.count()):
                    row = rows.nth(i)
                    if not row.locator('.downloadPDF').count():
                        continue
                    lesson = row.locator('.title').first.inner_text()
                    if lesson_filter and lesson != lesson_filter:
                        continue
                    row.locator('.downloadPDF').click()
                    page.locator('.material-download-modal-item').first.wait_for()
                    labels = page.locator('.material-download-modal-item').all_text_contents()
                    for j, label in enumerate(labels):
                        identity = digest(f'{url}|{set_name}|{group}|{i}|{lesson}|{j}'.encode())[:20]
                        tasks.append({'id': identity, 'url': url, 'set': set_name, 'group': group.strip(), 'row': i,
                            'lesson': lesson, 'attachment': j, 'label': label.strip(), 'course_title': title})
                    page.locator('.material-download-modal-close').click()
                    if limit and len({(x['set'], x['group'], x['row']) for x in tasks}) >= limit:
                        return tasks, {'limited': True, 'title': title, 'course_id': url.rsplit('/', 1)[-1]}
        if (group_filter or lesson_filter) and not tasks:
            raise ValueError('没有找到指定科目/课时中的资料')
        return tasks, {'limited': False, 'title': title, 'course_id': url.rsplit('/', 1)[-1]}
    finally:
        page.close()


def export_attachment(browser, store, item):
    # Reopening the source for each attempt refreshes expiring signed URLs.
    for attempt in range(3):
        page = browser.context.new_page()
        step = '打开课时'
        downloads, responses, popups, finished, failed = [], [], [], [], []
        armed = False
        def capture(response):
            if not armed or response.request.resource_type in ('stylesheet','script','font','image','media'):
                return
            content_type = response.headers.get('content-type', '').lower()
            if ('application/pdf' in content_type or 'attachment' in response.headers.get('content-disposition', '').lower()
                    or re.search(r'\.(pdf|docx?|xlsx?|pptx?|zip)(?:\?|$)', response.url, re.I)):
                responses.append(response)
        def hook(p):
            p.on('download', lambda download: downloads.append(download))
            p.on('response', capture)
        def popup(p):
            popups.append(p)
            hook(p)
        def request_done(request):
            if armed:
                finished.append(request)
        def request_failed(request):
            if armed:
                failed.append(request)
        hook(page)
        browser.context.on('response', capture)
        browser.context.on('requestfinished', request_done)
        browser.context.on('requestfailed', request_failed)
        page.on('popup', popup)
        try:
            rows = open_course_group(browser, page, item['url'], item['set'], item['group'])
            row = rows.nth(item['row'])
            if row.locator('.title').first.inner_text() != item['lesson']:
                raise ValueError('课时顺序已改变，请重新运行课程同步')
            row.locator('.downloadPDF').click()
            step = '打开附件'
            attachment = page.locator('.material-download-modal-item').nth(item['attachment'])
            if attachment.text_content().strip() != item['label']:
                raise ValueError('附件列表已改变，请重新运行课程同步')
            armed = True
            attachment.click(no_wait_after=True)
            step = '等待下载'
            wait_until(page, lambda: downloads or responses, 30000)
            if responses and not downloads:
                response = responses[-1]
                if response.status >= 400:
                    raise ValueError('附件请求返回错误状态，需刷新入口')
                if response.request.resource_type in ('xhr', 'fetch'):
                    # Fenbi creates a blob download only after its XHR completes. A large
                    # response may be evicted from Chromium's inspection buffer meanwhile.
                    size = int(response.headers.get('content-length', '0') or '0')
                    if size > 16 * 1024 * 1024:
                        print(f'附件约 {size / 1024 / 1024:.1f} MiB，等待网页完成传输。', flush=True)
                    step = '等待网页文件传输'
                    wait_until(page, lambda: downloads or response.request in finished or response.request in failed, 600000)
                    if response.request in failed:
                        raise RuntimeError('网页文件传输中断')
                    page.wait_for_timeout(1500)  # Let the page turn its completed XHR into a download.
            if downloads:
                step = '读取浏览器下载'
                download = downloads[0]
                if download.failure():
                    raise RuntimeError('浏览器下载失败')
                data = Path(download.path()).read_bytes()
                filename = download.suggested_filename
                mime = ''
            else:
                step = '读取 PDF 响应'
                response = responses[-1]
                filename = Path(urlsplit(response.url).path).name or '资料.pdf'
                disposition = response.headers.get('content-disposition', '')
                match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", disposition, re.I)
                if match:
                    filename = unquote(match.group(1))
                try:
                    data, mime = response.body(), response.headers.get('content-type', '')
                except Exception:
                    data, mime = fetch_asset(browser, response.url, item['url'], filename)
            if re.search(r'\.[a-zA-Z0-9]{2,5}$', item['label']):
                filename = item['label']
            asset = store.save_asset(data, filename, mime)
            step = '保存课程文件'
            cid = item['url'].rsplit('/', 1)[-1]
            folder = '/'.join(['courses', cid, safe_name(item['set'], 25), safe_name(item['group'], 25), safe_name(item['lesson'], 35)])
            original = filename
            filename = safe_name(item['label'] if '.' in item['label'] else item['label'] + Path(filename).suffix, 45)
            relative = f'{folder}/{asset["sha256"][:10]}-{filename}'
            target = store.path(relative)
            if not target.exists() or digest(target.read_bytes()) != asset['sha256']:
                atomic_write(target, data)
            entry = {**item, 'original_filename': original, 'asset': asset, 'path': relative, 'status': 'complete', 'captured_at': now()}
            course = store.index['courses'].setdefault(cid, {'title': item['course_title'], 'attachments': {}})
            versions = course['attachments'].setdefault(item['id'], [])
            if not versions or versions[-1]['asset']['sha256'] != asset['sha256']:
                versions.append(entry)
            write_json(store.path(f'courses/{cid}/index.json'), course)
            lines = ['# ' + course['title'], '']
            for values in course['attachments'].values():
                last = values[-1]
                lines.append(f"- {last['group']} / {last['lesson']} / [{last['label']}](<{last['path'].split('/', 2)[2]}>)")
            atomic_write(store.path(f'courses/{cid}/index.md'), '\n'.join(lines).encode('utf-8'))
            store.flush()
            return {'status': 'complete', 'path': relative, 'sha256': asset['sha256']}
        except AccessRequired:
            raise
        except Exception as exc:
            if attempt == 2:
                raise RuntimeError(f'附件保存失败：{step}（{type(exc).__name__}）；已重试三次') from None
        finally:
            browser.context.remove_listener('response', capture)
            browser.context.remove_listener('requestfinished', request_done)
            browser.context.remove_listener('requestfailed', request_failed)
            for p in popups + [page]:
                if not p.is_closed():
                    p.close()


def execute(args, browser):
    store = ExportStore(args.output)
    if args.command == 'resume':
        if not re.fullmatch(r'[\w-]+', args.run):
            raise ValueError('无效任务 ID')
        run = json.loads(store.path(f'runs/{args.run}.json').read_text('utf-8'))
        params = run['parameters']
        args = SimpleNamespace(**params)
        args.output = store.root
        run['issues'] = []
    else:
        if getattr(args, 'limit', None) is not None and args.limit <= 0:
            raise ValueError('--limit 必须是正整数')
        if getattr(args, 'record_url', None) and (getattr(args,'start',None) or getattr(args,'end',None)):
            raise ValueError('指定详情链接时请勿同时使用日期筛选')
        for value in (getattr(args, 'start', None), getattr(args, 'end', None)):
            if value:
                datetime.strptime(value, '%Y-%m-%d')
        if getattr(args, 'start', None) and getattr(args, 'end', None) and args.start > args.end:
            raise ValueError('起始日期不能晚于结束日期')
        run = {'schema_version': 1, 'id': datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8],
            'parameters': {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items() if k not in ('profile','headless')},
            'created_at': now(), 'tasks': [], 'results': {}, 'inventory': [], 'issues': [], 'discovery_complete': False}
    run_path = store.path(f'runs/{run["id"]}.json')
    def checkpoint():
        run['updated_at'] = now()
        write_json(run_path, run)
    checkpoint()
    try:
        if not run['discovery_complete']:
            run['issues'] = []
            if args.command == 'course':
                tasks, inventory = course_inventory(browser, course_url(args.course), args.limit, getattr(args,'group',None), getattr(args,'lesson',None))
                run['tasks'], run['inventory'] = tasks, [inventory]
            elif args.record_url:
                run['tasks'] = []
                for url in args.record_url:
                    record_url(url)
                    subject = 'shenlun' if 'routecs=shenlun' in url else ('xingce' if 'routecs=xingce' in url else args.subject)
                    if subject == 'all':
                        raise ValueError('详情链接未指定科目，请补充 --subject')
                    run['tasks'].append({'url':url,'id':urlsplit(url).path.rsplit('/',1)[-1], 'subject':subject})
            else:
                tasks = []
                subjects = ['xingce','shenlun'] if args.subject == 'all' else [args.subject]
                run['inventory'] = []
                for subject in subjects:
                    categories = ['练习','试卷'] if subject == 'xingce' else ['练习批改','套卷批改','小模考']
                    for category in categories:
                        found, inventory = history_inventory(browser, subject, category, args.start, args.end, args.limit)
                        tasks.extend(found)
                        run['tasks'] = list({x['subject']+':'+x['id']:x for x in tasks}.values())
                        run['inventory'].append(inventory)
                        checkpoint()
            run['issues'].extend(issue for inventory in run['inventory'] for issue in inventory.get('issues', []))
            run['discovery_complete'] = not any(
                x.get('pagination_complete') is False and not x.get('limited') for x in run['inventory'])
            checkpoint()
        for task in run['tasks']:
            key = task.get('subject', 'course') + ':' + task['id']
            if run['results'].get(key, {}).get('status') == 'complete':
                continue
            print(f"处理中：{task.get('lesson') or task.get('list_metadata',{}).get('sheetName') or task['id']}", flush=True)
            try:
                result = export_attachment(browser, store, task) if args.command == 'course' else export_record(browser, store, task)
            except AccessRequired:
                raise
            except Exception as exc:
                result = {'status':'failed','reason':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__}
            run['results'][key] = result
            checkpoint()
        run['status'] = 'partial' if any(r['status'] != 'complete' for r in run['results'].values()) or run['issues'] else 'complete'
        run['limited'] = any(x.get('limited') for x in run['inventory'])
    except AccessRequired as exc:
        run['status'] = exc.status
        run['issues'].append('需要在独立浏览器中完成登录或访问验证')
    except Exception as exc:
        run['status'] = 'partial' if run['results'] else 'failed'
        run['issues'].append(str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__)
    checkpoint()
    result_issues = [{'task':key, 'issues':value.get('issues') or [value.get('reason', value['status'])]}
        for key, value in run['results'].items() if value['status'] != 'complete']
    return {'status':run['status'], 'run_id':run['id'], 'output':str(store.root), 'tasks':len(run['tasks']),
        'complete':sum(x['status']=='complete' for x in run['results'].values()), 'limited':run.get('limited',False),
        'issues':run['issues'], 'incomplete_tasks':result_issues, 'manifest':str(run_path)}

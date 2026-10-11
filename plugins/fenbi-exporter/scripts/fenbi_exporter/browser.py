"""Dedicated browser ownership and read-only navigation."""
from __future__ import annotations
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

HISTORY = 'https://www.fenbi.com/spa/tiku/report/profile/xingce/xingce/history'
CATALOG = 'https://www.fenbi.com/spa/tiku/guide/catalog'


class AccessRequired(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(status)


def classify_access(text):
    if any(x in text for x in ('ERR_BLOCKED_BY_CLIENT', '访问过于频繁', '访问被拒绝', '403 Forbidden')):
        return 'blocked'
    if any(x in text for x in ('请完成验证码', '请完成安全验证', '拖动滑块', '点击完成验证')):
        return 'user_action_required'
    if any(x in text for x in ('扫码登录', '手机号登录', '短信验证码登录', '请先登录')):
        return 'auth_required'
    return 'ready'


def record_url(value):
    p = urlsplit(value)
    if p.scheme != 'https' or p.netloc not in ('www.fenbi.com', 'fenbi.com', 'spa.fenbi.com'):
        raise ValueError('记录链接必须来自粉笔')
    if not (re.fullmatch(r'/ti/exam/solution/[\w-]+', p.path) or p.path.startswith('/spa/tiku/report/')):
        raise ValueError('仅支持历史记录/解析链接')
    return value


def default_profile():
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'fenbi-exporter' / 'browser'


class BrowserSession:
    def __init__(self, profile=None, headless=False, fresh_session=False):
        self.profile = Path(profile or default_profile()).resolve()
        self.headless = headless
        self.fresh_session = fresh_session
        self.download_browser = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self.profile.mkdir(parents=True, exist_ok=True)
        self.pw = sync_playwright().start()
        try:
            self.context = self.pw.chromium.launch_persistent_context(str(self.profile),
                headless=self.headless, accept_downloads=True, viewport={'width': 1440, 'height': 1000})
            if self.fresh_session:
                # Some Windows Chromium profiles crash on native downloads after reuse.
                # Transfer only this plugin's state in memory; never write a token file.
                state = self.context.storage_state()
                self.context.close()
                self.download_browser = self.pw.chromium.launch(headless=self.headless)
                self.context = self.download_browser.new_context(storage_state=state,
                    accept_downloads=True, viewport={'width': 1440, 'height': 1000})
                del state
        except Exception:
            self.pw.stop()
            raise RuntimeError('浏览器启动失败：确认 Chromium 已安装且此插件配置目录未被另一任务使用') from None
        self.context.set_default_timeout(12000)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        return self

    def __exit__(self, *_):
        try:
            self.context.close()
        finally:
            try:
                if self.download_browser:
                    self.download_browser.close()
            finally:
                self.pw.stop()

    def check(self, page=None):
        page = page or self.page
        state = classify_access(page.locator('body').inner_text(timeout=15000))
        if state != 'ready':
            raise AccessRequired(state)

    def goto(self, url, page=None):
        page = page or self.page
        # Navigation failures are deliberately not echoed: Playwright errors may include signed URLs.
        for attempt in range(3):
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=45000)
                self.check(page)
                return page
            except AccessRequired:
                raise
            except Exception:
                if attempt == 2:
                    raise RuntimeError('页面加载失败（已重试三次）') from None
                page.wait_for_timeout(1000 * (attempt + 1))

    def login(self, timeout=600):
        authenticated = [False]
        def observe(response):
            if urlsplit(response.url).hostname == 'login.fenbi.com' and urlsplit(response.url).path == '/api/users/info':
                try:
                    authenticated[0] = response.ok and bool(response.json().get('userId'))
                except Exception:
                    pass
        self.page.on('response', observe)
        self.page.goto(HISTORY, wait_until='domcontentloaded')
        print('请在独立 Chromium 窗口完成粉笔登录。登录状态将仅保存于本机专用目录。', flush=True)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.page.is_closed():
                raise AccessRequired('auth_required')
            try:
                if authenticated[0]:
                    if classify_access(self.page.locator('body').inner_text()) == 'ready':
                        print('登录成功，专用浏览器状态已保存。', flush=True)
                        return
            except Exception:
                pass
            self.page.wait_for_timeout(1000)
        raise AccessRequired('auth_required')

import sys
import unittest
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fenbi_exporter.browser import BrowserSession, classify_access, record_url


class BrowserContracts(unittest.TestCase):
    def test_fresh_session_reuses_private_login_and_saves_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / 'profile'
            with BrowserSession(profile, headless=True) as browser:
                browser.context.add_cookies([{'name':'test_session','value':'synthetic',
                    'domain':'example.test','path':'/','expires':time.time()+3600}])
            with BrowserSession(profile, headless=True, fresh_session=True) as browser:
                cookies = browser.context.cookies('https://example.test')
                self.assertTrue(any(c['name']=='test_session' and c['value']=='synthetic' for c in cookies))
                browser.page.set_content('<a download="probe.txt" href="data:text/plain,download-ok">download</a>')
                with browser.page.expect_download() as event:
                    browser.page.locator('a').click()
                target = Path(tmp) / 'probe.txt'
                event.value.save_as(target)
                self.assertEqual(target.read_text(), 'download-ok')

    def test_access_states(self):
        self.assertEqual(classify_access('扫码登录 手机号登录'), 'auth_required')
        self.assertEqual(classify_access('请完成验证码'), 'user_action_required')
        self.assertEqual(classify_access('ERR_BLOCKED_BY_CLIENT'), 'blocked')
        self.assertEqual(classify_access('得分数据 考试情况'), 'ready')

    def test_detail_url_validation(self):
        self.assertTrue(record_url('https://spa.fenbi.com/ti/exam/solution/1_1_abc?routecs=xingce'))
        for url in ['https://evil.test/ti/exam/solution/x', 'https://spa.fenbi.com/ti/exam/start/x']:
            with self.assertRaises(ValueError):
                record_url(url)

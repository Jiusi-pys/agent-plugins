import sys
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fenbi_exporter.workflow import wait_for_solution, open_course_group

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/fenbi_exporter/extract.js'


class DomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def test_course_group_loads_every_lesson_before_inventory_or_download(self):
        page = self.browser.new_page()
        page.set_content('''<style>app-episode-nodes{display:block;height:400px;overflow:auto}
          .episode-wrapper{height:100px}</style><app-episode-nodes>
          <div class="wrapper"><div class="left"><div class="name">判断推理</div></div>
          <div class="right">41节</div></div><div id="lessons"></div></app-episode-nodes>
          <script>
          let count=0, pending=false;
          function more(){for(let i=0;i<20 && count<41;i++){
            count++;document.querySelector('#lessons').insertAdjacentHTML('beforeend',
            `<div class="episode-wrapper"><div class="title-wrapper"><div class="title" title="课时${count}">课时${count}</div></div></div>`);
          }}
          more();document.querySelector('app-episode-nodes').addEventListener('scroll',e=>{
            if(!pending && e.target.scrollTop+e.target.clientHeight>=e.target.scrollHeight-5){
              pending=true;setTimeout(()=>{more();pending=false},100);
            }
          });</script>''')
        class Browser:
            def goto(self, url, target):
                pass
        try:
            rows = open_course_group(Browser(), page, 'https://example.test/course', '主课时集', '判断推理')
            self.assertEqual(rows.count(), 41)
            self.assertEqual(rows.nth(31).locator('.title').inner_text(), '课时32')
        finally:
            page.close()

    def test_stalled_course_loading_is_not_reported_complete(self):
        from fenbi_exporter.workflow import load_course_rows
        page = self.browser.new_page()
        page.set_content('''<app-episode-nodes><div class="episode-wrapper">
          <div class="title-wrapper"><div class="title" title="课时1">课时1</div></div>
          </div></app-episode-nodes>''')
        try:
            with self.assertRaisesRegex(RuntimeError, '课时加载不完整'):
                load_course_rows(page, 2, timeout=200)
        finally:
            page.close()

    def test_live_dom_contract(self):
        page = self.browser.new_page()
        page.set_content('''<header>练习 13分 总用时 51秒</header><div>共计 2题</div>
          <div class="resizable-container"><div class="left"><p>给定资料原文</p></div><div class="right">
          <app-ti><div class="ti-container correct"><div class="title" id="title-0-0-0"><div class="title-index">1</div>
          <li apptooltip="标记"><svg class="active"></svg></li><li apptooltip="收藏"><svg class="active"></svg></li></div>
          <app-question-choice><app-format-html><p>材料<strong>重点</strong></p><img src="https://example.test/a.png"><p>后文</p></app-format-html>
          <ul class="choice-radios"><li><div class="input-radio">A</div></li><li><div class="input-radio correct">B</div></li></ul></app-question-choice>
          <span class="correct-answer">B</span><section id="section-solution-q1"><p>解析</p></section></div></app-ti></div></div>
          <app-ti><div class="ti-container wrong"><div class="title"><div class="title-index">2.</div></div>
          <app-question-choice><div class="input-radio correctLost">A</div><div class="input-radio wrong">D</div></app-question-choice></div></app-ti>
          <div class="answer-btn-container"><button class="answer-btn correct collected">1</button><div class="mark"></div><div class="collect"></div></div>
          <div class="answer-btn-container"><button class="answer-btn wrong">2</button></div>''')
        record = page.evaluate(SCRIPT.read_text('utf-8'))
        self.assertEqual(len(record['questions']), 2)
        one, two = record['questions']
        self.assertEqual(one['user_answer'], 'B')
        self.assertEqual(two['user_answer'], 'D')
        self.assertEqual(one['card'], {'marked': True, 'collected': True})
        self.assertEqual(two['card'], {'marked': False, 'collected': False})
        self.assertTrue(any(b['type'] == 'image' for b in one['blocks']))
        self.assertEqual(record['expected_count'], 2)
        self.assertEqual(one['blocks'][0]['text'], '给定资料原文')
        self.assertIn('总用时', record['summary'])
        self.assertIn('51秒', record['summary'])
        page.close()

    def test_lazy_image_and_formula_retain_original_order(self):
        page = self.browser.new_page()
        page.set_content('''<app-ti><span class="title-index">1</span><div class="ti-content">
          <p>题干</p><img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///w==" data-src="https://example.test/question.png">
          <span class="katex"><annotation encoding="application/x-tex">x^2</annotation></span><p>解析</p></div></app-ti>''')
        blocks = page.evaluate(SCRIPT.read_text('utf-8'))['questions'][0]['blocks']
        self.assertEqual(blocks[1]['src'], 'https://example.test/question.png')
        self.assertLess(next(i for i,b in enumerate(blocks) if b.get('type')=='image'), next(i for i,b in enumerate(blocks) if '$x^2$' in b.get('text','')))
        page.close()

    def test_route_discovery_does_not_wait_for_slow_optional_images(self):
        page = self.browser.new_page()
        pending = []
        page.route('https://example.test/slow.png', lambda route: pending.append(route))
        page.route('https://example.test/ti/exam/solution/a', lambda route: route.fulfill(
            content_type='text/html', body='<p>解析页面已就绪</p><img src="https://example.test/slow.png">'))
        try:
            page.goto('https://example.test/ti/exam/solution/a', wait_until='domcontentloaded')
            wait_for_solution(page, timeout=500)
        finally:
            page.wait_for_timeout(50)
            for route in pending:
                route.abort()
            page.close()

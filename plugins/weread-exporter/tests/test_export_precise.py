"""Offline regressions for rendered text, portable links, and UTF-8 exports."""
from __future__ import annotations

import asyncio
import builtins
from functools import partial
from contextlib import asynccontextmanager
import io
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from playwright.async_api import async_playwright
from test_plugin import load_exporter


READER_HTML = """<!doctype html><meta charset="utf-8">
<div class="readerCatalog_bookInfo_title_txt">本地样本</div>
<div class="renderTargetPageInfo_header_chapterTitle"></div>
<button class="readerControls_item catalog">目录</button>
<button class="readerCatalog_list_item">样本章节</button>
<canvas width="500" height="700"></canvas>
<script>
let position = 0;
let previous = START_PREVIOUS;
const title = document.querySelector('.renderTargetPageInfo_header_chapterTitle');
function draw() {
  title.textContent = previous ? '之前章节' : '样本章节';
  const ctx = document.querySelector('canvas').getContext('2d');
  ctx.clearRect(0, 0, 500, 700);
  const text = previous ? '之前章节正文。' : (position ? '第二页正文。' : '首屏正文。');
  Array.from(text).forEach((char, index) => ctx.fillText(char, 20 + index * 20, 50));
}
document.querySelector('.readerCatalog_list_item').onclick = () => {
  if (previous || position) { previous = false; position = 0; draw(); }
};
document.addEventListener('keydown', event => {
  if (event.key === 'ArrowRight' && position === 0) { position = 1; draw(); }
});
draw();
REPAINT_FIRST
</script>"""


class CanvasCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_screen_survives_resume_and_catalog_navigation(self):
        await self.check_first_screen(repaint=False)

    async def test_repainted_first_screen_is_exported_once(self):
        await self.check_first_screen(repaint=True)

    async def test_auxiliary_canvas_does_not_hide_first_spread(self):
        await self.check_first_screen(repaint=False, auxiliary=True)

    async def check_first_screen(self, *, repaint, auxiliary=False):
        exporter = load_exporter()
        real_sleep = asyncio.sleep

        async def fast_sleep(_seconds):
            await real_sleep(0)

        async with async_playwright() as playwright:
            for goto_first, start_previous in ((False, False), (True, False), (True, True)):
                with self.subTest(goto_first=goto_first, start_previous=start_previous):
                    with tempfile.TemporaryDirectory() as temp:
                        root = Path(temp)
                        md_dir, raw_dir = root / 'chapters', root / 'raw'
                        md_dir.mkdir()
                        raw_dir.mkdir()
                        catalog = root / '_catalog.json'
                        catalog.write_text(json.dumps(['样本章节'], ensure_ascii=False), encoding='utf-8')
                        html = (READER_HTML.replace('START_PREVIOUS', str(start_previous).lower())
                                .replace('REPAINT_FIRST', 'draw();' if repaint else ''))
                        if auxiliary:
                            html = html.replace('<canvas width="500" height="700"></canvas>',
                                                '<canvas width="500" height="700"></canvas>'
                                                '<canvas id="right" width="500" height="700" style="position:absolute;left:600px;top:100px"></canvas>')
                            html = html.replace('let position = 0;', """
                                const auxiliary = document.createElement('canvas');
                                auxiliary.getContext('2d').fillText('测量文本', 20, 50);
                                let position = 0;
                            """)
                            html = html.replace("  const text = previous", """
                                const right = document.querySelector('#right').getContext('2d');
                                right.clearRect(0, 0, 500, 700);
                                if (!previous && !position) right.fillText('右页正文。', 20, 50);
                                const text = previous""")

                        async def launch(_profile, **kwargs):
                            kwargs['headless'] = True
                            context = await playwright.chromium.launch_persistent_context(
                                str(root / 'profile'), **kwargs)

                            async def serve(route):
                                await route.fulfill(content_type='text/html; charset=utf-8',
                                                    body=html if '/reader/' in route.request.url else '<html>已登录</html>')

                            await context.route('**/*', serve)
                            return context

                        @asynccontextmanager
                        async def local_playwright():
                            yield SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch))

                        with patch.object(exporter, 'open', partial(builtins.open, encoding='utf-8'), create=True), \
                             patch.object(exporter, 'async_playwright', local_playwright), \
                             patch.object(exporter, 'asyncio', SimpleNamespace(sleep=fast_sleep)), \
                             patch.object(exporter, 'print', create=True):
                            result = await exporter.run_session('local-sample', str(md_dir), str(raw_dir),
                                                                1, set(), goto_first=goto_first,
                                                                catalog_path=str(catalog))
                        self.assertTrue(result[-1])
                        body = (md_dir / '0001.md').read_text(encoding='utf-8')
                        self.assertEqual(body.count('首屏正文。'), 1)
                        self.assertEqual(body.count('第二页正文。'), 1)
                        self.assertLess(body.index('首屏正文。'), body.index('第二页正文。'))
                        self.assertNotIn('之前章节正文。', body)
                        right_text = '右页正文。\n\n' if auxiliary else ''
                        self.assertEqual(body, '# 样本章节\n\n\n首屏正文。\n\n' + right_text + '第二页正文。\n')


class CanvasRepaintTests(unittest.IsolatedAsyncioTestCase):
    async def test_repaint_is_canvas_local_and_preserves_spread_order(self):
        exporter = load_exporter()
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.set_content('<canvas id="left" width="500" height="700"></canvas>'
                                       '<canvas id="right" width="500" height="700"></canvas>')
                await page.evaluate(exporter.CANVAS_HOOK)
                await page.evaluate("""() => {
                    const left = document.querySelector('#left').getContext('2d');
                    const right = document.querySelector('#right').getContext('2d');
                    left.fillText('旧', 20, 50);
                    // Identical text/coordinates on different canvases must survive.
                    right.fillText('同', 20, 50);
                    left.clearRect(0, 0, 500, 700);
                    left.fillText('同', 20, 50);
                    left.fillText('同', 40, 50);
                }""")
                chars = await page.evaluate('() => window.__wr_chars')
                rects = await page.evaluate(exporter.CANVAS_RECTS_JS)
                blocks = exporter.build_page_blocks(chars, [], rects, set())
                self.assertEqual(blocks, [{'type': 'text', 'text': '同同'},
                                          {'type': 'text', 'text': '同'}])
                self.assertEqual(await page.evaluate('() => window.__wr_count()'), 3)
                # Catalog no-repaint restoration must retain canvas ownership.
                await page.evaluate("""() => {
                    const snapshot = window.__wr_chars;
                    window.__wr_reset();
                    window.__wr_chars = snapshot;
                    const left = document.querySelector('#left').getContext('2d');
                    left.scale(2, 2);
                    left.clearRect(0, 0, 250, 350);
                    left.fillText('新', 10, 25);
                }""")
                chars = await page.evaluate('() => window.__wr_chars')
                blocks = exporter.build_page_blocks(chars, [], rects, set())
                self.assertEqual(blocks, [{'type': 'text', 'text': '新'},
                                          {'type': 'text', 'text': '同'}])
            finally:
                await browser.close()


class CanvasSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_selection_at_capture_excludes_helpers_and_tracks_canvas_identity(self):
        exporter = load_exporter()
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page(viewport={'width': 1200, 'height': 900})
                await page.set_content('<div id="host"></div>')
                await page.evaluate(exporter.CANVAS_HOOK)
                await page.evaluate("""() => {
                    function make(id, text, left, top, height = 700) {
                        const canvas = document.createElement('canvas');
                        canvas.id = id; canvas.width = 300; canvas.height = height;
                        canvas.style.cssText = `position:absolute;left:${left}px;top:${top}px`;
                        canvas.getContext('2d').fillText(text, 20, 50);
                        return canvas;
                    }
                    window.detached = make('detached', '离屏测量', 0, 0);
                    const hidden = make('hidden', '隐藏测量', 0, 0);
                    hidden.style.visibility = 'hidden';
                    document.body.append(hidden, make('outside', '视口外测量', -1000, 0),
                        make('small', '工具文字', 0, 0, 100));
                    // Paint before attaching and insert out of reading order.
                    document.body.append(make('right', '右页。', 700, 100),
                        make('left', '左页。', 0, 0));
                }""")
                chars = await page.evaluate('() => window.__wr_chars')
                rects = await page.evaluate(exporter.CANVAS_RECTS_JS)
                self.assertEqual([char['t'] for char in chars], ['左页。', '右页。'])
                self.assertEqual(await page.evaluate('() => window.__wr_count()'), 2)
                self.assertEqual(len(rects), 2)
                self.assertEqual([char['canvas_id'] for char in chars], [rect['canvas_id'] for rect in rects])
                # Left page has no text: right text must still use the right top offset.
                await page.evaluate("""() => {
                    document.querySelector('#left').getContext('2d').clearRect(0, 0, 300, 700);
                }""")
                chars = await page.evaluate('() => window.__wr_chars')
                images = [{'src': 'https://example.test/right.png', 'left': 720,
                           'top': 125, 'w': 100, 'h': 100}]
                blocks = exporter.build_page_blocks(chars, images, rects, set())
                self.assertEqual([block['type'] for block in blocks], ['img', 'text'])
                self.assertEqual(blocks[-1]['text'], '右页。')
                # A visible third canvas must not make the remaining groups disappear.
                await page.evaluate("""() => {
                    window.detached.style.left = '350px';
                    document.body.append(window.detached);
                    document.querySelector('#left').getContext('2d').fillText('左页。', 20, 50);
                }""")
                chars = await page.evaluate('() => window.__wr_chars')
                rects = await page.evaluate(exporter.CANVAS_RECTS_JS)
                blocks = exporter.build_page_blocks(chars, [], rects, set())
                self.assertEqual([block['text'] for block in blocks], ['左页。', '离屏测量', '右页。'])
                # Previously captured canvases stop contributing once detached.
                await page.evaluate("() => document.querySelector('#right').remove()")
                self.assertEqual(await page.evaluate('() => window.__wr_count()'), 2)
                self.assertEqual([char['t'] for char in await page.evaluate('() => window.__wr_chars')],
                                 ['左页。', '离屏测量'])
            finally:
                await browser.close()


class ExportFileTests(unittest.IsolatedAsyncioTestCase):
    async def run_export(self, root, *, strict_cp936=False, legacy_links=False):
        exporter = load_exporter()
        book_id = 'local-book'
        title, chapter = '测试书𠀀', '章节𠀀'
        blocks = [{'type': 'text', 'text': '正文𠀀。'},
                  {'type': 'img', 'src': 'https://example.test/figure.png'}]

        async def session(_book_id, md_dir, raw_dir, start_idx, seen_imgs, **kwargs):
            exporter.save_chapter(chapter, blocks, start_idx, md_dir, raw_dir)
            return title, '作者𠀀', 1, 4, start_idx, True

        def local_open(file, mode='r', *args, **kwargs):
            if 'b' not in mode and not args and 'encoding' not in kwargs:
                kwargs['encoding'] = 'cp936' if strict_cp936 else 'utf-8'
            return builtins.open(file, mode, *args, **kwargs)

        original_cwd = Path.cwd()
        try:
            os.chdir(root)
            with patch.object(exporter, 'run_session', side_effect=session), \
                 patch.object(exporter, 'open', side_effect=local_open, create=True), \
                 patch.object(exporter, 'print', create=True), \
                 patch.object(exporter.urllib.request, 'urlopen', side_effect=lambda *_args, **_kwargs: io.BytesIO(b'fixture-image' * 100)):
                await exporter.main(book_id)
                if legacy_links:
                    chapter_path = Path('output/local-book/chapters/0001.md')
                    chapter_path.write_text(chapter_path.read_text(encoding='utf-8').replace('../images/', 'images/'), encoding='utf-8')
                    await exporter.main(book_id)
                if strict_cp936:
                    self.assertEqual(exporter.get_last_chapter_title('output/local-book/chapters'), (chapter, 1))
                    catalog = Path('output/local-book/_catalog.json')
                    catalog.write_text(json.dumps([chapter], ensure_ascii=False), encoding='utf-8')
                    self.assertEqual(exporter.load_last_catalog_title(catalog), chapter)
                    # Exercise resume reads of existing raw JSON and chapter files.
                    await exporter.main(book_id)
        finally:
            os.chdir(original_cwd)
        return root / 'output' / book_id, root / 'output' / f'{title}.md'

    async def test_image_links_resolve_from_chapter_and_merged_document(self):
        with tempfile.TemporaryDirectory() as temp:
            book_dir, merged = await self.run_export(Path(temp))
            expected = (book_dir / 'images' / 'ch0001_img01.png').resolve()
            self.assertTrue(expected.is_file())
            for document in (book_dir / 'chapters' / '0001.md', merged):
                with self.subTest(document=document.name):
                    targets = re.findall(r'!\[图\]\(([^)]+)\)', document.read_text(encoding='utf-8'))
                    self.assertEqual(len(targets), 1)
                    self.assertNotIn('\\', targets[0])
                    self.assertEqual((document.parent / targets[0]).resolve(), expected)

    async def test_merge_rebases_legacy_generated_image_links(self):
        with tempfile.TemporaryDirectory() as temp:
            book_dir, merged = await self.run_export(Path(temp), legacy_links=True)
            body = merged.read_text(encoding='utf-8')
            self.assertIn('![图](local-book/images/ch0001_img01.png)', body)
            self.assertNotIn('![图](images/', body)
            self.assertNotIn('![图](../images/', body)

    async def test_export_and_resume_use_utf8_under_cp936_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            book_dir, merged = await self.run_export(Path(temp), strict_cp936=True)
            self.assertIn('正文𠀀。', merged.read_text(encoding='utf-8'))
            self.assertIn('章节𠀀', (book_dir / 'chapters' / '0001.md').read_text(encoding='utf-8'))
            self.assertEqual(json.loads((book_dir / 'raw' / '0001.json').read_text(encoding='utf-8'))['title'], '章节𠀀')

    async def test_catalog_write_uses_utf8_under_cp936_defaults(self):
        exporter = load_exporter()
        chapter = '章节𠀀'
        page = SimpleNamespace(click=AsyncMock(), evaluate=AsyncMock(), keyboard=SimpleNamespace(press=AsyncMock()))
        page.evaluate.side_effect = lambda script, *args: [chapter] if 'Array.from' in script else chapter if 'chapterTitle' in script else []
        item = SimpleNamespace(text_content=AsyncMock(return_value=chapter), click=AsyncMock())
        page.locator = lambda _selector: SimpleNamespace(first=item)
        real_open = builtins.open

        def cp936_open(file, mode='r', *args, **kwargs):
            if 'b' not in mode and not args and 'encoding' not in kwargs:
                kwargs['encoding'] = 'cp936'
            return real_open(file, mode, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / 'catalog.json'
            with patch.object(exporter, 'open', side_effect=cp936_open, create=True), \
                 patch.object(exporter, 'asyncio', SimpleNamespace(sleep=AsyncMock())), \
                 patch.object(exporter, 'print', create=True):
                await exporter.goto_first_chapter(page, catalog)
            self.assertEqual(json.loads(catalog.read_text(encoding='utf-8')), [chapter])


if __name__ == '__main__':
    unittest.main()

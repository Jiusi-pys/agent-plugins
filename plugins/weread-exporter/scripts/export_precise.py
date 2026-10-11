#!/usr/bin/env python3
"""
微信读书导出 — 精确图文版 v3

逐页捕获：每翻一页，抓当前视口内的 canvas 文字 + 视口内图片，
按屏幕 y 坐标把文字行和图片交错排序，图片精确落在对应段落之间。
双页拆分(左页→右页)，按章节切分，自动续传，卡住重开。
"""
import asyncio
import hashlib
import json
import os
import re
import sys
import urllib.request

from playwright.async_api import async_playwright

USER_DATA_DIR = os.path.join("cache", "browser_profile")

CANVAS_HOOK = """
(function() {
    // Track the current drawing of each canvas, not all historical fillText calls.
    const canvases = new Map();
    function stateFor(canvas) {
        if (!canvases.has(canvas))
            canvases.set(canvas, {canvas, id: canvases.size, chars: []});
        return canvases.get(canvas);
    }
    window.__wr_snapshot = function() {
        // Select at capture time: reader canvases may be painted before attachment.
        const visible = Array.from(document.querySelectorAll('canvas')).map(canvas => {
            const rect = canvas.getBoundingClientRect();
            return {canvas, rect};
        }).filter(({canvas, rect}) => canvas.isConnected && rect.height > 300 &&
            rect.width > 0 && rect.bottom > 0 && rect.top < window.innerHeight &&
            rect.right > 0 && rect.left < window.innerWidth &&
            canvas.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}))
          .sort((a, b) => a.rect.left - b.rect.left || a.rect.top - b.rect.top);
        const chars = [], rects = [];
        for (const {canvas, rect} of visible) {
            const state = stateFor(canvas);
            chars.push(...state.chars);
            rects.push({canvas_id: state.id, top: rect.top, left: rect.left,
                        w: Math.round(rect.width), h: Math.round(rect.height)});
        }
        return {chars, rects};
    };
    window.__wr_reset = function() {
        for (const state of canvases.values()) state.chars = [];
    };
    Object.defineProperty(window, '__wr_chars', {
        configurable: true,
        get() {
            return window.__wr_snapshot().chars;
        },
        set(chars) {
            // Restore catalog snapshots without losing ownership of each drawing.
            window.__wr_reset();
            const byId = new Map(Array.from(canvases.values(), state => [state.id, state]));
            for (const char of chars) {
                const state = byId.get(char.canvas_id);
                if (state) state.chars.push(char);
            }
        }
    });
    window.__wr_count = function() {
        return window.__wr_snapshot().chars.length;
    };
    const origFill = CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText = function(text, x, y) {
        const result = origFill.apply(this, arguments);
        if (text && text.trim()) {
            const state = stateFor(this.canvas);
            state.chars.push({t: text, x: Math.round(x*10)/10,
                              y: Math.round(y*10)/10, canvas_id: state.id});
        }
        return result;
    };
    const origClear = CanvasRenderingContext2D.prototype.clearRect;
    CanvasRenderingContext2D.prototype.clearRect = function(x, y, w, h) {
        const result = origClear.apply(this, arguments);
        const matrix = this.getTransform();
        // A full bitmap clear invalidates only this canvas. Account for DPR scaling.
        if (matrix.b === 0 && matrix.c === 0) {
            const x1 = matrix.a * x + matrix.e, x2 = matrix.a * (x + w) + matrix.e;
            const y1 = matrix.d * y + matrix.f, y2 = matrix.d * (y + h) + matrix.f;
            if (Math.min(x1, x2) <= 0 && Math.max(x1, x2) >= this.canvas.width &&
                Math.min(y1, y2) <= 0 && Math.max(y1, y2) >= this.canvas.height)
                stateFor(this.canvas).chars = [];
        }
        return result;
    };
})();
"""

# 当前视口内可见的书籍插图，带屏幕坐标
VIEWPORT_IMGS_JS = """
() => {
    const H = window.innerHeight, W = window.innerWidth, out = [];
    document.querySelectorAll('img[class*="wr_readerImage"]').forEach(i => {
        const src = i.src || i.getAttribute('data-src') || '';
        if (!src.includes('res.weread.qq.com/wrepub')) return;
        const r = i.getBoundingClientRect();
        if (r.width > 40 && r.height > 40 && r.bottom > 0 && r.top < H &&
            r.right > 0 && r.left < W &&
            getComputedStyle(i).visibility !== 'hidden' &&
            getComputedStyle(i).display !== 'none') {
            out.push({src, top: Math.round(r.top), left: Math.round(r.left),
                      w: i.naturalWidth||i.width, h: i.naturalHeight||i.height});
        }
    });
    return out;
}
"""

# 与文字捕获使用同一组可见 reader canvas 及其身份和屏幕位置
CANVAS_RECTS_JS = """
() => window.__wr_snapshot().rects
"""

MEASURE_RE = re.compile(r'^[a-zA-Z0-9`~!@#$%^&*()\-_=+\[\]{}|;:\',<.>/?\\"\s]+$')
SENTENCE_END = set("。！？；：」）】》…—")


def split_spread(chars):
    """双页拆分：返回 [左页chars, 右页chars] 或 [单页chars]"""
    if chars and all("canvas_id" in char for char in chars):
        pages = {}
        for char in chars:
            pages.setdefault(char["canvas_id"], []).append(char)
        return list(pages.values())
    if len(chars) < 20:
        return [chars]
    singles = [(i, c) for i, c in enumerate(chars) if len(c["t"]) == 1]
    if len(singles) < 10:
        return [chars]
    for j in range(1, len(singles)):
        if singles[j - 1][1]["y"] > 400 and singles[j][1]["y"] < 200:
            return [chars[:singles[j][0]], chars[singles[j][0]:]]
    return [chars]


def chars_to_lines(chars):
    """把单页字符按 y 分行，返回 [{y, text}]（未合并段落）"""
    real = [c for c in chars if len(c["t"]) == 1 or not MEASURE_RE.match(c["t"])]
    if not real:
        return []
    rows = {}
    for c in real:
        y_key = round(c["y"] / 3) * 3
        rows.setdefault(y_key, []).append(c)
    lines = []
    for yk in sorted(rows):
        line = "".join(c["t"] for c in sorted(rows[yk], key=lambda c: c["x"]))
        if line.strip():
            lines.append({"y": yk, "text": line.strip()})
    return lines


def build_page_blocks(chars, images, canvas_rects, seen_imgs):
    """把一次渲染(可能双页)拆成有序块列表: [{type:'text'/'img', ...}]
       文字行和图片按屏幕 y 交错；左页整页在前，右页在后。"""
    blocks = []
    pages = split_spread(chars)

    # 判定左右 canvas
    rects = sorted(canvas_rects, key=lambda r: r["left"])
    left_rect = rects[0] if rects else {"top": 0, "left": 0}
    right_rect = rects[1] if len(rects) > 1 else left_rect
    mid_x = (left_rect["left"] + right_rect["left"]) / 2 + 180 if len(rects) > 1 else 99999

    # 图片按左右分组
    left_imgs = [im for im in images if im["left"] < mid_x]
    right_imgs = [im for im in images if im["left"] >= mid_x]

    def emit_page(page_chars, page_rect, page_imgs):
        lines = chars_to_lines(page_chars)
        items = []
        for ln in lines:
            items.append(("text", page_rect["top"] + ln["y"], ln["text"]))
        for im in page_imgs:
            if im["src"] in seen_imgs:
                continue
            items.append(("img", im["top"], im))
        items.sort(key=lambda t: t[1])
        for typ, _y, payload in items:
            if typ == "text":
                blocks.append({"type": "text", "text": payload})
            else:
                seen_imgs.add(payload["src"])
                blocks.append({"type": "img", "src": payload["src"],
                                "w": payload["w"], "h": payload["h"]})

    if rects and all("canvas_id" in rect for rect in rects):
        # Match by identity, including blank canvases and more than two visible pages.
        chars_by_canvas = {}
        for char in chars:
            chars_by_canvas.setdefault(char["canvas_id"], []).append(char)
        images_by_canvas = [[] for _ in rects]
        for image in images:
            nearest = min(range(len(rects)), key=lambda index: max(
                rects[index]["left"] - image["left"],
                image["left"] - rects[index]["left"] - rects[index]["w"],
                0,
            ))
            images_by_canvas[nearest].append(image)
        for rect, page_images in zip(rects, images_by_canvas):
            emit_page(chars_by_canvas.get(rect["canvas_id"], []), rect, page_images)
    elif len(pages) > 2:
        raise ValueError("More than two canvas groups require canvas identity in rectangles")
    elif len(pages) == 2:
        emit_page(pages[0], left_rect, left_imgs)
        emit_page(pages[1], right_rect, right_imgs)
    else:
        # 单页：图片全归这页，仍按 y 排
        emit_page(pages[0], left_rect, left_imgs + right_imgs)
    return blocks


def img_filename(url, ch_idx, seq):
    ext = "jpg"
    m = re.search(r'\.(jpg|jpeg|png|gif|webp)', url.lower())
    if m:
        ext = m.group(1).replace("jpeg", "jpg")
    return f"ch{ch_idx:04d}_img{seq:02d}.{ext}"


def render_chapter_md(ch_title, blocks, ch_idx, image_prefix="images"):
    """把有序块渲染成 Markdown：文字行合并成段落，图片就地插入"""
    out = [f"# {ch_title}\n"]
    para = []
    img_records = []
    img_seq = 0

    def flush_para():
        nonlocal para
        if not para:
            return
        # 合并 canvas 断行为自然段：上一行不以句末标点结尾则接续
        merged = []
        for line in para:
            if line == ch_title:
                continue
            if merged and merged[-1] and merged[-1][-1] not in SENTENCE_END:
                merged[-1] += line
            else:
                merged.append(line)
        for m in merged:
            if m.strip():
                out.append(m.strip())
        para = []

    for b in blocks:
        if b["type"] == "text":
            para.append(b["text"])
        else:
            flush_para()
            img_seq += 1
            fname = img_filename(b["src"], ch_idx, img_seq)
            out.append(f"![图]({image_prefix}/{fname})")
            img_records.append({"url": b["src"], "file": fname})
    flush_para()

    body = "\n\n".join(out) + "\n"
    return body, img_records


async def wait_stable(page, prev_count, timeout=8):
    """等页面渲染稳定，返回稳定后的字符数"""
    last = -1
    for _ in range(int(timeout / 0.5)):
        c = await page.evaluate("() => window.__wr_count()")
        if c == last:
            return c
        last = c
        await asyncio.sleep(0.5)
    return last


def get_last_chapter_title(md_dir):
    if not os.path.exists(md_dir):
        return None, 0
    files = sorted(f for f in os.listdir(md_dir) if f.endswith(".md"))
    if not files:
        return None, 0
    idx = int(files[-1].replace(".md", ""))
    with open(os.path.join(md_dir, files[-1]), encoding="utf-8") as f:
        title = f.readline().strip().replace("# ", "")
    return title, idx


def load_last_catalog_title(catalog_path):
    try:
        with open(catalog_path, encoding="utf-8") as f:
            titles = json.load(f)
        return titles[-1] if titles else ""
    except Exception:
        return ""


async def _title(page):
    return await page.evaluate(
        "() => document.querySelector('.renderTargetPageInfo_header_chapterTitle')?.textContent?.trim() || ''")


async def fetch_book_title(page):
    info = await page.evaluate("""() => {
        const title = document.querySelector('.readerCatalog_bookInfo_title_txt, .bookInfo_right_header_title')
            ?.textContent?.trim() || document.title.replace(/-.*$/, '').trim();
        const author = document.querySelector('.readerCatalog_bookInfo_author, .bookInfo_author a')
            ?.textContent?.trim() || '';
        return {title, author};
    }""")
    return info.get("title", "未知"), info.get("author", "")


async def goto_first_chapter(page, catalog_path=None):
    first_title = ""
    try:
        await page.click("button.readerControls_item.catalog", timeout=5000)
        await asyncio.sleep(1.5)
        titles = await page.evaluate("""() => Array.from(
            document.querySelectorAll('.readerCatalog_list_item')).map(el => el.textContent.trim())""")
        if titles and catalog_path:
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump(titles, f, ensure_ascii=False)
        await page.evaluate("""() => {
            const sc = document.querySelector('.readerCatalog_list_scroll_area, [class*="readerCatalog_list_scroll"]');
            if (sc) sc.scrollTop = 0;
        }""")
        await asyncio.sleep(1)
        item = page.locator(".readerCatalog_list_item").first
        first_title = (await item.text_content() or "").strip()
        previous_title = await _title(page)
        previous_chars = await page.evaluate("() => window.__wr_chars")
        await page.evaluate("() => window.__wr_reset()")
        try:
            await item.click(timeout=4000)
            await asyncio.sleep(3)
        finally:
            # Clicking the current chapter may not repaint its canvas.
            if (await page.evaluate("() => window.__wr_count()") == 0
                    and await _title(page) == previous_title):
                await page.evaluate("chars => { window.__wr_chars = chars; }", previous_chars)
        try:
            await page.click("button.readerControls_item.catalog", timeout=2000)
        except Exception:
            await page.keyboard.press("Escape")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"  ⚠️  目录跳转异常: {e}")
    print(f"  ✅ 已跳到全书开头，当前:「{await _title(page)}」(点击首项「{first_title}」)")


def save_chapter(ch_title, blocks, ch_idx, md_dir, raw_dir):
    image_dir = os.path.join(os.path.dirname(md_dir), "images")
    image_prefix = os.path.relpath(image_dir, md_dir).replace(os.sep, "/")
    body, img_records = render_chapter_md(ch_title, blocks, ch_idx, image_prefix)
    text_len = sum(len(b["text"]) for b in blocks if b["type"] == "text")
    if text_len == 0 and not img_records:
        return 0, []
    with open(os.path.join(md_dir, f"{ch_idx:04d}.md"), "w", encoding="utf-8") as f:
        f.write(body)
    with open(os.path.join(raw_dir, f"{ch_idx:04d}.json"), "w", encoding="utf-8") as f:
        json.dump({"title": ch_title, "images": img_records, "text_len": text_len},
                  f, ensure_ascii=False)
    return text_len, img_records


async def run_session(book_id, md_dir, raw_dir, start_idx, seen_imgs,
                      goto_first=False, catalog_path=None):
    reached_end = False
    last_cat_title = load_last_catalog_title(catalog_path) if catalog_path else ""
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=False, viewport={"width": 1200, "height": 900},
            args=["--disable-blink-features=AutomationControlled"])

        login_page = await ctx.new_page()
        await login_page.goto("https://weread.qq.com/web/shelf", timeout=30000)
        await asyncio.sleep(3)
        if "login" in login_page.url.lower():
            print("\n  ⚠️  请扫码登录微信读书")
            for _ in range(120):
                await asyncio.sleep(5)
                if "login" not in login_page.url.lower():
                    print("  ✅ 登录成功"); break
            else:
                await login_page.close(); await ctx.close()
                return "", "", 0, 0, start_idx, False
        else:
            print("  ✅ 已登录")
        await login_page.close()

        page = await ctx.new_page()
        await page.add_init_script(CANVAS_HOOK)
        print("\n  打开阅读器...")
        await page.goto(f"https://weread.qq.com/web/reader/{book_id}",
                        wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

        book_title, book_author = await fetch_book_title(page)
        if goto_first:
            await goto_first_chapter(page, catalog_path)
            last_cat_title = load_last_catalog_title(catalog_path)

        await page.mouse.click(600, 450)
        await asyncio.sleep(0.5)

        current_chapter = await _title(page)
        print(f"  📖 {book_title} — {book_author}")
        print(f"  会话开始:「{current_chapter}」\n")

        ch_idx = start_idx
        ch_blocks = []
        total_chars = total_imgs = 0
        chapters_this_session = 0
        stale = 0
        page_num = 0

        async def capture_current_page():
            """抓当前页的有序块，累加到 ch_blocks；返回是否有新内容"""
            await asyncio.sleep(0.3)
            snapshot = await page.evaluate("() => window.__wr_snapshot()")
            chars, rects = snapshot["chars"], snapshot["rects"]
            imgs = await page.evaluate(VIEWPORT_IMGS_JS)
            before = len(ch_blocks)
            new_blocks = build_page_blocks(chars, imgs, rects, seen_imgs)
            # 文字去重：同一页可能重复捕获，按文本行内容去重
            for b in new_blocks:
                if b["type"] == "text":
                    if ch_blocks and ch_blocks[-1].get("type") == "text" and ch_blocks[-1]["text"] == b["text"]:
                        continue
                ch_blocks.append(b)
            return len(ch_blocks) > before

        # 首页已由导航绘制，保留捕获结果；等待本身不会触发重绘。
        await wait_stable(page, 0)
        await capture_current_page()

        while True:
            await page.evaluate("() => window.__wr_reset()")
            await page.mouse.click(600, 450)
            await page.keyboard.press("ArrowRight")
            await asyncio.sleep(1.0)
            await wait_stable(page, 0)

            new_chapter = await _title(page)
            if new_chapter and new_chapter != current_chapter:
                # 章节切换：保存上一章
                n, imgs = save_chapter(current_chapter, ch_blocks, ch_idx, md_dir, raw_dir)
                total_chars += n; total_imgs += len(imgs)
                note = f" +{len(imgs)}图" if imgs else ""
                print(f"  [{ch_idx:4d}] {current_chapter[:32]:32s} {n:6d}字 ({page_num}页){note}")
                is_last = bool(last_cat_title and current_chapter == last_cat_title)
                ch_idx += 1
                chapters_this_session += 1
                ch_blocks = []
                current_chapter = new_chapter
                page_num = 0
                stale = 0
                await capture_current_page()
                if is_last:
                    reached_end = True
                    # 再存这最后一章
                    break
                continue

            got_new = await capture_current_page()
            if not got_new:
                stale += 1
                if stale >= 10:
                    n, imgs = save_chapter(current_chapter, ch_blocks, ch_idx, md_dir, raw_dir)
                    total_chars += n; total_imgs += len(imgs)
                    note = f" +{len(imgs)}图" if imgs else ""
                    if last_cat_title and current_chapter == last_cat_title:
                        reached_end = True; note += " [全书末尾]"
                    print(f"  [{ch_idx:4d}] {current_chapter[:32]:32s} {n:6d}字 ({page_num}页){note}")
                    break
            else:
                stale = 0
            page_num += 1

        # reached_end 时把最后一章存下
        if reached_end and ch_blocks:
            n, imgs = save_chapter(current_chapter, ch_blocks, ch_idx, md_dir, raw_dir)
            if n or imgs:
                total_chars += n; total_imgs += len(imgs)
                print(f"  [{ch_idx:4d}] {current_chapter[:32]:32s} {n:6d}字 [末章]")
                chapters_this_session += 1

        await page.close(); await ctx.close()
        return book_title, book_author, chapters_this_session, total_chars, ch_idx, reached_end


def download_all_images(raw_dir, img_dir):
    os.makedirs(img_dir, exist_ok=True)
    tasks = []
    for jf in sorted(os.listdir(raw_dir)):
        if jf.endswith(".json"):
            with open(os.path.join(raw_dir, jf), encoding="utf-8") as source:
                images = json.load(source).get("images", [])
            for img in images:
                tasks.append((img["url"], img["file"]))
    if not tasks:
        print("  (无图片)"); return 0
    print(f"\n  下载 {len(tasks)} 张图片...")
    ok = 0
    for url, fname in tasks:
        fp = os.path.join(img_dir, fname)
        if os.path.exists(fp) and os.path.getsize(fp) > 1000:
            ok += 1; continue
        try:
            req = urllib.request.Request(url, headers={
                "Referer": "https://weread.qq.com/", "User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=20).read()
            if len(raw) > 500:
                with open(fp, "wb") as image_file:
                    image_file.write(raw)
                ok += 1
                if ok % 20 == 0:
                    print(f"    {ok}/{len(tasks)}...")
        except Exception as e:
            print(f"    ⚠️  {fname} 失败: {e}")
    print(f"  ✅ 图片下载完成 {ok}/{len(tasks)}")
    return ok


async def main(book_id):
    print("=" * 60)
    print("  weread-exporter — 精确图文导出 v3")
    print("=" * 60)
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    book_dir = os.path.join("output", book_id)
    md_dir = os.path.join(book_dir, "chapters")
    raw_dir = os.path.join(book_dir, "raw")
    img_dir = os.path.join(book_dir, "images")
    for d in (md_dir, raw_dir, img_dir):
        os.makedirs(d, exist_ok=True)

    seen_imgs = set()
    for jf in os.listdir(raw_dir):
        if jf.endswith(".json"):
            with open(os.path.join(raw_dir, jf), encoding="utf-8") as source:
                images = json.load(source).get("images", [])
            for img in images:
                seen_imgs.add(img["url"])

    catalog_path = os.path.join(book_dir, "_catalog.json")
    book_title = book_author = ""
    session = 0
    while True:
        session += 1
        last_title, last_idx = get_last_chapter_title(md_dir)
        start_idx = last_idx + 1 if last_idx > 0 else 1
        print(f"\n--- 会话 {session} ---")
        print(f"  上次: {last_title or '(无)'}, 编号: {last_idx}")
        goto_first = (session == 1 and last_idx == 0)
        title, author, added, chars_added, end_idx, reached_end = await run_session(
            book_id, md_dir, raw_dir, start_idx, seen_imgs,
            goto_first=goto_first, catalog_path=catalog_path)
        if title: book_title = title
        if author: book_author = author
        print(f"\n  本次: +{added} 章, +{chars_added:,} 字")
        if reached_end:
            print("\n  ✅ 已到全书最后一章，导出完成。"); break
        if added == 0:
            print("\n  无新章节，导出完成。"); break
        print("  3 秒后自动重开继续..."); await asyncio.sleep(3)

    download_all_images(raw_dir, img_dir)

    total_files = sorted(f for f in os.listdir(md_dir) if f.endswith(".md"))
    img_count = len([f for f in os.listdir(img_dir) if not f.startswith(".")])
    if not book_title: book_title = book_id
    safe = re.sub(r'[<>:"/\\|?*]', '_', book_title)
    merged = os.path.join("output", f"{safe}.md")
    merged_image_prefix = os.path.relpath(img_dir, os.path.dirname(merged)).replace(os.sep, "/")
    with open(merged, "w", encoding="utf-8") as out:
        out.write(f"# {book_title}\n\n**{book_author}**\n\n---\n\n")
        for fn in total_files:
            with open(os.path.join(md_dir, fn), encoding="utf-8") as chapter_file:
                body = chapter_file.read()
            # Rebase generated image links, including chapters from older exports.
            body = re.sub(
                r"(!\[图\]\()(?:\.\./)?images/([^\)\r\n]+)(\))",
                lambda match: f"{match[1]}{merged_image_prefix}/{match[2]}{match[3]}",
                body,
            )
            out.write(body)
            out.write("\n\n---\n\n")
    print(f"\n{'=' * 60}")
    print(f"  ✅ 全书导出完成!  📖 {book_title} — {book_author}")
    print(f"  📄 {len(total_files)} 章, {os.path.getsize(merged):,} bytes,  🖼 {img_count} 张图")
    print(f"  📦 {merged}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python export_precise.py <book_url_or_id>"); sys.exit(1)
    raw = sys.argv[1].strip().rstrip("/")
    book_id = raw.split("/")[-1] if "weread.qq.com" in raw else raw
    print(f"  Book ID: {book_id}")
    asyncio.run(main(book_id))

# WeRead Exporter

Codex plugin for exporting WeRead books that you are authorized to read to Markdown, with inline illustrations retained in reading order.

## Install

```powershell
codex plugin marketplace add .
codex plugin add weread-exporter@jiusi-agent-plugins
```

## Usage

Ask Codex to export a WeRead reader URL or book ID, and include a dedicated output directory. The plugin will guide the local setup and run:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
python scripts/export_precise.py <weread-reader-url-or-book-id>
```

On first use, the browser window prompts you to sign in or scan the WeRead QR code. Credentials are never requested, handled, or stored by the plugin. The browser profile and generated `cache/` and `output/` directories belong in your chosen working directory, not the plugin installation directory.

Use this only for books you are authorized to read, for personal study or backup. Do not use it to bypass access controls or distribute copyrighted content.

## Development

2026-10-11: all 19 exporter tests passed on US Ubuntu / Python 3.12.3 with real headless Chromium (38.888 seconds, no skips). The three review fixes and the additional image-only/identical-page regression were first reproduced as failing tests, fixed, and independently reviewed. Full-repository US results were 279 passed and 8 conversion-engine skips; all 8 passed separately on Windows. Evidence: repository `docs/reviews/2026-10-11-plugin-us-full-suite.md`. Live WeRead accounts were not tested.

```powershell
python -m pip install -r ./plugins/weread-exporter/requirements.txt
python -m playwright install chromium
python -m unittest discover -s ./plugins/weread-exporter/tests -v
```

The regression suite uses headless Chromium with locally supplied pages and mocked image downloads; it does not require an account or contact the live reader. It checks first-screen capture (including full-canvas clear/repaint and catalog navigation without a repaint), independent canvas capture in left-to-right page order, helper-canvas filtering at capture time (detached, hidden, outside the viewport, or below the reader height threshold), canvas identity matching with blank pages and more than two visible pages, image links resolved from both output locations, and UTF-8 export/resume under a simulated cp936 default.

It also covers whole-word ASCII, numbers and formulas drawn on visible canvases; repeated illustration references across pages and chapters; duplicate observations at one position; and stalled captures. A session that stops without confirming the book's end exits with code 1 when it makes no chapter progress. Its chapter fragments and raw records remain available, while an existing merged book is preserved. Only confirmed completion publishes the merged document and returns code 0.

Canvas paint revisions distinguish actual clears/redraws from resetting the exporter's capture buffer. Regressions include transitions to an image-only page with the same illustration and consecutive pages with identical text and images.

Text outputs use UTF-8. Chapter files in `output/<book-id>/chapters/` reference `../images/...`; the merged `output/<title>.md` references `<book-id>/images/...`. Existing exports with missing first-screen text must be exported again into a fresh output directory. Legacy cp936 files are not automatically converted; preserve them separately before starting a fresh export.

Use the `weread-export` skill after installing the plugin locally.

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

```powershell
python -m pip install -r ./plugins/weread-exporter/requirements.txt
python -m playwright install chromium
python -m unittest discover -s ./plugins/weread-exporter/tests -v
```

The regression suite uses headless Chromium with locally supplied pages and mocked image downloads; it does not require an account or contact the live reader. It checks first-screen capture (including full-canvas clear/repaint and catalog navigation without a repaint), independent canvas capture in left-to-right page order, helper-canvas filtering at capture time (detached, hidden, outside the viewport, or below the reader height threshold), canvas identity matching with blank pages and more than two visible pages, image links resolved from both output locations, and UTF-8 export/resume under a simulated cp936 default.

Text outputs use UTF-8. Chapter files in `output/<book-id>/chapters/` reference `../images/...`; the merged `output/<title>.md` references `<book-id>/images/...`. Existing exports with missing first-screen text must be exported again into a fresh output directory. Legacy cp936 files are not automatically converted; preserve them separately before starting a fresh export.

Use the `weread-export` skill after installing the plugin locally.

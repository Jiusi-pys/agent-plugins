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
python -m unittest discover -s ./plugins/weread-exporter/tests -v
```

Use the `weread-export` skill after installing the plugin locally.

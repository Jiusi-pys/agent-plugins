---
name: weread-export
description: Export a WeRead reader URL or book ID that the user is authorized to read to Markdown with inline illustrations. Use when the user asks to export, back up, or save their own legally accessible WeRead book.
---

# WeRead export

Use this workflow only for a book that the user is authorized to read. The output is for the user's personal study or backup use. Do not help distribute exported copyrighted content, bypass access controls, or process a book the user cannot access.

## Prerequisites

1. Confirm the user supplied a WeRead reader URL or book ID and an output location.
2. Install the bundled Python dependency from the plugin root:

   ```powershell
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

3. Run in a dedicated working directory. The exporter creates `cache/` and `output/` relative to the current directory; never use the plugin installation directory for user data.

## Export

From the plugin root, invoke the bundled script with the supplied URL or ID:

```powershell
python scripts/export_precise.py <weread-reader-url-or-book-id>
```

On first run, a Chromium window asks the user to sign in or scan the WeRead QR code. Do not request, handle, or store the user's credentials. The browser profile is retained in the chosen working directory for later authorized runs.

The exporter writes chapters, image records, downloaded images, and a merged Markdown file under `output/`. It automatically resumes from saved chapters after an interruption.

## Download images separately

If a prior export already produced `output/<book-id>/raw/*.json`, download or retry images without rerunning page capture:

```powershell
python scripts/download_images.py <weread-reader-url-or-book-id>
```

## Verify results

Check that `output/<book-id>/chapters/` contains Markdown files and that the merged Markdown file exists directly under `output/`. Report missing images or page-access restrictions plainly; do not attempt to circumvent the platform's restrictions.

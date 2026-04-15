#!/usr/bin/env python3
# codex-file-meta: begin
# relative_path: "skills/translate-web-to-chinese/scripts/translate_site.py"
# language: "python"
# summary: "Python module defining `build_arg_parser`, `main`, `translated_outputs_exist`, and `run_single_page_translation`."
# symbols: ["build_arg_parser", "main", "translated_outputs_exist", "run_single_page_translation", "build_replacements", "to_root_relative"]
# generated_by: "codebase-frontmatter-summary"
# codex-file-meta: end

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional

from site_common import (
    ensure_directory,
    load_json,
    relative_href,
    render_relations,
    rewrite_translated_content,
    save_json,
)

DEFAULT_TRANSLATOR_SCRIPT = (
    Path(__file__).resolve().parents[2] / "translate-url-to-chinese" / "scripts" / "translate_url.py"
)
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_MODEL_REASONING_EFFORT = "high"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate a crawled site into Simplified Chinese by calling the single-page translator iteratively."
    )
    parser.add_argument("--manifest", required=True, help="Path to crawl manifest.json")
    parser.add_argument("--output-dir", required=True, help="Directory for translated outputs")
    parser.add_argument(
        "--backend",
        default="sdk",
        choices=["sdk", "mock"],
        help="Single-page translation backend. Defaults to Codex SDK. 'mock' is for smoke tests.",
    )
    parser.add_argument(
        "--translator-script",
        default=str(DEFAULT_TRANSLATOR_SCRIPT),
        help="Path to the single-page translator script.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Codex model name. Defaults to gpt-5.4-mini.",
    )
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_MODEL_REASONING_EFFORT,
        choices=["minimal", "low", "medium", "high", "xhigh"],
        help="Codex reasoning effort. Defaults to high.",
    )
    parser.add_argument("--resume", action="store_true", help="Skip pages that are already translated.")
    parser.add_argument("--max-pages", type=int, help="Limit the number of translated pages.")
    parser.add_argument(
        "--working-dir",
        default=str(Path.cwd()),
        help="Working directory passed to Codex. Defaults to the current directory.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    source_manifest_path = Path(args.manifest).resolve()
    source_manifest = load_json(source_manifest_path)
    output_dir = Path(args.output_dir).resolve()
    pages_dir = output_dir / "pages"
    ensure_directory(pages_dir)

    translated_manifest = copy.deepcopy(source_manifest)
    translated_manifest["language"] = "zh-CN"
    translated_manifest["source_manifest"] = str(source_manifest_path)

    prior_manifest_path = output_dir / "manifest.json"
    prior_pages = {}
    if args.resume and prior_manifest_path.exists():
        prior_manifest = load_json(prior_manifest_path)
        prior_pages = {page["url"]: page for page in prior_manifest.get("pages", [])}

    page_map = {page["url"]: page for page in translated_manifest["pages"]}
    translated = 0
    translator_script = Path(args.translator_script).resolve()

    for page in translated_manifest["pages"]:
        if args.max_pages is not None and translated >= args.max_pages:
            break

        prior_page = prior_pages.get(page["url"])
        if args.resume and prior_page:
            page.update({key: value for key, value in prior_page.items() if key.startswith("translated_")})
            if translated_outputs_exist(output_dir, page):
                translated += 1
                continue

        raw_html_path = source_manifest_path.parent / page["raw_html_path"]
        page_output_dir = pages_dir / page["slug"]

        result = run_single_page_translation(
            translator_script=translator_script,
            page=page,
            raw_html_path=raw_html_path,
            page_output_dir=page_output_dir,
            backend=args.backend,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            working_dir=Path(args.working_dir).resolve(),
        )

        if result.get("translated_html_path"):
            html_rel = to_root_relative(output_dir, page_output_dir / result["translated_html_path"])
            html_path = output_dir / html_rel
            html_replacements = build_replacements(page, page_map, output_dir, html_path, "html")
            html_text = html_path.read_text(encoding="utf-8")
            html_path.write_text(
                rewrite_translated_content(html_text, html_replacements, "html"),
                encoding="utf-8",
            )
            page["translated_html_path"] = html_rel

        if result.get("translated_markdown_path"):
            markdown_rel = to_root_relative(
                output_dir, page_output_dir / result["translated_markdown_path"]
            )
            markdown_path = output_dir / markdown_rel
            md_replacements = build_replacements(page, page_map, output_dir, markdown_path, "md")
            markdown_text = markdown_path.read_text(encoding="utf-8")
            markdown_path.write_text(
                rewrite_translated_content(markdown_text, md_replacements, "md"),
                encoding="utf-8",
            )
            page["translated_markdown_path"] = markdown_rel

        page["translated_title"] = result["translated_title"]
        if result.get("translated_asset_dir"):
            page["translated_asset_dir"] = to_root_relative(
                output_dir, page_output_dir / result["translated_asset_dir"]
            )
        translated += 1

        save_json(prior_manifest_path, translated_manifest)

    markdown, html_doc = render_relations(translated_manifest)
    (output_dir / "relations.md").write_text(markdown, encoding="utf-8")
    (output_dir / "relations.html").write_text(html_doc, encoding="utf-8")
    save_json(prior_manifest_path, translated_manifest)

    print("Translated {} page(s) into {}".format(translated, output_dir))
    print("Manifest: {}".format(prior_manifest_path))
    return 0


def translated_outputs_exist(output_root: Path, page: Dict) -> bool:
    has_outputs = bool(page.get("translated_markdown_path") or page.get("translated_html_path"))
    markdown_ok = not page.get("translated_markdown_path") or (output_root / page["translated_markdown_path"]).exists()
    html_ok = not page.get("translated_html_path") or (output_root / page["translated_html_path"]).exists()
    return has_outputs and markdown_ok and html_ok


def run_single_page_translation(
    translator_script: Path,
    page: Dict,
    raw_html_path: Path,
    page_output_dir: Path,
    backend: str,
    model: Optional[str],
    reasoning_effort: str,
    working_dir: Path,
) -> Dict[str, str]:
    if not translator_script.exists():
        raise FileNotFoundError("Single-page translator not found: {}".format(translator_script))

    command = [
        "python3",
        str(translator_script),
        "--url",
        page["url"],
        "--output-dir",
        str(page_output_dir),
        "--output-format",
        "both",
        "--backend",
        backend,
        "--model",
        model or DEFAULT_MODEL,
        "--reasoning-effort",
        reasoning_effort,
        "--working-dir",
        str(working_dir),
        "--raw-html-file",
        str(raw_html_path),
        "--title",
        page["title"],
    ]
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Single-page translation failed for {} with code {}:\n{}\n{}".format(
                page["url"],
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Single-page translator returned non-JSON output for {}:\n{}\n{}".format(
                page["url"], completed.stdout, completed.stderr
            )
        ) from exc


def build_replacements(
    page: Dict, page_map: Dict[str, Dict], output_root: Path, output_path: Path, fmt: str
) -> Dict[str, str]:
    replacements: Dict[str, str] = {}
    for link in page.get("link_rewrites", []):
        target = page_map.get(link["normalized_url"])
        if not target:
            continue
        target_rel = target.get(
            "translated_html_path" if fmt == "html" else "translated_markdown_path"
        )
        if not target_rel:
            extension = ".html" if fmt == "html" else ".md"
            target_rel = "pages/{}/index{}".format(target["slug"], extension)
        target_abs = output_root / target_rel
        replacements[link["normalized_url"]] = relative_href(output_path, target_abs)
        replacements[link["original_href"]] = relative_href(output_path, target_abs)
    return replacements


def to_root_relative(output_root: Path, path: Path) -> str:
    return path.relative_to(output_root).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

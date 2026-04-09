#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

from codex_mcp_client import (
    DEFAULT_BACKEND,
    DEFAULT_MODEL,
    DEFAULT_MODEL_REASONING_EFFORT,
    run_translation_via_codex_mcp,
)
from site_common import (
    ensure_directory,
    load_json,
    relative_href,
    render_relations,
    rewrite_translated_content,
    save_json,
)

TRANSLATION_SCHEMA = {
    "type": "object",
    "properties": {
        "translated_title": {"type": "string"},
        "translated_html": {"type": "string"},
        "translated_markdown": {"type": "string"},
    },
    "required": ["translated_title", "translated_html", "translated_markdown"],
    "additionalProperties": False,
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Translate crawled pages into Simplified Chinese.")
    parser.add_argument("--manifest", required=True, help="Path to crawl manifest.json")
    parser.add_argument("--output-dir", required=True, help="Directory for translated outputs")
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        choices=["auto", "mcp", "sdk", "exec", "mock"],
        help="Translation backend. Defaults to Codex MCP. 'auto' tries MCP, then the SDK bridge, then codex exec.",
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
    parser.add_argument(
        "--sdk-bridge",
        default=str(Path(__file__).with_name("codex_sdk_bridge.mjs")),
        help="Path to the optional Node.js SDK bridge script.",
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
    source_manifest = load_json(Path(args.manifest))
    output_dir = Path(args.output_dir).resolve()
    pages_dir = output_dir / "pages"
    ensure_directory(pages_dir)

    translated_manifest = copy.deepcopy(source_manifest)
    translated_manifest["language"] = "zh-CN"
    translated_manifest["source_manifest"] = str(Path(args.manifest).resolve())

    prior_manifest_path = output_dir / "manifest.json"
    prior_pages = {}
    if args.resume and prior_manifest_path.exists():
        prior_manifest = load_json(prior_manifest_path)
        prior_pages = {page["url"]: page for page in prior_manifest.get("pages", [])}

    page_map = {page["url"]: page for page in translated_manifest["pages"]}
    translated = 0

    backend = args.backend
    for page in translated_manifest["pages"]:
        if args.max_pages is not None and translated >= args.max_pages:
            break

        prior_page = prior_pages.get(page["url"])
        if args.resume and prior_page:
            page.update(
                {
                    key: value
                    for key, value in prior_page.items()
                    if key.startswith("translated_")
                }
            )
            if page.get("translated_markdown_path") and page.get("translated_html_path"):
                translated += 1
                continue

        raw_html = (
            Path(args.manifest).resolve().parent / page["raw_html_path"]
        ).read_text(encoding="utf-8")

        translation = translate_page(
            page=page,
            raw_html=raw_html,
            backend=backend,
            sdk_bridge=Path(args.sdk_bridge),
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            working_dir=Path(args.working_dir).resolve(),
        )
        if backend == "auto" and translation.get("_backend_used"):
            backend = translation["_backend_used"]

        html_path = pages_dir / (page["slug"] + ".html")
        markdown_path = pages_dir / (page["slug"] + ".md")
        ensure_directory(html_path.parent)
        ensure_directory(markdown_path.parent)

        html_replacements = build_replacements(page, page_map, output_dir, html_path, "html")
        md_replacements = build_replacements(page, page_map, output_dir, markdown_path, "md")

        translated_html = rewrite_translated_content(
            translation["translated_html"], html_replacements, "html"
        )
        translated_markdown = rewrite_translated_content(
            translation["translated_markdown"], md_replacements, "md"
        )

        html_path.write_text(translated_html, encoding="utf-8")
        markdown_path.write_text(translated_markdown, encoding="utf-8")

        page["translated_title"] = translation["translated_title"]
        page["translated_html_path"] = str(html_path.relative_to(output_dir))
        page["translated_markdown_path"] = str(markdown_path.relative_to(output_dir))
        translated += 1

        save_json(prior_manifest_path, translated_manifest)

    markdown, html_doc = render_relations(translated_manifest)
    (output_dir / "relations.md").write_text(markdown, encoding="utf-8")
    (output_dir / "relations.html").write_text(html_doc, encoding="utf-8")
    save_json(prior_manifest_path, translated_manifest)

    print("Translated {} page(s) into {}".format(translated, output_dir))
    print("Manifest: {}".format(prior_manifest_path))
    return 0


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
            target_rel = "pages/{}{}".format(target["slug"], extension)
        target_abs = output_root / target_rel
        replacements[link["normalized_url"]] = relative_href(output_path, target_abs)
        replacements[link["original_href"]] = relative_href(output_path, target_abs)
    return replacements


def translate_page(
    page: Dict,
    raw_html: str,
    backend: str,
    sdk_bridge: Path,
    model: Optional[str],
    reasoning_effort: str,
    working_dir: Path,
) -> Dict[str, str]:
    prompt = build_prompt(page, raw_html)
    if backend == "mock":
        return mock_translation(page, raw_html)
    if backend == "mcp":
        return run_codex_mcp(prompt, working_dir, model, reasoning_effort)
    if backend == "auto":
        try:
            response = run_codex_mcp(prompt, working_dir, model, reasoning_effort)
            response["_backend_used"] = "mcp"
            return response
        except Exception:
            pass
    if backend == "sdk":
        return run_sdk_bridge(prompt, sdk_bridge, working_dir, model, reasoning_effort)
    if backend == "exec":
        return run_codex_exec(prompt, working_dir, model, reasoning_effort)
    try:
        response = run_sdk_bridge(prompt, sdk_bridge, working_dir, model, reasoning_effort)
        response["_backend_used"] = "sdk"
        return response
    except Exception:
        response = run_codex_exec(prompt, working_dir, model, reasoning_effort)
        response["_backend_used"] = "exec"
        return response


def build_prompt(page: Dict, raw_html: str) -> str:
    return (
        "Translate the following English documentation page into Simplified Chinese.\n"
        "Requirements:\n"
        "1. Keep all code blocks, inline code, URLs, href values, and image sources unchanged.\n"
        "2. Preserve the overall HTML structure.\n"
        "3. Produce natural Simplified Chinese for prose text.\n"
        "4. Return only JSON that matches the provided schema.\n"
        "5. Do not add commentary.\n\n"
        "Page URL:\n"
        f"{page['url']}\n\n"
        "Page title:\n"
        f"{page['title']}\n\n"
        "Raw HTML:\n"
        f"{raw_html}\n"
    )


def clean_child_env() -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    return env


def run_codex_exec(
    prompt: str, working_dir: Path, model: Optional[str], reasoning_effort: str
) -> Dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="translate-web-") as temp_dir:
        schema_path = Path(temp_dir) / "schema.json"
        output_path = Path(temp_dir) / "final-message.json"
        schema_path.write_text(json.dumps(TRANSLATION_SCHEMA), encoding="utf-8")

        command = [
            "codex",
            "-c",
            'model_reasoning_effort="{}"'.format(reasoning_effort),
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "-C",
            str(working_dir),
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
        ]
        if model:
            command.extend(["-m", model])

        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            env=clean_child_env(),
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "codex exec failed with code {}:\n{}\n{}".format(
                    completed.returncode, completed.stdout, completed.stderr
                )
            )
        return json.loads(output_path.read_text(encoding="utf-8"))


def run_sdk_bridge(
    prompt: str,
    sdk_bridge: Path,
    working_dir: Path,
    model: Optional[str],
    reasoning_effort: str,
) -> Dict[str, str]:
    if not sdk_bridge.exists():
        raise FileNotFoundError("SDK bridge not found: {}".format(sdk_bridge))

    payload = {
        "prompt": prompt,
        "outputSchema": TRANSLATION_SCHEMA,
        "workingDirectory": str(working_dir),
        "model": model,
        "reasoningEffort": reasoning_effort,
    }
    completed = subprocess.run(
        ["node", str(sdk_bridge)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=clean_child_env(),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "SDK bridge failed with code {}:\n{}\n{}".format(
                completed.returncode, completed.stdout, completed.stderr
            )
        )
    response = json.loads(completed.stdout)
    return response["finalResponse"]


def run_codex_mcp(
    prompt: str, working_dir: Path, model: Optional[str], reasoning_effort: str
) -> Dict[str, str]:
    return run_translation_via_codex_mcp(
        prompt,
        working_dir=working_dir,
        model=model,
        reasoning_effort=reasoning_effort,
    )


def mock_translation(page: Dict, raw_html: str) -> Dict[str, str]:
    translated_title = "中文译文｜{}".format(page["title"])
    translated_html = raw_html.replace(page["title"], translated_title)
    translated_markdown = (
        "# {}\n\n"
        "这是一个离线 mock 译文，用来验证递归流程、链接重写和输出目录。\n\n"
        "原始地址：{}\n"
    ).format(translated_title, page["url"])
    return {
        "translated_title": translated_title,
        "translated_html": translated_html,
        "translated_markdown": translated_markdown,
    }


if __name__ == "__main__":
    raise SystemExit(main())

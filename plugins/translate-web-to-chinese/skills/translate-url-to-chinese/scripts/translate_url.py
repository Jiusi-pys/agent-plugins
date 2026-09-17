#!/usr/bin/env python3
# codex-file-meta: begin
# relative_path: "skills/translate-url-to-chinese/scripts/translate_url.py"
# language: "python"
# summary: "Python module defining `AssetReference`, `PageParser`, `build_arg_parser`, and `main`."
# symbols: ["AssetReference", "PageParser", "build_arg_parser", "main", "translate_page", "build_prompt", "clean_child_env", "run_sdk_bridge"]
# generated_by: "codebase-frontmatter-summary"
# codex-file-meta: end

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_BACKEND = "sdk"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_MODEL_REASONING_EFFORT = "high"
DEFAULT_USER_AGENT = (
    "translate-url-to-chinese/1.0 "
    "(Codex SDK page translator; +https://developers.openai.com/codex/sdk)"
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

HTML_ATTRIBUTE_LINK_RE = re.compile(
    r'(\b(?:href|src|action|poster|data-href|data-src)\s*=\s*)(["\'])(.*?)(\2)',
    re.IGNORECASE | re.DOTALL,
)
CSS_URL_RE = re.compile(r"url\(\s*(?P<quote>['\"]?)(?P<target>[^)'\"]+)(?P=quote)\s*\)")
TEXT_SUFFIXES = {".css", ".js", ".mjs", ".json", ".map", ".svg", ".txt", ".xml"}
LINK_ASSET_RELS = {
    "stylesheet",
    "icon",
    "shortcut",
    "apple-touch-icon",
    "manifest",
    "preload",
    "modulepreload",
}
LINK_ASSET_SUFFIX_RE = re.compile(
    r"\.(?:css|js|mjs|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|otf|map)(?:$|[?#])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AssetReference:
    original: str
    normalized_url: str


class PageParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.assets: List[AssetReference] = []
        self._in_title = False
        self._title_parts: List[str] = []

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self._title_parts if part.strip()).strip()

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_map = dict(attrs)
        tag_name = tag.lower()
        if tag_name == "title":
            self._in_title = True
            return

        if tag_name == "link":
            href = attrs_map.get("href")
            rel_tokens = {
                token.strip().lower()
                for token in (attrs_map.get("rel") or "").split()
                if token.strip()
            }
            if href and (
                rel_tokens.intersection(LINK_ASSET_RELS) or LINK_ASSET_SUFFIX_RE.search(href)
            ):
                self._record_asset(href)
            return

        for attr_name in ("src", "poster"):
            value = attrs_map.get(attr_name)
            if value and tag_name in {"script", "img", "source", "video", "audio", "track"}:
                self._record_asset(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    def _record_asset(self, value: str) -> None:
        if value.startswith("#"):
            return
        normalized = normalize_url(value, self.base_url)
        if not normalized:
            return
        reference = AssetReference(original=value, normalized_url=normalized)
        if reference not in self.assets:
            self.assets.append(reference)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate a single web page into Simplified Chinese Markdown or web output."
    )
    parser.add_argument("--url", required=True, help="Page URL to translate.")
    parser.add_argument("--output-dir", required=True, help="Directory for translated outputs.")
    parser.add_argument(
        "--output-format",
        default="both",
        choices=["markdown", "web", "both"],
        help="Write Markdown, localized web output, or both.",
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        choices=["sdk", "mock"],
        help="Translation backend. Defaults to Codex SDK. 'mock' is for smoke tests.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Codex model name.")
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_MODEL_REASONING_EFFORT,
        choices=["minimal", "low", "medium", "high", "xhigh"],
        help="Codex reasoning effort.",
    )
    parser.add_argument(
        "--sdk-bridge",
        default=str(Path(__file__).with_name("codex_sdk_bridge.mjs")),
        help="Path to the Node.js SDK bridge script.",
    )
    parser.add_argument(
        "--working-dir",
        default=str(Path.cwd()),
        help="Working directory passed to Codex. Defaults to the current directory.",
    )
    parser.add_argument(
        "--raw-html-file",
        help="Optional existing HTML file for the source page. Skips network fetch when provided.",
    )
    parser.add_argument("--title", help="Optional known page title.")
    parser.add_argument("--timeout", type=int, default=20, help="Per-request timeout in seconds.")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent value.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    page_url = normalize_url(args.url)
    if not page_url:
        raise SystemExit("Page URL must be http://, https://, or file://")

    output_dir = Path(args.output_dir).resolve()
    ensure_directory(output_dir)

    if args.raw_html_file:
        raw_html = Path(args.raw_html_file).resolve().read_text(encoding="utf-8")
        final_url = page_url
    else:
        final_url, _, raw_html = fetch_html(page_url, args.user_agent, args.timeout)

    discovered_title, _ = extract_page_metadata(raw_html, final_url)
    page_title = args.title or discovered_title or final_url

    translation = translate_page(
        page_url=final_url,
        page_title=page_title,
        raw_html=raw_html,
        backend=args.backend,
        sdk_bridge=Path(args.sdk_bridge),
        working_dir=Path(args.working_dir).resolve(),
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )

    result = {
        "url": final_url,
        "source_title": page_title,
        "translated_title": translation["translated_title"],
        "backend": args.backend,
        "output_format": args.output_format,
    }

    if args.output_format in {"markdown", "both"}:
        markdown_path = output_dir / "index.md"
        markdown_path.write_text(translation["translated_markdown"], encoding="utf-8")
        result["translated_markdown_path"] = str(markdown_path.relative_to(output_dir))

    if args.output_format in {"web", "both"}:
        html_path = output_dir / "index.html"
        assets_dir = output_dir / "assets"
        ensure_directory(assets_dir)
        asset_rewrites, copied_assets = copy_page_assets(
            raw_html=raw_html,
            page_url=final_url,
            html_output_path=html_path,
            assets_dir=assets_dir,
            user_agent=args.user_agent,
            timeout=args.timeout,
        )
        translated_html = rewrite_html_link_targets(translation["translated_html"], asset_rewrites)
        html_path.write_text(translated_html, encoding="utf-8")
        result["translated_html_path"] = str(html_path.relative_to(output_dir))
        result["translated_asset_dir"] = str(assets_dir.relative_to(output_dir))
        result["copied_asset_paths"] = copied_assets

    result_path = output_dir / "translation.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["result_path"] = str(result_path.relative_to(output_dir))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def translate_page(
    page_url: str,
    page_title: str,
    raw_html: str,
    backend: str,
    sdk_bridge: Path,
    working_dir: Path,
    model: Optional[str],
    reasoning_effort: str,
) -> Dict[str, str]:
    prompt = build_prompt(page_url, page_title, raw_html)
    if backend == "mock":
        return mock_translation(page_url, page_title, raw_html)
    return run_sdk_bridge(
        prompt=prompt,
        sdk_bridge=sdk_bridge,
        working_dir=working_dir,
        model=model,
        reasoning_effort=reasoning_effort,
    )


def build_prompt(page_url: str, page_title: str, raw_html: str) -> str:
    return (
        "Translate the following English documentation page into Simplified Chinese.\n"
        "Requirements:\n"
        "1. Keep code blocks, inline code, URLs, href values, src values, CSS selectors, JS identifiers, and asset filenames unchanged.\n"
        "2. Preserve the overall HTML structure.\n"
        "3. Translate prose, headings, button labels, and other user-facing text into natural Simplified Chinese.\n"
        "4. Return only JSON that matches the provided schema.\n"
        "5. Do not add commentary.\n\n"
        "Page URL:\n"
        f"{page_url}\n\n"
        "Page title:\n"
        f"{page_title}\n\n"
        "Raw HTML:\n"
        f"{raw_html}\n"
    )


def clean_child_env() -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    return env


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


def mock_translation(page_url: str, page_title: str, raw_html: str) -> Dict[str, str]:
    translated_title = "中文译文｜{}".format(page_title)
    translated_html = raw_html.replace(page_title, translated_title)
    translated_markdown = (
        "# {}\n\n"
        "这是一个离线 mock 译文，用来验证单页翻译流程和输出目录。\n\n"
        "原始地址：{}\n"
    ).format(translated_title, page_url)
    return {
        "translated_title": translated_title,
        "translated_html": translated_html,
        "translated_markdown": translated_markdown,
    }


def normalize_url(url: str, base_url: Optional[str] = None) -> Optional[str]:
    if base_url:
        url = urllib.parse.urljoin(base_url, url)

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in {"http", "https", "file"}:
        return None

    raw_path = parsed.path or "/"
    normalized_path = posixpath.normpath(raw_path)
    if not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path
    if raw_path.endswith("/") and normalized_path != "/":
        normalized_path += "/"

    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered_pairs = [
        (key, value)
        for key, value in query_pairs
        if not key.lower().startswith("utm_")
    ]
    query = urllib.parse.urlencode(filtered_pairs, doseq=True)

    return urllib.parse.urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            "",
            query,
            "",
        )
    )


def scope_prefix(root_url: str) -> str:
    parsed = urllib.parse.urlparse(root_url)
    path = parsed.path or "/"
    if path.endswith("/"):
        return path
    parent = posixpath.dirname(path)
    if not parent.startswith("/"):
        parent = "/" + parent
    if not parent.endswith("/"):
        parent += "/"
    return parent or "/"


def short_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def fetch_resource(url: str, user_agent: str, timeout: int) -> Tuple[str, str, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = normalize_url(response.geturl()) or url
        content_type = response.headers.get("Content-Type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read()
        return final_url, content_type, charset, body


def fetch_html(url: str, user_agent: str, timeout: int) -> Tuple[str, str, str]:
    final_url, content_type, charset, body = fetch_resource(url, user_agent, timeout)
    text = body.decode(charset, errors="replace")
    if "html" not in content_type.lower() and "<html" not in text.lower():
        raise ValueError("Response is not HTML")
    return final_url, content_type, text


def extract_page_metadata(html_text: str, page_url: str) -> Tuple[str, List[AssetReference]]:
    parser = PageParser(page_url)
    parser.feed(html_text)
    return parser.title or page_url, parser.assets


def copy_page_assets(
    raw_html: str,
    page_url: str,
    html_output_path: Path,
    assets_dir: Path,
    user_agent: str,
    timeout: int,
) -> Tuple[Dict[str, str], List[str]]:
    _, assets = extract_page_metadata(raw_html, page_url)
    cache: Dict[str, Path] = {}
    copied_assets: List[str] = []
    rewrites: Dict[str, str] = {}

    for asset in assets:
        local_path = copy_asset(
            asset_url=asset.normalized_url,
            page_url=page_url,
            assets_dir=assets_dir,
            user_agent=user_agent,
            timeout=timeout,
            cache=cache,
        )
        if not local_path:
            continue
        rel_target = relative_href(html_output_path, local_path)
        rewrites[asset.original] = rel_target
        rewrites[asset.normalized_url] = rel_target
        relative_asset_path = str(local_path.relative_to(html_output_path.parent))
        if relative_asset_path not in copied_assets:
            copied_assets.append(relative_asset_path)

    copied_assets.sort()
    return rewrites, copied_assets


def copy_asset(
    asset_url: str,
    page_url: str,
    assets_dir: Path,
    user_agent: str,
    timeout: int,
    cache: Dict[str, Path],
) -> Optional[Path]:
    cached = cache.get(asset_url)
    if cached:
        return cached
    if not same_origin(page_url, asset_url):
        return None

    final_url, content_type, charset, payload = fetch_resource(asset_url, user_agent, timeout)
    cached = cache.get(final_url)
    if cached:
        cache[asset_url] = cached
        return cached

    relative_asset_path = asset_output_relpath(final_url, page_url)
    local_path = assets_dir / relative_asset_path
    ensure_directory(local_path.parent)
    cache[asset_url] = local_path
    cache[final_url] = local_path

    if is_text_asset(local_path, content_type):
        text = payload.decode(charset, errors="replace")
        if is_css_asset(local_path, content_type):
            text = rewrite_css_urls(
                text=text,
                css_url=final_url,
                css_output_path=local_path,
                page_url=page_url,
                assets_dir=assets_dir,
                user_agent=user_agent,
                timeout=timeout,
                cache=cache,
            )
        local_path.write_text(text, encoding="utf-8")
    else:
        local_path.write_bytes(payload)

    return local_path


def rewrite_css_urls(
    text: str,
    css_url: str,
    css_output_path: Path,
    page_url: str,
    assets_dir: Path,
    user_agent: str,
    timeout: int,
    cache: Dict[str, Path],
) -> str:
    def replace(match: re.Match) -> str:
        quote = match.group("quote") or ""
        target = match.group("target").strip()
        if not target or target.startswith("data:") or target.startswith("#"):
            return match.group(0)
        normalized = normalize_url(target, css_url)
        if not normalized:
            return match.group(0)
        local_path = copy_asset(
            asset_url=normalized,
            page_url=page_url,
            assets_dir=assets_dir,
            user_agent=user_agent,
            timeout=timeout,
            cache=cache,
        )
        if not local_path:
            return match.group(0)
        relative_target = relative_href(css_output_path, local_path)
        return "url({}{})".format(quote, relative_target + quote)

    return CSS_URL_RE.sub(replace, text)


def asset_output_relpath(asset_url: str, page_url: str) -> str:
    parsed = urllib.parse.urlparse(asset_url)
    trim_prefix = scope_prefix(page_url)
    rel_path = parsed.path or "/"
    if trim_prefix and rel_path.startswith(trim_prefix):
        rel_path = rel_path[len(trim_prefix) :]
    else:
        rel_path = rel_path.lstrip("/")
    if not rel_path or rel_path.endswith("/"):
        rel_path = rel_path.rstrip("/") + "/index"
    rel_path = urllib.parse.unquote(rel_path).replace(" ", "-")
    rel_path = re.sub(r"[^A-Za-z0-9._/-]+", "-", rel_path)
    rel_path = re.sub(r"/{2,}", "/", rel_path).strip("/")
    rel_path = rel_path or short_id(asset_url)
    if parsed.query:
        stem, suffix = os.path.splitext(rel_path)
        rel_path = "{}--{}{}".format(stem, short_id(parsed.query), suffix)
    return rel_path


def same_origin(page_url: str, candidate_url: str) -> bool:
    page = urllib.parse.urlparse(page_url)
    candidate = urllib.parse.urlparse(candidate_url)
    return page.scheme == candidate.scheme and page.netloc == candidate.netloc


def is_css_asset(path: Path, content_type: str) -> bool:
    return path.suffix.lower() == ".css" or "text/css" in content_type.lower()


def is_text_asset(path: Path, content_type: str) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or content_type.startswith("text/")


def relative_href(from_file: Path, to_file: Path) -> str:
    return os.path.relpath(to_file, start=from_file.parent).replace(os.sep, "/")


def rewrite_html_link_targets(text: str, replacements: Dict[str, str]) -> str:
    if not replacements:
        return text

    def replace(match: re.Match) -> str:
        prefix, quote, value, _ = match.groups()
        return prefix + quote + replacements.get(value, value) + quote

    return HTML_ATTRIBUTE_LINK_RE.sub(replace, text)


if __name__ == "__main__":
    raise SystemExit(main())

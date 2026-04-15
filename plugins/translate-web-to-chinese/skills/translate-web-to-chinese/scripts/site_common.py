#!/usr/bin/env python3
# codex-file-meta: begin
# relative_path: "skills/translate-web-to-chinese/scripts/site_common.py"
# language: "python"
# summary: "Python module defining `normalize_url`, `scope_prefix`, `in_scope`, and `short_id`."
# symbols: ["normalize_url", "scope_prefix", "in_scope", "short_id", "slug_from_url", "ensure_directory", "save_json", "load_json"]
# generated_by: "codebase-frontmatter-summary"
# codex-file-meta: end

from __future__ import annotations

import hashlib
import html
import json
import os
import posixpath
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_USER_AGENT = (
    "translate-web-to-chinese/1.0 "
    "(Codex local crawler; +https://developers.openai.com/codex/sdk)"
)


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


def in_scope(url: str, root_url: str, restrict_path: bool = True) -> bool:
    candidate = urllib.parse.urlparse(url)
    root = urllib.parse.urlparse(root_url)
    if candidate.scheme != root.scheme or candidate.netloc != root.netloc:
        return False
    if not restrict_path:
        return True
    return candidate.path.startswith(scope_prefix(root_url))


def short_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def slug_from_url(url: str, trim_prefix: Optional[str] = None) -> str:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path or "/"
    if trim_prefix and path.startswith(trim_prefix):
        path = path[len(trim_prefix) :]
        if not path.startswith("/") and path:
            path = "/" + path
    if path.endswith("/"):
        path = path + "index"

    stem = urllib.parse.unquote(path).lstrip("/")
    if not stem:
        stem = "index"
    stem = re.sub(r"\.(html?|xhtml)$", "", stem, flags=re.IGNORECASE)
    stem = stem.replace(" ", "-")
    stem = re.sub(r"[^A-Za-z0-9._/-]+", "-", stem)
    stem = re.sub(r"/{2,}", "/", stem).strip("-/")
    stem = stem or "index"

    if parsed.query:
        stem += "--" + short_id(parsed.query)

    return stem


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, payload: Dict) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_html(url: str, user_agent: str, timeout: int) -> Tuple[str, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = normalize_url(response.geturl()) or url
        content_type = response.headers.get("Content-Type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        raw_body = response.read()
        body = raw_body.decode(charset, errors="replace")
        if "html" not in content_type.lower() and "<html" not in body.lower():
            raise ValueError("Response is not HTML")
        return final_url, content_type, body


@dataclass
class LinkRecord:
    href: str
    normalized_url: str


class MetadataParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: List[LinkRecord] = []
        self._in_title = False
        self._title_parts: List[str] = []

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self._title_parts if part.strip()).strip()

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_map = dict(attrs)
        if tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "a":
            href = attrs_map.get("href")
            if not href or href.startswith("#"):
                return
            normalized = normalize_url(href, self.base_url)
            if normalized:
                self.links.append(LinkRecord(href=href, normalized_url=normalized))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


def extract_metadata(html_text: str, page_url: str) -> Tuple[str, List[LinkRecord]]:
    parser = MetadataParser(page_url)
    parser.feed(html_text)
    return parser.title or page_url, parser.links


def relative_href(from_file: Path, to_file: Path) -> str:
    return os.path.relpath(to_file, start=from_file.parent).replace(os.sep, "/")


HTML_ATTRIBUTE_LINK_RE = re.compile(
    r'(\b(?:href|src|action|poster|data-href|data-src)\s*=\s*)(["\'])(.*?)(\2)',
    re.IGNORECASE | re.DOTALL,
)

MARKDOWN_CODE_RE = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`)")
MARKDOWN_LINK_RE = re.compile(r"(!?\[[^\]]+\])\(([^()\s]+)(\s+\"[^\"]*\")?\)")
MARKDOWN_REF_DEF_RE = re.compile(r"(^\s*\[[^\]]+\]:\s*)(\S+)(.*)$", re.MULTILINE)


def rewrite_html_link_targets(text: str, replacements: Dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        prefix, quote, value, _ = match.groups()
        return prefix + quote + replacements.get(value, value) + quote

    return HTML_ATTRIBUTE_LINK_RE.sub(replace, text)


def _rewrite_markdown_segment(text: str, replacements: Dict[str, str]) -> str:
    def replace_link(match: re.Match) -> str:
        prefix, url, suffix = match.groups()
        return "{}({}{})".format(prefix, replacements.get(url, url), suffix or "")

    text = MARKDOWN_LINK_RE.sub(replace_link, text)

    def replace_reference(match: re.Match) -> str:
        prefix, url, suffix = match.groups()
        return prefix + replacements.get(url, url) + suffix

    return MARKDOWN_REF_DEF_RE.sub(replace_reference, text)


def rewrite_markdown_link_targets(text: str, replacements: Dict[str, str]) -> str:
    parts = MARKDOWN_CODE_RE.split(text)
    for index, part in enumerate(parts):
        if not part or part.startswith("`") or part.startswith("~~~") or part.startswith("```"):
            continue
        parts[index] = _rewrite_markdown_segment(part, replacements)
    return "".join(parts)


def rewrite_translated_content(text: str, replacements: Dict[str, str], format_name: str) -> str:
    if not replacements:
        return text
    if format_name == "html":
        return rewrite_html_link_targets(text, replacements)
    if format_name == "md":
        return rewrite_markdown_link_targets(text, replacements)
    raise ValueError("Unsupported format: {}".format(format_name))


def sorted_pages(manifest: Dict) -> List[Dict]:
    return sorted(manifest["pages"], key=lambda item: (item["depth"], item["url"]))


def render_relations(manifest: Dict) -> Tuple[str, str]:
    page_map = {page["url"]: page for page in manifest["pages"]}
    title = "Translated Page Graph" if manifest.get("language") == "zh-CN" else "Page Graph"

    md_lines = [
        "# " + title,
        "",
        "- Root URL: `{}`".format(manifest["root_url"]),
        "- Page count: `{}`".format(len(manifest["pages"])),
        "- Scope prefix: `{}`".format(manifest.get("scope_prefix", "/")),
        "",
    ]

    rows = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <title>{}</title>".format(html.escape(title)),
        "  <style>",
        "    body { font-family: sans-serif; margin: 2rem; line-height: 1.5; }",
        "    table { border-collapse: collapse; width: 100%; }",
        "    th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; vertical-align: top; }",
        "    code { background: #f4f4f4; padding: 0.1rem 0.25rem; }",
        "    ul { margin: 0; padding-left: 1.2rem; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>{}</h1>".format(html.escape(title)),
        "  <p>Root URL: <code>{}</code></p>".format(html.escape(manifest["root_url"])),
        "  <p>Page count: <code>{}</code></p>".format(len(manifest["pages"])),
        "  <table>",
        "    <thead>",
        "      <tr><th>Page</th><th>Parents</th><th>Children</th><th>Outputs</th></tr>",
        "    </thead>",
        "    <tbody>",
    ]

    for page in sorted_pages(manifest):
        parents = [page_map[url] for url in page.get("referrers", []) if url in page_map]
        children = [page_map[url] for url in page.get("children", []) if url in page_map]

        md_lines.extend(
            [
                "## {}".format(page.get("translated_title") or page["title"]),
                "",
                "- Source URL: `{}`".format(page["url"]),
                "- Depth: `{}`".format(page["depth"]),
                "- Parents: {}".format(
                    ", ".join("`{}`".format(parent["url"]) for parent in parents) or "None"
                ),
                "- Children: {}".format(
                    ", ".join("`{}`".format(child["url"]) for child in children) or "None"
                ),
            ]
        )

        outputs = []
        if page.get("translated_markdown_path"):
            outputs.append("Markdown: `{}`".format(page["translated_markdown_path"]))
        if page.get("translated_html_path"):
            outputs.append("HTML: `{}`".format(page["translated_html_path"]))
        md_lines.append("- Outputs: {}".format(", ".join(outputs) or "Not translated yet"))
        md_lines.append("")

        output_cells = []
        if page.get("translated_markdown_path"):
            output_cells.append("<div><code>{}</code></div>".format(html.escape(page["translated_markdown_path"])))
        if page.get("translated_html_path"):
            output_cells.append("<div><code>{}</code></div>".format(html.escape(page["translated_html_path"])))
        if not output_cells:
            output_cells.append("<div>Not translated yet</div>")

        rows.extend(
            [
                "      <tr>",
                "        <td><strong>{}</strong><div><code>{}</code></div></td>".format(
                    html.escape(page.get("translated_title") or page["title"]),
                    html.escape(page["url"]),
                ),
                "        <td>{}</td>".format(_link_list_html(parents)),
                "        <td>{}</td>".format(_link_list_html(children)),
                "        <td>{}</td>".format("".join(output_cells)),
                "      </tr>",
            ]
        )

    rows.extend(["    </tbody>", "  </table>", "</body>", "</html>"])
    return "\n".join(md_lines).strip() + "\n", "\n".join(rows) + "\n"


def _link_list_html(pages: Iterable[Dict]) -> str:
    rendered = [
        "<li><strong>{}</strong><br><code>{}</code></li>".format(
            html.escape(page.get("translated_title") or page["title"]),
            html.escape(page["url"]),
        )
        for page in pages
    ]
    if not rendered:
        return "None"
    return "<ul>{}</ul>".format("".join(rendered))

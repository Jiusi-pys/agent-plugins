#!/usr/bin/env python3
# codex-file-meta: begin
# relative_path: "skills/translate-web-to-chinese/scripts/crawl_site.py"
# language: "python"
# summary: "Python module defining `build_arg_parser`, and `main`."
# symbols: ["build_arg_parser", "main"]
# generated_by: "codebase-frontmatter-summary"
# codex-file-meta: end

from __future__ import annotations

import argparse
import datetime as dt
from collections import deque
from pathlib import Path
from typing import Dict, Set

from site_common import (
    DEFAULT_USER_AGENT,
    ensure_directory,
    extract_metadata,
    fetch_html,
    in_scope,
    normalize_url,
    render_relations,
    save_json,
    scope_prefix,
    short_id,
    slug_from_url,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl a site and record page relations.")
    parser.add_argument("--url", required=True, help="Entrypoint page URL.")
    parser.add_argument("--output-dir", required=True, help="Directory for crawl artifacts.")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum number of pages to fetch.")
    parser.add_argument("--max-depth", type=int, default=3, help="Maximum recursion depth.")
    parser.add_argument("--timeout", type=int, default=20, help="Per-request timeout in seconds.")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent value.")
    parser.add_argument(
        "--allow-cross-path",
        action="store_true",
        help="Crawl the full origin instead of only the entrypoint path prefix.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    root_url = normalize_url(args.url)
    if not root_url:
        raise SystemExit("Entrypoint URL must be http://, https://, or file://")

    output_dir = Path(args.output_dir).resolve()
    raw_dir = output_dir / "raw"
    ensure_directory(raw_dir)
    active_scope_prefix = scope_prefix(root_url)

    queue = deque([(root_url, 0, None)])
    scheduled: Set[str] = {root_url}
    pages: Dict[str, Dict] = {}

    while queue and len(pages) < args.max_pages:
        current_url, depth, referrer = queue.popleft()
        existing = pages.get(current_url)
        if existing:
            if referrer and referrer not in existing["referrers"]:
                existing["referrers"].append(referrer)
            continue

        try:
            final_url, _, body = fetch_html(current_url, args.user_agent, args.timeout)
        except Exception as exc:
            print("Skipping {}: {}".format(current_url, exc))
            continue

        if not in_scope(final_url, root_url, restrict_path=not args.allow_cross_path):
            print("Skipping {} after redirect to {} outside crawl scope".format(current_url, final_url))
            continue

        title, links = extract_metadata(body, final_url)
        page_id = short_id(final_url)
        slug = slug_from_url(final_url, trim_prefix=active_scope_prefix)
        raw_rel_path = "raw/{}.html".format(page_id)
        (output_dir / raw_rel_path).write_text(body, encoding="utf-8")

        internal_children = []
        link_rewrites = []
        for link in links:
            if not in_scope(link.normalized_url, root_url, restrict_path=not args.allow_cross_path):
                continue
            link_rewrites.append(
                {
                    "original_href": link.href,
                    "normalized_url": link.normalized_url,
                }
            )
            if link.normalized_url not in internal_children:
                internal_children.append(link.normalized_url)

        pages[final_url] = {
            "page_id": page_id,
            "url": final_url,
            "title": title,
            "slug": slug,
            "depth": depth,
            "referrers": [referrer] if referrer else [],
            "children": internal_children,
            "link_rewrites": link_rewrites,
            "raw_html_path": raw_rel_path,
        }

        if depth >= args.max_depth:
            continue

        for child_url in internal_children:
            if child_url in scheduled:
                continue
            if len(scheduled) >= args.max_pages:
                break
            scheduled.add(child_url)
            queue.append((child_url, depth + 1, final_url))

    manifest = {
        "version": 1,
        "language": "en",
        "generated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "root_url": root_url,
        "scope_prefix": active_scope_prefix,
        "pages": list(pages.values()),
    }

    save_json(output_dir / "manifest.json", manifest)
    markdown, html_doc = render_relations(manifest)
    (output_dir / "relations.md").write_text(markdown, encoding="utf-8")
    (output_dir / "relations.html").write_text(html_doc, encoding="utf-8")

    print("Crawled {} page(s) into {}".format(len(manifest["pages"]), output_dir))
    print("Manifest: {}".format(output_dir / "manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from site_common import load_json, render_relations


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render markdown and HTML relation reports.")
    parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    parser.add_argument("--output-dir", required=True, help="Directory for rendered reports")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    manifest = load_json(Path(args.manifest))
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown, html_doc = render_relations(manifest)
    (output_dir / "relations.md").write_text(markdown, encoding="utf-8")
    (output_dir / "relations.html").write_text(html_doc, encoding="utf-8")
    print("Rendered relation reports into {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

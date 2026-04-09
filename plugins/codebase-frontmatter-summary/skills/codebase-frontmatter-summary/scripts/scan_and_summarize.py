#!/usr/bin/env python3
"""Scan a codebase bottom-up, add managed frontmatter to files, and write per-directory summaries."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from codex_backends import (
    DEFAULT_BACKEND,
    DEFAULT_MODEL,
    DEFAULT_MODEL_REASONING_EFFORT,
    run_json_task,
)

PLUGIN_NAME = "codebase-frontmatter-summary"
DEFAULT_SUMMARY_NAME = "SUMMARY.md"
FILE_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "symbols": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "symbols"],
    "additionalProperties": False,
}
DIRECTORY_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
    },
    "required": ["overview"],
    "additionalProperties": False,
}
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
}
DEFAULT_EXCLUDED_FILES = {
    ".DS_Store",
}
COMMENT_STYLE_BY_SUFFIX = {
    ".bash": "hash",
    ".c": "block",
    ".cc": "block",
    ".conf": "hash",
    ".cpp": "block",
    ".cs": "block",
    ".css": "block",
    ".go": "block",
    ".h": "block",
    ".hpp": "block",
    ".htm": "html",
    ".html": "html",
    ".ini": "hash",
    ".java": "block",
    ".js": "block",
    ".json5": "block",
    ".jsx": "block",
    ".kt": "block",
    ".kts": "block",
    ".lua": "line-dash",
    ".markdown": "html",
    ".md": "html",
    ".mdx": "html",
    ".php": "hash",
    ".pl": "hash",
    ".pm": "hash",
    ".properties": "hash",
    ".py": "hash",
    ".r": "hash",
    ".rb": "hash",
    ".rs": "block",
    ".scala": "block",
    ".sh": "hash",
    ".sql": "line-dash",
    ".svg": "html",
    ".swift": "block",
    ".toml": "hash",
    ".ts": "block",
    ".tsx": "block",
    ".xml": "html",
    ".yaml": "hash",
    ".yml": "hash",
    ".zsh": "hash",
}
COMMENT_STYLE_BY_NAME = {
    ".env": "hash",
    "dockerfile": "hash",
    "makefile": "hash",
}
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*[:=]", re.MULTILINE)
JS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:(?:async\s+)?function|class|interface|type|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
SHELL_FUNCTION_RE = re.compile(
    r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{",
    re.MULTILINE,
)
C_LIKE_SYMBOL_RE = re.compile(
    r"^\s*(?:class|struct|enum|interface)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
HEADING_RE = re.compile(r"^\s*#\s+(.+)$", re.MULTILINE)
HTML_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HTML_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
WORD_RE = re.compile(r"\s+")


@dataclass
class FileResult:
    path: Path
    rel_path: str
    language: str
    summary: str
    symbols: list[str]
    modified: bool
    skipped_reason: str | None


@dataclass
class DirectoryResult:
    path: Path
    rel_path: str
    file_results: list[FileResult]
    child_directories: list["DirectoryResult"]
    summary_path: Path
    summary_overview: str
    summary_written: bool


class SummaryGenerator:
    def __init__(
        self,
        *,
        backend: str,
        model: str,
        reasoning_effort: str,
        sdk_bridge: Path,
        working_dir: Path,
        file_max_chars: int,
        directory_max_chars: int,
    ) -> None:
        self.backend = backend
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.sdk_bridge = sdk_bridge
        self.working_dir = working_dir
        self.file_max_chars = file_max_chars
        self.directory_max_chars = directory_max_chars

    def summarize_file(self, rel_path: str, path: Path, language: str, content: str) -> tuple[str, list[str]]:
        if self.backend == "heuristic":
            return summarize_file_heuristic(path, content)

        prompt = build_file_summary_prompt(
            rel_path=rel_path,
            language=language,
            content=truncate_for_prompt(content, self.file_max_chars),
        )
        try:
            response = run_json_task(
                prompt,
                output_schema=FILE_SUMMARY_SCHEMA,
                backend=self.backend,
                sdk_bridge=self.sdk_bridge,
                working_dir=self.working_dir,
                model=self.model,
                reasoning_effort=self.reasoning_effort,
            )
            summary = normalize_sentence(str(response.get("summary", "")), max_length=180)
            symbols = sanitize_symbols(response.get("symbols"))
            if summary:
                return summary, symbols
        except Exception:
            if self.backend != "auto":
                raise
        return summarize_file_heuristic(path, content)

    def summarize_directory(
        self,
        rel_path: str,
        display_path: str,
        file_results: list[FileResult],
        child_directories: list[DirectoryResult],
    ) -> str:
        if self.backend == "heuristic":
            return build_directory_overview_heuristic(file_results, child_directories)

        prompt = build_directory_summary_prompt(
            rel_path=display_path,
            file_results=file_results,
            child_directories=child_directories,
            max_chars=self.directory_max_chars,
        )
        try:
            response = run_json_task(
                prompt,
                output_schema=DIRECTORY_SUMMARY_SCHEMA,
                backend=self.backend,
                sdk_bridge=self.sdk_bridge,
                working_dir=self.working_dir,
                model=self.model,
                reasoning_effort=self.reasoning_effort,
            )
            overview = normalize_sentence(str(response.get("overview", "")), max_length=280)
            if overview:
                return overview
        except Exception:
            if self.backend != "auto":
                raise
        return build_directory_overview_heuristic(file_results, child_directories)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Root directory to scan.")
    parser.add_argument(
        "--summary-name",
        default=DEFAULT_SUMMARY_NAME,
        help=f"Summary file name to write in each directory. Default: {DEFAULT_SUMMARY_NAME}",
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        choices=["auto", "mcp", "sdk", "exec", "heuristic"],
        help="Summary backend. Default: Codex MCP.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Codex model name. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_MODEL_REASONING_EFFORT,
        choices=["minimal", "low", "medium", "high", "xhigh"],
        help=f"Codex reasoning effort. Default: {DEFAULT_MODEL_REASONING_EFFORT}",
    )
    parser.add_argument(
        "--sdk-bridge",
        default=str(Path(__file__).with_name("codex_sdk_bridge.mjs")),
        help="Path to the optional Node.js Codex SDK bridge script.",
    )
    parser.add_argument(
        "--working-dir",
        default=str(Path.cwd()),
        help="Working directory passed to Codex. Defaults to the current directory.",
    )
    parser.add_argument(
        "--file-max-chars",
        type=int,
        default=12000,
        help="Maximum file content characters sent to Codex per file summary request.",
    )
    parser.add_argument(
        "--directory-max-chars",
        type=int,
        default=12000,
        help="Maximum directory child summary characters sent to Codex per directory request.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude. Can be passed multiple times.",
    )
    parser.add_argument(
        "--exclude-file",
        action="append",
        default=[],
        help="File name to exclude. Can be passed multiple times.",
    )
    parser.add_argument(
        "--unsafe-force-raw-frontmatter",
        action="store_true",
        help="Prepend raw frontmatter to text files that do not have a safe inline comment syntax.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write frontmatter and summary files. Without this flag the script only reports planned work.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    excluded_dirs = set(DEFAULT_EXCLUDED_DIRS) | set(args.exclude_dir)
    excluded_files = set(DEFAULT_EXCLUDED_FILES) | set(args.exclude_file) | {args.summary_name}
    summarizer = SummaryGenerator(
        backend=args.backend,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        sdk_bridge=Path(args.sdk_bridge).resolve(),
        working_dir=Path(args.working_dir).expanduser().resolve(),
        file_max_chars=args.file_max_chars,
        directory_max_chars=args.directory_max_chars,
    )

    result = process_directory(
        root=root,
        current=root,
        summary_name=args.summary_name,
        excluded_dirs=excluded_dirs,
        excluded_files=excluded_files,
        unsafe_force_raw=args.unsafe_force_raw_frontmatter,
        write=args.write,
        summarizer=summarizer,
    )

    totals = tally(result)
    mode = "write" if args.write else "preview"
    print(
        json.dumps(
            {
                "mode": mode,
                "backend": args.backend,
                "root": str(root),
                "directories": totals["directories"],
                "files": totals["files"],
                "modified_files": totals["modified_files"],
                "written_summaries": totals["written_summaries"],
                "skipped_files": totals["skipped_files"],
            },
            indent=2,
        )
    )
    return 0


def process_directory(
    *,
    root: Path,
    current: Path,
    summary_name: str,
    excluded_dirs: set[str],
    excluded_files: set[str],
    unsafe_force_raw: bool,
    write: bool,
    summarizer: SummaryGenerator,
) -> DirectoryResult:
    file_results: list[FileResult] = []
    child_directories: list[DirectoryResult] = []

    entries = sorted(current.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    for entry in entries:
        if entry.is_symlink():
            continue
        if entry.is_dir():
            if entry.name in excluded_dirs:
                continue
            child_directories.append(
                process_directory(
                    root=root,
                    current=entry,
                    summary_name=summary_name,
                    excluded_dirs=excluded_dirs,
                    excluded_files=excluded_files,
                    unsafe_force_raw=unsafe_force_raw,
                    write=write,
                    summarizer=summarizer,
                )
            )
            continue
        if not entry.is_file():
            continue
        if entry.name in excluded_files:
            continue
        file_results.append(
            process_file(
                root=root,
                path=entry,
                unsafe_force_raw=unsafe_force_raw,
                write=write,
                summarizer=summarizer,
            )
        )

    summary_path = current / summary_name
    rel_path = relative_directory_path(root, current)
    display_path = current.name if current == root else rel_path
    summary_overview = summarizer.summarize_directory(
        rel_path=rel_path,
        display_path=display_path,
        file_results=file_results,
        child_directories=child_directories,
    )
    summary_content = render_directory_summary(
        display_path=display_path,
        summary_overview=summary_overview,
        file_results=file_results,
        child_directories=child_directories,
    )
    summary_written = False
    if write:
        summary_written = write_text_if_changed(summary_path, summary_content)

    return DirectoryResult(
        path=current,
        rel_path=rel_path,
        file_results=file_results,
        child_directories=child_directories,
        summary_path=summary_path,
        summary_overview=summary_overview,
        summary_written=summary_written,
    )


def process_file(
    *,
    root: Path,
    path: Path,
    unsafe_force_raw: bool,
    write: bool,
    summarizer: SummaryGenerator,
) -> FileResult:
    raw_bytes = path.read_bytes()
    rel_path = path.relative_to(root).as_posix()
    if is_binary(raw_bytes):
        return FileResult(
            path=path,
            rel_path=rel_path,
            language=detect_language(path),
            summary=f"Binary file ({len(raw_bytes)} bytes).",
            symbols=[],
            modified=False,
            skipped_reason="binary file",
        )

    text = raw_bytes.decode("utf-8", errors="replace")
    style = detect_comment_style(path)
    if style is None and unsafe_force_raw:
        style = "raw"

    preamble, body = split_preamble(path, text)
    body = strip_managed_frontmatter(body, style) if style else body
    body = body.lstrip("\n")

    language = detect_language(path)
    summary, symbols = summarizer.summarize_file(rel_path, path, language, body)
    modified = False
    skipped_reason = None
    if style:
        metadata_block = render_frontmatter(
            style=style,
            rel_path=rel_path,
            language=language,
            summary=summary,
            symbols=symbols,
        )
        new_text = preamble + metadata_block + body
        if write:
            modified = write_text_if_changed(path, new_text)
    else:
        skipped_reason = "no safe frontmatter style"

    return FileResult(
        path=path,
        rel_path=rel_path,
        language=language,
        summary=summary,
        symbols=symbols,
        modified=modified,
        skipped_reason=skipped_reason,
    )


def split_preamble(path: Path, text: str) -> tuple[str, str]:
    prefix = ""
    body = text
    if body.startswith("\ufeff"):
        prefix = "\ufeff"
        body = body[1:]

    if body.startswith("#!"):
        shebang, remainder = split_first_line(body)
        prefix += shebang
        body = remainder

    suffix = path.suffix.lower()
    if suffix in MARKDOWN_SUFFIXES and body.startswith("---\n"):
        end = body.find("\n---\n", 4)
        if end != -1:
            end += len("\n---\n")
            prefix += body[:end]
            body = body[end:]

    for pattern in (r"^(<!DOCTYPE[^>]*>\s*\n?)", r"^(<\?xml[^>]*\?>\s*\n?)"):
        match = re.match(pattern, body, flags=re.IGNORECASE)
        if match:
            prefix += match.group(1)
            body = body[match.end() :]

    if path.suffix.lower() == ".php":
        match = re.match(r"^(<\?php\s*\n?)", body, flags=re.IGNORECASE)
        if match:
            prefix += match.group(1)
            body = body[match.end() :]

    return prefix, body


def strip_managed_frontmatter(body: str, style: str | None) -> str:
    if not style:
        return body
    start_marker, end_marker = frontmatter_markers(style)
    if not body.startswith(start_marker):
        return body
    end_index = body.find(end_marker)
    if end_index == -1:
        return body
    body = body[end_index + len(end_marker) :]
    return body.lstrip("\n")


def render_frontmatter(
    *,
    style: str,
    rel_path: str,
    language: str,
    summary: str,
    symbols: list[str],
) -> str:
    fields = [
        ("relative_path", rel_path),
        ("language", language),
        ("summary", summary),
        ("symbols", symbols),
        ("generated_by", PLUGIN_NAME),
    ]
    start_marker, end_marker = frontmatter_markers(style)
    if style == "hash":
        lines = [start_marker.rstrip("\n")]
        lines.extend(f"# {key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields)
        lines.append(end_marker.rstrip("\n"))
        return "\n".join(lines) + "\n\n"
    if style == "line-dash":
        lines = [start_marker.rstrip("\n")]
        lines.extend(f"-- {key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields)
        lines.append(end_marker.rstrip("\n"))
        return "\n".join(lines) + "\n\n"
    if style in {"block", "html", "raw"}:
        lines = [start_marker.rstrip("\n")]
        lines.extend(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields)
        lines.append(end_marker.rstrip("\n"))
        return "\n".join(lines) + "\n\n"
    raise ValueError(f"unsupported style: {style}")


def frontmatter_markers(style: str) -> tuple[str, str]:
    if style == "hash":
        return "# codex-file-meta: begin\n", "# codex-file-meta: end\n"
    if style == "line-dash":
        return "-- codex-file-meta: begin\n", "-- codex-file-meta: end\n"
    if style == "block":
        return "/* codex-file-meta: begin\n", "codex-file-meta: end */\n"
    if style == "html":
        return "<!-- codex-file-meta: begin\n", "codex-file-meta: end -->\n"
    if style == "raw":
        return "---\n", "---\n"
    raise ValueError(f"unsupported style: {style}")


def detect_comment_style(path: Path) -> str | None:
    lowered_name = path.name.lower()
    if lowered_name in COMMENT_STYLE_BY_NAME:
        return COMMENT_STYLE_BY_NAME[lowered_name]
    return COMMENT_STYLE_BY_SUFFIX.get(path.suffix.lower())


def detect_language(path: Path) -> str:
    suffix = path.suffix.lower()
    if path.name == "Dockerfile":
        return "dockerfile"
    mapping = {
        ".c": "c",
        ".cc": "cpp",
        ".conf": "config",
        ".cpp": "cpp",
        ".css": "css",
        ".csv": "csv",
        ".go": "go",
        ".h": "c-header",
        ".hpp": "cpp-header",
        ".html": "html",
        ".htm": "html",
        ".ini": "ini",
        ".java": "java",
        ".js": "javascript",
        ".json": "json",
        ".json5": "json5",
        ".jsx": "jsx",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".lua": "lua",
        ".md": "markdown",
        ".markdown": "markdown",
        ".mdx": "mdx",
        ".php": "php",
        ".py": "python",
        ".rb": "ruby",
        ".rs": "rust",
        ".sh": "shell",
        ".sql": "sql",
        ".svg": "svg",
        ".swift": "swift",
        ".toml": "toml",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".txt": "text",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    return mapping.get(suffix, suffix.lstrip(".") or "text")


def summarize_file_heuristic(path: Path, content: str) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return summarize_python(content)
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return summarize_javascript(content, suffix)
    if suffix in {".sh", ".bash", ".zsh"} or content.startswith("#!/bin/sh") or content.startswith("#!/usr/bin/env bash"):
        return summarize_shell(content)
    if suffix in MARKDOWN_SUFFIXES:
        return summarize_markdown(content)
    if suffix in {".json"}:
        return summarize_json(content)
    if suffix in {".yaml", ".yml", ".toml", ".ini", ".conf", ".properties"}:
        return summarize_key_value(content, detect_language(path))
    if suffix in {".html", ".htm", ".xml", ".svg"}:
        return summarize_markup(content)
    if suffix in {".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".cs", ".go", ".rs", ".swift", ".kt", ".kts"}:
        return summarize_c_like(content, detect_language(path))
    return summarize_generic(content, detect_language(path))


def summarize_python(content: str) -> tuple[str, list[str]]:
    try:
        module = ast.parse(content or "\n")
    except SyntaxError:
        return summarize_generic(content, "python")

    docstring = ast.get_docstring(module)
    symbols = [
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    if docstring:
        return normalize_sentence(docstring), symbols[:8]
    if symbols:
        return f"Python module defining {format_names(symbols)}.", symbols[:8]
    return summarize_generic(content, "python")


def summarize_javascript(content: str, suffix: str) -> tuple[str, list[str]]:
    symbols = unique(JS_SYMBOL_RE.findall(content))[:8]
    language = "TypeScript" if suffix in {".ts", ".tsx"} else "JavaScript"
    if symbols:
        return f"{language} module defining {format_names(symbols)}.", symbols
    return summarize_generic(content, language.lower())


def summarize_shell(content: str) -> tuple[str, list[str]]:
    symbols = unique(SHELL_FUNCTION_RE.findall(content))[:8]
    if symbols:
        return f"Shell script defining {format_names(symbols)}.", symbols
    return summarize_generic(content, "shell")


def summarize_markdown(content: str) -> tuple[str, list[str]]:
    heading_match = HEADING_RE.search(content)
    heading = clean_inline_text(heading_match.group(1)) if heading_match else ""
    paragraph = first_markdown_paragraph(content)
    symbols = [heading] if heading else []
    if paragraph:
        lead = normalize_sentence(paragraph)
        if heading:
            return f"Markdown document \"{heading}\". {lead}", symbols
        return lead, symbols
    if heading:
        return f"Markdown document titled \"{heading}\".", symbols
    return "Markdown document.", symbols


def summarize_json(content: str) -> tuple[str, list[str]]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return summarize_generic(content, "json")
    if isinstance(payload, dict):
        keys = list(payload.keys())[:8]
        if keys:
            return f"JSON object with top-level keys {format_names(keys)}.", [str(key) for key in keys]
        return "JSON object.", []
    if isinstance(payload, list):
        return f"JSON array with {len(payload)} item(s).", []
    return "JSON value.", []


def summarize_key_value(content: str, language: str) -> tuple[str, list[str]]:
    keys = unique(TOP_LEVEL_KEY_RE.findall(content))[:8]
    label = language.upper() if language in {"ini", "yaml"} else language.capitalize()
    if keys:
        return f"{label} file with top-level keys {format_names(keys)}.", keys
    return summarize_generic(content, language)


def summarize_markup(content: str) -> tuple[str, list[str]]:
    title_match = HTML_TITLE_RE.search(content)
    h1_match = HTML_H1_RE.search(content)
    title = clean_inline_text(title_match.group(1)) if title_match else ""
    heading = clean_inline_text(h1_match.group(1)) if h1_match else ""
    symbols = [value for value in [title or heading] if value]
    if title and heading and title != heading:
        return f"Markup document titled \"{title}\" with heading \"{heading}\".", symbols
    if title:
        return f"Markup document titled \"{title}\".", symbols
    if heading:
        return f"Markup document headed \"{heading}\".", symbols
    return "Markup document.", symbols


def summarize_c_like(content: str, language: str) -> tuple[str, list[str]]:
    symbols = unique(C_LIKE_SYMBOL_RE.findall(content))[:8]
    if symbols:
        return f"{language.capitalize()} source defining {format_names(symbols)}.", symbols
    return summarize_generic(content, language)


def summarize_generic(content: str, language: str) -> tuple[str, list[str]]:
    paragraph = first_non_empty_paragraph(content)
    if paragraph:
        return f"{language.capitalize()} file: {normalize_sentence(paragraph)}", []
    line_count = len(content.splitlines())
    return f"{language.capitalize()} file with {line_count} line(s).", []


def render_directory_summary(
    *,
    display_path: str,
    summary_overview: str,
    file_results: list[FileResult],
    child_directories: list[DirectoryResult],
) -> str:
    lines = [
        f"# Directory Summary: {display_path}",
        "",
        f"Generated by `{PLUGIN_NAME}`.",
        "",
        summary_overview,
        "",
        "## Files",
    ]
    if file_results:
        for file_result in file_results:
            detail = f"- `{Path(file_result.rel_path).name}`: {file_result.summary}"
            if file_result.skipped_reason:
                detail += f" Frontmatter skipped: {file_result.skipped_reason}."
            lines.append(detail)
    else:
        lines.append("- None.")

    lines.extend(["", "## Directories"])
    if child_directories:
        for child in child_directories:
            lines.append(f"- `{Path(child.rel_path).name}/`: {child.summary_overview}")
    else:
        lines.append("- None.")

    return "\n".join(lines).rstrip() + "\n"


def build_directory_overview_heuristic(
    file_results: list[FileResult],
    child_directories: list[DirectoryResult],
) -> str:
    file_count = len(file_results)
    dir_count = len(child_directories)
    parts = [f"Contains {file_count} file(s) and {dir_count} subdirectory(s)."]
    highlights: list[str] = []
    for file_result in file_results[:3]:
        highlights.append(f"`{Path(file_result.rel_path).name}`: {file_result.summary}")
    for child in child_directories[:2]:
        highlights.append(f"`{Path(child.rel_path).name}/`: {child.summary_overview}")
    if highlights:
        parts.append("Highlights: " + " ".join(highlights))
    return " ".join(parts)


def build_file_summary_prompt(*, rel_path: str, language: str, content: str) -> str:
    return (
        "Summarize this repository file for generated frontmatter.\n"
        "Return JSON only.\n"
        "Rules:\n"
        "1. `summary` must be one concrete sentence, 180 characters or fewer.\n"
        "2. `symbols` must be an array of up to 8 meaningful top-level identifiers, headings, or entrypoints.\n"
        "3. Do not invent behavior that is not visible in the file.\n"
        "4. Do not mention frontmatter or metadata blocks.\n\n"
        "JSON schema:\n"
        f"{json.dumps(FILE_SUMMARY_SCHEMA, ensure_ascii=False, indent=2)}\n\n"
        "File path:\n"
        f"{rel_path}\n\n"
        "Language:\n"
        f"{language}\n\n"
        "File content:\n"
        f"{content}\n"
    )


def build_directory_summary_prompt(
    *,
    rel_path: str,
    file_results: list[FileResult],
    child_directories: list[DirectoryResult],
    max_chars: int,
) -> str:
    child_lines = ["Files:"]
    if file_results:
        for file_result in file_results:
            child_lines.append(
                f"- {Path(file_result.rel_path).name}: {file_result.summary}"
            )
    else:
        child_lines.append("- none")

    child_lines.append("")
    child_lines.append("Directories:")
    if child_directories:
        for child in child_directories:
            child_lines.append(
                f"- {Path(child.rel_path).name}/: {child.summary_overview}"
            )
    else:
        child_lines.append("- none")

    child_context = truncate_for_prompt("\n".join(child_lines), max_chars)
    return (
        "Summarize this directory from its direct children.\n"
        "Return JSON only.\n"
        "Rules:\n"
        "1. `overview` must be a concise directory summary, 280 characters or fewer.\n"
        "2. Only use the provided direct child summaries.\n"
        "3. Mention both files and child directories when they exist.\n"
        "4. Do not mention frontmatter or metadata blocks.\n\n"
        "JSON schema:\n"
        f"{json.dumps(DIRECTORY_SUMMARY_SCHEMA, ensure_ascii=False, indent=2)}\n\n"
        "Directory path:\n"
        f"{rel_path}\n\n"
        "Direct child summaries:\n"
        f"{child_context}\n"
    )


def tally(result: DirectoryResult) -> dict[str, int]:
    totals = {
        "directories": 1,
        "files": len(result.file_results),
        "modified_files": sum(1 for item in result.file_results if item.modified),
        "written_summaries": 1 if result.summary_written else 0,
        "skipped_files": sum(1 for item in result.file_results if item.skipped_reason),
    }
    for child in result.child_directories:
        child_totals = tally(child)
        for key, value in child_totals.items():
            totals[key] += value
    return totals


def write_text_if_changed(path: Path, text: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def relative_directory_path(root: Path, current: Path) -> str:
    if current == root:
        return "."
    return current.relative_to(root).as_posix()


def is_binary(payload: bytes) -> bool:
    if not payload:
        return False
    sample = payload[:1024]
    if b"\x00" in sample:
        return True
    text_bytes = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(32, 127)))
    non_text = sample.translate(None, text_bytes)
    return len(non_text) / max(1, len(sample)) > 0.30


def split_first_line(text: str) -> tuple[str, str]:
    newline = text.find("\n")
    if newline == -1:
        return text, ""
    return text[: newline + 1], text[newline + 1 :]


def first_non_empty_paragraph(content: str) -> str:
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        if stripped.startswith(("codex-file-meta:", "# codex-file-meta:", "-- codex-file-meta:", "<!-- codex-file-meta:")):
            continue
        lines.append(stripped)
        if len(" ".join(lines)) > 180:
            break
    return clean_inline_text(" ".join(lines))


def first_markdown_paragraph(content: str) -> str:
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        if stripped.startswith("#"):
            continue
        lines.append(stripped)
        if len(" ".join(lines)) > 180:
            break
    return clean_inline_text(" ".join(lines))


def clean_inline_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = WORD_RE.sub(" ", text).strip()
    return text


def normalize_sentence(text: str, max_length: int = 180) -> str:
    sentence = clean_inline_text(text)
    if not sentence:
        return ""
    sentence = sentence.rstrip(".")
    if len(sentence) > max_length:
        sentence = sentence[: max_length - 3].rstrip() + "..."
    return sentence + "."


def sanitize_symbols(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        cleaned = clean_inline_text(item)
        if cleaned:
            values.append(cleaned[:80])
    return unique(values)[:8]


def truncate_for_prompt(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head_size = max_chars // 2
    tail_size = max_chars - head_size
    return (
        text[:head_size].rstrip()
        + "\n\n[... truncated ...]\n\n"
        + text[-tail_size:].lstrip()
    )


def format_names(names: Iterable[str]) -> str:
    visible = [f"`{name}`" for name in unique(list(names)) if name][:4]
    if not visible:
        return "top-level symbols"
    if len(visible) == 1:
        return visible[0]
    return ", ".join(visible[:-1]) + f", and {visible[-1]}"


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import ast
import re
from pathlib import PurePosixPath
from typing import Iterable

from .util import ordered_dict

JS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:(?:async\s+)?function|class|interface|type|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
SHELL_FUNCTION_RE = re.compile(
    r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{",
    re.MULTILINE,
)
C_SYMBOL_RE = re.compile(
    r"^\s*(?:class|struct|enum|interface)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
C_FUNCTION_RE = re.compile(
    r"^\s*[A-Za-z_][A-Za-z0-9_\s\*]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{",
    re.MULTILINE,
)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+)$", re.MULTILINE)
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*[:=]", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\.]+))", re.MULTILINE)
INCLUDE_RE = re.compile(r'^\s*#include\s+[<"]([^>"]+)[>"]', re.MULTILINE)
REQUIRE_RE = re.compile(r'require\(["\']([^"\']+)["\']\)')
SOURCE_RE = re.compile(r'^\s*(?:source|\.)\s+["\']?([^"\']+)["\']?', re.MULTILINE)
DEFINE_RE = re.compile(r"^\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
ASSIGN_DEFINE_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]{2,})\s*[:=]", re.MULTILINE)
WORD_RE = re.compile(r"[A-Za-z0-9_]+")
SECTION_LINE_SPAN = 80


def build_file_metadata_candidate(
    *,
    rel_path: str,
    kind: str,
    language: str,
    text: str,
    token_estimate: int,
    related_files: list[str],
    related_tests: list[str],
    priority_sections: list[dict[str, str]],
) -> dict:
    exports = extract_symbols(language, text)
    summary = summarize_text(rel_path, kind, language, text, exports)
    defines = extract_defines(text)
    depends_on = extract_dependencies(language, text)
    tags = derive_tags(rel_path, kind, language, exports, depends_on)
    keywords = derive_keywords(rel_path, tags, exports, defines)
    return ordered_dict(
        [
            ("path", rel_path),
            ("kind", kind),
            ("language", language),
            ("role", derive_role(rel_path, kind, exports)),
            ("summary", summary),
            ("tags", tags),
            ("keywords", keywords),
            ("exports", exports),
            ("defines", defines),
            ("depends_on", depends_on),
            ("related_files", related_files),
            ("related_tests", related_tests),
            ("priority_sections", priority_sections),
            ("importance", estimate_importance(rel_path, kind)),
            ("complexity", estimate_complexity(token_estimate, len(exports) + len(defines))),
            ("token_estimate", token_estimate),
            ("confidence", "medium"),
        ]
    )


def summarize_text(rel_path: str, kind: str, language: str, text: str, symbols: list[str]) -> str:
    if language == "python":
        try:
            module = ast.parse(text or "\n")
            docstring = ast.get_docstring(module)
            if docstring:
                return clean_sentence(docstring)
        except SyntaxError:
            pass
    if language in {"markdown", "mdx", "rst"}:
        heading = first_heading(text)
        paragraph = first_paragraph(text)
        if heading and paragraph:
            return clean_sentence(f'{heading}. {paragraph}')
        if heading:
            return clean_sentence(f"Document centered on {heading}.")
    if kind == "config":
        keys = unique(TOP_LEVEL_KEY_RE.findall(text))[:5]
        if keys:
            return clean_sentence(f"Configuration file with top-level keys {format_names(keys)}.")
    if symbols:
        return clean_sentence(f"{language.capitalize()} file defining {format_names(symbols[:5])}.")
    paragraph = first_paragraph(text)
    if paragraph:
        return clean_sentence(paragraph)
    return clean_sentence(f"{language.capitalize()} {kind.replace('_', ' ')}.")


def extract_symbols(language: str, text: str) -> list[str]:
    if language == "python":
        try:
            module = ast.parse(text or "\n")
            symbols = [
                node.name
                for node in module.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]
            return unique(symbols)[:12]
        except SyntaxError:
            return []
    if language in {"javascript", "typescript", "jsx", "tsx"}:
        return unique(JS_SYMBOL_RE.findall(text))[:12]
    if language == "shell":
        return unique(SHELL_FUNCTION_RE.findall(text))[:12]
    if language in {"c", "cpp", "c-header", "cpp-header", "java", "rust", "go", "swift", "kotlin"}:
        return unique(C_SYMBOL_RE.findall(text) + C_FUNCTION_RE.findall(text))[:12]
    return []


def extract_defines(text: str) -> list[str]:
    return unique(DEFINE_RE.findall(text) + ASSIGN_DEFINE_RE.findall(text))[:12]


def extract_dependencies(language: str, text: str) -> list[str]:
    dependencies: list[str] = []
    if language == "python":
        for left, right in IMPORT_RE.findall(text):
            dependencies.append((left or right).replace(".", "/"))
    elif language in {"c", "cpp", "c-header", "cpp-header"}:
        dependencies.extend(INCLUDE_RE.findall(text))
    elif language in {"javascript", "typescript", "jsx", "tsx"}:
        dependencies.extend(REQUIRE_RE.findall(text))
    elif language == "shell":
        dependencies.extend(SOURCE_RE.findall(text))
    return unique([item for item in dependencies if item])[:12]


def derive_tags(rel_path: str, kind: str, language: str, exports: list[str], depends_on: list[str]) -> list[str]:
    path = PurePosixPath(rel_path)
    parts = [part.lower() for part in path.parts[:-1] if part not in {"src", "lib"}]
    tags = [kind, language]
    tags.extend(parts[-3:])
    if exports:
        tags.extend(symbol.lower() for symbol in exports[:2])
    if depends_on:
        tags.append("imports")
    return unique([tag.replace("_", "-") for tag in tags if tag])[:8]


def derive_keywords(rel_path: str, tags: list[str], exports: list[str], defines: list[str]) -> list[str]:
    words = WORD_RE.findall(rel_path.replace("/", " "))
    keywords = [word.lower() for word in words if len(word) > 2]
    keywords.extend(tag.lower() for tag in tags)
    keywords.extend(symbol.lower() for symbol in exports[:6])
    keywords.extend(symbol.lower() for symbol in defines[:6])
    return unique(keywords)[:12]


def derive_role(rel_path: str, kind: str, exports: list[str]) -> str:
    path = PurePosixPath(rel_path)
    name = path.name.lower()
    if name in {"main.py", "main.ts", "index.js", "index.ts", "app.py"} or "cli" in name:
        return "entrypoint"
    if kind == "config":
        return "configuration"
    if kind == "test":
        return "test"
    if kind == "document":
        return "reference"
    if exports:
        return "core_impl"
    if "scripts" in path.parts:
        return "automation"
    return "supporting"


def estimate_importance(rel_path: str, kind: str) -> str:
    if rel_path.count("/") == 0 and kind in {"config", "document"}:
        return "high"
    if kind in {"source_code", "config"}:
        return "high" if "core" in rel_path or "runtime" in rel_path else "medium"
    if kind == "test":
        return "medium"
    return "low"


def estimate_complexity(token_estimate: int, symbol_count: int) -> str:
    if token_estimate >= 4000 or symbol_count >= 12:
        return "high"
    if token_estimate >= 1400 or symbol_count >= 5:
        return "medium"
    return "low"


def split_sections(rel_path: str, language: str, text: str) -> list[dict]:
    lines = text.splitlines()
    if not lines:
        return []
    sections = _sectionize_by_headings(lines)
    if not sections and language == "python":
        sections = _sectionize_python(lines, text)
    if not sections and language in {"javascript", "typescript", "jsx", "tsx", "shell"}:
        sections = _sectionize_symbols(lines, text, language)
    if not sections:
        sections = _sectionize_chunks(lines)
    result = []
    for index, section in enumerate(sections, start=1):
        body = "\n".join(lines[section["start_line"] - 1 : section["end_line"]])
        summary = clean_sentence(section.get("summary") or first_paragraph(body) or section["title"])
        result.append(
            ordered_dict(
                [
                    ("id", section.get("id") or f"s{index}"),
                    ("title", section.get("title") or f"Section {index}"),
                    ("start_line", section["start_line"]),
                    ("end_line", section["end_line"]),
                    ("summary", summary or "No summary available."),
                    ("symbols", section.get("symbols") or extract_symbols(language, body)[:8]),
                ]
            )
        )
    return result


def build_directory_candidate(dir_path: str, child_files: list[dict], child_dirs: list[dict]) -> dict:
    topics = unique(
        item
        for child in child_files
        for item in (child.get("tags") or [])[:3]
        if item not in {"source_code", "config", "test", "document", "markup", "script"}
    )[:8]
    key_files = [child["path"] for child in child_files[:5]]
    entrypoints = [child["path"] for child in child_files if child.get("role") == "entrypoint"][:5]
    core_files = [child["path"] for child in child_files if child.get("kind") == "source_code"][:5]
    test_files = [child["path"] for child in child_files if child.get("kind") == "test"][:5]
    config_files = [child["path"] for child in child_files if child.get("kind") == "config"][:5]
    read_order = entrypoints + [path for path in key_files if path not in entrypoints]
    pitfalls: list[str] = []
    if config_files:
        pitfalls.append("Keep generated guide and state artifacts out of runtime configuration.")
    if test_files and core_files:
        pitfalls.append("Check matching tests before editing implementation files in this directory.")
    if not pitfalls:
        pitfalls.append("Prefer frontmatter and section indexes before full-file reads.")
    role = "directory"
    if "tests" in dir_path.split("/"):
        role = "test support"
    elif entrypoints:
        role = "entrypoint directory"
    elif core_files:
        role = "implementation directory"
    elif config_files:
        role = "configuration directory"
    return ordered_dict(
        [
            ("path", dir_path),
            ("role", role),
            ("frontmatter_summary", summarize_directory_frontmatter(child_files)),
            ("key_files", key_files),
            ("entrypoints", entrypoints),
            ("core_files", core_files),
            ("test_files", test_files),
            ("config_files", config_files),
            ("topics", topics),
            ("pitfalls", pitfalls),
            ("read_order", read_order),
            ("confidence", "medium"),
        ]
    )


def summarize_directory_frontmatter(child_files: list[dict]) -> str:
    if not child_files:
        return "No file frontmatter in this directory yet."
    snippets: list[str] = []
    for child in child_files[:6]:
        path = PurePosixPath(child["path"]).name
        summary = clean_sentence(child.get("summary", ""))
        if summary:
            snippets.append(f"`{path}`: {summary}")
        else:
            snippets.append(f"`{path}`")
    return " ".join(snippets)


def first_heading(text: str) -> str:
    match = HEADING_RE.search(text)
    return clean_sentence(match.group(1)) if match else ""


def first_paragraph(text: str) -> str:
    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    if not paragraphs:
        return ""
    return clean_sentence(paragraphs[0].replace("\n", " "))


def clean_sentence(text: str) -> str:
    return " ".join(str(text).strip().split())[:240]


def format_names(values: Iterable[str]) -> str:
    items = [f"`{value}`" for value in values if value]
    if not items:
        return "no symbols"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _sectionize_by_headings(lines: list[str]) -> list[dict]:
    sections: list[dict] = []
    headings = [(idx + 1, HEADING_RE.match(line).group(1).strip()) for idx, line in enumerate(lines) if HEADING_RE.match(line)]
    for index, (start_line, title) in enumerate(headings):
        end_line = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        sections.append({"id": f"h{index + 1}", "title": title, "start_line": start_line, "end_line": end_line})
    return sections


def _sectionize_python(lines: list[str], text: str) -> list[dict]:
    try:
        module = ast.parse(text or "\n")
    except SyntaxError:
        return []
    sections: list[dict] = []
    for index, node in enumerate(module.body, start=1):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start_line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", None)
        if not start_line or not end_line:
            continue
        sections.append(
            {
                "id": f"py{index}",
                "title": node.name,
                "start_line": start_line,
                "end_line": end_line,
                "symbols": [node.name],
            }
        )
    return sections


def _sectionize_symbols(lines: list[str], text: str, language: str) -> list[dict]:
    pattern = JS_SYMBOL_RE if language in {"javascript", "typescript", "jsx", "tsx"} else SHELL_FUNCTION_RE
    sections: list[dict] = []
    for index, match in enumerate(pattern.finditer(text), start=1):
        start_line = text[: match.start()].count("\n") + 1
        end_line = start_line + SECTION_LINE_SPAN - 1
        sections.append(
            {
                "id": f"s{index}",
                "title": match.group(1),
                "start_line": start_line,
                "end_line": min(len(lines), end_line),
                "symbols": [match.group(1)],
            }
        )
    return sections


def _sectionize_chunks(lines: list[str]) -> list[dict]:
    sections: list[dict] = []
    for index, start in enumerate(range(1, len(lines) + 1, SECTION_LINE_SPAN), start=1):
        end = min(len(lines), start + SECTION_LINE_SPAN - 1)
        sections.append({"id": f"chunk{index}", "title": f"Lines {start}-{end}", "start_line": start, "end_line": end})
    return sections

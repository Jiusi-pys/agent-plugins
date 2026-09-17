from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .config import DEFAULT_EXCLUDED_DIRS, DEFAULT_EXCLUDED_FILES, IndexerConfig
from .util import approx_token_count, sha256_bytes

TEXT_SAMPLE_BYTES = 4096
SOURCE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".lua",
    ".php",
    ".pl",
    ".pm",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
}
SCRIPT_SUFFIXES = {".bash", ".ps1", ".py", ".sh", ".zsh"}
DOC_SUFFIXES = {".md", ".markdown", ".mdx", ".rst", ".txt"}
CONFIG_SUFFIXES = {".conf", ".env", ".ini", ".json", ".json5", ".properties", ".toml", ".yaml", ".yml"}
MARKUP_SUFFIXES = {".css", ".csv", ".htm", ".html", ".svg", ".xml"}


@dataclass(frozen=True)
class FileSnapshot:
    abs_path: Path
    rel_path: str
    kind: str
    language: str
    size: int
    mtime_ns: int
    content_hash: str
    token_estimate: int
    line_count: int
    is_binary: bool


@dataclass(frozen=True)
class TreeSnapshot:
    root: Path
    files: list[FileSnapshot]
    directories: list[str]


def scan_tree(config: IndexerConfig) -> TreeSnapshot:
    files: list[FileSnapshot] = []
    directories = {"."}
    root = config.root
    path_filter = _normalize_filter(config.path_filter)

    for current_root, dirnames, filenames in _walk(root):
        current_path = Path(current_root)
        rel_dir = "." if current_path == root else current_path.relative_to(root).as_posix()
        if path_filter and not _path_matches(rel_dir, path_filter):
            dirnames[:] = [name for name in dirnames if _path_matches(_join(rel_dir, name), path_filter)]
            filenames = [name for name in filenames if _path_matches(_join(rel_dir, name), path_filter)]
        dirnames[:] = sorted(name for name in dirnames if name not in DEFAULT_EXCLUDED_DIRS)
        filenames = sorted(filenames)
        if rel_dir != ".":
            directories.add(rel_dir)

        for filename in filenames:
            if filename in DEFAULT_EXCLUDED_FILES:
                continue
            abs_path = current_path / filename
            rel_path = abs_path.relative_to(root).as_posix()
            if path_filter and not _path_matches(rel_path, path_filter):
                continue
            try:
                raw = abs_path.read_bytes()
            except OSError:
                continue
            is_binary = _is_binary(raw)
            text = "" if is_binary else raw.decode("utf-8", errors="replace")
            files.append(
                FileSnapshot(
                    abs_path=abs_path,
                    rel_path=rel_path,
                    kind=detect_kind(rel_path, is_binary=is_binary),
                    language=detect_language(abs_path),
                    size=abs_path.stat().st_size,
                    mtime_ns=abs_path.stat().st_mtime_ns,
                    content_hash=sha256_bytes(raw),
                    token_estimate=0 if is_binary else approx_token_count(text),
                    line_count=0 if is_binary else len(text.splitlines()),
                    is_binary=is_binary,
                )
            )
    return TreeSnapshot(root=root, files=sorted(files, key=lambda item: item.rel_path), directories=sorted(directories))


def _walk(root: Path):
    import os

    return os.walk(root)


def _normalize_filter(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip().strip("/")
    return stripped or None


def _path_matches(rel_path: str, path_filter: str) -> bool:
    if rel_path in {"", "."}:
        return True
    if rel_path == path_filter:
        return True
    return rel_path.startswith(path_filter + "/") or path_filter.startswith(rel_path + "/")


def _join(rel_dir: str, name: str) -> str:
    return name if rel_dir in {"", "."} else f"{rel_dir}/{name}"


def _is_binary(raw: bytes) -> bool:
    if not raw:
        return False
    if b"\0" in raw[:TEXT_SAMPLE_BYTES]:
        return True
    sample = raw[:TEXT_SAMPLE_BYTES]
    non_text = sum(1 for byte in sample if byte < 9 or (13 < byte < 32))
    return non_text / max(1, len(sample)) > 0.2


def detect_language(path: Path) -> str:
    if path.name == "Dockerfile":
        return "dockerfile"
    suffix = path.suffix.lower()
    mapping = {
        ".bash": "shell",
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
        ".pl": "perl",
        ".pm": "perl",
        ".py": "python",
        ".r": "r",
        ".rb": "ruby",
        ".rs": "rust",
        ".rst": "rst",
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
        ".zsh": "shell",
    }
    return mapping.get(suffix, suffix.lstrip(".") or "text")


def detect_kind(rel_path: str, *, is_binary: bool) -> str:
    path = PurePosixPath(rel_path)
    if is_binary:
        return "binary"
    lower_parts = [part.lower() for part in path.parts]
    suffix = path.suffix.lower()
    name = path.name.lower()
    if "test" in lower_parts or "tests" in lower_parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    if name in {"makefile", "dockerfile"} or suffix in SCRIPT_SUFFIXES or "scripts" in lower_parts:
        return "script"
    if suffix in DOC_SUFFIXES:
        return "document"
    if suffix in CONFIG_SUFFIXES or name in {"package.json", "pyproject.toml"} or "config" in lower_parts:
        return "config"
    if suffix in SOURCE_SUFFIXES:
        return "source_code"
    if suffix in MARKUP_SUFFIXES:
        return "markup"
    return "text"

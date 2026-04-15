from __future__ import annotations

from pathlib import PurePosixPath

from .config import IndexerConfig
from .scanner import FileSnapshot
from .util import approx_token_count
from .validators import normalize_file_metadata


def build_file_metadata(
    snapshot: FileSnapshot,
    text: str,
    *,
    config: IndexerConfig,
    provider,
    all_paths: list[str],
    priority_sections: list[dict[str, str]],
) -> dict:
    path = PurePosixPath(snapshot.rel_path)
    related_files = _related_files(snapshot.rel_path, all_paths)
    related_tests = _related_tests(snapshot.rel_path, all_paths)
    repo_hints = {
        "siblings": [candidate for candidate in related_files[:4]],
        "tests": related_tests[:4],
        "directory": path.parent.as_posix() if str(path.parent) != "." else ".",
    }
    payload = provider.summarize_file(
        rel_path=snapshot.rel_path,
        kind=snapshot.kind,
        language=snapshot.language,
        text=text,
        token_estimate=snapshot.token_estimate or approx_token_count(text),
        repo_hints=repo_hints,
        related_files=related_files,
        related_tests=related_tests,
        priority_sections=priority_sections,
    )
    return normalize_file_metadata(payload)


def render_inline_markdown_frontmatter(metadata: dict, body: str) -> str:
    fields = [
        ("path", metadata["path"]),
        ("summary", metadata["summary"]),
        ("tags", metadata["tags"]),
        ("importance", metadata["importance"]),
        ("confidence", metadata["confidence"]),
    ]
    lines = ["---"]
    for key, value in fields:
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.extend(["---", ""])
    stripped = body
    if stripped.startswith("---\n"):
        closing = stripped.find("\n---\n", 4)
        if closing != -1:
            stripped = stripped[closing + len("\n---\n") :]
    return "\n".join(lines) + stripped.lstrip("\n")


def _related_files(rel_path: str, all_paths: list[str]) -> list[str]:
    stem = PurePosixPath(rel_path).stem
    directory = PurePosixPath(rel_path).parent.as_posix()
    related = [
        candidate
        for candidate in all_paths
        if candidate != rel_path
        and PurePosixPath(candidate).stem == stem
        and PurePosixPath(candidate).parent.as_posix() == directory
    ]
    return related[:8]


def _related_tests(rel_path: str, all_paths: list[str]) -> list[str]:
    stem = PurePosixPath(rel_path).stem.lower()
    tests = [
        candidate
        for candidate in all_paths
        if "test" in candidate.lower() and (stem in candidate.lower() or PurePosixPath(candidate).stem.lower() in stem)
    ]
    return tests[:8]

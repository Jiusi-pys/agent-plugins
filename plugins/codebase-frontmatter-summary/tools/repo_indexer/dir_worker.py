from __future__ import annotations

from .util import fingerprint_parts
from .validators import normalize_directory_metadata


def compute_child_fingerprint(
    dir_path: str,
    *,
    child_file_states: list[tuple[str, str]],
    child_dir_states: list[tuple[str, str]],
) -> str:
    parts = [f"dir:{dir_path}"]
    parts.extend(f"file:{path}:{content_hash}" for path, content_hash in child_file_states)
    parts.extend(f"child:{path}:{fingerprint}" for path, fingerprint in child_dir_states)
    return fingerprint_parts(parts)


def build_directory_metadata(dir_path: str, *, child_files: list[dict], child_dirs: list[dict], provider) -> dict:
    return normalize_directory_metadata(
        provider.summarize_directory(dir_path=dir_path, child_files=child_files, child_dirs=child_dirs)
    )

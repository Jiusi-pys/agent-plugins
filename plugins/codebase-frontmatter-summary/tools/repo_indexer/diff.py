from __future__ import annotations

from dataclasses import dataclass

from .config import FILE_METADATA_VERSION, PIPELINE_VERSION, SECTION_INDEX_VERSION
from .scanner import TreeSnapshot
from .state_db import DirState, FileState
from .util import parent_directories


@dataclass(frozen=True)
class DiffResult:
    new_files: set[str]
    changed_files: set[str]
    unchanged_files: set[str]
    removed_files: set[str]
    dirty_dirs: set[str]
    removed_dirs: set[str]


def compute_diff(
    snapshot: TreeSnapshot,
    previous_files: dict[str, FileState],
    previous_dirs: dict[str, DirState],
) -> DiffResult:
    current_files = {entry.rel_path: entry for entry in snapshot.files}
    current_dirs = set(snapshot.directories)
    previous_paths = set(previous_files)

    new_files: set[str] = set()
    changed_files: set[str] = set()
    unchanged_files: set[str] = set()
    dirty_dirs: set[str] = set()

    for rel_path, entry in current_files.items():
        previous = previous_files.get(rel_path)
        if previous is None:
            new_files.add(rel_path)
        elif _file_changed(entry, previous):
            changed_files.add(rel_path)
        else:
            unchanged_files.add(rel_path)

    removed_files = previous_paths - set(current_files)
    removed_dirs = set(previous_dirs) - current_dirs

    for rel_path in new_files | changed_files | removed_files:
        dirty_dirs.update(parent_directories(rel_path))
    if removed_dirs:
        dirty_dirs.update(removed_dirs)
    if dirty_dirs:
        dirty_dirs.add(".")

    return DiffResult(
        new_files=new_files,
        changed_files=changed_files,
        unchanged_files=unchanged_files,
        removed_files=removed_files,
        dirty_dirs=dirty_dirs,
        removed_dirs=removed_dirs,
    )


def _file_changed(entry, previous: FileState) -> bool:
    if previous.pipeline_version != PIPELINE_VERSION:
        return True
    if previous.frontmatter_version != FILE_METADATA_VERSION:
        return True
    if previous.section_version != SECTION_INDEX_VERSION:
        return True
    if previous.size != entry.size:
        return True
    if previous.mtime_ns != entry.mtime_ns:
        return True
    if previous.content_hash != entry.content_hash:
        return True
    return False

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
from typing import Any

from .config import IndexerConfig, PIPELINE_VERSION
from .diff import compute_diff
from .dir_worker import build_directory_metadata, compute_child_fingerprint
from .file_worker import build_file_metadata, render_inline_markdown_frontmatter
from .guide_builder import build_generated_guides, export_host_guides, write_generated_guides
from .providers import build_provider
from .read_planner import plan_read
from .scanner import TreeSnapshot, scan_tree
from .section_worker import build_section_index, should_index_sections
from .state_db import StateDB
from .util import (
    directory_artifact_path,
    directory_depth,
    ensure_dir,
    file_artifact_path,
    json_dumps,
    read_json,
    remove_file_if_exists,
    sha256_bytes,
    utc_now,
    write_json_if_changed,
    write_text_if_changed,
)
from .validators import SchemaError, normalize_directory_metadata, normalize_file_metadata, normalize_section_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Incremental repository knowledge compiler.")
    subparsers = parser.add_subparsers(dest="command")

    for name in ("scan", "refresh"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--path", dest="path_filter")
        command.add_argument("--backend", default="heuristic")
        command.add_argument("--model", default="gpt-5.4-mini")
        command.add_argument("--reasoning-effort", default="high")
        command.add_argument("--no-export-guides", action="store_true")
        command.add_argument("--inline-markdown-frontmatter", action="store_true")
    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--root", required=True)
    export = subparsers.add_parser("export-guides")
    export.add_argument("--root", required=True)
    export.add_argument("--backend", default="heuristic")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        return _compat_main(argv)
    if args.command == "doctor":
        return _doctor(Path(args.root).expanduser().resolve())
    if args.command == "export-guides":
        return _export_guides_only(Path(args.root).expanduser().resolve(), backend=args.backend)
    config = IndexerConfig(
        root=Path(args.root).expanduser().resolve(),
        backend=args.backend,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        write=args.command == "refresh",
        export_guides=not args.no_export_guides,
        inline_markdown_frontmatter=args.inline_markdown_frontmatter,
        path_filter=args.path_filter,
    )
    summary = run_index(config)
    print(json_dumps(summary))
    return 0


def run_index(config: IndexerConfig) -> dict[str, Any]:
    state_db = StateDB(config.root)
    if config.write:
        _prepare_layout(config)
        state_db.initialize()
    provider = build_provider(config)
    snapshot = scan_tree(config)
    previous_files = state_db.load_files() if state_db.db_path.exists() else {}
    previous_dirs = state_db.load_dirs() if state_db.db_path.exists() else {}
    diff = compute_diff(snapshot, previous_files, previous_dirs)

    run_id = state_db.start_run("refresh" if config.write else "scan") if config.write else None
    removed_artifacts = _remove_deleted_artifacts(config, previous_files, previous_dirs, diff, persist=config.write, state_db=state_db)
    file_metadata, section_indexes = _build_file_artifacts(
        config=config,
        snapshot=snapshot,
        diff=diff,
        previous_files=previous_files,
        provider=provider,
        persist=config.write,
        state_db=state_db,
    )
    directory_metadata = _build_directory_artifacts(
        config=config,
        snapshot=snapshot,
        diff=diff,
        previous_dirs=previous_dirs,
        file_metadata=file_metadata,
        provider=provider,
        persist=config.write,
        state_db=state_db,
    )
    root_metadata = directory_metadata["."]
    guides = build_generated_guides(
        config=config,
        root_metadata=root_metadata,
        directory_metadata=[directory_metadata[path] for path in sorted(directory_metadata)],
        file_metadata=[file_metadata[path] for path in sorted(file_metadata)],
        provider=provider,
    )
    written_guides = write_generated_guides(config, guides) if config.write else []
    exported_guides = (
        export_host_guides(
            config,
            root_metadata=root_metadata,
            directory_metadata=[directory_metadata[path] for path in sorted(directory_metadata)],
            file_metadata=[file_metadata[path] for path in sorted(file_metadata)],
        )
        if config.write and config.export_guides
        else []
    )
    manifest_path = config.root / "scan-manifest.json"
    pipeline_path = config.state_dir / "pipeline.json"
    run_report_path = config.runs_dir / f"{utc_now().replace(':', '-')}.json"
    manifest = _render_manifest(config, snapshot, root_metadata, directory_metadata, file_metadata)
    if config.write:
        write_json_if_changed(manifest_path, manifest)
        write_json_if_changed(
            pipeline_path,
            {
                "pipeline_version": PIPELINE_VERSION,
                "backend": config.backend,
                "generated_at": utc_now(),
            },
        )
        write_json_if_changed(
            run_report_path,
            {
                "run_id": run_id,
                "generated_at": utc_now(),
                "new_count": len(diff.new_files),
                "changed_count": len(diff.changed_files),
                "removed_count": len(diff.removed_files),
            },
        )
        if run_id:
            state_db.finish_run(
                run_id,
                new_count=len(diff.new_files),
                changed_count=len(diff.changed_files),
                removed_count=len(diff.removed_files),
                status="ok",
            )
    read_plan = plan_read(
        "refresh repository knowledge layer" if config.write else "inspect repository summaries",
        [directory_metadata[path] for path in sorted(directory_metadata)],
        [file_metadata[path] for path in sorted(file_metadata)],
    )
    return {
        "root": str(config.root),
        "mode": "refresh" if config.write else "scan",
        "backend": config.backend,
        "new_files": sorted(diff.new_files),
        "changed_files": sorted(diff.changed_files),
        "removed_files": sorted(diff.removed_files),
        "unchanged_files": len(diff.unchanged_files),
        "written_guides": written_guides,
        "exported_guides": exported_guides,
        "removed_artifacts": removed_artifacts,
        "file_metadata_count": len(file_metadata),
        "section_index_count": len(section_indexes),
        "directory_count": len(directory_metadata),
        "manifest_path": str(manifest_path),
        "read_plan": read_plan,
    }


def _prepare_layout(config: IndexerConfig) -> None:
    for path in (
        config.scanmeta_root,
        config.state_dir,
        config.files_dir,
        config.sections_dir,
        config.dirs_dir,
        config.generated_dir,
        config.runs_dir,
    ):
        ensure_dir(path)


def _remove_deleted_artifacts(config, previous_files, previous_dirs, diff, *, persist: bool, state_db: StateDB) -> list[str]:
    removed: list[str] = []
    for rel_path in diff.removed_files:
        previous = previous_files[rel_path]
        if previous.artifact_path:
            remove_file_if_exists(previous.artifact_path)
            removed.append(previous.artifact_path)
        if previous.section_artifact_path:
            remove_file_if_exists(previous.section_artifact_path)
            removed.append(previous.section_artifact_path)
        if persist:
            state_db.remove_file(rel_path)
    for rel_path in diff.removed_dirs:
        previous = previous_dirs[rel_path]
        if previous.artifact_path:
            remove_file_if_exists(previous.artifact_path)
            removed.append(previous.artifact_path)
        if persist:
            state_db.remove_dir(rel_path)
    return sorted(set(removed))


def _build_file_artifacts(*, config: IndexerConfig, snapshot: TreeSnapshot, diff, previous_files, provider, persist: bool, state_db: StateDB):
    file_metadata: dict[str, dict] = {}
    section_indexes: dict[str, dict] = {}
    all_paths = [entry.rel_path for entry in snapshot.files]

    for entry in snapshot.files:
        artifact_path = file_artifact_path(config.files_dir, entry.rel_path)
        section_path = file_artifact_path(config.sections_dir, entry.rel_path)
        needs_rebuild = entry.rel_path in diff.new_files or entry.rel_path in diff.changed_files or not artifact_path.exists()
        section_needed = should_index_sections(entry, config)
        if needs_rebuild:
            raw = entry.abs_path.read_bytes()
            text = "" if entry.is_binary else raw.decode("utf-8", errors="replace")
            section_index = None
            priority_sections: list[dict[str, str]] = []
            if section_needed:
                section_index = build_section_index(entry, text, provider)
                section_indexes[entry.rel_path] = section_index
                priority_sections = [
                    {"id": section["id"], "reason": section["summary"]}
                    for section in section_index["sections"][:3]
                ]
            metadata = build_file_metadata(
                entry,
                text,
                config=config,
                provider=provider,
                all_paths=all_paths,
                priority_sections=priority_sections,
            )
            file_metadata[entry.rel_path] = metadata
            if persist:
                write_json_if_changed(artifact_path, metadata)
                if section_index:
                    write_json_if_changed(section_path, section_index)
                elif section_path.exists():
                    section_path.unlink()
                if config.inline_markdown_frontmatter and metadata["language"] == "markdown":
                    write_text_if_changed(entry.abs_path, render_inline_markdown_frontmatter(metadata, text))
                state_db.upsert_file(
                    path=entry.rel_path,
                    kind=entry.kind,
                    size=entry.size,
                    mtime_ns=entry.mtime_ns,
                    content_hash=entry.content_hash,
                    status="indexed",
                    artifact_path=str(artifact_path),
                    section_artifact_path=str(section_path) if section_index else None,
                    token_estimate=entry.token_estimate,
                )
                state_db.record_artifact(
                    target_path=entry.rel_path,
                    artifact_type="file_metadata",
                    artifact_path=str(artifact_path),
                    sha256=sha256_bytes(json_dumps(metadata).encode("utf-8")),
                )
                if section_index:
                    state_db.record_artifact(
                        target_path=entry.rel_path,
                        artifact_type="section_index",
                        artifact_path=str(section_path),
                        sha256=sha256_bytes(json_dumps(section_index).encode("utf-8")),
                    )
        else:
            file_metadata[entry.rel_path] = normalize_file_metadata(read_json(artifact_path))
            if section_path.exists():
                section_indexes[entry.rel_path] = normalize_section_index(read_json(section_path))
    return file_metadata, section_indexes


def _build_directory_artifacts(*, config: IndexerConfig, snapshot: TreeSnapshot, diff, previous_dirs, file_metadata, provider, persist: bool, state_db: StateDB):
    directory_metadata: dict[str, dict] = {}
    directory_fingerprints: dict[str, str] = {}
    snapshot_map = {entry.rel_path: entry for entry in snapshot.files}

    for dir_path in sorted(snapshot.directories, key=directory_depth, reverse=True):
        child_files = [
            file_metadata[path]
            for path in sorted(file_metadata)
            if _parent_dir(path) == dir_path
        ]
        child_dirs = [
            directory_metadata[path]
            for path in sorted(directory_metadata)
            if _parent_dir(path) == dir_path
        ]
        child_file_states = [(path, snapshot_map[path].content_hash) for path in sorted(file_metadata) if _parent_dir(path) == dir_path]
        child_dir_states = [(path, directory_fingerprints[path]) for path in sorted(directory_metadata) if _parent_dir(path) == dir_path]
        fingerprint = compute_child_fingerprint(
            dir_path,
            child_file_states=child_file_states,
            child_dir_states=child_dir_states,
        )
        artifact_path = directory_artifact_path(config.dirs_dir, dir_path)
        previous = previous_dirs.get(dir_path)
        needs_rebuild = (
            dir_path in diff.dirty_dirs
            or previous is None
            or previous.child_fingerprint != fingerprint
            or not artifact_path.exists()
        )
        if needs_rebuild:
            metadata = build_directory_metadata(dir_path, child_files=child_files, child_dirs=child_dirs, provider=provider)
            directory_metadata[dir_path] = metadata
            if persist:
                write_json_if_changed(artifact_path, metadata)
                state_db.upsert_dir(path=dir_path, child_fingerprint=fingerprint, status="indexed", artifact_path=str(artifact_path))
                state_db.record_artifact(
                    target_path=dir_path,
                    artifact_type="directory_summary",
                    artifact_path=str(artifact_path),
                    sha256=sha256_bytes(json_dumps(metadata).encode("utf-8")),
                )
        else:
            directory_metadata[dir_path] = normalize_directory_metadata(read_json(artifact_path))
        directory_fingerprints[dir_path] = fingerprint
    return directory_metadata


def _render_manifest(config: IndexerConfig, snapshot: TreeSnapshot, root_metadata: dict, directory_metadata: dict[str, dict], file_metadata: dict[str, dict]) -> dict:
    return {
        "generated_by": "codebase-frontmatter-summary",
        "pipeline_version": PIPELINE_VERSION,
        "root": str(config.root),
        "artifacts_root": ".scanmeta",
        "state_db": ".scanmeta/state/index.sqlite",
        "generated_guides": {
            "agents": ".scanmeta/generated/AGENTS.generated.md",
            "claude": ".scanmeta/generated/CLAUDE.generated.md",
            "repo_map": ".scanmeta/generated/repo-map.md",
        },
        "root_directory_summary": ".scanmeta/dirs/root.json",
        "file_metadata_dir": ".scanmeta/files",
        "section_index_dir": ".scanmeta/sections",
        "directory_summary_dir": ".scanmeta/dirs",
        "file_count": len(snapshot.files),
        "directory_count": len(snapshot.directories),
        "top_directories": [directory_metadata[path]["path"] for path in sorted(directory_metadata)[:8]],
        "top_files": [file_metadata[path]["path"] for path in sorted(file_metadata)[:8]],
        "root_role": root_metadata.get("role", "directory"),
    }


def _doctor(root: Path) -> int:
    try:
        config = IndexerConfig(root=root, write=False)
        errors = []
        for path in sorted((config.files_dir).glob("*.json")):
            try:
                normalize_file_metadata(read_json(path))
            except (SchemaError, FileNotFoundError, ValueError) as exc:
                errors.append(f"{path}: {exc}")
        for path in sorted((config.sections_dir).glob("*.json")):
            try:
                normalize_section_index(read_json(path))
            except (SchemaError, FileNotFoundError, ValueError) as exc:
                errors.append(f"{path}: {exc}")
        for path in sorted((config.dirs_dir).glob("*.json")):
            try:
                normalize_directory_metadata(read_json(path))
            except (SchemaError, FileNotFoundError, ValueError) as exc:
                errors.append(f"{path}: {exc}")
        if not (config.generated_dir / "AGENTS.generated.md").exists():
            errors.append("missing .scanmeta/generated/AGENTS.generated.md")
        if errors:
            print(json_dumps({"root": str(root), "status": "error", "errors": errors}))
            return 1
        print(json_dumps({"root": str(root), "status": "ok"}))
        return 0
    except Exception as exc:
        print(json_dumps({"root": str(root), "status": "error", "errors": [str(exc)]}))
        return 1


def _export_guides_only(root: Path, *, backend: str) -> int:
    config = IndexerConfig(root=root, backend=backend, write=False)
    root_summary = read_json(config.dirs_dir / "root.json")
    directory_metadata = [read_json(path) for path in sorted(config.dirs_dir.glob("*.json"))]
    file_metadata = [read_json(path) for path in sorted(config.files_dir.glob("*.json"))]
    export_host_guides(config, root_metadata=root_summary, directory_metadata=directory_metadata, file_metadata=file_metadata)
    print(json_dumps({"root": str(root), "status": "ok"}))
    return 0


def _compat_main(argv: list[str] | None) -> int:
    legacy = argparse.ArgumentParser()
    legacy.add_argument("--root", required=True)
    legacy.add_argument("--backend", default="heuristic")
    legacy.add_argument("--model", default="gpt-5.4-mini")
    legacy.add_argument("--reasoning-effort", default="high")
    legacy.add_argument("--write", action="store_true")
    legacy.add_argument("--path")
    legacy.add_argument("--inline-markdown-frontmatter", action="store_true")
    args = legacy.parse_args(argv)
    config = IndexerConfig(
        root=Path(args.root).expanduser().resolve(),
        backend=args.backend,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        write=args.write,
        path_filter=args.path,
        inline_markdown_frontmatter=args.inline_markdown_frontmatter,
    )
    summary = run_index(config)
    print(json_dumps(summary))
    return 0


def _parent_dir(rel_path: str) -> str:
    parent = PurePosixPath(rel_path).parent
    return "." if str(parent) in {"", "."} else parent.as_posix()

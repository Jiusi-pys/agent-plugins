#!/usr/bin/env python3
"""Collect read-only Git change signals for Agentic Review.

This script intentionally reports observable inventory and heuristics only. It does
not execute project code or decide whether a change is safe.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SENSITIVE_PARTS = {
    "auth",
    "authentication",
    "authorization",
    "billing",
    "checkout",
    "crypto",
    "iam",
    "payment",
    "payments",
    "permission",
    "permissions",
    "privacy",
    "secret",
    "secrets",
    "security",
}
CI_PARTS = {".github", ".gitlab", "ci", "workflows"}
MIGRATION_PARTS = {"migration", "migrations", "schema"}
TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__"}
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".adoc", ".txt"}
LOCK_NAMES = {
    "cargo.lock",
    "composer.lock",
    "gemfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}


def run_git(repo: Path, args: list[str], allow_failure: bool = False) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode and not allow_failure:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(message or f"git {' '.join(args)} failed")
    return completed.stdout


def path_parts(path: str) -> set[str]:
    normalized = path.replace("\\", "/").lower()
    parts: set[str] = set()
    for part in normalized.split("/"):
        parts.add(part)
        stem, _ = os.path.splitext(part)
        parts.update(token for token in stem.replace("-", "_").split("_") if token)
    return parts


def matches_parts(path: str, candidates: set[str]) -> bool:
    return bool(path_parts(path) & candidates)


def parse_numstat(text: str) -> tuple[list[dict[str, object]], int, int]:
    files: list[dict[str, object]] = []
    total_added = 0
    total_deleted = 0
    for line in text.splitlines():
        fields = line.split("\t", 2)
        if len(fields) != 3:
            continue
        added_raw, deleted_raw, path = fields
        binary = added_raw == "-" or deleted_raw == "-"
        added = 0 if binary else int(added_raw)
        deleted = 0 if binary else int(deleted_raw)
        total_added += added
        total_deleted += deleted
        files.append(
            {"path": path, "added": added, "deleted": deleted, "binary": binary}
        )
    return files, total_added, total_deleted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit read-only Git change inventory as JSON."
    )
    parser.add_argument("--repo", default=".", help="Repository path (default: current directory)")
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Git baseline to compare with the worktree (default: HEAD)",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=[],
        help="Restrict inventory to a path; repeat as needed",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    try:
        root_text = run_git(repo, ["rev-parse", "--show-toplevel"])
        root = Path(root_text.strip()).resolve()
    except RuntimeError as exc:
        print(json.dumps({"error": "not-a-git-repository", "detail": str(exc)}))
        return 2

    separator = ["--", *args.paths] if args.paths else []
    base_exists = bool(
        run_git(root, ["rev-parse", "--verify", "--quiet", args.base], allow_failure=True).strip()
    )
    if not base_exists:
        print(
            json.dumps(
                {"error": "invalid-baseline", "baseline": args.base, "repository": str(root)}
            )
        )
        return 2

    numstat = run_git(root, ["diff", "--numstat", args.base, *separator])
    changed, total_added, total_deleted = parse_numstat(numstat)
    status = run_git(
        root, ["status", "--porcelain=v1", "--untracked-files=all", "-z", *separator]
    )
    status_entries = [entry for entry in status.split("\0") if entry]
    untracked = [entry[3:] for entry in status_entries if entry.startswith("?? ")]

    changed_paths = [str(item["path"]) for item in changed]
    all_paths = list(dict.fromkeys([*changed_paths, *untracked]))
    total_lines = total_added + total_deleted

    categories = {
        "sensitive": sorted(p for p in all_paths if matches_parts(p, SENSITIVE_PARTS)),
        "ci": sorted(p for p in all_paths if matches_parts(p, CI_PARTS)),
        "migrations": sorted(p for p in all_paths if matches_parts(p, MIGRATION_PARTS)),
        "tests": sorted(p for p in all_paths if matches_parts(p, TEST_PARTS)),
        "lockfiles": sorted(p for p in all_paths if Path(p).name.lower() in LOCK_NAMES),
        "documents": sorted(p for p in all_paths if Path(p).suffix.lower() in DOC_SUFFIXES),
    }
    source_paths = [
        p
        for p in all_paths
        if p not in categories["tests"] and Path(p).suffix.lower() not in DOC_SUFFIXES
    ]

    signals: list[dict[str, str]] = []
    if len(all_paths) > 20 or total_lines > 500:
        signals.append(
            {"name": "large-change", "reason": f"{len(all_paths)} files and {total_lines} changed lines"}
        )
    if categories["sensitive"]:
        signals.append({"name": "sensitive-path", "reason": "paths suggest a trust or money boundary"})
    if categories["ci"]:
        signals.append({"name": "ci-change", "reason": "continuous-integration configuration changed"})
    if categories["migrations"]:
        signals.append({"name": "migration-change", "reason": "schema or migration path changed"})
    if categories["lockfiles"]:
        signals.append({"name": "dependency-change", "reason": "dependency lockfile changed"})
    if source_paths and not categories["tests"]:
        signals.append({"name": "source-without-test-change", "reason": "source changed without a changed test path"})
    if untracked:
        signals.append({"name": "untracked-files", "reason": f"{len(untracked)} untracked files are in scope"})

    result = {
        "repository": str(root),
        "baseline": args.base,
        "path_filters": args.paths,
        "summary": {
            "files": len(all_paths),
            "tracked_files": len(changed),
            "untracked_files": len(untracked),
            "added_lines": total_added,
            "deleted_lines": total_deleted,
        },
        "files": changed,
        "untracked": untracked,
        "categories": categories,
        "signals": signals,
        "caveats": [
            "Path categories are heuristics, not findings or a risk verdict.",
            "Line totals exclude untracked and binary file contents.",
            "This script does not execute tests, linters, builds, or project code.",
        ],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from .validators import normalize_read_plan

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def plan_read(
    task: str,
    candidate_dirs: Iterable[dict],
    candidate_files: Iterable[dict],
    *,
    max_candidates: int = 5,
) -> dict:
    task_terms = Counter(_tokenize(task))
    ranked_dirs = sorted(candidate_dirs, key=lambda item: _score_dir(item, task_terms), reverse=True)
    ranked_files = sorted(candidate_files, key=lambda item: _score_file(item, task_terms), reverse=True)
    selected_files = ranked_files[:max_candidates]

    steps = ["read_root_guides", "read_dir_summaries", "read_file_frontmatter"]
    if any(int(item.get("token_estimate", 0)) >= 2000 for item in selected_files):
        steps.append("read_section_indexes")
    steps.append("read_relevant_sections")
    full_read_required = _needs_full_read(task)
    if full_read_required:
        steps.append("read_full_files")

    return normalize_read_plan(
        {
            "task": task,
            "candidate_dirs": [item.get("path", "") for item in ranked_dirs[:max_candidates]],
            "candidate_files": [item.get("path", "") for item in selected_files],
            "steps": steps,
            "full_read_required": full_read_required,
        }
    )


def _score_dir(item: dict, task_terms: Counter[str]) -> tuple[int, int, int]:
    haystack = _join_values(
        [
            item.get("path", ""),
            item.get("role", ""),
            " ".join(item.get("topics", []) or []),
            " ".join(item.get("key_files", []) or []),
        ]
    )
    overlap = _overlap_score(task_terms, haystack)
    return overlap, len(item.get("key_files", []) or []), -len(item.get("path", ""))


def _score_file(item: dict, task_terms: Counter[str]) -> tuple[int, int, int]:
    haystack = _join_values(
        [
            item.get("path", ""),
            item.get("summary", ""),
            item.get("role", ""),
            " ".join(item.get("tags", []) or []),
            " ".join(item.get("keywords", []) or []),
            " ".join(item.get("exports", []) or []),
        ]
    )
    overlap = _overlap_score(task_terms, haystack)
    importance = {"high": 3, "medium": 2, "low": 1}.get(str(item.get("importance", "medium")), 2)
    token_penalty = -int(item.get("token_estimate", 0))
    return overlap, importance, token_penalty


def _overlap_score(task_terms: Counter[str], haystack: str) -> int:
    if not task_terms:
        return 0
    haystack_terms = set(_tokenize(haystack))
    return sum(weight for term, weight in task_terms.items() if term in haystack_terms)


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value or "") if len(token) > 1]


def _join_values(values: list[str]) -> str:
    return " ".join(value for value in values if value)


def _needs_full_read(task: str) -> bool:
    lowered = task.lower()
    triggers = [
        "patch",
        "modify",
        "edit",
        "fix",
        "change",
        "exact",
        "line",
        "bug",
        "regression",
        "verify behavior",
        "implementation",
    ]
    return any(trigger in lowered for trigger in triggers)

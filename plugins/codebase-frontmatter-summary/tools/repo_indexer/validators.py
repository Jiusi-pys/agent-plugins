from __future__ import annotations

from typing import Any

from .util import ordered_dict

FILE_METADATA_FIELDS = [
    "path",
    "kind",
    "language",
    "role",
    "summary",
    "tags",
    "keywords",
    "exports",
    "defines",
    "depends_on",
    "related_files",
    "related_tests",
    "priority_sections",
    "importance",
    "complexity",
    "token_estimate",
    "confidence",
]

SECTION_INDEX_FIELDS = ["path", "sections"]
DIRECTORY_METADATA_FIELDS = [
    "path",
    "role",
    "key_files",
    "entrypoints",
    "core_files",
    "test_files",
    "config_files",
    "topics",
    "pitfalls",
    "read_order",
    "confidence",
]
READ_PLAN_FIELDS = ["task", "candidate_dirs", "candidate_files", "steps", "full_read_required"]
ALLOWED_IMPORTANCE = {"low", "medium", "high"}
ALLOWED_COMPLEXITY = {"low", "medium", "high"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


class SchemaError(ValueError):
    pass


def normalize_file_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    path = _require_string(raw, "path")
    summary = _clean_summary(raw.get("summary"))
    payload = ordered_dict(
        [
            ("path", path),
            ("kind", _clean_string(raw.get("kind")) or "text"),
            ("language", _clean_string(raw.get("language")) or "text"),
            ("role", _clean_string(raw.get("role")) or "supporting"),
            ("summary", summary or "No summary available."),
            ("tags", _clean_list(raw.get("tags"), limit=8)),
            ("keywords", _clean_list(raw.get("keywords"), limit=12)),
            ("exports", _clean_list(raw.get("exports"), limit=12)),
            ("defines", _clean_list(raw.get("defines"), limit=12)),
            ("depends_on", _clean_list(raw.get("depends_on"), limit=12)),
            ("related_files", _clean_list(raw.get("related_files"), limit=12)),
            ("related_tests", _clean_list(raw.get("related_tests"), limit=12)),
            ("priority_sections", _clean_priority_sections(raw.get("priority_sections"))),
            ("importance", _clean_enum(raw.get("importance"), ALLOWED_IMPORTANCE, default="medium")),
            ("complexity", _clean_enum(raw.get("complexity"), ALLOWED_COMPLEXITY, default="medium")),
            ("token_estimate", _clean_int(raw.get("token_estimate"), default=0)),
            ("confidence", _clean_enum(raw.get("confidence"), ALLOWED_CONFIDENCE, default="medium")),
        ]
    )
    _assert_keys(payload, FILE_METADATA_FIELDS)
    return payload


def normalize_section_index(raw: dict[str, Any]) -> dict[str, Any]:
    path = _require_string(raw, "path")
    sections = raw.get("sections")
    if not isinstance(sections, list):
        raise SchemaError("sections must be a list")
    normalized = []
    for index, item in enumerate(sections, start=1):
        if not isinstance(item, dict):
            raise SchemaError("section items must be objects")
        normalized.append(
            ordered_dict(
                [
                    ("id", _clean_string(item.get("id")) or f"s{index}"),
                    ("title", _clean_string(item.get("title")) or f"Section {index}"),
                    ("start_line", _clean_int(item.get("start_line"), default=1)),
                    ("end_line", _clean_int(item.get("end_line"), default=1)),
                    ("summary", _clean_summary(item.get("summary")) or "No summary available."),
                    ("symbols", _clean_list(item.get("symbols"), limit=12)),
                ]
            )
        )
    payload = ordered_dict([("path", path), ("sections", normalized)])
    _assert_keys(payload, SECTION_INDEX_FIELDS)
    return payload


def normalize_directory_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    payload = ordered_dict(
        [
            ("path", _require_string(raw, "path")),
            ("role", _clean_string(raw.get("role")) or "directory"),
            ("key_files", _clean_list(raw.get("key_files"), limit=12)),
            ("entrypoints", _clean_list(raw.get("entrypoints"), limit=12)),
            ("core_files", _clean_list(raw.get("core_files"), limit=12)),
            ("test_files", _clean_list(raw.get("test_files"), limit=12)),
            ("config_files", _clean_list(raw.get("config_files"), limit=12)),
            ("topics", _clean_list(raw.get("topics"), limit=12)),
            ("pitfalls", _clean_list(raw.get("pitfalls"), limit=8)),
            ("read_order", _clean_list(raw.get("read_order"), limit=12)),
            ("confidence", _clean_enum(raw.get("confidence"), ALLOWED_CONFIDENCE, default="medium")),
        ]
    )
    _assert_keys(payload, DIRECTORY_METADATA_FIELDS)
    return payload


def normalize_read_plan(raw: dict[str, Any]) -> dict[str, Any]:
    payload = ordered_dict(
        [
            ("task", _clean_string(raw.get("task")) or ""),
            ("candidate_dirs", _clean_list(raw.get("candidate_dirs"), limit=8)),
            ("candidate_files", _clean_list(raw.get("candidate_files"), limit=8)),
            ("steps", _clean_list(raw.get("steps"), limit=12)),
            ("full_read_required", bool(raw.get("full_read_required"))),
        ]
    )
    _assert_keys(payload, READ_PLAN_FIELDS)
    return payload


def _assert_keys(payload: dict[str, Any], keys: list[str]) -> None:
    if list(payload.keys()) != keys:
        raise SchemaError(f"unexpected key order: {list(payload.keys())}")


def _require_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise SchemaError(f"{key} must be a string")
    cleaned = _clean_string(value)
    if not cleaned:
        raise SchemaError(f"{key} is required")
    return cleaned


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_summary(value: Any) -> str:
    summary = " ".join(_clean_string(value).split())
    return summary[:480]


def _clean_list(value: Any, *, limit: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    result: list[str] = []
    for item in value:
        cleaned = _clean_string(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _clean_priority_sections(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    result: list[dict[str, str]] = []
    if not isinstance(value, list):
        return result
    for item in value:
        if not isinstance(item, dict):
            continue
        section_id = _clean_string(item.get("id"))
        reason = _clean_string(item.get("reason"))
        if section_id:
            result.append(ordered_dict([("id", section_id), ("reason", reason or "Relevant entry point.")]))
    return result[:8]


def _clean_enum(value: Any, allowed: set[str], *, default: str) -> str:
    cleaned = _clean_string(value).lower()
    return cleaned if cleaned in allowed else default


def _clean_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

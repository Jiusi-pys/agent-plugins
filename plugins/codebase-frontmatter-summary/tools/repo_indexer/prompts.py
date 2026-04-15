from __future__ import annotations

import json
from typing import Any


def build_file_summary_prompt(
    *,
    path: str,
    kind_guess: str,
    language_guess: str,
    repo_hints: dict[str, Any],
    token_estimate: int,
    content: str,
) -> str:
    return f"""[system]
You are a repository indexing worker.
Analyze exactly one file and emit strict JSON only.
Do not edit the source file.
Return top-level fields in this order:
path, kind, language, role, summary, tags, keywords, exports, defines,
depends_on, related_files, related_tests, priority_sections,
importance, complexity, token_estimate, confidence

[user]
Path: {path}
Kind guess: {kind_guess}
Language guess: {language_guess}
Repo hints: {json.dumps(repo_hints, ensure_ascii=False)}
Token estimate: {token_estimate}
Content:
```text
{content}
```"""


def build_section_summary_prompt(*, path: str, language: str, numbered_content: str) -> str:
    return f"""[system]
You are a large-file section indexer.
Split the file into semantically meaningful sections and emit strict JSON only.

[user]
Path: {path}
Language: {language}
Content with line numbers:
```text
{numbered_content}
```"""


def build_directory_summary_prompt(*, dir_path: str, child_files: list[dict], child_dirs: list[dict]) -> str:
    return f"""[system]
You are a directory summarization worker.
Produce strict JSON only.

[user]
Directory: {dir_path}
Child file metadata:
{json.dumps(child_files, ensure_ascii=False, indent=2)}

Child directory metadata:
{json.dumps(child_dirs, ensure_ascii=False, indent=2)}
"""


def build_guide_prompt(*, root_metadata: dict, important_dirs: list[dict], important_files: list[dict]) -> str:
    return f"""[system]
You are a repository guide builder.
Generate AGENTS-oriented guidance, not a generic repository summary.
Return JSON with a single field named markdown.

[user]
Root metadata:
{json.dumps(root_metadata, ensure_ascii=False, indent=2)}

Important directories:
{json.dumps(important_dirs, ensure_ascii=False, indent=2)}

Important files:
{json.dumps(important_files, ensure_ascii=False, indent=2)}
"""


def build_repair_prompt(*, schema_name: str, invalid_payload: dict[str, Any], schema: dict[str, Any]) -> str:
    return f"""[system]
Repair the structured output so it matches the schema exactly.
Return JSON only.

[user]
Schema name: {schema_name}
Schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Invalid payload:
{json.dumps(invalid_payload, ensure_ascii=False, indent=2)}
"""

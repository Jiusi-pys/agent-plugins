from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .config import DEFAULT_MODEL, DEFAULT_REASONING_EFFORT, IndexerConfig
from .heuristics import build_directory_candidate, build_file_metadata_candidate, split_sections
from .prompts import (
    build_directory_summary_prompt,
    build_file_summary_prompt,
    build_guide_prompt,
    build_repair_prompt,
    build_section_summary_prompt,
)
from .validators import normalize_directory_metadata, normalize_file_metadata, normalize_section_index

FILE_SCHEMA = {
    "type": "object",
    "properties": {key: {} for key in normalize_file_metadata({"path": "x"}).keys()},
    "required": list(normalize_file_metadata({"path": "x"}).keys()),
}
SECTION_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}, "sections": {"type": "array"}},
    "required": ["path", "sections"],
}
DIRECTORY_SCHEMA = {
    "type": "object",
    "properties": {key: {} for key in normalize_directory_metadata({"path": "."}).keys()},
    "required": list(normalize_directory_metadata({"path": "."}).keys()),
}
GUIDE_SCHEMA = {
    "type": "object",
    "properties": {"markdown": {"type": "string"}},
    "required": ["markdown"],
    "additionalProperties": False,
}


class BaseProvider:
    def summarize_file(
        self,
        *,
        rel_path: str,
        kind: str,
        language: str,
        text: str,
        token_estimate: int,
        repo_hints: dict[str, Any],
        related_files: list[str],
        related_tests: list[str],
        priority_sections: list[dict[str, str]],
    ) -> dict[str, Any]:
        return normalize_file_metadata(
            build_file_metadata_candidate(
                rel_path=rel_path,
                kind=kind,
                language=language,
                text=text,
                token_estimate=token_estimate,
                related_files=related_files,
                related_tests=related_tests,
                priority_sections=priority_sections,
            )
        )

    def summarize_sections(self, *, rel_path: str, language: str, text: str) -> dict[str, Any]:
        return normalize_section_index({"path": rel_path, "sections": split_sections(rel_path, language, text)})

    def summarize_directory(self, *, dir_path: str, child_files: list[dict], child_dirs: list[dict]) -> dict[str, Any]:
        return normalize_directory_metadata(build_directory_candidate(dir_path, child_files, child_dirs))

    def render_guide(self, *, root_metadata: dict, important_dirs: list[dict], important_files: list[dict]) -> str:
        lines = [
            "# Repository Guide",
            "",
            root_metadata.get("role", "Repository index"),
            "",
            "## Repository Map",
            "",
        ]
        if important_dirs:
            for item in important_dirs[:6]:
                lines.append(f"- `{item['path']}`: {item.get('role', 'directory')}")
        else:
            lines.append("- No directory summaries available yet.")
        lines.extend(["", "## Progressive Reading Policy", "", "1. Read `AGENTS.md` and `CLAUDE.md` first.", "2. Read `.scanmeta/dirs/root.json` and the nearest directory summaries.", "3. Read `.scanmeta/files/*.json` for candidate files.", "4. Read section indexes before full files when the file is large.", "5. Escalate to full-file reads only for patching, exact behavior, or unresolved ambiguity.", "", "## High-Signal Files", ""])
        if important_files:
            for item in important_files[:6]:
                lines.append(f"- `{item['path']}`: {item.get('summary', '')}")
        else:
            lines.append("- No file metadata available yet.")
        return "\n".join(lines).rstrip() + "\n"

    def repair_structured_output(self, *, schema_name: str, invalid_payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        return invalid_payload


class CodexProvider(BaseProvider):
    def __init__(self, config: IndexerConfig) -> None:
        self.config = config
        self._backend_module = _load_legacy_codex_backends()

    def summarize_file(self, **kwargs) -> dict[str, Any]:
        heuristic = super().summarize_file(**kwargs)
        prompt = build_file_summary_prompt(
            path=kwargs["rel_path"],
            kind_guess=kwargs["kind"],
            language_guess=kwargs["language"],
            repo_hints=kwargs["repo_hints"],
            token_estimate=kwargs["token_estimate"],
            content=kwargs["text"][: self.config.file_max_chars],
        )
        try:
            response = self._run_json(prompt, FILE_SCHEMA)
            try:
                return normalize_file_metadata(response)
            except Exception:
                repaired = self.repair_structured_output(
                    schema_name="file_metadata",
                    invalid_payload=response,
                    schema=FILE_SCHEMA,
                )
                return normalize_file_metadata(repaired)
        except Exception:
            return heuristic

    def summarize_sections(self, *, rel_path: str, language: str, text: str) -> dict[str, Any]:
        heuristic = super().summarize_sections(rel_path=rel_path, language=language, text=text)
        numbered = "\n".join(f"{index + 1:04d}: {line}" for index, line in enumerate(text.splitlines()))
        try:
            response = self._run_json(
                build_section_summary_prompt(path=rel_path, language=language, numbered_content=numbered),
                SECTION_SCHEMA,
            )
            try:
                return normalize_section_index(response)
            except Exception:
                repaired = self.repair_structured_output(
                    schema_name="section_index",
                    invalid_payload=response,
                    schema=SECTION_SCHEMA,
                )
                return normalize_section_index(repaired)
        except Exception:
            return heuristic

    def summarize_directory(self, *, dir_path: str, child_files: list[dict], child_dirs: list[dict]) -> dict[str, Any]:
        heuristic = super().summarize_directory(dir_path=dir_path, child_files=child_files, child_dirs=child_dirs)
        try:
            response = self._run_json(
                build_directory_summary_prompt(dir_path=dir_path, child_files=child_files, child_dirs=child_dirs),
                DIRECTORY_SCHEMA,
            )
            try:
                return normalize_directory_metadata(response)
            except Exception:
                repaired = self.repair_structured_output(
                    schema_name="directory_metadata",
                    invalid_payload=response,
                    schema=DIRECTORY_SCHEMA,
                )
                return normalize_directory_metadata(repaired)
        except Exception:
            return heuristic

    def render_guide(self, *, root_metadata: dict, important_dirs: list[dict], important_files: list[dict]) -> str:
        heuristic = super().render_guide(
            root_metadata=root_metadata,
            important_dirs=important_dirs,
            important_files=important_files,
        )
        try:
            response = self._run_json(
                build_guide_prompt(
                    root_metadata=root_metadata,
                    important_dirs=important_dirs,
                    important_files=important_files,
                ),
                GUIDE_SCHEMA,
            )
            markdown = str(response.get("markdown", "")).strip()
            return markdown + ("\n" if markdown and not markdown.endswith("\n") else "")
        except Exception:
            return heuristic

    def repair_structured_output(self, *, schema_name: str, invalid_payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._run_json(
                build_repair_prompt(schema_name=schema_name, invalid_payload=invalid_payload, schema=schema),
                schema,
            )
        except Exception:
            return invalid_payload

    def _run_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return self._backend_module.run_json_task(
            prompt,
            output_schema=schema,
            backend=self.config.backend,
            sdk_bridge=(Path(__file__).resolve().parents[2] / "skills" / "codebase-frontmatter-summary" / "scripts" / "codex_sdk_bridge.mjs"),
            working_dir=self.config.root,
            model=self.config.model or DEFAULT_MODEL,
            reasoning_effort=self.config.reasoning_effort or DEFAULT_REASONING_EFFORT,
        )


def build_provider(config: IndexerConfig) -> BaseProvider:
    if config.backend == "heuristic":
        return BaseProvider()
    return CodexProvider(config)


def _load_legacy_codex_backends():
    module_path = Path(__file__).resolve().parents[2] / "skills" / "codebase-frontmatter-summary" / "scripts" / "codex_backends.py"
    spec = importlib.util.spec_from_file_location("_repo_indexer_codex_backends", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load Codex backends from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

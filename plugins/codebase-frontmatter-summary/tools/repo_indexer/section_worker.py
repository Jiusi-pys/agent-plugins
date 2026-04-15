from __future__ import annotations

from .config import IndexerConfig
from .scanner import FileSnapshot
from .validators import normalize_section_index


def should_index_sections(snapshot: FileSnapshot, config: IndexerConfig) -> bool:
    if snapshot.is_binary:
        return False
    return (
        snapshot.token_estimate >= config.large_file_token_threshold
        or snapshot.line_count >= config.large_file_line_threshold
    )


def build_section_index(snapshot: FileSnapshot, text: str, provider) -> dict:
    return normalize_section_index(provider.summarize_sections(rel_path=snapshot.rel_path, language=snapshot.language, text=text))

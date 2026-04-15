from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PIPELINE_VERSION = "2.0.0"
FILE_METADATA_VERSION = "2.0.0"
SECTION_INDEX_VERSION = "2.0.0"
DIRECTORY_SUMMARY_VERSION = "2.0.0"
GUIDE_VERSION = "2.0.0"

PLUGIN_NAME = "codebase-frontmatter-summary"
DEFAULT_BACKEND = "heuristic"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "high"
LARGE_FILE_TOKEN_THRESHOLD = 2200
LARGE_FILE_LINE_THRESHOLD = 180
DEFAULT_FILE_MAX_CHARS = 12000
DEFAULT_DIRECTORY_MAX_CHARS = 12000

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".scanmeta",
    ".claude",
    ".agents",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
}

DEFAULT_EXCLUDED_FILES = {
    ".DS_Store",
    "AGENTS.md",
    "CLAUDE.md",
    "CLAUDE.local.md",
    "scan-manifest.json",
}


@dataclass(frozen=True)
class IndexerConfig:
    root: Path
    backend: str = DEFAULT_BACKEND
    model: str = DEFAULT_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    write: bool = True
    export_guides: bool = True
    inline_markdown_frontmatter: bool = False
    path_filter: str | None = None
    file_max_chars: int = DEFAULT_FILE_MAX_CHARS
    directory_max_chars: int = DEFAULT_DIRECTORY_MAX_CHARS
    large_file_token_threshold: int = LARGE_FILE_TOKEN_THRESHOLD
    large_file_line_threshold: int = LARGE_FILE_LINE_THRESHOLD

    @property
    def scanmeta_root(self) -> Path:
        return self.root / ".scanmeta"

    @property
    def state_dir(self) -> Path:
        return self.scanmeta_root / "state"

    @property
    def files_dir(self) -> Path:
        return self.scanmeta_root / "files"

    @property
    def sections_dir(self) -> Path:
        return self.scanmeta_root / "sections"

    @property
    def dirs_dir(self) -> Path:
        return self.scanmeta_root / "dirs"

    @property
    def generated_dir(self) -> Path:
        return self.scanmeta_root / "generated"

    @property
    def runs_dir(self) -> Path:
        return self.scanmeta_root / "runs"

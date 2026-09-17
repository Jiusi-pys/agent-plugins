from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import (
    DIRECTORY_SUMMARY_VERSION,
    FILE_METADATA_VERSION,
    GUIDE_VERSION,
    PIPELINE_VERSION,
    SECTION_INDEX_VERSION,
)
from .util import ensure_dir, utc_now


@dataclass(frozen=True)
class FileState:
    path: str
    kind: str
    size: int
    mtime_ns: int
    content_hash: str
    status: str
    last_indexed_at: str | None
    frontmatter_version: str
    section_version: str
    pipeline_version: str
    artifact_path: str | None
    section_artifact_path: str | None
    token_estimate: int


@dataclass(frozen=True)
class DirState:
    path: str
    child_fingerprint: str
    status: str
    last_indexed_at: str | None
    summary_version: str
    artifact_path: str | None


class StateDB:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.db_path = root / ".scanmeta" / "state" / "index.sqlite"

    def connect(self) -> sqlite3.Connection:
        ensure_dir(self.db_path.parent)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        self._ensure_schema(connection)
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            self._write_schema_versions(connection)
            connection.commit()

    def load_files(self) -> dict[str, FileState]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM files").fetchall()
        return {row["path"]: _row_to_file_state(row) for row in rows}

    def load_dirs(self) -> dict[str, DirState]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM dirs").fetchall()
        return {row["path"]: _row_to_dir_state(row) for row in rows}

    def start_run(self, mode: str) -> str:
        run_id = utc_now().replace(":", "-")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO runs (
                  run_id, started_at, finished_at, mode,
                  new_count, changed_count, removed_count, status
                ) VALUES (?, ?, NULL, ?, 0, 0, 0, 'running')
                """,
                (run_id, utc_now(), mode),
            )
            connection.commit()
        return run_id

    def finish_run(self, run_id: str, *, new_count: int, changed_count: int, removed_count: int, status: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE runs
                   SET finished_at = ?, new_count = ?, changed_count = ?, removed_count = ?, status = ?
                 WHERE run_id = ?
                """,
                (utc_now(), new_count, changed_count, removed_count, status, run_id),
            )
            connection.commit()

    def upsert_file(
        self,
        *,
        path: str,
        kind: str,
        size: int,
        mtime_ns: int,
        content_hash: str,
        status: str,
        artifact_path: str | None,
        section_artifact_path: str | None,
        token_estimate: int,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO files (
                  path, kind, size, mtime_ns, content_hash, status, last_indexed_at,
                  frontmatter_version, section_version, pipeline_version,
                  artifact_path, section_artifact_path, token_estimate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                  kind = excluded.kind,
                  size = excluded.size,
                  mtime_ns = excluded.mtime_ns,
                  content_hash = excluded.content_hash,
                  status = excluded.status,
                  last_indexed_at = excluded.last_indexed_at,
                  frontmatter_version = excluded.frontmatter_version,
                  section_version = excluded.section_version,
                  pipeline_version = excluded.pipeline_version,
                  artifact_path = excluded.artifact_path,
                  section_artifact_path = excluded.section_artifact_path,
                  token_estimate = excluded.token_estimate
                """,
                (
                    path,
                    kind,
                    size,
                    mtime_ns,
                    content_hash,
                    status,
                    utc_now(),
                    FILE_METADATA_VERSION,
                    SECTION_INDEX_VERSION,
                    PIPELINE_VERSION,
                    artifact_path,
                    section_artifact_path,
                    token_estimate,
                ),
            )
            connection.commit()

    def remove_file(self, path: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM files WHERE path = ?", (path,))
            connection.execute("DELETE FROM artifacts WHERE target_path = ?", (path,))
            connection.commit()

    def upsert_dir(self, *, path: str, child_fingerprint: str, status: str, artifact_path: str | None) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO dirs (path, child_fingerprint, status, last_indexed_at, summary_version, artifact_path)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                  child_fingerprint = excluded.child_fingerprint,
                  status = excluded.status,
                  last_indexed_at = excluded.last_indexed_at,
                  summary_version = excluded.summary_version,
                  artifact_path = excluded.artifact_path
                """,
                (path, child_fingerprint, status, utc_now(), DIRECTORY_SUMMARY_VERSION, artifact_path),
            )
            connection.commit()

    def remove_dir(self, path: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM dirs WHERE path = ?", (path,))
            connection.execute("DELETE FROM artifacts WHERE target_path = ?", (path,))
            connection.commit()

    def record_artifact(self, *, target_path: str, artifact_type: str, artifact_path: str, sha256: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO artifacts (target_path, artifact_type, artifact_path, sha256, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(target_path, artifact_type) DO UPDATE SET
                  artifact_path = excluded.artifact_path,
                  sha256 = excluded.sha256,
                  updated_at = excluded.updated_at
                """,
                (target_path, artifact_type, artifact_path, sha256, utc_now()),
            )
            connection.commit()

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS files (
              path TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              size INTEGER NOT NULL,
              mtime_ns INTEGER NOT NULL,
              content_hash TEXT NOT NULL,
              status TEXT NOT NULL,
              last_indexed_at TEXT,
              frontmatter_version TEXT NOT NULL,
              section_version TEXT NOT NULL,
              pipeline_version TEXT NOT NULL,
              artifact_path TEXT,
              section_artifact_path TEXT,
              token_estimate INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS dirs (
              path TEXT PRIMARY KEY,
              child_fingerprint TEXT NOT NULL,
              status TEXT NOT NULL,
              last_indexed_at TEXT,
              summary_version TEXT NOT NULL,
              artifact_path TEXT
            );

            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              mode TEXT NOT NULL,
              new_count INTEGER NOT NULL,
              changed_count INTEGER NOT NULL,
              removed_count INTEGER NOT NULL,
              status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS artifacts (
              target_path TEXT NOT NULL,
              artifact_type TEXT NOT NULL,
              artifact_path TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (target_path, artifact_type)
            );

            CREATE TABLE IF NOT EXISTS schema_versions (
              name TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        self._write_schema_versions(connection)

    def _write_schema_versions(self, connection: sqlite3.Connection) -> None:
        connection.executemany(
            "INSERT OR REPLACE INTO schema_versions (name, value) VALUES (?, ?)",
            [
                ("pipeline", PIPELINE_VERSION),
                ("file_metadata", FILE_METADATA_VERSION),
                ("section_index", SECTION_INDEX_VERSION),
                ("directory_summary", DIRECTORY_SUMMARY_VERSION),
                ("guide", GUIDE_VERSION),
            ],
        )


def _row_to_file_state(row: sqlite3.Row) -> FileState:
    return FileState(
        path=row["path"],
        kind=row["kind"],
        size=row["size"],
        mtime_ns=row["mtime_ns"],
        content_hash=row["content_hash"],
        status=row["status"],
        last_indexed_at=row["last_indexed_at"],
        frontmatter_version=row["frontmatter_version"],
        section_version=row["section_version"],
        pipeline_version=row["pipeline_version"],
        artifact_path=row["artifact_path"],
        section_artifact_path=row["section_artifact_path"],
        token_estimate=row["token_estimate"],
    )


def _row_to_dir_state(row: sqlite3.Row) -> DirState:
    return DirState(
        path=row["path"],
        child_fingerprint=row["child_fingerprint"],
        status=row["status"],
        last_indexed_at=row["last_indexed_at"],
        summary_version=row["summary_version"],
        artifact_path=row["artifact_path"],
    )

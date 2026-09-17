from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")
    return True


def write_json_if_changed(path: Path, payload: dict[str, Any] | list[Any]) -> bool:
    text = json_dumps(payload) + "\n"
    return write_text_if_changed(path, text)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def artifact_stem(rel_path: str, *, root_name: str = "root") -> str:
    normalized = rel_path.strip("./")
    if not normalized:
        return root_name
    safe = normalized.replace("\\", "/").replace("/", "__")
    return safe


def file_artifact_path(base_dir: Path, rel_path: str, suffix: str = ".json") -> Path:
    return base_dir / f"{artifact_stem(rel_path)}{suffix}"


def directory_artifact_path(base_dir: Path, rel_path: str) -> Path:
    return base_dir / f"{artifact_stem(rel_path)}.json"


def generated_artifact_path(base_dir: Path, name: str) -> Path:
    return base_dir / name


def approx_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def parent_directories(rel_path: str) -> list[str]:
    path = PurePosixPath(rel_path)
    directories: list[str] = []
    current = path.parent
    while str(current) not in {"", "."}:
        directories.append(current.as_posix())
        current = current.parent
    directories.append(".")
    return directories


def directory_depth(rel_path: str) -> int:
    if rel_path in {"", "."}:
        return 0
    return len(PurePosixPath(rel_path).parts)


def fingerprint_parts(parts: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for part in sorted(parts):
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def ordered_dict(pairs: list[tuple[str, Any]]) -> OrderedDict[str, Any]:
    return OrderedDict(pairs)


def remove_file_if_exists(path: str | Path | None) -> None:
    if not path:
        return
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()

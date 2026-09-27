"""Small deterministic helpers; workflow decisions remain with the host agent."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_json(path):
    path = Path(path)
    if path.stat().st_size > 64 * 1024**2:
        raise ValueError('JSON exceeds 64 MiB: ' + str(path))
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Non-finite JSON number: ' + value)
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)


def save_json(path, value):
    """Atomic replacement for coordinator-owned state, never for original books."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    fd, tmp = tempfile.mkstemp(prefix='.book-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(payload)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty ' + label)
    return value


def exact_coverage(actual, expected):
    if not isinstance(actual, list) or not all(isinstance(x, str) for x in actual):
        raise ValueError('Invalid coverage list')
    if len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise ValueError('Incomplete, duplicate or unknown segment coverage')

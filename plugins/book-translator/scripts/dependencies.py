"""Explicit adapter for the existing EPUB editor, not a plugin auto-installer."""
from pathlib import Path
import re
import subprocess
import sys
import json

from common import load_json, file_digest

FILES = ('skills/epub-edit/SKILL.md', 'scripts/epub_editor.py', 'scripts/epub_metadata.py')
OPTIONAL_FILES = ('scripts/ebook_reading_layout.py',)


def editor_files(root):
    """Lock optional imported helpers when present, retaining legacy packages."""
    manifest = 'plugin.json' if (root / 'plugin.json').is_file() else '.codex-plugin/plugin.json'
    optional = tuple(name for name in OPTIONAL_FILES
                     if (root / name).exists() or (root / name).is_symlink())
    return (manifest, *FILES, *optional)


def inside(root, relative):
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Dependency path escapes plugin: ' + relative)
    return path


def resolve_editor(root):
    root = Path(root).resolve(strict=True)
    expected_files = editor_files(root)
    manifest_path = expected_files[0]
    manifest = load_json(inside(root, manifest_path))
    if manifest.get('name') != 'epub-editor':
        raise ValueError('Expected epub-editor plugin identity')
    version = manifest.get('version', '')
    if not re.fullmatch(r'0\.(?:1|2)\.\d+(?:\+[A-Za-z0-9.-]+)?', version):
        raise ValueError('Untested epub-editor version: ' + str(version))
    hashes = {name: file_digest(inside(root, name)) for name in expected_files}
    help_result = subprocess.run([sys.executable, str(inside(root, 'scripts/epub_editor.py')), '--help'],
                                 capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
    if help_result.returncode or not all(flag in help_result.stdout for flag in ('--metadata', '--inspect', '--recount')):
        raise ValueError('EPUB editor CLI/dependencies unavailable: ' + help_result.stderr[-1500:])
    supports_style = bool(re.search(r'(?<![\w-])--reading-style(?![\w-])', help_result.stdout))
    return {'name': 'epub-editor', 'root': str(root), 'version': version, 'adapter': 'epub-editor-cli-v1',
            'python': sys.executable, 'files': hashes,
            'capabilities': {'reading_style': supports_style}}


def verify_editor(lock):
    if lock.get('name') != 'epub-editor' or lock.get('adapter') != 'epub-editor-cli-v1':
        raise ValueError('Invalid dependency lock')
    capabilities = lock.get('capabilities', {})
    if not isinstance(capabilities, dict) or type(capabilities.get('reading_style', False)) is not bool:
        raise ValueError('Invalid dependency capabilities')
    root = Path(lock['root']).resolve(strict=True)
    expected = set(editor_files(root))
    if set(lock.get('files', {})) != expected:
        raise ValueError('Incomplete dependency lock')
    for relative, checksum in lock['files'].items():
        if file_digest(inside(root, relative)) != checksum:
            raise ValueError('Dependency changed; prepare/review again: ' + relative)
    return inside(root, 'scripts/epub_editor.py')


def call_editor(lock, source, output=None, metadata=None):
    script = verify_editor(lock)
    args = [sys.executable, str(script), str(source)]
    if output is None:
        args += ['--inspect']
    else:
        args += [str(output), '--metadata', str(metadata), '--recount']
        if lock.get('capabilities', {}).get('reading_style', False):
            args += ['--reading-style', 'preserve']
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    if result.returncode != 0:
        raise ValueError(f'EPUB editor exit {result.returncode}: {result.stderr[-1500:]} {result.stdout[-1500:]}')
    try:
        report = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError('EPUB editor returned non-JSON output') from exc
    if not isinstance(report, dict) or (output is not None and report.get('issues') != []):
        raise ValueError('EPUB editor issues or missing completion report')
    if output is None and not isinstance(report.get('metadata'), dict):
        raise ValueError('EPUB editor inspect did not return metadata')
    if output is not None and not Path(output).is_file():
        raise ValueError('EPUB editor reported success without output')
    return report

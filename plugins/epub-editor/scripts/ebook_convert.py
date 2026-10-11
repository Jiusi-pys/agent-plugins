"""Convert local books through Calibre/Pandoc without overwriting user files."""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import etree as E

from ebook_safety import (UnsafeBook, stage_text, inspect_epub, pandoc_epub,
                         validate_file, validate_assets, markdown_images, embed_markdown_images,
                         rtf_ast_bookmarks, odt_bookmarks)

KINDS = ('txt', 'epub', 'mobi', 'html', 'markdown', 'azw3', 'docx', 'rtf', 'fb2', 'odt')
ALIASES = {'htm': 'html', 'md': 'markdown', 'markdown': 'markdown'}
EXTENSIONS = {'markdown': 'md', 'html': 'html'}


class ConversionError(ValueError):
    def __init__(self, message, kind='conversion', issues=None):
        super().__init__(message)
        self.issues = issues or [{'kind': kind, 'message': str(message)}]


def formats():
    return {'input': list(KINDS), 'output': list(KINDS), 'aliases': dict(ALIASES)}


def _kind(path):
    extension = path.suffix.lower().lstrip('.')
    kind = ALIASES.get(extension, extension)
    if kind not in KINDS:
        raise ConversionError('Unsupported book format: .' + extension, 'unsupported_format')
    return kind


def _find_engine(name, explicit=None):
    env_name = 'CALIBRE_EBOOK_CONVERT' if name == 'calibre' else 'PANDOC_PATH'
    requested = explicit or os.environ.get(env_name)
    if requested:
        candidate = Path(requested).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(str(requested))
        return str(Path(found).resolve()) if found else None
    command = 'ebook-convert' if name == 'calibre' else 'pandoc'
    found = shutil.which(command)
    if found:
        return str(Path(found).resolve())
    if os.name == 'nt':
        folders = [os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)'), os.environ.get('LOCALAPPDATA')]
        relative = ('Calibre2/ebook-convert.exe', 'Calibre/ebook-convert.exe') if name == 'calibre' else ('Pandoc/pandoc.exe', 'Programs/Pandoc/pandoc.exe')
        for folder in filter(None, folders):
            for suffix in relative:
                candidate = Path(folder) / suffix
                if candidate.is_file():
                    return str(candidate.resolve())
    return None


def doctor(calibre=None, pandoc=None):
    report = {'issues': []}
    for name, explicit in (('calibre', calibre), ('pandoc', pandoc)):
        executable = _find_engine(name, explicit)
        state = {'available': False, 'path': executable, 'version': None}
        if executable:
            try:
                result = subprocess.run([executable, '--version'], capture_output=True, text=True,
                                        encoding='utf-8', errors='replace', timeout=10, shell=False)
                if result.returncode != 0:
                    raise ConversionError('Engine --version failed: ' + result.stderr[-2000:])
                state.update(available=True, version=result.stdout.strip() or result.stderr.strip())
            except (OSError, subprocess.TimeoutExpired, ConversionError) as exc:
                report['issues'].append({'kind': 'engine_probe', 'message': name + ': ' + str(exc)})
        else:
            report['issues'].append({'kind': 'missing_engine', 'message': name + ' not found; specify --' + name + ' or install its official CLI'})
        report[name] = state
    return report


def _run(args, stage, deadline, env, name):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ConversionError('Conversion timeout expired', 'engine_timeout')
    try:
        result = subprocess.run(args, cwd=str(stage), capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=remaining,
                                shell=False, env=env)
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(name + ' exceeded the conversion timeout', 'engine_timeout') from exc
    except OSError as exc:
        raise ConversionError('Cannot run ' + name + ': ' + str(exc), 'engine_execution') from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout)[-5000:]
        raise ConversionError(name + ' failed with exit ' + str(result.returncode) + ': ' + details, 'engine_failure')
    if result.stderr.strip() or re.search(r'(?im)^\s*(?:\[warning\]|warning\s*:)', result.stdout):
        raise ConversionError(name + ' reported diagnostics: ' + (result.stderr or result.stdout)[-5000:], 'engine_warning')


def _publish(candidate, output, staged_assets=None):
    """Own each new file with exclusive creation; roll back only those we own."""
    created_files = []
    created_dirs = []
    destination_assets = output.parent / (output.stem + '_assets')
    try:
        if staged_assets and staged_assets.exists():
            files = validate_assets(staged_assets)
            if files:
                destination_assets.mkdir()
                created_dirs.append(destination_assets)
                for source in files:
                    destination = destination_assets / source.relative_to(staged_assets)
                    pending = []
                    parent = destination.parent
                    while not parent.exists():
                        pending.append(parent)
                        parent = parent.parent
                    for folder in reversed(pending):
                        folder.mkdir()
                        created_dirs.append(folder)
                    with destination.open('xb') as stream:
                        created_files.append(destination)
                        with source.open('rb') as reader:
                            shutil.copyfileobj(reader, stream)
        with output.open('xb') as stream:
            created_files.append(output)
            with candidate.open('rb') as reader:
                shutil.copyfileobj(reader, stream)
    except Exception:
        for path in reversed(created_files):
            path.unlink(missing_ok=True)
        for path in reversed(created_dirs):
            path.rmdir()
        raise
    return [str(destination_assets)] if created_dirs else []


def _check_md(candidate, staged_assets, stage):
    files = validate_assets(staged_assets)
    for url in markdown_images(candidate.read_text(encoding='utf-8')):
        parsed = urlsplit(url)
        if parsed.scheme == 'data':
            continue
        if parsed.scheme or parsed.netloc or '\\' in parsed.path:
            raise ConversionError('Markdown output image is not local: ' + url, 'output_resource')
        if not parsed.path:
            raise ConversionError('Empty Markdown image path', 'output_resource')
        relative = Path(unquote(parsed.path))
        resolved = (stage / relative).resolve()
        if relative.is_absolute() or not resolved.is_relative_to(staged_assets.resolve()) or resolved not in files:
            raise ConversionError('Missing or escaping Markdown output image: ' + url, 'output_resource')


def convert(source, output, *, calibre=None, pandoc=None, input_encoding='utf-8', timeout=120):
    unresolved_output = Path(output).expanduser()
    if unresolved_output.is_symlink():
        raise ConversionError('Output is a symbolic link: ' + str(unresolved_output), 'output_conflict')
    source, output = Path(source).expanduser().resolve(), unresolved_output.resolve()
    input_kind, output_kind = _kind(source), _kind(output)
    if source == output:
        raise ConversionError('Input and output must differ', 'output_conflict')
    if not source.is_file():
        raise ConversionError('Input file not found: ' + str(source), 'missing_input')
    if output.exists() or output.is_symlink():
        raise ConversionError('Output already exists: ' + str(output), 'output_conflict')
    if not output.parent.is_dir():
        raise ConversionError('Output parent directory does not exist: ' + str(output.parent), 'output_directory')
    assets_output = output.parent / (output.stem + '_assets')
    if output_kind == 'markdown' and (assets_output.exists() or assets_output.is_symlink()):
        raise ConversionError('Output resource directory already exists: ' + str(assets_output), 'output_conflict')
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ConversionError('--timeout must be a positive finite number', 'invalid_options')
    deadline = time.monotonic() + timeout
    report = {'output': str(output), 'input_format': input_kind, 'output_format': output_kind,
              'engines': [], 'assets': [], 'warnings': [], 'issues': []}
    if output_kind == 'txt':
        report['warnings'].append('TXT cannot preserve images, styles, linked navigation, or embedded book metadata.')
    elif output_kind in ('mobi', 'rtf', 'markdown', 'odt', 'docx', 'fb2', 'html'):
        report['warnings'].append('Format conversion can change layout, navigation, note presentation, and unsupported metadata; it is not lossless.')
    engine_cache = {}

    def engine(name):
        if name not in engine_cache:
            executable = _find_engine(name, calibre if name == 'calibre' else pandoc)
            if not executable:
                raise ConversionError(name + ' CLI not found; specify --' + name + ' or install ' +
                                      ('Calibre (https://calibre-ebook.com/download)' if name == 'calibre' else 'Pandoc (https://pandoc.org/installing.html)'), 'missing_engine')
            engine_cache[name] = executable
            report['engines'].append({'name': name, 'path': executable})
        return engine_cache[name]

    try:
        with tempfile.TemporaryDirectory(prefix='ebook-convert-') as temporary:
            stage = Path(temporary)
            env = os.environ.copy()
            config = stage / 'calibre-config'
            config.mkdir()
            env['CALIBRE_CONFIG_DIRECTORY'] = str(config)
            env['CALIBRE_TEMP_DIR'] = str(stage)
            epub = stage / 'input.epub'
            if input_kind == 'epub':
                inspect_epub(source)
                shutil.copyfile(source, epub)
            else:
                extension = EXTENSIONS.get(input_kind, input_kind)
                staged_input = stage / 'source' / source.name
                staged_input.parent.mkdir()
                if input_kind in ('txt', 'markdown', 'html'):
                    stage_text(source, staged_input, input_encoding, input_kind)
                else:
                    validate_file(source, input_kind)
                    shutil.copyfile(source, staged_input)
                if input_kind == 'markdown':
                    embed_markdown_images(staged_input)
                    args = [engine('pandoc'), str(staged_input), '--from=markdown', '--to=epub3',
                            '--standalone', '--sandbox', '--fail-if-warnings', '--output', str(epub)]
                    _run(args, stage, deadline, env, 'pandoc')
                else:
                    args = [engine('calibre'), str(staged_input), str(epub)]
                    if input_kind in ('txt', 'html'):
                        args += ['--input-encoding', 'utf-8']
                    if input_kind == 'txt':
                        args += ['--formatting-type', 'plain', '--paragraph-type', 'off']
                    _run(args, stage, deadline, env, 'calibre')
                validate_file(epub, 'epub')
            candidate = stage / ('output.' + EXTENSIONS.get(output_kind, output_kind))
            staged_assets = None
            if output_kind == 'epub':
                candidate = epub
            elif output_kind in ('html', 'markdown', 'odt', 'rtf'):
                normalized = stage / 'pandoc-input.epub'
                if pandoc_epub(epub, normalized):
                    report['warnings'].append('Temporary EPUB anchors, note links, and non-linear documents were normalized for Pandoc; the source book is unchanged.')
                args = [engine('pandoc'), str(normalized), '--from=epub', '--to=' + ('html5' if output_kind == 'html' else output_kind),
                        '--sandbox', '--fail-if-warnings', '--output', str(candidate)]
                if output_kind == 'rtf':
                    ast = stage / 'rtf-bookmarks.json'
                    _run([engine('pandoc'), str(normalized), '--from=epub', '--to=json', '--sandbox',
                          '--fail-if-warnings', '--extract-media=rtf-media', '--output', str(ast)], stage, deadline, env, 'pandoc')
                    rtf_ast_bookmarks(ast)
                    args = [engine('pandoc'), str(ast), '--from=json', '--to=rtf', '--standalone',
                            '--sandbox', '--fail-if-warnings', '--output', str(candidate)]
                if output_kind == 'html':
                    args += ['--standalone', '--embed-resources']
                elif output_kind == 'markdown':
                    staged_assets = stage / assets_output.name
                    args += ['--standalone', '--wrap=none', '--extract-media=' + assets_output.name]
                _run(args, stage, deadline, env, 'pandoc')
                if output_kind == 'odt':
                    odt_bookmarks(candidate)
            else:
                args = [engine('calibre'), str(epub), str(candidate)]
                if output_kind == 'txt':
                    args += ['--txt-output-encoding', 'utf-8', '--txt-output-formatting', 'plain']
                _run(args, stage, deadline, env, 'calibre')
            validate_file(candidate, output_kind)
            if output_kind == 'markdown':
                _check_md(candidate, staged_assets, stage)
            report['assets'] = _publish(candidate, output, staged_assets)
    except ConversionError:
        raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, E.XMLSyntaxError) as exc:
        raise ConversionError(str(exc), 'validation') from exc
    return report


def main():
    class JsonParser(argparse.ArgumentParser):
        def error(self, message):
            print(json.dumps({'issues': [{'kind': 'invalid_options', 'message': message}]}, ensure_ascii=False))
            raise SystemExit(1)
    parser = JsonParser(description=__doc__)
    parser.add_argument('source', type=Path, nargs='?')
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--calibre')
    parser.add_argument('--pandoc')
    parser.add_argument('--input-encoding', default='utf-8')
    parser.add_argument('--timeout', type=float, default=120)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--doctor', action='store_true')
    mode.add_argument('--formats', action='store_true')
    args = parser.parse_args()
    try:
        if args.doctor or args.formats:
            if args.source or args.output:
                raise ConversionError('Diagnostic modes do not accept source or output paths', 'invalid_options')
            report = formats() if args.formats else doctor(args.calibre, args.pandoc)
        else:
            if not args.source or not args.output:
                raise ConversionError('Specify source and output paths, --doctor, or --formats', 'invalid_options')
            report = convert(args.source, args.output, calibre=args.calibre, pandoc=args.pandoc,
                             input_encoding=args.input_encoding, timeout=args.timeout)
        print(json.dumps(report, ensure_ascii=False))
        return 1 if report.get('issues') else 0
    except ConversionError as exc:
        print(json.dumps({'issues': exc.issues}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

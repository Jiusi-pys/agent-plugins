"""Install the actual local catalog in an isolated Codex configuration directory."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def run(repository, test_home):
    repository, test_home = Path(repository).resolve(strict=True), Path(test_home).resolve()
    test_home.mkdir(parents=True, exist_ok=False)
    codex = shutil.which('codex')
    if not codex:
        raise RuntimeError('Codex CLI unavailable')
    # This subprocess-only override uses CODEX_HOME for its documented purpose;
    # the parent shell environment and user's normal config are never mutated.
    environment = dict(os.environ, CODEX_HOME=str(test_home))
    outputs = []
    for arguments in (
        ['plugin', 'marketplace', 'add', str(repository), '--json'],
        ['plugin', 'add', 'epub-editor@jiusi-agent-plugins', '--json'],
        ['plugin', 'add', 'book-translator@jiusi-agent-plugins', '--json'],
        ['plugin', 'list', '--marketplace', 'jiusi-agent-plugins', '--json'],
    ):
        result = subprocess.run([codex, *arguments], env=environment, cwd=repository,
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        outputs.append({'arguments': arguments, 'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            raise RuntimeError(json.dumps(outputs, ensure_ascii=True))
    cache = test_home / 'plugins' / 'cache' / 'jiusi-agent-plugins'
    roots = {}
    for name in ('book-translator', 'epub-editor'):
        # An empty, isolated test home was created above: exactly one install is expected.
        manifests = list((cache / name).glob('*/plugin.json'))
        if len(manifests) != 1:
            raise RuntimeError('Expected exactly one installed manifest for ' + name)
        roots[name] = manifests[0].parent
    result = subprocess.run([sys.executable, str(roots['book-translator'] / 'scripts' / 'book_translate.py'),
                             'doctor', '--epub-editor-root', str(roots['epub-editor'])],
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr)
    for skill in ('book-translate', 'translation-review'):
        if not (roots['book-translator'] / 'skills' / skill / 'SKILL.md').is_file():
            raise RuntimeError('Installed skill missing: ' + skill)
    report = {'status': 'passed', 'roots': {k: str(v) for k, v in roots.items()},
              'doctor': json.loads(result.stdout), 'commands': outputs}
    (test_home / 'install-evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--test-home', required=True)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.repository, arguments.test_home), ensure_ascii=True, indent=2))

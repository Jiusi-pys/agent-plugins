#!/usr/bin/env python3
"""Clean up messy project root directories by organizing files into proper locations."""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional


# File classification rules
FILE_CLASSIFICATION = {
    # Source code → src/
    '.c': 'src', '.cpp': 'src', '.cc': 'src', '.cxx': 'src',
    '.py': 'src', '.rs': 'src', '.go': 'src',
    '.js': 'src', '.ts': 'src', '.jsx': 'src', '.tsx': 'src',
    '.java': 'src', '.kt': 'src', '.scala': 'src',
    
    # Headers → include/
    '.h': 'include', '.hpp': 'include', '.hxx': 'include',
    '.hh': 'include', '.inc': 'include',
    
    # Documentation → docs/
    '.md': 'docs', '.rst': 'docs', '.adoc': 'docs',
    '.tex': 'docs', '.pdf': 'docs',
    
    # Scripts → scripts/
    '.sh': 'scripts', '.bash': 'scripts', '.zsh': 'scripts',
    '.ps1': 'scripts', '.bat': 'scripts', '.cmd': 'scripts',
    
    # Configuration → config/
    '.json': 'config', '.yaml': 'config', '.yml': 'config',
    '.toml': 'config', '.ini': 'config', '.cfg': 'config',
    '.conf': 'config', '.xml': 'config',
    
    # Assets → assets/
    '.png': 'assets', '.jpg': 'assets', '.jpeg': 'assets',
    '.gif': 'assets', '.svg': 'assets', '.ico': 'assets',
    '.mp3': 'assets', '.wav': 'assets', '.ogg': 'assets',
    '.mp4': 'assets', '.webm': 'assets',
    '.ttf': 'assets', '.otf': 'assets', '.woff': 'assets',
    '.woff2': 'assets',
    
    # Data → data/
    '.csv': 'data', '.tsv': 'data',
    '.sql': 'data', '.db': 'data', '.sqlite': 'data',
    '.sqlite3': 'data',
}

# Files that must stay in root (case-insensitive)
ROOT_PROTECTED_FILES = {
    # Documentation
    'readme.md', 'readme.rst', 'readme.txt', 'readme',
    'license', 'license.md', 'license.txt', 'copying',
    'changelog.md', 'changelog', 'history.md',
    'contributing.md', 'code_of_conduct.md',
    'authors', 'authors.md', 'maintainers.md',
    'security.md',
    
    # Version control
    '.gitignore', '.gitattributes', '.gitmodules',
    
    # Editor
    '.editorconfig',
    
    # CI/CD
    '.gitlab-ci.yml', '.travis.yml', 'jenkinsfile',
    'azure-pipelines.yml', '.drone.yml',
    'netlify.toml', 'vercel.json',
    
    # Docker
    'dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    '.dockerignore',
    
    # Build systems
    'cmakelists.txt', 'makefile', 'gnumakefile',
    'configure', 'configure.ac', 'makefile.am',
    'meson.build', 'meson_options.txt',
    
    # Package managers
    'cargo.toml', 'cargo.lock',
    'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'setup.py', 'setup.cfg', 'pyproject.toml',
    'requirements.txt', 'requirements-dev.txt',
    'pipfile', 'pipfile.lock',
    'conanfile.txt', 'conanfile.py', 'vcpkg.json',
    'package.xml',  # ROS2
    
    # Linters/Formatters
    '.clang-format', '.clang-tidy',
    '.eslintrc', '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml',
    '.prettierrc', '.prettierrc.js', '.prettierrc.json',
    '.pylintrc', '.flake8', '.isort.cfg',
    'mypy.ini', '.mypy.ini',
    '.rustfmt.toml', 'rustfmt.toml',
    'clippy.toml', '.clippy.toml',
    
    # Testing
    'pytest.ini', 'conftest.py',
    'jest.config.js', 'vitest.config.js',
    'tox.ini', 'noxfile.py',
    
    # TypeScript/JavaScript
    'tsconfig.json', 'jsconfig.json',
    '.babelrc', 'babel.config.js',
    'webpack.config.js', 'vite.config.js', 'rollup.config.js',
    
    # Environment
    '.env', '.env.local', '.env.development', '.env.production',
    '.python-version', 'runtime.txt',
    'rust-toolchain', 'rust-toolchain.toml',
    
    # Other
    'manifest.in',
    'compile_commands.json',
    'workspace', 'build.bazel',
}


def get_target_directory(file_path: Path) -> Optional[str]:
    """Determine target directory for a file based on extension."""
    ext = file_path.suffix.lower()
    name_lower = file_path.name.lower()
    
    # Check if file is protected
    if name_lower in ROOT_PROTECTED_FILES:
        return None
    
    # Check extension-based classification
    if ext in FILE_CLASSIFICATION:
        return FILE_CLASSIFICATION[ext]
    
    return None


def scan_root(project_path: Path) -> list[tuple[Path, str]]:
    """Scan root directory and identify files to move."""
    moves = []
    
    for item in project_path.iterdir():
        # Skip directories and hidden files (except specific ones)
        if item.is_dir():
            continue
        
        # Check if this file should be moved
        target_dir = get_target_directory(item)
        if target_dir:
            moves.append((item, target_dir))
    
    return moves


def clean_root(project_path: Path, dry_run: bool = False, interactive: bool = False) -> int:
    """Clean root directory by moving files to appropriate locations."""
    moves = scan_root(project_path)
    
    if not moves:
        print("✅ Root directory is already clean!")
        return 0
    
    print(f"Found {len(moves)} files to organize:\n")
    
    moved = 0
    for file_path, target_dir in moves:
        target_path = project_path / target_dir / file_path.name
        rel_source = file_path.relative_to(project_path)
        rel_target = target_path.relative_to(project_path)
        
        if dry_run:
            print(f"  [DRY-RUN] {rel_source} → {rel_target}")
            moved += 1
            continue
        
        if interactive:
            response = input(f"  Move {rel_source} → {rel_target}? [y/N] ").strip().lower()
            if response != 'y':
                print(f"    Skipped")
                continue
        
        # Check if target exists
        if target_path.exists():
            print(f"  ⚠️  Skipping {rel_source}: target already exists")
            continue
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(file_path), str(target_path))
        print(f"  ✓ {rel_source} → {rel_target}")
        moved += 1
    
    if dry_run:
        print(f"\n[DRY-RUN] Would move {moved} files")
    else:
        print(f"\n✅ Moved {moved} files")
    
    return moved


def main():
    parser = argparse.ArgumentParser(
        description='Clean up messy project root directories'
    )
    parser.add_argument('path', type=Path, help='Project path to clean')
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be moved without actually moving'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Ask confirmation for each file'
    )
    
    args = parser.parse_args()
    project_path = args.path.resolve()
    
    if not project_path.exists():
        print(f"Error: Path '{project_path}' does not exist")
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"Error: '{project_path}' is not a directory")
        sys.exit(1)
    
    print(f"Cleaning root directory: {project_path}\n")
    
    moved = clean_root(project_path, args.dry_run, args.interactive)
    
    if moved > 0 and not args.dry_run:
        print("\n💡 Run 'validate_structure.py' to check for remaining issues")


if __name__ == '__main__':
    main()

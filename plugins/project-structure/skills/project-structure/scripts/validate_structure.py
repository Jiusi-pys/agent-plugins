#!/usr/bin/env python3
"""Validate project directory structure and report violations."""

import argparse
import os
import re
import sys
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Violation:
    severity: Severity
    path: Path
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    violations: list[Violation] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return any(v.severity == Severity.ERROR for v in self.violations)
    
    @property
    def has_warnings(self) -> bool:
        return any(v.severity == Severity.WARNING for v in self.violations)


# Root directory whitelist
ROOT_ALLOWED_FILES = {
    # Documentation
    'readme.md', 'readme.rst', 'readme.txt', 'readme',
    'license', 'license.md', 'license.txt', 'copying',
    'changelog.md', 'changelog', 'history.md',
    'contributing.md', 'code_of_conduct.md',
    'authors', 'authors.md', 'maintainers.md',
    # Version control
    '.gitignore', '.gitattributes', '.gitmodules',
    '.hgignore', '.svnignore',
    # Editor
    '.editorconfig',
    # CI/CD
    '.gitlab-ci.yml', '.travis.yml', 'jenkinsfile',
    'azure-pipelines.yml', 'bitbucket-pipelines.yml',
    '.drone.yml', 'netlify.toml', 'vercel.json',
    # Docker
    'dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    '.dockerignore',
    # Security
    'security.md', '.gitleaks.toml',
}

ROOT_ALLOWED_DIRS = {
    # Standard structure
    'src', 'include', 'lib', 'build', 'bin', 'obj',
    'docs', 'doc', 'documentation',
    'scripts', 'script',
    'config', 'configs', 'conf',
    'tests', 'test', 'testing',
    'assets', 'resources', 'res',
    'tools', 'tool', 'utils', 'utilities',
    'examples', 'example', 'samples', 'sample',
    'vendor', 'third_party', 'external', 'deps',
    'data',
    # IDE/Editor
    '.vscode', '.idea', '.vim',
    # CI/CD
    '.github', '.gitlab', '.circleci',
    # Version control
    '.git', '.hg', '.svn',
}

# Type-specific additions
TYPE_SPECIFIC = {
    'c': {
        'files': {
            'cmakelists.txt', 'makefile', 'gnumakefile',
            'configure', 'configure.ac', 'makefile.am',
            'meson.build', 'meson_options.txt',
            'conanfile.txt', 'conanfile.py',
            'vcpkg.json', 'workspace', 'build.bazel',
            '.clang-format', '.clang-tidy',
            'compile_commands.json',
        },
        'dirs': set(),
    },
    'cpp': {
        'files': {
            'cmakelists.txt', 'makefile', 'gnumakefile',
            'configure', 'configure.ac', 'makefile.am',
            'meson.build', 'meson_options.txt',
            'conanfile.txt', 'conanfile.py',
            'vcpkg.json', 'workspace', 'build.bazel',
            '.clang-format', '.clang-tidy',
            'compile_commands.json',
        },
        'dirs': set(),
    },
    'ros2': {
        'files': {
            'package.xml', 'cmakelists.txt', 'setup.py', 'setup.cfg',
            'colcon.pkg', 'colcon_ignore', 'ament_ignore',
        },
        'dirs': {
            'launch', 'msg', 'srv', 'action',
            'resource', 'rviz', 'urdf', 'meshes', 'worlds',
        },
    },
    'python': {
        'files': {
            'setup.py', 'setup.cfg', 'pyproject.toml',
            'requirements.txt', 'requirements-dev.txt',
            'pipfile', 'pipfile.lock',
            'poetry.lock', 'pdm.lock',
            'tox.ini', 'noxfile.py',
            '.python-version', 'runtime.txt',
            'pytest.ini', 'conftest.py',
            '.pylintrc', '.flake8', '.isort.cfg',
            'mypy.ini', '.mypy.ini',
            'manifest.in',
        },
        'dirs': set(),
    },
    'rust': {
        'files': {
            'cargo.toml', 'cargo.lock',
            'rust-toolchain', 'rust-toolchain.toml',
            '.rustfmt.toml', 'rustfmt.toml',
            'clippy.toml', '.clippy.toml',
            'deny.toml',
        },
        'dirs': {'benches', 'target', '.cargo'},
    },
    'nodejs': {
        'files': {
            'package.json', 'package-lock.json',
            'yarn.lock', 'pnpm-lock.yaml',
            '.npmrc', '.yarnrc', '.yarnrc.yml',
            'tsconfig.json', 'jsconfig.json',
            '.eslintrc', '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml',
            '.prettierrc', '.prettierrc.js', '.prettierrc.json',
            '.babelrc', 'babel.config.js',
            'webpack.config.js', 'vite.config.js', 'rollup.config.js',
            'jest.config.js', 'vitest.config.js',
            '.env', '.env.local', '.env.development', '.env.production',
        },
        'dirs': {'node_modules', 'dist', 'public', 'static'},
    },
    'embedded': {
        'files': {
            'cmakelists.txt', 'makefile',
            'platformio.ini',
            '.cproject', '.project',
            'kconfig', 'defconfig', '.config',
        },
        'dirs': {
            'ld', 'linker', 'link',
            'startup', 'boot',
            'drivers', 'hal', 'bsp',
            'board', 'boards',
            'arch', 'cpu',
            'middleware', 'components',
        },
    },
}

# File classification by extension
FILE_CLASSIFICATION = {
    # Source code → src/
    '.c': 'src', '.cpp': 'src', '.cc': 'src', '.cxx': 'src',
    '.py': 'src', '.rs': 'src', '.go': 'src',
    '.js': 'src', '.ts': 'src', '.jsx': 'src', '.tsx': 'src',
    '.java': 'src', '.kt': 'src', '.scala': 'src',
    # Headers → include/
    '.h': 'include', '.hpp': 'include', '.hxx': 'include',
    '.hh': 'include', '.inc': 'include',
    # Scripts → scripts/
    '.sh': 'scripts', '.bash': 'scripts', '.zsh': 'scripts',
    '.ps1': 'scripts', '.bat': 'scripts', '.cmd': 'scripts',
}


def get_allowed_sets(project_type: Optional[str]) -> tuple[set, set]:
    """Get allowed files and directories for project type."""
    allowed_files = ROOT_ALLOWED_FILES.copy()
    allowed_dirs = ROOT_ALLOWED_DIRS.copy()
    
    if project_type and project_type in TYPE_SPECIFIC:
        allowed_files.update(TYPE_SPECIFIC[project_type]['files'])
        allowed_dirs.update(TYPE_SPECIFIC[project_type]['dirs'])
    else:
        # Allow all type-specific entries when no type specified
        for type_config in TYPE_SPECIFIC.values():
            allowed_files.update(type_config['files'])
            allowed_dirs.update(type_config['dirs'])
    
    return allowed_files, allowed_dirs


def detect_project_type(project_path: Path) -> Optional[str]:
    """Auto-detect project type from root files."""
    root_files = {f.name.lower() for f in project_path.iterdir() if f.is_file()}
    
    if 'package.xml' in root_files:
        return 'ros2'
    if 'cargo.toml' in root_files:
        return 'rust'
    if 'package.json' in root_files:
        return 'nodejs'
    if 'pyproject.toml' in root_files or 'setup.py' in root_files:
        return 'python'
    if 'cmakelists.txt' in root_files or 'makefile' in root_files:
        # Check for embedded indicators
        root_dirs = {d.name.lower() for d in project_path.iterdir() if d.is_dir()}
        if root_dirs & {'startup', 'hal', 'drivers', 'ld', 'linker'}:
            return 'embedded'
        # Check for C++ files
        has_cpp = any(project_path.rglob('*.cpp')) or any(project_path.rglob('*.cc'))
        return 'cpp' if has_cpp else 'c'
    
    return None


def validate_root_directory(project_path: Path, project_type: Optional[str]) -> ValidationResult:
    """Validate root directory contents."""
    result = ValidationResult()
    allowed_files, allowed_dirs = get_allowed_sets(project_type)
    
    for item in project_path.iterdir():
        name_lower = item.name.lower()
        
        if item.is_dir():
            if name_lower not in allowed_dirs and not name_lower.startswith('.'):
                result.violations.append(Violation(
                    severity=Severity.WARNING,
                    path=item,
                    message=f"Non-standard directory in root: {item.name}",
                    suggestion=f"Consider moving to standard location or renaming"
                ))
        else:
            # Check if file is allowed
            if name_lower not in allowed_files:
                ext = item.suffix.lower()
                
                # Check if it's a source file that should be in subdirectory
                if ext in FILE_CLASSIFICATION:
                    target_dir = FILE_CLASSIFICATION[ext]
                    result.violations.append(Violation(
                        severity=Severity.ERROR,
                        path=item,
                        message=f"Source file in root directory: {item.name}",
                        suggestion=f"Move to {target_dir}/"
                    ))
                # Check for temporary/backup files
                elif item.name.endswith('~') or item.name.endswith('.swp') or item.name.endswith('.tmp'):
                    result.violations.append(Violation(
                        severity=Severity.ERROR,
                        path=item,
                        message=f"Temporary file in project: {item.name}",
                        suggestion="Delete or add to .gitignore"
                    ))
                # Check for build artifacts
                elif ext in {'.o', '.obj', '.a', '.so', '.dll', '.exe', '.pyc'}:
                    result.violations.append(Violation(
                        severity=Severity.ERROR,
                        path=item,
                        message=f"Build artifact in root: {item.name}",
                        suggestion="Move to build/ or delete"
                    ))
                else:
                    result.violations.append(Violation(
                        severity=Severity.WARNING,
                        path=item,
                        message=f"Unrecognized file in root: {item.name}",
                        suggestion="Consider moving to appropriate subdirectory"
                    ))
    
    return result


def validate_structure(project_path: Path, project_type: Optional[str]) -> ValidationResult:
    """Full project structure validation."""
    result = validate_root_directory(project_path, project_type)
    
    # Check for missing recommended files
    if not (project_path / 'README.md').exists() and not (project_path / 'README.rst').exists():
        result.violations.append(Violation(
            severity=Severity.INFO,
            path=project_path,
            message="Missing README.md",
            suggestion="Add README.md with project description"
        ))
    
    if not (project_path / 'LICENSE').exists() and not (project_path / 'LICENSE.md').exists():
        result.violations.append(Violation(
            severity=Severity.INFO,
            path=project_path,
            message="Missing LICENSE file",
            suggestion="Add LICENSE file with appropriate license"
        ))
    
    if not (project_path / '.gitignore').exists():
        result.violations.append(Violation(
            severity=Severity.INFO,
            path=project_path,
            message="Missing .gitignore",
            suggestion="Add .gitignore to exclude build artifacts"
        ))
    
    # Check for deep nesting
    for path in project_path.rglob('*'):
        if path.is_file():
            depth = len(path.relative_to(project_path).parts)
            if depth > 6:
                result.violations.append(Violation(
                    severity=Severity.WARNING,
                    path=path,
                    message=f"Deep nesting ({depth} levels): {path.relative_to(project_path)}",
                    suggestion="Consider flattening directory structure"
                ))
    
    # Check for empty directories (except .gitkeep)
    for path in project_path.rglob('*'):
        if path.is_dir():
            contents = list(path.iterdir())
            if not contents:
                result.violations.append(Violation(
                    severity=Severity.INFO,
                    path=path,
                    message=f"Empty directory: {path.relative_to(project_path)}",
                    suggestion="Add .gitkeep or remove if unused"
                ))
    
    return result


def fix_violations(project_path: Path, result: ValidationResult) -> int:
    """Attempt to fix violations by moving files."""
    fixed = 0
    
    for violation in result.violations:
        if violation.severity != Severity.ERROR:
            continue
        
        if not violation.path.exists():
            continue
        
        ext = violation.path.suffix.lower()
        if ext in FILE_CLASSIFICATION:
            target_dir = project_path / FILE_CLASSIFICATION[ext]
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / violation.path.name
            
            if not target_path.exists():
                shutil.move(str(violation.path), str(target_path))
                print(f"  Moved: {violation.path.name} → {target_path.relative_to(project_path)}")
                fixed += 1
    
    return fixed


def print_violations(result: ValidationResult, project_path: Path) -> None:
    """Print validation results."""
    if not result.violations:
        print("✅ No violations found!")
        return
    
    errors = [v for v in result.violations if v.severity == Severity.ERROR]
    warnings = [v for v in result.violations if v.severity == Severity.WARNING]
    infos = [v for v in result.violations if v.severity == Severity.INFO]
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for v in errors:
            rel_path = v.path.relative_to(project_path) if v.path != project_path else '.'
            print(f"  [{v.severity.value}] {rel_path}: {v.message}")
            if v.suggestion:
                print(f"           → {v.suggestion}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for v in warnings:
            rel_path = v.path.relative_to(project_path) if v.path != project_path else '.'
            print(f"  [{v.severity.value}] {rel_path}: {v.message}")
            if v.suggestion:
                print(f"           → {v.suggestion}")
    
    if infos:
        print(f"\nℹ️  INFO ({len(infos)}):")
        for v in infos:
            rel_path = v.path.relative_to(project_path) if v.path != project_path else '.'
            print(f"  [{v.severity.value}] {rel_path}: {v.message}")
            if v.suggestion:
                print(f"           → {v.suggestion}")


def main():
    parser = argparse.ArgumentParser(
        description='Validate project directory structure'
    )
    parser.add_argument('path', type=Path, help='Project path to validate')
    parser.add_argument(
        '--type', '-t',
        choices=list(TYPE_SPECIFIC.keys()),
        help='Project type (auto-detected if not specified)'
    )
    parser.add_argument(
        '--fix', '-f',
        action='store_true',
        help='Auto-fix violations by moving misplaced files'
    )
    
    args = parser.parse_args()
    project_path = args.path.resolve()
    
    if not project_path.exists():
        print(f"Error: Path '{project_path}' does not exist")
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"Error: '{project_path}' is not a directory")
        sys.exit(1)
    
    # Detect or use specified project type
    project_type = args.type or detect_project_type(project_path)
    
    print(f"Validating: {project_path}")
    if project_type:
        print(f"Project type: {project_type}")
    else:
        print("Project type: generic (not detected)")
    
    # Validate
    result = validate_structure(project_path, project_type)
    
    # Fix if requested
    if args.fix and result.has_errors:
        print("\nAttempting to fix violations...")
        fixed = fix_violations(project_path, result)
        print(f"Fixed {fixed} violations")
        # Re-validate
        result = validate_structure(project_path, project_type)
    
    # Print results
    print_violations(result, project_path)
    
    # Exit code
    if result.has_errors:
        sys.exit(1)
    elif result.has_warnings:
        sys.exit(0)  # Warnings don't fail
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

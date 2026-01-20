# Project Structure Validation Rules

## Root Directory Whitelist

### Allowed Files (any project type)

```python
ROOT_ALLOWED_FILES = {
    # Documentation
    'README.md', 'README.rst', 'README.txt', 'README',
    'LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING',
    'CHANGELOG.md', 'CHANGELOG', 'HISTORY.md',
    'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md',
    'AUTHORS', 'AUTHORS.md', 'MAINTAINERS.md',
    
    # Version control
    '.gitignore', '.gitattributes', '.gitmodules',
    '.hgignore', '.svnignore',
    
    # Editor/IDE
    '.editorconfig',
    
    # CI/CD
    '.gitlab-ci.yml', '.travis.yml', 'Jenkinsfile',
    'azure-pipelines.yml', 'bitbucket-pipelines.yml',
    '.drone.yml', 'netlify.toml', 'vercel.json',
    
    # Docker
    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    '.dockerignore',
    
    # Security
    'SECURITY.md', '.gitleaks.toml',
}
```

### Allowed Directories (any project type)

```python
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
```

### Type-Specific Additions

#### C/C++
```python
CPP_ROOT_FILES = {
    'CMakeLists.txt', 'Makefile', 'GNUmakefile',
    'configure', 'configure.ac', 'Makefile.am',
    'meson.build', 'meson_options.txt',
    'conanfile.txt', 'conanfile.py',
    'vcpkg.json', 'WORKSPACE', 'BUILD.bazel',
    '.clang-format', '.clang-tidy',
    'compile_commands.json',
}
```

#### ROS2
```python
ROS2_ROOT_FILES = {
    'package.xml', 'CMakeLists.txt', 'setup.py', 'setup.cfg',
    'resource/*',  # ROS2 ament resource marker
    'colcon.pkg', 'COLCON_IGNORE', 'AMENT_IGNORE',
}
ROS2_ROOT_DIRS = {
    'launch', 'msg', 'srv', 'action',
    'resource', 'rviz', 'urdf', 'meshes', 'worlds',
}
```

#### Python
```python
PYTHON_ROOT_FILES = {
    'setup.py', 'setup.cfg', 'pyproject.toml',
    'requirements.txt', 'requirements-dev.txt',
    'Pipfile', 'Pipfile.lock',
    'poetry.lock', 'pdm.lock',
    'tox.ini', 'noxfile.py',
    '.python-version', 'runtime.txt',
    'pytest.ini', 'conftest.py',
    '.pylintrc', '.flake8', '.isort.cfg',
    'mypy.ini', '.mypy.ini',
    'MANIFEST.in',
}
```

#### Rust
```python
RUST_ROOT_FILES = {
    'Cargo.toml', 'Cargo.lock',
    'rust-toolchain', 'rust-toolchain.toml',
    '.rustfmt.toml', 'rustfmt.toml',
    'clippy.toml', '.clippy.toml',
    'deny.toml', '.cargo/config.toml',
}
RUST_ROOT_DIRS = {
    'benches', 'target',
}
```

#### Node.js
```python
NODEJS_ROOT_FILES = {
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
}
NODEJS_ROOT_DIRS = {
    'node_modules', 'dist', 'public', 'static',
}
```

#### Embedded
```python
EMBEDDED_ROOT_FILES = {
    'CMakeLists.txt', 'Makefile',
    'platformio.ini',
    '.cproject', '.project',
    'Kconfig', 'defconfig', '.config',
}
EMBEDDED_ROOT_DIRS = {
    'ld', 'linker', 'link',
    'startup', 'boot',
    'drivers', 'hal', 'bsp',
    'board', 'boards',
    'arch', 'cpu',
    'middleware', 'components',
}
```

## File Classification Rules

### By Extension

```python
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
    '.md': 'docs', '.rst': 'docs', '.txt': 'docs',
    '.adoc': 'docs', '.tex': 'docs',
    
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
    
    # Data → data/
    '.csv': 'data', '.tsv': 'data',
    '.sql': 'data', '.db': 'data', '.sqlite': 'data',
}
```

### By Filename Pattern

```python
FILENAME_CLASSIFICATION = {
    # Test files → tests/
    r'^test_.*\.py$': 'tests',
    r'^.*_test\.py$': 'tests',
    r'^.*\.test\.js$': 'tests',
    r'^.*\.spec\.js$': 'tests',
    r'^.*_test\.go$': 'tests',
    r'^.*_test\.rs$': 'tests',
    
    # Example files → examples/
    r'^example.*': 'examples',
    r'^demo.*': 'examples',
    r'^sample.*': 'examples',
}
```

## Violation Severity

| Severity | Description | Action |
|----------|-------------|--------|
| ERROR | Critical structure violation | Must fix |
| WARNING | Non-standard but acceptable | Should fix |
| INFO | Suggestion for improvement | Optional |

### Error Conditions
- Source files (.c, .cpp, .py, etc.) in root directory
- Build artifacts in root directory
- Temporary files (*~, *.swp, *.tmp) anywhere
- Node_modules or __pycache__ committed to VCS

### Warning Conditions
- Non-standard directory names (e.g., `source` instead of `src`)
- Mixed case in directory names
- Very deep nesting (>5 levels)

### Info Conditions
- Empty directories
- Missing recommended files (README, LICENSE)
- Inconsistent naming conventions

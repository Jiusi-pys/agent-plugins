---
name: project-structure
description: |
  Project engineering file management and directory structure enforcement. Use when:
  (1) Initializing new projects with standardized directory layout
  (2) Validating existing project structure for compliance
  (3) Cleaning up messy root directories by organizing files
  (4) Checking project organization rules and reporting violations
  (5) User asks about project file organization best practices
  Supports: C/C++, ROS2, Python, Rust, Node.js, embedded systems, and general software projects.
---

# Project Structure Management

## Core Principle

**根目录必须保持整洁**。根目录只允许存放：
- 项目配置文件（CMakeLists.txt, Makefile, package.json, Cargo.toml, setup.py 等）
- 版本控制文件（.gitignore, .gitattributes）
- 项目文档（README.md, LICENSE, CHANGELOG.md, CONTRIBUTING.md）
- IDE/编辑器配置目录（.vscode/, .idea/）
- CI/CD 配置（.github/, .gitlab-ci.yml）

**其他一切文件必须归类到对应子目录**。

## Standard Directory Layout

```
project-root/
├── src/              # Source code
│   ├── main/         # Main application code
│   └── lib/          # Library code (if applicable)
├── include/          # Public header files (C/C++)
├── lib/              # Third-party libraries or generated libs
├── build/            # Build outputs (gitignored)
├── bin/              # Compiled binaries (gitignored)
├── docs/             # Documentation
│   ├── api/          # API documentation
│   └── guides/       # User guides
├── scripts/          # Build, deployment, utility scripts
├── config/           # Configuration files
├── tests/            # Test files
│   ├── unit/         # Unit tests
│   └── integration/  # Integration tests
├── assets/           # Static assets (images, data files)
├── tools/            # Development tools and utilities
├── examples/         # Example code or usage demos
└── vendor/           # Vendored dependencies (if not using package manager)
```

## Workflow

### 1. Initialize New Project

Run `scripts/init_project.py`:

```bash
python3 scripts/init_project.py <project-name> --type <project-type> [--path <output-dir>]
```

Project types: `c`, `cpp`, `ros2`, `python`, `rust`, `nodejs`, `embedded`, `generic`

### 2. Validate Existing Project

Run `scripts/validate_structure.py`:

```bash
python3 scripts/validate_structure.py <project-path> [--fix] [--type <project-type>]
```

Options:
- `--fix`: Auto-move misplaced files to correct locations
- `--type`: Specify project type for type-specific rules

### 3. Clean Root Directory

Run `scripts/clean_root.py`:

```bash
python3 scripts/clean_root.py <project-path> [--dry-run] [--interactive]
```

Options:
- `--dry-run`: Show what would be moved without actually moving
- `--interactive`: Ask confirmation for each file

## Project Type Specifics

### C/C++ Projects
- Headers in `include/`, sources in `src/`
- CMakeLists.txt or Makefile in root
- Build outputs to `build/`

### ROS2 Projects
- Package structure follows REP-149
- `package.xml` and `CMakeLists.txt` in root
- Launch files in `launch/`
- Message/Service definitions in `msg/`, `srv/`, `action/`

### Python Projects
- Package code in `src/<package_name>/` or `<package_name>/`
- `setup.py`, `pyproject.toml`, or `setup.cfg` in root
- Tests mirror source structure in `tests/`

### Rust Projects
- Standard Cargo layout
- `Cargo.toml` in root
- Source in `src/`, binary crates in `src/bin/`

### Node.js Projects
- `package.json` in root
- Source in `src/` or `lib/`
- Built files in `dist/`

### Embedded Projects
- Board-specific code in `src/board/`
- HAL/drivers in `src/hal/` or `src/drivers/`
- Linker scripts in `ld/` or `linker/`
- Startup code in `startup/`

## Rules Reference

See `references/rules.md` for complete validation rules.

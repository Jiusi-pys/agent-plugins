#!/usr/bin/env python3
"""Initialize a new project with standardized directory structure."""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Project templates define which directories to create
PROJECT_TEMPLATES = {
    'generic': {
        'dirs': ['src', 'docs', 'scripts', 'config', 'tests', 'assets'],
        'files': {
            'README.md': '# {project_name}\n\nProject description here.\n',
            '.gitignore': '''# Build outputs
build/
bin/
obj/
dist/

# IDE
.vscode/
.idea/
*.swp
*~

# OS
.DS_Store
Thumbs.db
''',
        }
    },
    'c': {
        'dirs': ['src', 'include', 'lib', 'build', 'docs', 'scripts', 'tests'],
        'files': {
            'README.md': '# {project_name}\n\nC project.\n\n## Build\n\n```bash\nmkdir build && cd build\ncmake ..\nmake\n```\n',
            'CMakeLists.txt': '''cmake_minimum_required(VERSION 3.16)
project({project_name} C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

include_directories(include)

file(GLOB_RECURSE SOURCES "src/*.c")

add_executable({project_name} ${{SOURCES}})
''',
            '.gitignore': '''# Build
build/
bin/
*.o
*.a
*.so
*.dylib

# IDE
.vscode/
.idea/
compile_commands.json

# OS
.DS_Store
*~
''',
            'src/.gitkeep': '',
            'include/.gitkeep': '',
        }
    },
    'cpp': {
        'dirs': ['src', 'include', 'lib', 'build', 'docs', 'scripts', 'tests'],
        'files': {
            'README.md': '# {project_name}\n\nC++ project.\n\n## Build\n\n```bash\nmkdir build && cd build\ncmake ..\nmake\n```\n',
            'CMakeLists.txt': '''cmake_minimum_required(VERSION 3.16)
project({project_name} CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

file(GLOB_RECURSE SOURCES "src/*.cpp" "src/*.cc")

add_executable({project_name} ${{SOURCES}})
''',
            '.gitignore': '''# Build
build/
bin/
*.o
*.a
*.so
*.dylib

# IDE
.vscode/
.idea/
compile_commands.json

# OS
.DS_Store
*~
''',
            'src/.gitkeep': '',
            'include/.gitkeep': '',
        }
    },
    'ros2': {
        'dirs': ['src', 'include', 'launch', 'config', 'msg', 'srv', 'action', 'resource', 'test'],
        'files': {
            'README.md': '# {project_name}\n\nROS2 package.\n\n## Build\n\n```bash\ncolcon build --packages-select {project_name}\n```\n',
            'CMakeLists.txt': '''cmake_minimum_required(VERSION 3.8)
project({project_name})

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

include_directories(include)

# Add executables here
# add_executable(node_name src/node.cpp)
# ament_target_dependencies(node_name rclcpp std_msgs)

# Install targets
# install(TARGETS node_name DESTINATION lib/${{PROJECT_NAME}})

# Install launch files
install(DIRECTORY launch DESTINATION share/${{PROJECT_NAME}})

# Install config files
install(DIRECTORY config DESTINATION share/${{PROJECT_NAME}})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
''',
            'package.xml': '''<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>{project_name}</name>
  <version>0.0.1</version>
  <description>{project_name} ROS2 package</description>
  <maintainer email="maintainer@example.com">Maintainer</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>rclcpp</depend>
  <depend>std_msgs</depend>

  <test_depend>ament_lint_auto</test_depend>
  <test_depend>ament_lint_common</test_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
''',
            '.gitignore': '''# Build
build/
install/
log/

# IDE
.vscode/
.idea/

# OS
.DS_Store
*~
''',
            'resource/{project_name}': '',
            'src/.gitkeep': '',
            'include/{project_name}/.gitkeep': '',
            'launch/.gitkeep': '',
            'config/.gitkeep': '',
        }
    },
    'python': {
        'dirs': ['src/{project_name}', 'tests', 'docs', 'scripts', 'config'],
        'files': {
            'README.md': '# {project_name}\n\nPython project.\n\n## Install\n\n```bash\npip install -e .\n```\n',
            'pyproject.toml': '''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_name}"
version = "0.0.1"
description = "{project_name}"
readme = "README.md"
requires-python = ">=3.8"
license = {{text = "MIT"}}
dependencies = []

[project.optional-dependencies]
dev = ["pytest", "black", "flake8", "mypy"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 100
target-version = ["py38"]

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
''',
            '.gitignore': '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/
*.egg

# Virtual environments
venv/
.venv/
env/

# IDE
.vscode/
.idea/
*.swp

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# OS
.DS_Store
*~
''',
            'src/{project_name}/__init__.py': '"""Main package for {project_name}."""\n\n__version__ = "0.0.1"\n',
            'tests/__init__.py': '',
            'tests/test_{project_name}.py': '''"""Tests for {project_name}."""

import pytest
from {project_name} import __version__


def test_version():
    assert __version__ == "0.0.1"
''',
        }
    },
    'rust': {
        'dirs': ['src', 'tests', 'benches', 'examples', 'docs'],
        'files': {
            'README.md': '# {project_name}\n\nRust project.\n\n## Build\n\n```bash\ncargo build --release\n```\n',
            'Cargo.toml': '''[package]
name = "{project_name}"
version = "0.1.0"
edition = "2021"
description = "{project_name}"
license = "MIT"

[dependencies]

[dev-dependencies]

[profile.release]
opt-level = 3
lto = true
''',
            '.gitignore': '''# Rust
target/
Cargo.lock

# IDE
.vscode/
.idea/

# OS
.DS_Store
*~
''',
            'src/main.rs': '''fn main() {{
    println!("Hello, {project_name}!");
}}
''',
            'src/lib.rs': '''//! {project_name} library

pub fn hello() -> &'static str {{
    "Hello, {project_name}!"
}}

#[cfg(test)]
mod tests {{
    use super::*;

    #[test]
    fn test_hello() {{
        assert_eq!(hello(), "Hello, {project_name}!");
    }}
}}
''',
        }
    },
    'nodejs': {
        'dirs': ['src', 'lib', 'tests', 'docs', 'scripts', 'config'],
        'files': {
            'README.md': '# {project_name}\n\nNode.js project.\n\n## Install\n\n```bash\nnpm install\n```\n',
            'package.json': '''{{
  "name": "{project_name}",
  "version": "0.0.1",
  "description": "{project_name}",
  "main": "src/index.js",
  "scripts": {{
    "start": "node src/index.js",
    "test": "jest",
    "lint": "eslint src/"
  }},
  "keywords": [],
  "license": "MIT",
  "devDependencies": {{
    "eslint": "^8.0.0",
    "jest": "^29.0.0"
  }}
}}
''',
            '.gitignore': '''# Node
node_modules/
dist/
build/

# Logs
*.log
npm-debug.log*

# IDE
.vscode/
.idea/

# OS
.DS_Store
*~

# Environment
.env
.env.local
''',
            'src/index.js': '''/**
 * Main entry point for {project_name}
 */

console.log("Hello from {project_name}!");
''',
            '.eslintrc.json': '''{{
  "env": {{
    "node": true,
    "es2021": true,
    "jest": true
  }},
  "extends": "eslint:recommended",
  "parserOptions": {{
    "ecmaVersion": "latest",
    "sourceType": "module"
  }},
  "rules": {{
    "indent": ["error", 2],
    "quotes": ["error", "single"],
    "semi": ["error", "always"]
  }}
}}
''',
        }
    },
    'embedded': {
        'dirs': ['src', 'include', 'lib', 'build', 'docs', 'scripts', 
                 'startup', 'ld', 'drivers', 'hal', 'board', 'config', 'tests'],
        'files': {
            'README.md': '# {project_name}\n\nEmbedded systems project.\n\n## Build\n\n```bash\nmkdir build && cd build\ncmake -DCMAKE_TOOLCHAIN_FILE=../cmake/toolchain.cmake ..\nmake\n```\n',
            'CMakeLists.txt': '''cmake_minimum_required(VERSION 3.16)
project({project_name} C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Toolchain should be set via CMAKE_TOOLCHAIN_FILE

include_directories(
    include
    hal
    drivers
    board
)

file(GLOB_RECURSE SOURCES 
    "src/*.c"
    "hal/*.c"
    "drivers/*.c"
    "board/*.c"
    "startup/*.c"
    "startup/*.s"
)

add_executable({project_name}.elf ${{SOURCES}})

# Linker script
set(LINKER_SCRIPT "${{CMAKE_SOURCE_DIR}}/ld/link.ld")
target_link_options({project_name}.elf PRIVATE
    -T${{LINKER_SCRIPT}}
    -Wl,-Map=${{PROJECT_NAME}}.map
)

# Generate binary and hex files
add_custom_command(TARGET {project_name}.elf POST_BUILD
    COMMAND ${{CMAKE_OBJCOPY}} -O binary {project_name}.elf {project_name}.bin
    COMMAND ${{CMAKE_OBJCOPY}} -O ihex {project_name}.elf {project_name}.hex
    COMMENT "Generating binary and hex files"
)
''',
            '.gitignore': '''# Build
build/
*.o
*.elf
*.bin
*.hex
*.map

# IDE
.vscode/
.idea/

# OS
.DS_Store
*~
''',
            'src/main.c': '''/**
 * @file main.c
 * @brief Main entry point for {project_name}
 */

#include "main.h"

int main(void)
{{
    /* Initialize hardware */
    
    /* Main loop */
    while (1)
    {{
        /* Application code */
    }}
    
    return 0;
}}
''',
            'include/main.h': '''/**
 * @file main.h
 * @brief Main header for {project_name}
 */

#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>
#include <stdbool.h>

#endif /* MAIN_H */
''',
            'ld/link.ld': '''/* Linker script template - customize for your MCU */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 256K
    RAM (rwx)   : ORIGIN = 0x20000000, LENGTH = 64K
}

SECTIONS
{
    .text :
    {
        *(.isr_vector)
        *(.text*)
        *(.rodata*)
    } > FLASH

    .data :
    {
        *(.data*)
    } > RAM AT > FLASH

    .bss :
    {
        *(.bss*)
        *(COMMON)
    } > RAM
}
''',
        }
    },
}


def create_project(name: str, project_type: str, output_path: Path) -> None:
    """Create a new project with the specified structure."""
    if project_type not in PROJECT_TEMPLATES:
        print(f"Error: Unknown project type '{project_type}'")
        print(f"Available types: {', '.join(PROJECT_TEMPLATES.keys())}")
        sys.exit(1)
    
    template = PROJECT_TEMPLATES[project_type]
    project_path = output_path / name
    
    if project_path.exists():
        print(f"Error: Directory '{project_path}' already exists")
        sys.exit(1)
    
    print(f"Creating {project_type} project: {name}")
    print(f"Location: {project_path}")
    
    # Create project root
    project_path.mkdir(parents=True)
    
    # Create directories
    for dir_pattern in template['dirs']:
        dir_path = project_path / dir_pattern.format(project_name=name)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {dir_path.relative_to(project_path)}/")
    
    # Create files
    for file_pattern, content in template['files'].items():
        file_path = project_path / file_pattern.format(project_name=name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.format(project_name=name))
        print(f"  Created: {file_path.relative_to(project_path)}")
    
    print(f"\n✅ Project '{name}' created successfully!")
    print(f"\nNext steps:")
    print(f"  cd {project_path}")
    if project_type == 'python':
        print(f"  python -m venv venv && source venv/bin/activate")
        print(f"  pip install -e .[dev]")
    elif project_type in ('c', 'cpp', 'embedded'):
        print(f"  mkdir build && cd build && cmake .. && make")
    elif project_type == 'rust':
        print(f"  cargo build")
    elif project_type == 'nodejs':
        print(f"  npm install")
    elif project_type == 'ros2':
        print(f"  colcon build --packages-select {name}")


def main():
    parser = argparse.ArgumentParser(
        description='Initialize a new project with standardized directory structure'
    )
    parser.add_argument('name', help='Project name')
    parser.add_argument(
        '--type', '-t',
        choices=list(PROJECT_TEMPLATES.keys()),
        default='generic',
        help='Project type (default: generic)'
    )
    parser.add_argument(
        '--path', '-p',
        type=Path,
        default=Path.cwd(),
        help='Output directory (default: current directory)'
    )
    
    args = parser.parse_args()
    create_project(args.name, args.type, args.path)


if __name__ == '__main__':
    main()

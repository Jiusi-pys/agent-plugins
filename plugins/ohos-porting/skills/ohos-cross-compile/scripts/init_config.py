#!/usr/bin/env python3
"""
Initialize ohos_toolchain_config.json for OpenHarmony cross-compilation.

Usage:
    python init_config.py --sdk-root /path/to/ohos-sdk/native
    python init_config.py --interactive
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def find_sdk_root() -> Optional[str]:
    """Auto-detect OHOS SDK root from common locations."""
    candidates = [
        os.environ.get("OHOS_SDK_ROOT"),
        os.environ.get("OHOS_NDK_ROOT"),
        Path.home() / "ohos-sdk" / "linux" / "native",
        Path("/opt/ohos-sdk/native"),
    ]
    
    # Search parent directories
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents)[:5]:
        candidates.append(parent / "OpenHarmony" / "prebuilts" / "ohos-sdk" / "linux" / "11" / "native")
        candidates.append(parent / "prebuilts" / "ohos-sdk" / "linux" / "native")
    
    for path in candidates:
        if path and Path(path).is_dir():
            llvm_bin = Path(path) / "llvm" / "bin" / "clang"
            if llvm_bin.exists():
                return str(Path(path).resolve())
    return None


def validate_sdk_root(sdk_root: str) -> Tuple[bool, List[str]]:
    """Validate SDK root directory structure."""
    root = Path(sdk_root)
    errors = []
    
    required = [
        ("llvm/bin/clang", "Clang compiler"),
        ("llvm/bin/clang++", "Clang++ compiler"),
        ("llvm/bin/lld", "LLD linker"),
        ("llvm/bin/llvm-ar", "Archive tool"),
        ("sysroot/usr/include/stdio.h", "C headers"),
        ("sysroot/usr/lib/aarch64-linux-ohos/libc.so", "musl libc"),
        ("llvm/lib/aarch64-linux-ohos/libc++_shared.so", "C++ runtime"),
    ]
    
    for path, desc in required:
        if not (root / path).exists():
            errors.append(f"Missing {desc}: {path}")
    
    return len(errors) == 0, errors


def find_build_tools() -> Dict[str, str]:
    """Find GN and Ninja build tools."""
    tools = {"gn": "", "ninja": ""}
    
    # Check PATH first
    for tool in tools:
        for p in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(p) / tool
            if candidate.exists():
                tools[tool] = str(candidate)
                break
    
    # Search common locations
    search_dirs = [
        Path.cwd(),
        Path.home(),
        Path("/opt"),
    ]
    
    for base in search_dirs:
        for pattern in ["**/gn", "**/ninja"]:
            for match in base.glob(pattern):
                if match.is_file() and os.access(match, os.X_OK):
                    name = match.name
                    if name in tools and not tools[name]:
                        tools[name] = str(match.resolve())
    
    return tools


def generate_config(sdk_root: str, build_tools: Dict[str, str], project_name: str = "myproject") -> Dict:
    """Generate configuration dictionary."""
    return {
        "$schema": "./ohos_toolchain_config.schema.json",
        "_comment": "OpenHarmony Cross-Compilation Toolchain Configuration",
        
        "ohos_sdk_root": sdk_root,
        
        "toolchain": {
            "cc": f"{sdk_root}/llvm/bin/aarch64-unknown-linux-ohos-clang",
            "cxx": f"{sdk_root}/llvm/bin/aarch64-unknown-linux-ohos-clang++",
            "ar": f"{sdk_root}/llvm/bin/llvm-ar",
            "ranlib": f"{sdk_root}/llvm/bin/llvm-ranlib",
            "strip": f"{sdk_root}/llvm/bin/llvm-strip",
            "objdump": f"{sdk_root}/llvm/bin/llvm-objdump",
            "readelf": f"{sdk_root}/llvm/bin/llvm-readelf",
            "nm": f"{sdk_root}/llvm/bin/llvm-nm"
        },
        
        "sysroot": f"{sdk_root}/sysroot",
        
        "cxx_runtime": {
            "shared": f"{sdk_root}/llvm/lib/aarch64-linux-ohos/libc++_shared.so",
            "static": f"{sdk_root}/llvm/lib/aarch64-linux-ohos/libc++_static.a",
            "abi": f"{sdk_root}/llvm/lib/aarch64-linux-ohos/libc++abi.a"
        },
        
        "build_tools": build_tools,
        
        "target": {
            "triple": "aarch64-linux-ohos",
            "arch": "aarch64",
            "cpu": "arm64",
            "os": "ohos"
        },
        
        "default_flags": {
            "cflags": ["-D__MUSL__"],
            "cxxflags": ["-std=c++17", "-D__MUSL__"],
            "ldflags": ["-fuse-ld=lld"],
            "rpath": ["/data", "/system/lib64"]
        },
        
        "deploy": {
            "dev_path": "/data",
            "system_path": "/system/lib64",
            "project_path": f"/data/{project_name}/lib"
        },
        
        "device": {
            "connection": "hdc",
            "serial": ""
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Initialize OpenHarmony toolchain configuration"
    )
    parser.add_argument(
        "--sdk-root", "-s",
        help="Path to OHOS SDK native directory"
    )
    parser.add_argument(
        "--output", "-o",
        default="ohos_toolchain_config.json",
        help="Output config file path"
    )
    parser.add_argument(
        "--project", "-p",
        default="myproject",
        help="Project name for deployment paths"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing config"
    )
    
    args = parser.parse_args()
    
    # Check existing config
    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(f"Config already exists: {output_path}")
        print("Use --force to overwrite")
        sys.exit(1)
    
    # Determine SDK root
    sdk_root = args.sdk_root
    
    if not sdk_root:
        sdk_root = find_sdk_root()
        if sdk_root:
            print(f"Auto-detected SDK: {sdk_root}")
        elif args.interactive:
            sdk_root = input("Enter OHOS SDK root path: ").strip()
        else:
            print("ERROR: Cannot find OHOS SDK. Use --sdk-root or --interactive")
            sys.exit(1)
    
    # Validate
    valid, errors = validate_sdk_root(sdk_root)
    if not valid:
        print("SDK validation failed:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    
    print(f"SDK validated: {sdk_root}")
    
    # Find build tools
    build_tools = find_build_tools()
    if build_tools["gn"]:
        print(f"Found GN: {build_tools['gn']}")
    else:
        print("WARNING: GN not found in PATH")
    
    if build_tools["ninja"]:
        print(f"Found Ninja: {build_tools['ninja']}")
    else:
        print("WARNING: Ninja not found in PATH")
    
    # Generate config
    config = generate_config(sdk_root, build_tools, args.project)
    
    # Write
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\nConfig written to: {output_path}")
    print("\nNext steps:")
    print("  1. Run scripts/device_survey.sh on target device")
    print("  2. Run scripts/check_toolchain.sh to verify setup")
    print("  3. Start building your project")


if __name__ == "__main__":
    main()

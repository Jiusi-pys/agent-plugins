#!/bin/bash
# OpenHarmony Toolchain Verification Script
# Run on the Linux host to verify the command-line-tools and prebuilts layout.
#
# Usage:
#   ./check_toolchain.sh                               # Auto-detect from config
#   ./check_toolchain.sh /path/to/command-line-tools   # Explicit command-line-tools root
#   OHOS_COMMAND_LINE_TOOLS=/path/to/command-line-tools ./check_toolchain.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ERRORS=$((ERRORS + 1)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "      $1"; }

ERRORS=0

CONFIG_FILE=""
COMMAND_LINE_TOOLS_ROOT="${OHOS_COMMAND_LINE_TOOLS:-}"
PREBUILTS_ROOT="${OPENHARMONY_PREBUILTS_ROOT:-}"
OHOS_NATIVE_ROOT=""
LLVM_ROOT="${OHOS_LLVM_ROOT:-}"
SYSROOT="${OHOS_SYSROOT:-}"
GN_PATH="${OHOS_GN:-}"
NINJA_PATH="${OHOS_NINJA:-}"

find_config() {
    local cfg
    local candidates=(
        "./ohos_toolchain_config.json"
        "../ohos_toolchain_config.json"
        "$(dirname "$0")/../ohos_toolchain_config.json"
    )

    for cfg in "${candidates[@]}"; do
        if [[ -f "$cfg" ]]; then
            echo "$cfg"
            return 0
        fi
    done

    return 1
}

load_config() {
    local cfg="$1"
    local key="$2"
    python3 - "$cfg" "$key" <<'PY'
import json
import sys

cfg_path, key = sys.argv[1], sys.argv[2]
with open(cfg_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

value = data
for part in key.split("."):
    if not isinstance(value, dict) or part not in value:
        sys.exit(1)
    value = value[part]

if isinstance(value, str):
    print(value)
else:
    sys.exit(1)
PY
}

if [[ $# -gt 0 ]]; then
    COMMAND_LINE_TOOLS_ROOT="$1"
fi

if [[ -z "$COMMAND_LINE_TOOLS_ROOT" ]] || [[ -z "$PREBUILTS_ROOT" ]] || [[ -z "$LLVM_ROOT" ]] || [[ -z "$SYSROOT" ]]; then
    if CONFIG_FILE="$(find_config)"; then
        [[ -z "$COMMAND_LINE_TOOLS_ROOT" ]] && COMMAND_LINE_TOOLS_ROOT="$(load_config "$CONFIG_FILE" "command_line_tools_root" 2>/dev/null || true)"
        [[ -z "$PREBUILTS_ROOT" ]] && PREBUILTS_ROOT="$(load_config "$CONFIG_FILE" "openharmony_prebuilts_root" 2>/dev/null || true)"
        [[ -z "$LLVM_ROOT" ]] && LLVM_ROOT="$(load_config "$CONFIG_FILE" "llvm_root" 2>/dev/null || true)"
        [[ -z "$SYSROOT" ]] && SYSROOT="$(load_config "$CONFIG_FILE" "sysroot" 2>/dev/null || true)"
        [[ -z "$GN_PATH" ]] && GN_PATH="$(load_config "$CONFIG_FILE" "build_tools.gn" 2>/dev/null || true)"
        [[ -z "$NINJA_PATH" ]] && NINJA_PATH="$(load_config "$CONFIG_FILE" "build_tools.ninja" 2>/dev/null || true)"
        info "Loaded toolchain contract from: $CONFIG_FILE"
    fi
fi

# Backward-compatible fallback for environments that still export OHOS_SDK_ROOT.
if [[ -z "$COMMAND_LINE_TOOLS_ROOT" ]] && [[ -n "${OHOS_SDK_ROOT:-}" ]]; then
    COMMAND_LINE_TOOLS_ROOT="$(cd "${OHOS_SDK_ROOT}/../.." 2>/dev/null && pwd)"
    warn "Derived command_line_tools_root from OHOS_SDK_ROOT for compatibility."
fi

if [[ -z "$COMMAND_LINE_TOOLS_ROOT" ]]; then
    echo "ERROR: Cannot determine command-line-tools root"
    echo "Usage: $0 /path/to/command-line-tools"
    echo "   or: OHOS_COMMAND_LINE_TOOLS=/path/to/command-line-tools $0"
    echo "   or: populate command_line_tools_root in ohos_toolchain_config.json"
    exit 1
fi

if [[ -z "$PREBUILTS_ROOT" ]]; then
    echo "ERROR: Cannot determine openharmony_prebuilts root"
    echo "Set OPENHARMONY_PREBUILTS_ROOT or populate openharmony_prebuilts_root in ohos_toolchain_config.json"
    exit 1
fi

OHOS_NATIVE_ROOT="${COMMAND_LINE_TOOLS_ROOT}/sdk/native"
[[ -n "$LLVM_ROOT" ]] || LLVM_ROOT="${OHOS_NATIVE_ROOT}/llvm"
[[ -n "$SYSROOT" ]] || SYSROOT="${OHOS_NATIVE_ROOT}/sysroot"
[[ -n "$NINJA_PATH" ]] || NINJA_PATH="${OHOS_NATIVE_ROOT}/build-tools/cmake/bin/ninja"

echo "========================================"
echo "OpenHarmony Toolchain Verification"
echo "========================================"
echo ""
echo "command-line-tools root: $COMMAND_LINE_TOOLS_ROOT"
echo "openharmony_prebuilts root: $PREBUILTS_ROOT"
echo "native tool root: $OHOS_NATIVE_ROOT"
echo ""

# 1. Directory Structure
echo "--- Directory Structure ---"
if [ -d "$COMMAND_LINE_TOOLS_ROOT" ]; then
    pass "command-line-tools root exists"
else
    fail "command-line-tools root not found: $COMMAND_LINE_TOOLS_ROOT"
    exit 1
fi

if [ -d "$PREBUILTS_ROOT" ]; then
    pass "openharmony_prebuilts root exists"
else
    fail "openharmony_prebuilts root not found: $PREBUILTS_ROOT"
fi

for dir in "$OHOS_NATIVE_ROOT" "$LLVM_ROOT" "$LLVM_ROOT/bin" "$LLVM_ROOT/lib" "$SYSROOT" "$SYSROOT/usr/include" "$SYSROOT/usr/lib"; do
    if [ -d "$dir" ]; then
        pass "${dir#$COMMAND_LINE_TOOLS_ROOT/}"
    else
        fail "${dir#$COMMAND_LINE_TOOLS_ROOT/} missing"
    fi
done
echo ""

# 2. Compiler Binaries
echo "--- Compiler Binaries ---"
LLVM_BIN="$LLVM_ROOT/bin"

REQUIRED_BINS=(
    "clang:C compiler"
    "clang++:C++ compiler"
    "lld:LLD linker"
    "llvm-ar:Archive tool"
    "llvm-nm:Symbol table"
    "llvm-objdump:Disassembler"
    "llvm-readelf:ELF reader"
    "llvm-strip:Strip tool"
)

for entry in "${REQUIRED_BINS[@]}"; do
    bin="${entry%%:*}"
    desc="${entry##*:}"
    if [ -x "$LLVM_BIN/$bin" ]; then
        pass "$bin ($desc)"
    else
        fail "$bin missing ($desc)"
    fi
done

# Check wrapper script
WRAPPER="$LLVM_BIN/aarch64-unknown-linux-ohos-clang++"
if [ -x "$WRAPPER" ]; then
    pass "aarch64 wrapper script"
else
    warn "aarch64 wrapper script missing (manual flags required)"
fi
echo ""

# 3. Sysroot Contents
echo "--- Sysroot Contents ---"

REQUIRED_HEADERS=(
    "usr/include/stdio.h:C stdio"
    "usr/include/stdlib.h:C stdlib"
    "usr/include/string.h:C string"
    "usr/include/pthread.h:POSIX threads"
    "usr/include/dlfcn.h:Dynamic loading"
    "usr/include/sys/socket.h:Sockets"
)

for entry in "${REQUIRED_HEADERS[@]}"; do
    header="${entry%%:*}"
    desc="${entry##*:}"
    if [ -f "$SYSROOT/$header" ]; then
        pass "$header"
    else
        fail "$header missing ($desc)"
    fi
done

# C++ headers
if [ -d "$SYSROOT/usr/include/c++" ]; then
    pass "C++ standard library headers"
else
    fail "C++ headers missing"
fi
echo ""

# 4. Libraries
echo "--- System Libraries ---"
SYSROOT_LIB="$SYSROOT/usr/lib/aarch64-linux-ohos"

REQUIRED_LIBS=(
    "libc.so:musl C library"
    "libm.so:Math library"
    "libdl.so:Dynamic loader"
    "libpthread.so:Threads"
)

for entry in "${REQUIRED_LIBS[@]}"; do
    lib="${entry%%:*}"
    desc="${entry##*:}"
    if [ -f "$SYSROOT_LIB/$lib" ] || [ -L "$SYSROOT_LIB/$lib" ]; then
        pass "$lib ($desc)"
    else
        fail "$lib missing ($desc)"
    fi
done

# CRT objects
CRT_OBJS=("Scrt1.o" "crt1.o" "crti.o" "crtn.o")
for obj in "${CRT_OBJS[@]}"; do
    if [ -f "$SYSROOT_LIB/$obj" ]; then
        pass "$obj"
    else
        fail "CRT object $obj missing"
    fi
done
echo ""

# 5. C++ Runtime
echo "--- C++ Runtime ---"
CXX_LIB="$LLVM_ROOT/lib/aarch64-linux-ohos"

if [ -f "$CXX_LIB/libc++_shared.so" ]; then
    SIZE=$(ls -lh "$CXX_LIB/libc++_shared.so" | awk '{print $5}')
    pass "libc++_shared.so ($SIZE)"
else
    fail "libc++_shared.so missing"
fi

if [ -f "$CXX_LIB/libc++_static.a" ]; then
    SIZE=$(ls -lh "$CXX_LIB/libc++_static.a" | awk '{print $5}')
    pass "libc++_static.a ($SIZE)"
else
    warn "libc++_static.a missing (static linking unavailable)"
fi

if [ -f "$CXX_LIB/libc++abi.a" ]; then
    pass "libc++abi.a"
else
    warn "libc++abi.a missing"
fi
echo ""

# 5b. Build Tools
echo "--- Build Tools ---"
if [[ -n "$GN_PATH" ]]; then
    if [[ -x "$GN_PATH" ]]; then
        pass "gn"
    else
        fail "Configured gn missing: $GN_PATH"
    fi
else
    warn "gn path not configured"
fi

if [[ -x "$NINJA_PATH" ]]; then
    pass "ninja"
else
    fail "Configured ninja missing: $NINJA_PATH"
fi
echo ""

# 6. Compiler Version
echo "--- Compiler Version ---"
if [ -x "$LLVM_BIN/clang" ]; then
    VERSION=$("$LLVM_BIN/clang" --version 2>&1 | head -1)
    info "$VERSION"
    
    if echo "$VERSION" | grep -q "OHOS"; then
        pass "OHOS-patched Clang"
    else
        warn "Not OHOS-patched Clang (may work but not official)"
    fi
fi
echo ""

# 7. Compilation Test
echo "--- Compilation Test ---"
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

cat > "$TEMP_DIR/test.cpp" << 'EOF'
#include <iostream>
#include <cstdio>
int main() {
    std::cout << "Hello, OpenHarmony!" << std::endl;
    printf("musl libc works\n");
    return 0;
}
EOF

CXX="$LLVM_BIN/aarch64-unknown-linux-ohos-clang++"
if [ ! -x "$CXX" ]; then
    CXX="$LLVM_BIN/clang++"
    CXX_FLAGS="--target=aarch64-unknown-linux-ohos --sysroot=$SYSROOT -D__MUSL__"
else
    CXX_FLAGS=""
fi

# Try compilation
if $CXX $CXX_FLAGS -std=c++17 -O2 -fuse-ld=lld \
    -Wl,-rpath,/data -Wl,-rpath,/system/lib64 \
    -o "$TEMP_DIR/test_ohos" "$TEMP_DIR/test.cpp" 2>"$TEMP_DIR/compile.log"; then
    pass "C++ compilation successful"
    
    # Verify output
    FILE_INFO=$(file "$TEMP_DIR/test_ohos")
    if echo "$FILE_INFO" | grep -q "aarch64"; then
        pass "Output is aarch64 ELF"
    else
        fail "Output is not aarch64: $FILE_INFO"
    fi
    
    # Check dependencies
    DEPS=$("$LLVM_BIN/llvm-readelf" -d "$TEMP_DIR/test_ohos" 2>/dev/null | grep NEEDED || true)
    if echo "$DEPS" | grep -q "libc++_shared.so"; then
        pass "Links to libc++_shared.so"
    fi
    if echo "$DEPS" | grep -q "libc.so"; then
        pass "Links to libc.so (musl)"
    fi
    
    # Check RPATH
    RPATH=$("$LLVM_BIN/llvm-readelf" -d "$TEMP_DIR/test_ohos" 2>/dev/null | grep RPATH || true)
    if [ -n "$RPATH" ]; then
        pass "RPATH set: $(echo $RPATH | grep -oP '\[.*\]')"
    else
        warn "No RPATH in binary"
    fi
else
    fail "Compilation failed"
    info "Error log:"
    cat "$TEMP_DIR/compile.log" | head -20
fi
echo ""

# Summary
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    echo "Toolchain is ready for cross-compilation."
else
    echo -e "${RED}$ERRORS check(s) failed.${NC}"
    echo "Please fix the issues above before proceeding."
fi
echo "========================================"

exit $ERRORS

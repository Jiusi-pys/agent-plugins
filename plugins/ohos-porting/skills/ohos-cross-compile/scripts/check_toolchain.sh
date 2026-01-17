#!/bin/bash
# OpenHarmony Toolchain Verification Script
# Run on HOST machine to verify SDK installation
#
# Usage:
#   ./check_toolchain.sh                    # Auto-detect from config
#   ./check_toolchain.sh /path/to/sdk       # Explicit path
#   OHOS_SDK_ROOT=/path/to/sdk ./check_toolchain.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ERRORS=$((ERRORS + 1)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "      $1"; }

ERRORS=0

# Determine SDK root
if [ -n "$1" ]; then
    OHOS_SDK_ROOT="$1"
elif [ -z "$OHOS_SDK_ROOT" ]; then
    # Try to load from config
    CONFIG_PATHS=(
        "./ohos_toolchain_config.json"
        "../ohos_toolchain_config.json"
        "$(dirname "$0")/../ohos_toolchain_config.json"
    )
    
    for cfg in "${CONFIG_PATHS[@]}"; do
        if [ -f "$cfg" ]; then
            OHOS_SDK_ROOT=$(python3 -c "import json; print(json.load(open('$cfg'))['ohos_sdk_root'])" 2>/dev/null)
            if [ -n "$OHOS_SDK_ROOT" ]; then
                info "Loaded SDK root from: $cfg"
                break
            fi
        fi
    done
fi

if [ -z "$OHOS_SDK_ROOT" ]; then
    echo "ERROR: Cannot determine OHOS SDK root"
    echo "Usage: $0 /path/to/ohos-sdk/native"
    echo "   or: OHOS_SDK_ROOT=/path/to/sdk $0"
    echo "   or: Create ohos_toolchain_config.json"
    exit 1
fi

echo "========================================"
echo "OpenHarmony Toolchain Verification"
echo "========================================"
echo ""
echo "SDK Root: $OHOS_SDK_ROOT"
echo ""

# 1. Directory Structure
echo "--- Directory Structure ---"
if [ -d "$OHOS_SDK_ROOT" ]; then
    pass "SDK root exists"
else
    fail "SDK root not found: $OHOS_SDK_ROOT"
    exit 1
fi

for dir in llvm llvm/bin llvm/lib sysroot sysroot/usr/include sysroot/usr/lib; do
    if [ -d "$OHOS_SDK_ROOT/$dir" ]; then
        pass "$dir/"
    else
        fail "$dir/ missing"
    fi
done
echo ""

# 2. Compiler Binaries
echo "--- Compiler Binaries ---"
LLVM_BIN="$OHOS_SDK_ROOT/llvm/bin"

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
SYSROOT="$OHOS_SDK_ROOT/sysroot"

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
CXX_LIB="$OHOS_SDK_ROOT/llvm/lib/aarch64-linux-ohos"

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
    CXX_FLAGS="--target=aarch64-linux-ohos --sysroot=$SYSROOT -D__MUSL__"
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

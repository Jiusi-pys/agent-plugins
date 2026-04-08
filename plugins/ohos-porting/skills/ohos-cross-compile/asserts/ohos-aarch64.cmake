# OpenHarmony aarch64 Cross-Compilation Toolchain
# 
# Usage:
#   cmake -DCMAKE_TOOLCHAIN_FILE=ohos-aarch64.cmake \
#         -DOHOS_SDK_ROOT=/path/to/sdk ..
#
# Or set environment variable:
#   export OHOS_SDK_ROOT=/path/to/sdk
#   cmake -DCMAKE_TOOLCHAIN_FILE=ohos-aarch64.cmake ..

cmake_minimum_required(VERSION 3.16)

# System identification
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_CROSSCOMPILING TRUE)

# SDK path resolution
if(DEFINED ENV{OHOS_SDK_ROOT})
    set(OHOS_SDK_ROOT "$ENV{OHOS_SDK_ROOT}" CACHE PATH "OHOS SDK root")
endif()

if(NOT OHOS_SDK_ROOT)
    message(FATAL_ERROR "OHOS_SDK_ROOT must be set")
endif()

if(NOT IS_DIRECTORY "${OHOS_SDK_ROOT}")
    message(FATAL_ERROR "OHOS_SDK_ROOT does not exist: ${OHOS_SDK_ROOT}")
endif()

# Paths
set(OHOS_LLVM "${OHOS_SDK_ROOT}/llvm")
set(CMAKE_SYSROOT "${OHOS_SDK_ROOT}/sysroot")

# Compilers (prefer wrapper scripts)
set(_WRAPPER "${OHOS_LLVM}/bin/aarch64-unknown-linux-ohos-clang++")
if(EXISTS "${_WRAPPER}")
    set(CMAKE_C_COMPILER "${OHOS_LLVM}/bin/aarch64-unknown-linux-ohos-clang")
    set(CMAKE_CXX_COMPILER "${_WRAPPER}")
else()
    set(CMAKE_C_COMPILER "${OHOS_LLVM}/bin/clang")
    set(CMAKE_CXX_COMPILER "${OHOS_LLVM}/bin/clang++")
    set(CMAKE_C_COMPILER_TARGET "aarch64-linux-ohos")
    set(CMAKE_CXX_COMPILER_TARGET "aarch64-linux-ohos")
endif()

# Tools
set(CMAKE_AR "${OHOS_LLVM}/bin/llvm-ar" CACHE FILEPATH "")
set(CMAKE_RANLIB "${OHOS_LLVM}/bin/llvm-ranlib" CACHE FILEPATH "")
set(CMAKE_STRIP "${OHOS_LLVM}/bin/llvm-strip" CACHE FILEPATH "")
set(CMAKE_NM "${OHOS_LLVM}/bin/llvm-nm" CACHE FILEPATH "")
set(CMAKE_OBJDUMP "${OHOS_LLVM}/bin/llvm-objdump" CACHE FILEPATH "")

# Search paths
set(CMAKE_FIND_ROOT_PATH "${CMAKE_SYSROOT}")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Compiler flags
set(CMAKE_C_FLAGS_INIT "-D__MUSL__")
set(CMAKE_CXX_FLAGS_INIT "-D__MUSL__")

# Linker
set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "-fuse-ld=lld")

# RPATH
set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH TRUE)
set(CMAKE_INSTALL_RPATH "/data;/system/lib64")
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH FALSE)

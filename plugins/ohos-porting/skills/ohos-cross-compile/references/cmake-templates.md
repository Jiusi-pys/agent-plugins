# CMake Templates for OpenHarmony Cross-Compilation

## Toolchain File

**File: cmake/ohos-aarch64.cmake**

```cmake
# OpenHarmony SDK Clang Toolchain for aarch64
# Usage: cmake -DCMAKE_TOOLCHAIN_FILE=cmake/ohos-aarch64.cmake ..

cmake_minimum_required(VERSION 3.16)

#========================================
# System Identification
#========================================
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_CROSSCOMPILING TRUE)

#========================================
# SDK Path Configuration
#========================================
# Priority: Environment variable > Cache > Default
if(DEFINED ENV{OHOS_SDK_ROOT})
    set(OHOS_SDK_ROOT "$ENV{OHOS_SDK_ROOT}" CACHE PATH "OHOS SDK root")
elseif(NOT DEFINED OHOS_SDK_ROOT)
    # Try to load from config.json
    find_file(_CONFIG_FILE
        NAMES ohos_toolchain_config.json
        PATHS
            "${CMAKE_SOURCE_DIR}"
            "${CMAKE_SOURCE_DIR}/.."
        NO_DEFAULT_PATH
    )
    if(_CONFIG_FILE)
        file(READ "${_CONFIG_FILE}" _CONFIG_JSON)
        string(JSON OHOS_SDK_ROOT GET "${_CONFIG_JSON}" ohos_sdk_root)
    else()
        message(FATAL_ERROR "OHOS_SDK_ROOT not set. Use -DOHOS_SDK_ROOT=... or set environment variable")
    endif()
endif()

set(CMAKE_SYSROOT "${OHOS_SDK_ROOT}/sysroot")

#========================================
# Compiler Configuration
#========================================
set(OHOS_LLVM_BIN "${OHOS_SDK_ROOT}/llvm/bin")

# Use wrapper scripts (recommended)
set(CMAKE_C_COMPILER "${OHOS_LLVM_BIN}/aarch64-unknown-linux-ohos-clang")
set(CMAKE_CXX_COMPILER "${OHOS_LLVM_BIN}/aarch64-unknown-linux-ohos-clang++")

# Fallback to base clang if wrapper not found
if(NOT EXISTS "${CMAKE_CXX_COMPILER}")
    set(CMAKE_C_COMPILER "${OHOS_LLVM_BIN}/clang")
    set(CMAKE_CXX_COMPILER "${OHOS_LLVM_BIN}/clang++")
    set(CMAKE_C_COMPILER_TARGET "aarch64-linux-ohos")
    set(CMAKE_CXX_COMPILER_TARGET "aarch64-linux-ohos")
endif()

# Tools
set(CMAKE_AR "${OHOS_LLVM_BIN}/llvm-ar" CACHE FILEPATH "")
set(CMAKE_RANLIB "${OHOS_LLVM_BIN}/llvm-ranlib" CACHE FILEPATH "")
set(CMAKE_STRIP "${OHOS_LLVM_BIN}/llvm-strip" CACHE FILEPATH "")
set(CMAKE_NM "${OHOS_LLVM_BIN}/llvm-nm" CACHE FILEPATH "")
set(CMAKE_OBJDUMP "${OHOS_LLVM_BIN}/llvm-objdump" CACHE FILEPATH "")

#========================================
# Search Path Configuration
#========================================
set(CMAKE_FIND_ROOT_PATH "${CMAKE_SYSROOT}")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

#========================================
# Compiler Flags
#========================================
set(CMAKE_C_FLAGS_INIT "-D__MUSL__")
set(CMAKE_CXX_FLAGS_INIT "-D__MUSL__")

# Use LLD linker
set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "-fuse-ld=lld")

#========================================
# RPATH Configuration
#========================================
set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH TRUE)
set(CMAKE_INSTALL_RPATH "/data;/system/lib64")
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH FALSE)

#========================================
# C++ Standard Library
#========================================
set(OHOS_CXX_SHARED_LIB "${OHOS_SDK_ROOT}/llvm/lib/aarch64-linux-ohos/libc++_shared.so")
set(OHOS_CXX_STATIC_LIB "${OHOS_SDK_ROOT}/llvm/lib/aarch64-linux-ohos/libc++_static.a")
```

## CMakeLists.txt Template

```cmake
cmake_minimum_required(VERSION 3.16)
project(MyProject VERSION 1.0.0 LANGUAGES CXX)

#========================================
# C++ Standard
#========================================
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

#========================================
# Build Options
#========================================
option(BUILD_SHARED_LIBS "Build shared libraries" ON)
option(BUILD_TESTS "Build unit tests" OFF)
option(ENABLE_LOGGING "Enable HiLog integration" ON)

#========================================
# Compiler Warnings
#========================================
add_compile_options(
    -Wall
    -Wextra
    -Wpedantic
    -Werror=return-type
)

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-O0 -g)
    add_compile_definitions(DEBUG=1)
else()
    add_compile_options(-O2 -DNDEBUG)
endif()

#========================================
# Shared Library
#========================================
add_library(myproject
    src/core.cpp
    src/utils.cpp
    src/api.cpp
)

target_include_directories(myproject
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_compile_definitions(myproject
    PRIVATE BUILDING_MYPROJECT
    PUBLIC $<$<NOT:$<BOOL:${BUILD_SHARED_LIBS}>>:MYPROJECT_STATIC>
)

# Symbol visibility
set_target_properties(myproject PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

#========================================
# Executable
#========================================
add_executable(myapp src/main.cpp)

target_link_libraries(myapp PRIVATE myproject)

#========================================
# RPATH (if not set by toolchain)
#========================================
if(NOT CMAKE_INSTALL_RPATH)
    set_target_properties(myproject myapp PROPERTIES
        BUILD_WITH_INSTALL_RPATH TRUE
        INSTALL_RPATH "/data;/system/lib64"
    )
endif()

#========================================
# Installation
#========================================
include(GNUInstallDirs)

install(TARGETS myproject myapp
    EXPORT myproject-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

#========================================
# Tests (Optional)
#========================================
if(BUILD_TESTS)
    enable_testing()
    
    add_executable(myproject_test
        test/test_main.cpp
        test/test_core.cpp
    )
    
    target_link_libraries(myproject_test PRIVATE myproject)
    
    add_test(NAME myproject_test COMMAND myproject_test)
endif()
```

## Build Commands

```bash
# Configure (cross-compile)
cmake -S . -B build-ohos \
    -DCMAKE_TOOLCHAIN_FILE=cmake/ohos-aarch64.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/data/myproject

# Or with explicit SDK path
cmake -S . -B build-ohos \
    -DCMAKE_TOOLCHAIN_FILE=cmake/ohos-aarch64.cmake \
    -DOHOS_SDK_ROOT=/path/to/ohos-sdk/native \
    -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build build-ohos -j$(nproc)

# Install to staging directory
cmake --install build-ohos --prefix staging

# Verbose build
cmake --build build-ohos --verbose
```

## Finding Dependencies

### For OHOS system libraries

```cmake
# Manual linking (system libs are in sysroot)
target_link_libraries(myproject PRIVATE
    c       # musl libc
    m       # math
    dl      # dlopen
    pthread # threads
)
```

### For third-party libraries (cross-compiled)

```cmake
# Set search paths
list(APPEND CMAKE_PREFIX_PATH
    "${CMAKE_SOURCE_DIR}/third_party/install"
)

find_package(SomeLib REQUIRED)
target_link_libraries(myproject PRIVATE SomeLib::SomeLib)
```

### For header-only libraries

```cmake
target_include_directories(myproject PRIVATE
    ${CMAKE_SOURCE_DIR}/third_party/header_only/include
)
```

## Multi-Configuration

```cmake
# Detect cross-compilation
if(CMAKE_CROSSCOMPILING)
    message(STATUS "Cross-compiling for: ${CMAKE_SYSTEM_PROCESSOR}")
    
    # OHOS-specific settings
    if(CMAKE_SYSROOT MATCHES "ohos")
        message(STATUS "Target: OpenHarmony")
        add_compile_definitions(TARGET_OHOS=1)
    endif()
else()
    message(STATUS "Native build")
endif()
```

## Integration with HiLog (Optional)

```cmake
# When OHOS hilog is available
if(ENABLE_LOGGING AND CMAKE_CROSSCOMPILING)
    find_library(HILOG_LIBRARY hilog
        PATHS "${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos"
        NO_DEFAULT_PATH
    )
    
    if(HILOG_LIBRARY)
        target_link_libraries(myproject PRIVATE ${HILOG_LIBRARY})
        target_compile_definitions(myproject PRIVATE USE_HILOG=1)
    endif()
endif()
```

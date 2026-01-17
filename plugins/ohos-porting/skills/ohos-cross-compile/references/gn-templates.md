# GN Build Templates for OpenHarmony

## Complete BUILD.gn Template

```gn
# OpenHarmony GN Build File
# Location: project_root/BUILD.gn

import("//build/ohos.gni")

#========================================
# Build Configurations
#========================================

config("project_config") {
  include_dirs = [
    "include",
    "src",
  ]
  
  cflags_cc = [
    "-std=c++17",
    "-Wall",
    "-Wextra",
    "-Werror=return-type",
    "-fvisibility=hidden",
  ]
  
  defines = [ "BUILDING_PROJECT" ]
  
  if (is_debug) {
    cflags_cc += [ "-O0", "-g" ]
    defines += [ "DEBUG=1" ]
  } else {
    cflags_cc += [ "-O2", "-DNDEBUG" ]
  }
}

config("project_public_config") {
  include_dirs = [ "include" ]
  
  defines = [
    "API_EXPORT=__attribute__((visibility(\"default\")))",
  ]
}

#========================================
# Shared Library
#========================================

ohos_shared_library("myproject") {
  sources = [
    "src/core.cpp",
    "src/utils.cpp",
    "src/api.cpp",
  ]
  
  configs = [ ":project_config" ]
  public_configs = [ ":project_public_config" ]
  
  # RPATH for runtime library search
  ldflags = [
    "-Wl,-rpath,/data",
    "-Wl,-rpath,/system/lib64",
  ]
  
  # Internal dependencies (same repository)
  deps = [
    "//third_party/json:json",
  ]
  
  # External OHOS system dependencies
  external_deps = [
    "c_utils:utils",
    "hilog:libhilog",
  ]
  
  # Component metadata
  part_name = "myproject"
  subsystem_name = "thirdparty"
  
  # Output name (default: lib<target_name>.so)
  output_name = "libmyproject"
}

#========================================
# Static Library
#========================================

ohos_static_library("myproject_static") {
  sources = [
    "src/core.cpp",
    "src/utils.cpp",
  ]
  
  configs = [ ":project_config" ]
  public_configs = [ ":project_public_config" ]
  
  part_name = "myproject"
  subsystem_name = "thirdparty"
}

#========================================
# Executable
#========================================

ohos_executable("myapp") {
  sources = [ "src/main.cpp" ]
  
  configs = [ ":project_config" ]
  
  deps = [ ":myproject" ]
  
  ldflags = [
    "-Wl,-rpath,/data",
    "-Wl,-rpath,/system/lib64",
  ]
  
  external_deps = [ "hilog:libhilog" ]
  
  part_name = "myproject"
  subsystem_name = "thirdparty"
}

#========================================
# Unit Tests
#========================================

ohos_executable("myproject_test") {
  testonly = true
  
  sources = [
    "test/test_main.cpp",
    "test/test_core.cpp",
    "test/test_utils.cpp",
  ]
  
  deps = [ ":myproject" ]
  
  external_deps = [
    "googletest:gtest",
    "googletest:gtest_main",
  ]
  
  part_name = "myproject"
  subsystem_name = "thirdparty"
}

#========================================
# Group Target
#========================================

group("all") {
  deps = [
    ":myproject",
    ":myapp",
  ]
  
  if (is_debug) {
    deps += [ ":myproject_test" ]
  }
}
```

## ohos.build Component Registration

```json
{
  "subsystem": "thirdparty",
  "parts": {
    "myproject": {
      "module_list": [
        "//path/to/myproject:myproject",
        "//path/to/myproject:myapp"
      ],
      "inner_kits": [
        {
          "name": "//path/to/myproject:myproject",
          "header": {
            "header_files": [ "myproject.h" ],
            "header_base": "//path/to/myproject/include"
          }
        }
      ],
      "test_list": [
        "//path/to/myproject:myproject_test"
      ]
    }
  }
}
```

## Conditional Compilation Patterns

### Architecture-specific

```gn
if (target_cpu == "arm64") {
  sources += [ "src/arch/aarch64_opt.cpp" ]
  cflags_cc += [ "-march=armv8-a" ]
} else if (target_cpu == "x64") {
  sources += [ "src/arch/x86_64_opt.cpp" ]
}
```

### Feature toggles

```gn
declare_args() {
  enable_logging = true
  enable_profiling = false
}

if (enable_logging) {
  defines += [ "ENABLE_LOGGING=1" ]
  external_deps += [ "hilog:libhilog" ]
}

if (enable_profiling) {
  defines += [ "ENABLE_PROFILING=1" ]
  cflags_cc += [ "-pg" ]
}
```

### Debug vs Release

```gn
if (is_debug) {
  cflags_cc += [ "-O0", "-g", "-fsanitize=address" ]
  ldflags += [ "-fsanitize=address" ]
} else {
  cflags_cc += [ "-O2", "-DNDEBUG" ]
  ldflags += [ "-Wl,--gc-sections" ]
}
```

## Common external_deps

| Component | external_deps | Header |
|-----------|---------------|--------|
| Logging | `hilog:libhilog` | `<hilog/log.h>` |
| Utils | `c_utils:utils` | Various |
| SoftBus | `dsoftbus:softbus_client` | `<softbus/...>` |
| IPC | `ipc:ipc_core` | `<ipc_skeleton.h>` |
| EventHandler | `eventhandler:libeventhandler` | `<event_handler.h>` |

## Build Commands

```bash
# Generate build files
gn gen out/arm64 --args='
  target_os = "ohos"
  target_cpu = "arm64"
  is_debug = false
  is_component_build = true
'

# Build specific target
ninja -C out/arm64 //path/to/myproject:myproject

# Build all
ninja -C out/arm64 //path/to/myproject:all

# List available targets
gn ls out/arm64

# Show target info
gn desc out/arm64 //path/to/myproject:myproject

# Show deps tree
gn desc out/arm64 //path/to/myproject:myapp deps --tree
```

---
name: ohos-cpp-style
description: OpenHarmony and KaihongOS C/C++ coding guidance. Use when Codex needs to write, edit, review, or refactor OHOS-native C/C++ code, create or update BUILD.gn files, apply OHOS naming and file layout conventions, or check threading, serialization, and permission-related implementation patterns.
---

# OHOS C++ Style

Use when Codex needs to write or review OpenHarmony C/C++ code.

Use this skill when producing or reviewing C/C++ code for OpenHarmony or KaihongOS projects.

## Start Here

Read `config.json` before relying on repository-specific paths or toolchain values.

```json
{
  "paths": {
    "openharmony_source": "/path/to/OpenHarmony",
    "openharmony_prebuilts": "/path/to/openharmony_prebuilts",
    "output_dir": "/path/to/out/<board>"
  }
}
```

If the config values are placeholders, keep generated code generic and avoid inventing machine-specific paths.

## Core Conventions

- Use `CamelCase` for namespaces, classes, and structs.
- Use `camelCase` for methods.
- Use `snake_case_` for member fields.
- Use `UPPER_SNAKE_CASE` for macros and constants.
- Use `snake_case` for file names.
- Keep platform-specific code isolated instead of scattering conditional compilation across unrelated files.

## File Skeleton

```cpp
/*
 * Copyright (c) 2024-2026 Your Organization
 * Licensed under the Apache License, Version 2.0
 */

#ifndef PROJECT__MODULE_NAME_H_
#define PROJECT__MODULE_NAME_H_

namespace OHOS {
class SessionManager {
public:
    int32_t Initialize();
private:
    bool initialized_ = false;
};
}  // namespace OHOS

#endif  // PROJECT__MODULE_NAME_H_
```

## BUILD.gn and Layout Guidance

- Prefer explicit targets and dependencies in `BUILD.gn`.
- Keep headers and sources grouped by responsibility.
- Use the templates in `asserts/BUILD.gn` and `references/gn-templates.md` as the baseline shape.
- When adding a new OHOS-specific module, keep the interface minimal and isolate adaptation code in a dedicated file pair.

## Formatting

Prefer the repository clang-format file when present.

```bash
clang-format -style=file -i file.cpp file.h
```

Use `asserts/.clang-format` as the reference when a project-local file is missing.

## Reference Files

Read these only when they are relevant:

- `references/gn-templates.md` for `BUILD.gn` patterns
- `references/thread-patterns.md` for synchronization and concurrency patterns
- `references/serialization.md` for data encoding and marshaling patterns
- `references/permission-config.md` for permission-related native code considerations

## Output Expectations

- Produce code that matches OHOS naming and layout conventions.
- Keep comments sparse and useful.
- Prefer small, focused files and explicit ownership boundaries.

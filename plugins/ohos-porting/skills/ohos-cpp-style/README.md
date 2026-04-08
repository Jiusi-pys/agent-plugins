# ohos-cpp-style

Supplemental notes for the Codex-facing `ohos-cpp-style` skill.

## Scope

This directory is a reusable OHOS C/C++ guidance pack for:

- naming and file layout
- `BUILD.gn` structure
- formatting expectations
- threading and serialization references
- permission-related native code considerations

## Start Order

1. Read [SKILL.md](./SKILL.md) for the active Codex workflow.
2. Check [config.json](./config.json) for repository-local paths.
3. If `config.json` still contains placeholders, keep generated code generic.

## Naming Summary

- `CamelCase` for namespaces, classes, and structs
- `camelCase` for methods
- `snake_case_` for member fields
- `snake_case` for file names
- `UPPER_SNAKE_CASE` for macros and constants

## Reference Files

- `references/gn-templates.md`
- `references/thread-patterns.md`
- `references/serialization.md`
- `references/permission-config.md`

## Notes

- Do not assume the checked-in config matches the current machine.
- Prefer repository-local `.clang-format` settings when available.
- Keep OHOS adaptation code isolated instead of spreading platform checks across unrelated files.

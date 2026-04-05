# ohos-cpp-style

Supplemental notes for the Codex-facing `ohos-cpp-style` skill.

## Scope

This directory is no longer a project-specific rmw_dsoftbus migration bundle. Treat it as a reusable OHOS C/C++ guidance pack for:

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
- rmw_dsoftbus/src/session_manager.cpp
- rmw_dsoftbus/src/native_token.cpp
- rmw_dsoftbus/test/softbus_dlopen_shim.cpp

### 构建文件
- rmw_dsoftbus/BUILD.gn

## 🔄 更新记录

### v1.0.0 (2026-01-15)
- 初始版本
- 基于 rmw_dsoftbus 项目实战经验
- 涵盖 10 大主题
- 包含完整代码模板和示例

## 📞 反馈和改进

如果发现规范中的问题或有改进建议，请：
1. 检查实际代码是否符合新的最佳实践
2. 更新 skill.md 中的相应章节
3. 在 README.md 中记录更新

---

**创建日期**: 2026-01-15
**基于项目**: rmw_dsoftbus (M-DDS)
**分析代码行数**: 约 3000+ 行
**参考文档数**: 10+ 篇

---
name: api-mapping
description: Linux API to OpenHarmony API mapping guidance. Use when Codex needs to replace Linux-specific APIs, choose OpenHarmony-native equivalents, or sketch compatibility layers during a port.
---

# API Mapping

Use this skill while replacing Linux-specific APIs in a ported codebase.

## Workflow

1. Confirm the original Linux API surface that the code depends on.
2. Check `references/linux-api-mapping.md` for the closest OpenHarmony-native replacement.
3. Decide whether the right fix is a direct API swap, a compatibility shim, or feature reduction.
4. Keep adaptation code isolated in a narrow file pair instead of scattering conditional logic across the codebase.

---
name: stub-interposition
description: Runtime function interposition for diagnostics and tests. Use when Codex needs to trace or override dynamic calls with `LD_PRELOAD` stubs without recompiling the target binary.
---

# Stub Interposition

Use this skill when runtime inspection is easier than invasive source edits.

## Workflow

1. Pick the narrowest stub that isolates the behavior under test.
2. Build the stub with `scripts/stubctl build <stub-name>`.
3. Run the target with `scripts/stubctl run <stub-name> -- <command>`.
4. Keep the stubs focused on logging or temporary behavior overrides, not product logic.

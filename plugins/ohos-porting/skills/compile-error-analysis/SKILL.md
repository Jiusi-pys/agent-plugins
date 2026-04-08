---
name: compile-error-analysis
description: OpenHarmony compile and link failure diagnosis. Use when Codex needs to classify build failures, narrow them to missing headers, bad symbols, type errors, or linker problems, and choose the next repair step.
---

# Compile Error Analysis

Use this skill after a build fails.

## Workflow

1. Capture the failing command and the smallest log excerpt that proves the failure class.
2. Categorize the failure as header, symbol, type, or linker related.
3. Fix the lowest-level cause first.
4. Re-run the narrowest build or test target that reproduces the failure.

## Helper

```bash
./scripts/analyze_errors.sh build.log
```

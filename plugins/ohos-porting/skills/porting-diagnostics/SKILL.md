---
name: porting-diagnostics
description: Portability diagnostics for Linux software moving to OpenHarmony. Use when Codex needs to scan a source tree, identify unsupported APIs, review dependency risk, and estimate migration difficulty before coding starts.
---

# Porting Diagnostics

Use this skill before editing code.

## Quick Start

```bash
./scripts/quick_scan.sh /path/to/source
python3 scripts/full_analysis.py /path/to/source --output report.json
```

## Workflow

1. Run the quick scan to identify obvious platform-only APIs and dependencies.
2. Run the full analysis for a source tree that looks viable.
3. Group findings into direct replacements, missing dependencies, and architectural blockers.
4. Feed the results into `ohos-porting-workflow`.

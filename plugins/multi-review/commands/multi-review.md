---
description: 异质多感知代码审查 (preflight → 风险路由 → 并行只读 sensor → 独立反证 → 统一裁决)。不做多数投票；只有已验证的问题才阻断；绝不自动改码或合并。
argument-hint: "[<commit-sha> | staged | <ref> | <a..b>] [deep] [--intent <path>]"
---

Run the **multi-review** code-review pipeline. The selection comes from
`$ARGUMENTS` (empty → review the working tree).

## 1. Parse `$ARGUMENTS` into a workflow `args` object

- the lone word `staged` → `{ "staged": true }`
- a single commit (`commit <sha>`, a bare sha, `HEAD`, `HEAD~2`, …) → `{ "commit": "<sha>" }`
- a range `<a>..<b>` / `<a>...<b>`, or a branch/ref like `origin/main` → `{ "target": "<value>" }`
- empty → no target key (working tree)
- the word `deep` anywhere → also set `"mode": "deep"`
- `--intent <path>` → also set `"intent_file": "<path>"`

Always also set:
- `"preflight": "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.sh"`

## 2. Launch the workflow

Call the **Workflow** tool with:
- `scriptPath`: `"${CLAUDE_PLUGIN_ROOT}/workflows/multi-review.js"`
- `args`: the object built in step 1

(The workflow orchestrates the plugin's namespaced subagents
`multi-review:review-*`: risk-router → parallel sensors → independent verifier →
judge. It runs in the background; the user can watch it with `/workflows`.)

## 3. Report

Relay the final gate — `PASS` / `PASS_WITH_NOTES` / `HUMAN_REQUIRED` / `BLOCK` /
`REJECT_INTAKE` — together with the returned `summary_markdown`. Do **not**
auto-edit code or auto-merge; final merge responsibility stays with a human owner.

> First time in a repo? Copy `${CLAUDE_PLUGIN_ROOT}/templates/REVIEW.md` to the
> repo root for project-specific risk policy, and `templates/intent.md` to
> `.review/intent.md` for per-PR intent.

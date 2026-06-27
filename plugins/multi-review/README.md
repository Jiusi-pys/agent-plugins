# multi-review

Heterogeneous, evidence-gated code review for Claude Code. A deterministic
preflight, a risk router, parallel **read-only** sensors, an **independent
falsifier**, and a unified judge — wired together as a dynamic workflow.

Design principle (after Addy Osmani, *Agentic Code Review*): value comes from
**heterogeneity, not headcount**. So there is **no majority-vote filtering**
(a singleton finding survives), every candidate is killed or kept by an
**independent verifier** that receives only `{target, claim, location,
reproduction_hint}` (never the originating reviewer's reasoning), **only verified
findings block**, R2 bearing-path changes are always `HUMAN_REQUIRED`, and the
pipeline **never edits code and never merges**.

## Install

```bash
/plugin marketplace add Jiusi-pys/agent-plugins
/plugin install multi-review@jiusi-agent-plugins
```

## Use

```
/multi-review                       # review the working tree (uncommitted + untracked)
/multi-review <sha>                 # review exactly one commit
/multi-review HEAD                  # review the latest commit
/multi-review staged                # review only staged changes
/multi-review origin/main           # this branch vs a ref (ref...HEAD)
/multi-review abc123..def456        # an explicit commit range
/multi-review <sha> deep            # deep mode (more sensors, verify everything)
/multi-review HEAD --intent .review/intent.md
```

Selection precedence: a single `commit` > `staged` > `target` (ref/range) >
working tree. The pipeline runs in the background; watch it with `/workflows`.

### Result — one gate plus a human summary

| Gate | Meaning |
| ---- | ------- |
| `PASS` | nothing verified, no human trigger |
| `PASS_WITH_NOTES` | only verified low/medium issues |
| `HUMAN_REQUIRED` | an unresolved high-risk item, or any R2 bearing-path change |
| `BLOCK` | a deterministic gate failed, or a verified critical/high finding |
| `REJECT_INTAKE` | unreviewable: oversized, or missing intent / test evidence (R3) |

## What's inside

| Component | What it is |
| --------- | ---------- |
| `skills/review-contract/SKILL.md` | single source of truth for the Finding / verdict / risk-route / judge schemas + evidence bar |
| `agents/review-risk-router.md` | cheap (haiku) risk tiering R0–R3 + sensor selection |
| `agents/review-correctness.md` · `review-test-integrity.md` · `review-security.md` · `review-architecture.md` · `review-runtime.md` · `review-intent.md` | six read-only sensors (sonnet), each with a distinct failure model |
| `agents/review-verifier.md` | independent falsifier (opus) — confirms a candidate before it can block |
| `agents/review-judge.md` | synthesizes verified verdicts into the final gate (opus) |
| `commands/multi-review.md` | the `/multi-review` entry point (launches the workflow) |
| `workflows/multi-review.js` | the orchestrator (dynamic workflow, run via the command) |
| `scripts/preflight.sh` | deterministic gate + intake scoring (also usable standalone in CI) |
| `templates/REVIEW.md` · `templates/intent.md` | copy into your repo: static review policy + per-PR intent |

## Per-repo setup (recommended)

```bash
cp "$(plugin root)/templates/REVIEW.md" ./REVIEW.md          # static risk policy
mkdir -p .review && cp "$(plugin root)/templates/intent.md" .review/intent.md
```

`REVIEW.md` (repo root) declares high-risk paths, the risk-scoring weights, and
the evidence bar; sensors read it to calibrate severity. `.review/intent.md`
records per-PR Goal / Acceptance criteria / Non-goals so the intent sensor can
check "is this what was asked".

## Standalone preflight (CI)

`scripts/preflight.sh` emits one JSON object and exits `0`=OK / `10`=BLOCK /
`20`=REJECT_INTAKE, so it doubles as a CI deterministic gate:

```bash
scripts/preflight.sh                 # working tree
scripts/preflight.sh 'HEAD^!'        # exactly the latest commit
scripts/preflight.sh origin/main     # this branch vs origin/main
scripts/preflight.sh staged          # staged changes only
```

Env toggles: `REVIEW_RUN_GATES` (lint/typecheck, default 1) · `REVIEW_RUN_TESTS`
(default 0) · `REVIEW_GATE_TIMEOUT` · `REVIEW_REJECT_SCORE` (default 12) ·
`REVIEW_HARD_MAX_LINES` (4000) · `REVIEW_HARD_MAX_FILES` (80) ·
`REVIEW_INTENT_FILE`.

## Composition with the built-in cloud review

```
R0: preflight (+ optional /code-review low)
R1: /multi-review
R2: /multi-review + /code-review ultra + a human owner
R3: split / supply evidence, then re-run
```

`/code-review ultra` is Anthropic's cloud multi-agent review — use it as an extra
sensor on R2 changes, not a replacement for project gates or the human chain of
responsibility.

## Notes

- Sensors are **read-only**: their `tools` exclude Edit/Write, and the static ones
  run in `permissionMode: plan`. `review-runtime` and `review-verifier` may execute
  the narrowest safe commands (`permissionMode: default`) to observe behavior.
- The workflow references its sensors by their namespaced ids (`multi-review:review-*`)
  and its bundled preflight via `${CLAUDE_PLUGIN_ROOT}`, so it is fully self-contained.
- Requires `python3` for `preflight.sh`'s JSON assembly (falls back to a minimal
  manual JSON if absent). Linux/macOS shell.

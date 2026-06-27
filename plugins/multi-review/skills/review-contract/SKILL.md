---
name: review-contract
description: Shared output contract for the multi-sensor code-review pipeline. Defines the Finding, Verifier verdict, Risk-route, and Judge gate schemas plus the evidence bar. Preloaded by every review subagent so candidate findings, verdicts and gate decisions share one machine-readable format.
---

# Review Contract

This Skill is the **single source of truth** for every artifact exchanged inside
the `multi-review` pipeline. Reviewers, the verifier, the risk router and the
judge all speak these schemas. Do **not** invent free-prose protocols between
agents — prose is for the human-facing summary only.

The design principle behind this contract (after Addy Osmani, *Agentic Code
Review*): value comes from **heterogeneity, not headcount**. A single reviewer
may raise a candidate; it is kept or killed by an **independent verifier**, never
by majority vote. Therefore:

- Reviewers emit **candidates**, not verdicts.
- A candidate with no `trigger` and no `evidence` never reaches verification.
- Only a **verified** finding may block.
- Findings must be **introduced by the target diff** — pre-existing issues are
  out of scope.
- CI-deterministic concerns (formatting, lint, type, naming, style) never become
  AI findings.

---

## 1. Finding (emitted by every sensor)

Sensors return a JSON object `{ "findings": Finding[] }`. Return
`{ "findings": [] }` when no evidence-supported issue exists. One `Finding`:

```json
{
  "sensor": "review-correctness",
  "location": { "file": "src/auth/session.ts", "line": 142 },
  "introduced_by_diff": true,
  "claim": "logout 与 token refresh 并发时可能重新激活已注销会话",
  "impact": "攻击者或旧客户端能够继续使用已注销会话",
  "trigger": "refresh 在 logout 删除会话之后提交",
  "evidence": ["src/auth/session.ts:128-151", "src/auth/logout.ts:44-53"],
  "reproduction_hint": "并行执行 refresh 与 logout,并控制 refresh 在删除后提交",
  "severity": "high",
  "confidence": 0.76
}
```

| Field                | Type                                            | Rule |
| -------------------- | ----------------------------------------------- | ---- |
| `sensor`             | string                                          | Originating subagent `name`. |
| `location.file`      | string                                          | Repo-relative path. |
| `location.line`      | integer                                         | Best line; `0` if file-level. |
| `introduced_by_diff` | boolean                                         | MUST be `true` to be reportable. |
| `claim`              | string                                          | The concrete defect, not a pattern smell. |
| `impact`             | string                                          | What breaks for a user / the system. |
| `trigger`            | string                                          | Concrete path/condition that exercises it. Required. |
| `evidence`           | string[] of `file:line` / `file:start-end`      | ≥1 entry. Required. |
| `reproduction_hint`  | string                                          | Narrowest way to reproduce/observe. |
| `severity`           | `"critical" \| "high" \| "medium" \| "low"`     | Behavioral impact, not aesthetics. |
| `confidence`         | number `0.0–1.0`                                | **Only schedules verification. Never blocks directly.** |

A finding **missing `trigger` or `evidence` is discarded before verification.**

---

## 2. Verifier verdict (emitted by `review-verifier`)

The verifier receives **only** `{ target, claim, location, reproduction_hint }`
— never the originating reviewer's reasoning, impact text, or evidence chain.
It must trace the path itself and try to **falsify first**.

```json
{
  "candidate_ref": { "file": "src/auth/session.ts", "line": 142 },
  "status": "verified",
  "introduced_by_diff": true,
  "trigger": "concrete, reconstructed trigger path",
  "evidence": ["src/auth/session.ts:128-151"],
  "rationale": "为何成立/不成立的判断依据",
  "needs_human": null,
  "severity": "high"
}
```

| Field                | Type                                            | Rule |
| -------------------- | ----------------------------------------------- | ---- |
| `candidate_ref`      | `{file, line}`                                  | Echoes the candidate under test. |
| `status`             | `"verified" \| "rejected" \| "unresolved"`      | Exactly one. |
| `introduced_by_diff` | boolean                                         | Verifier's own determination. |
| `trigger`            | string \| null                                  | Required, concrete, when `verified`. |
| `evidence`           | string[]                                        | Code/runtime evidence; required when `verified`. |
| `rationale`          | string                                          | Why verified / rejected / unresolved. |
| `needs_human`        | string \| null                                  | Required when `unresolved`: exactly what needs human judgment. |
| `severity`           | severity enum \| null                           | Verifier may correct the candidate's severity. |

Rules:
- `verified` ⇒ concrete `trigger` **and** `evidence`, and `introduced_by_diff: true`.
- `unresolved` ⇒ non-null `needs_human`.
- Default to `rejected`/`unresolved` under uncertainty — do not confirm on a hunch.

---

## 3. Risk route (emitted by `review-risk-router`)

```json
{
  "risk_level": "R2",
  "score": 7,
  "signals": [
    { "signal": "touches src/auth/**", "points": 3 },
    { "signal": "changed_files=31 (>25)", "points": 2 },
    { "signal": "no acceptance criteria", "points": 2 }
  ],
  "sensors": [
    "review-correctness", "review-test-integrity", "review-security",
    "review-architecture", "review-intent"
  ],
  "recommend_ultrareview": true,
  "always_human_required": true,
  "rationale": "承重认证路径 + 大 diff + 缺意图"
}
```

| Field                   | Type                              | Rule |
| ----------------------- | --------------------------------- | ---- |
| `risk_level`            | `"R0" \| "R1" \| "R2" \| "R3"`    | See REVIEW.md scoring. |
| `score`                 | integer                           | Sum of signal points. |
| `signals`               | `{signal, points}[]`              | Each contributing signal. |
| `sensors`               | string[] of sensor names          | Which sensors to run this round. |
| `recommend_ultrareview` | boolean                           | True for R2/R3 bearing paths. |
| `always_human_required` | boolean                           | True for R2. |
| `rationale`             | string                            | One-line justification. |

Valid sensor names: `review-correctness`, `review-test-integrity`,
`review-security`, `review-architecture`, `review-runtime`, `review-intent`.

Risk tiers (seed; calibrate against project history):

| Tier | Meaning            | Sensor set |
| ---- | ------------------ | ---------- |
| R0   | mechanical         | 1 fast reviewer (`review-correctness`) |
| R1   | ordinary behavior  | correctness + test-integrity + security; verify high-confidence |
| R2   | bearing path       | + architecture (+ intent / runtime); verify each; ultrareview; human owner |
| R3   | unreviewable       | **circuit-break** — no fleet; demand split / evidence |

---

## 4. Judge gate (emitted by `review-judge`, final pipeline output)

```json
{
  "gate": "HUMAN_REQUIRED",
  "risk_level": "R2",
  "blocking_findings": [],
  "human_required_reasons": ["R2 bearing-path change always requires a human owner"],
  "notes": [],
  "unresolved": [],
  "summary_markdown": "## Review summary\n..."
}
```

| Field                    | Type                                                              | Rule |
| ------------------------ | ----------------------------------------------------------------- | ---- |
| `gate`                   | `"PASS" \| "PASS_WITH_NOTES" \| "HUMAN_REQUIRED" \| "BLOCK" \| "REJECT_INTAKE"` | Final decision. |
| `risk_level`             | risk enum                                                         | Echoed from route. |
| `blocking_findings`      | Finding[] (verified only)                                        | Only `verified` findings may appear. |
| `human_required_reasons` | string[]                                                          | Why a human must decide. |
| `notes`                  | Finding[]                                                         | Non-blocking, ≤5 (see evidence bar). |
| `unresolved`             | Finding[]                                                         | High-risk unresolved items. |
| `summary_markdown`       | string                                                            | Concise human-facing report. |

Gate logic:

- Deterministic preflight failure ⇒ **BLOCK** (non-negotiable).
- Intake violation (no intent / no test evidence / oversized diff) ⇒ **REJECT_INTAKE**.
- Any `verified` `critical`/`high` finding ⇒ **BLOCK**.
- `unresolved` high-risk finding ⇒ **HUMAN_REQUIRED**.
- R2 change ⇒ always **HUMAN_REQUIRED** (even if otherwise clean).
- Verified low/medium only, no human trigger ⇒ **PASS_WITH_NOTES**.
- Nothing verified, no human trigger ⇒ **PASS**.

Never auto-modify code. Never auto-merge.

---

## 5. Evidence bar (shared by all sensors)

- Behavioral findings MUST give a concrete trigger path.
- MUST cite `file:line` evidence.
- MUST be introduced by the current diff.
- Do NOT report CI-deterministic issues (lint/format/type/style/naming).
- Do NOT report pre-existing issues the diff did not introduce.
- A reviewer reports at most **5 non-blocking** findings per run; prioritize by
  blast radius, not count.
- A "suspicious pattern" is not a finding until a concrete trigger is traced.

# REVIEW.md — code review policy

> Static review policy for the `multi-review` pipeline and any managed Claude
> Code Review. Per-PR *intent* does **not** live here — it lives in the PR body
> or `.review/intent.md` (see template). Claude's managed Code Review injects
> this file as top-priority review instructions; the custom pipeline requires
> each sensor to read it.

## High-risk paths

Touching any of these raises the risk tier and pulls in the security /
architecture sensors:

- `src/auth/**`, `**/auth/**`, `**/authz/**`
- `src/billing/**`, `**/payment*/**`
- `src/privacy/**`, `**/pii/**`
- `migrations/**`, `**/migration*/**`, `**/schema*/**`
- `.github/workflows/**`, `**/ci/**`
- `infrastructure/**`, `**/terraform/**`, `**/k8s/**`, `**/helm/**`
- `src/agents/**`, `**/prompt*/**`, `**/llm/**` (user-controlled data → LLM/tools)

## Risk scoring (seed — calibrate against project PR + incident history)

Sum the points; map to a tier. These are seed weights, not gospel.

| Signal                                                   | Points |
| -------------------------------------------------------- | ------ |
| `changed_files > 25`                                     | +2     |
| `changed_lines > 800`                                    | +2     |
| modifies auth / payment / migration / CI                 | +3     |
| deletes or skips tests                                   | +4     |
| lowers coverage / lint / type / security threshold       | +5     |
| changes a public API or a persisted format               | +3     |
| no acceptance criteria supplied                          | +2     |
| no test command + output supplied                        | +2     |

| Tier | Score band (seed) | Strategy |
| ---- | ----------------- | -------- |
| R0   | 0                 | deterministic gates + 1 fast reviewer |
| R1   | 1–4               | 3 sensors + verify high-confidence candidates |
| R2   | ≥5, or any bearing path / test weakening / threshold drop | 5 sensors + verify each + `/code-review ultra` + domain owner |
| R3   | intake score ≥ 12, or > 4000 changed lines, or > 80 changed files, or no intent / no evidence | **circuit-break**: split or supply evidence, do not run the fleet |

R3 is a fuse, not "send more agents." The numeric circuit-break boundary lives in
`scripts/review/preflight.sh` and is tunable: `REVIEW_REJECT_SCORE` (default 12),
`REVIEW_HARD_MAX_LINES` (default 4000), `REVIEW_HARD_MAX_FILES` (default 80).
At/above any of these, preflight returns `REJECT_INTAKE` before the fleet runs.

## Important findings (always at least Important)

- authentication or authorization bypass
- tenant / user data crossing a boundary
- irreversible schema change
- deleting, skipping, or weakening tests
- lowering lint / coverage / typecheck / security gates
- user-controlled data reaching an LLM prompt / tool call / agent memory unconstrained
- backward-incompatible public API change
- non-idempotent behavior that can double-charge or double-write

## Evidence bar

- Behavioral findings MUST give a concrete trigger path.
- MUST cite `file:line` evidence.
- Do NOT report issues CI deterministically covers (lint/format/type/style).
- Do NOT report pre-existing issues the current diff did not introduce.
- At most **5 non-blocking** findings per run.

## Gate outcomes

`PASS` · `PASS_WITH_NOTES` · `HUMAN_REQUIRED` · `BLOCK` · `REJECT_INTAKE`

- Only deterministic-gate failures and **verified** critical/high findings BLOCK.
- R2 bearing-path changes are always `HUMAN_REQUIRED`.
- The pipeline never auto-modifies code and never auto-merges; final merge
  responsibility stays with a human owner.

## Pipeline ↔ built-in review composition

```
R0: preflight + /code-review low
R1: /multi-review
R2: /multi-review + /code-review ultra + human owner
R3: split / supply evidence before review
```

`/code-review ultra` (a.k.a. `claude ultrareview <ref> --json`) is an extra
**cloud sensor** for R2, not a replacement for project-specific gates, the risk
router, or the human chain of responsibility.

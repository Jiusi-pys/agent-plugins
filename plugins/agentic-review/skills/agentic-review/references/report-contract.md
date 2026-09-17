# Review report contract

Lead with actionable findings. Keep the report useful even when commentary or inline annotations are hidden.

## Finding format

Order findings by priority, then by confidence:

- **P0 — Stop-ship:** active exploitation, irreversible loss, or catastrophic failure is credible and immediate.
- **P1 — High:** likely correctness, security, privacy, data, availability, or core-design failure that should be resolved before proceeding.
- **P2 — Medium:** bounded but material defect, missing requirement, operational gap, or maintainability risk.
- **P3 — Low:** worthwhile improvement with a concrete consequence; omit cosmetic preferences.

Each finding contains:

1. a concise imperative title;
2. the tightest file and line/section location;
3. observed evidence, clearly separated from inference;
4. an activating scenario and resulting impact;
5. a concrete remediation or decision needed;
6. how to verify the resolution;
7. confidence (`high`, `medium`, or `low`) and what limits it.

Do not inflate priority because a topic sounds important. If consequence or reachability is unproven, lower confidence, gather evidence, or present it under open questions instead of as a finding.

## Summary after findings

Include:

- **Scope and baseline:** exact artifact reviewed and exclusions.
- **Intent:** short statement labeled `stated` or `inferred`.
- **Risk tier:** tier and the dimensions that drove it.
- **Evidence ledger:** commands/checks inspected or run, outcomes, and gaps. Distinguish `passed`, `failed`, `not run`, and `not applicable`.
- **Human decision points:** choices about product intent, risk acceptance, ownership, or high-blast-radius release.
- **Residual risk:** what this review could not establish.

Use `not ready for full review` when intake is inadequate, `material concerns found` when P0/P1/P2 findings remain, and `no actionable findings found` when none remain. These are assessments, not merge or publication authority.

If there are no findings, say so directly and still provide scope, evidence gaps, and residual risk. Never imply that absence of findings proves correctness.

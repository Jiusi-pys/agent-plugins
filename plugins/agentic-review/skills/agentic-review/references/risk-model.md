# Risk model

Select review depth according to the cost of being wrong, not who or what authored the artifact.

## Core dimensions

Assess each dimension explicitly:

- **Blast radius:** affected users, money, data, privacy, security, availability, compliance, and downstream systems.
- **Lifetime:** throwaway experiment, short-lived feature, or infrastructure expected to be maintained for years.
- **Shared understanding:** one informed owner, a small team, or many teams that must operate and evolve the result.
- **Reversibility:** simple rollback, stateful migration, destructive or externally committed action.
- **Uncertainty:** ambiguity in intent, unfamiliar components, unverifiable assumptions, missing evidence, or novel technology.

Automated path and size signals are hints. A one-line authorization change can be Tier 3; a large generated snapshot can be Tier 0.

## Tiers

| Tier | Typical consequence | Minimum review depth | Human gate |
|---|---|---|---|
| 0 — Trivial | Local, reversible, short-lived, no meaningful user or data impact | Scope confirmation, relevant deterministic check, focused inspection | Owner samples the result |
| 1 — Routine | Localized maintained behavior with bounded impact | Intent reconstruction, deterministic checks, all three review passes, relevant tests | Owner understands residual risk |
| 2 — Significant | Cross-component behavior, shared interfaces, user-visible failure, dependencies, CI, or operational change | Tier 1 plus broader call-site/consumer tracing, failure and rollback analysis, stronger evidence | Responsible maintainer reviews decision points |
| 3 — Critical | Auth, payments, secrets, privacy/PII, destructive data changes, trust boundaries, safety, compliance, or high availability | Full evidence stack, security/abuse analysis, independent reviewer with different priors, owner-specific runbook and rollback proof | Named accountable human must decide |

Choose the highest tier indicated by any credible dimension. Record why the tier was chosen and what evidence could change it.

## Layered evidence

Apply cheap, deterministic evidence before expensive interpretation when it is safe and relevant:

1. syntax/format/schema validation;
2. lint, type checks, static analysis, or document link/structure checks;
3. focused tests or executable examples;
4. broader integration, mutation, performance, compatibility, or security checks proportionate to risk;
5. model review lenses;
6. human ownership of consequential judgment.

Do not run commands that require new dependencies, network access, secrets, or meaningful external writes without authorization. Report skipped layers and why.

## Intake evidence by tier

Tier 0 can proceed with inferred intent when impact is genuinely negligible. Tier 1 and above should have a clear objective, scope, and observed verification output. Tier 2 should also identify consumers, compatibility constraints, and rollback. Tier 3 should identify an accountable owner, trust boundaries, abuse cases, operational detection, and a tested recovery path.

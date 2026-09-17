# Software design document review

Review a design as an executable decision record: it should let implementers, operators, and future maintainers understand what to build, why it is the right tradeoff, and how failure will be detected and recovered.

## Establish the decision

Extract and cross-check:

- problem statement, users/stakeholders, goals, and non-goals;
- measurable success criteria and constraints;
- current state and evidence that the problem is real;
- proposed system boundaries, ownership, and dependencies;
- alternatives considered and the reason they were rejected;
- assumptions that must remain true.

Mark missing information rather than filling it in silently. Verify repository-specific claims against local code or documentation when feasible.

## Comprehension lens

Walk one normal scenario end to end. Check that components, APIs, data models, states, invariants, and ownership form a coherent system. Look for undefined terms, contradictory diagrams/prose, hand-waved integrations, and decisions deferred to implementation that materially affect feasibility.

## Adversarial lens

Walk boundary and failure scenarios:

- malformed, stale, duplicated, reordered, adversarial, or unexpectedly large input;
- dependency timeout, partial outage, retry storm, split brain, concurrency, and backpressure;
- authorization and trust-boundary transitions;
- data classification, privacy, retention, deletion, residency, and audit needs;
- migration from the current state, mixed-version operation, and rollback after state changes;
- capacity, cost, performance, accessibility, and operational ownership;
- abuse and misuse that the stated requirements omit.

Report a design defect only when a plausible scenario violates a goal, invariant, or necessary property. Phrase open product choices as human decision points, not bugs.

## Verification lens

Require a proportionate proof plan:

- acceptance criteria tied to goals;
- prototypes or experiments for the riskiest assumptions;
- test strategy at component and system boundaries;
- observability that distinguishes success, degradation, and silent corruption;
- rollout stages, guardrails, stop conditions, rollback or forward-fix strategy;
- owner and operational response for critical failure modes.

A design is not complete merely because its happy-path architecture is plausible. For Tier 2 or 3, unresolved high-impact assumptions need an owner and a deadline or explicit decision gate.

## Document-quality boundary

Comment on writing or structure only when it obstructs a decision, creates multiple reasonable interpretations, hides a risk, or prevents implementation/operation. Copyediting is outside this review unless requested.

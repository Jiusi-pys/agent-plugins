# Local code review

## Build a change map

Inspect repository guidance first (`AGENTS.md`, contributing instructions, local policies, and relevant package documentation). Establish Git status and the exact baseline before reading isolated hunks.

Map changed files to runtime behavior:

- entry points and callers;
- data and control flow across changed boundaries;
- public APIs, schemas, configuration, and compatibility promises;
- tests, fixtures, generated artifacts, lockfiles, CI, and deployment paths;
- existing helpers or conventions the change may duplicate or bypass.

Use repository search to validate reachability and assumptions. Do not infer runtime impact from filenames alone.

## Comprehension lens

Explain the behavioral delta in plain language. Check whether the implementation matches the stated intent and non-goals, including negative space: behavior that should remain unchanged. Identify hidden coupling, new state, changed defaults, or implicit contracts.

## Adversarial lens

Prioritize material defects:

- incorrect branches, boundary conditions, units, ordering, concurrency, retries, idempotency, and partial failure;
- validation gaps and unsafe transitions across trust boundaries;
- authorization, authentication, injection, secret, privacy, and data-retention failures;
- backward/forward compatibility and migration sequencing;
- resource leaks, unbounded work, performance cliffs, and availability hazards;
- error handling that converts detectable failure into silent corruption or misleading success.

Trace a concrete failure scenario before reporting a finding. State the input or system state that activates it and the observable consequence.

## Verification lens

Read changed tests more skeptically than unchanged production code. Look for assertions rewritten to bless new behavior, removed cases, newly skipped tests, weakened coverage or lint thresholds, broad mocks, golden-file churn, and checks that never exercise the changed path.

Run the smallest repository-provided checks that can falsify the change, then expand according to the risk tier. Prefer existing scripts and documented commands. Capture the exact command and outcome. Do not claim a check passed if it was not run in the current review.

When valuable and already supported by the project, consider mutation, property, fuzz, integration, compatibility, or load testing. Do not introduce these frameworks during a read-only review.

## False-positive filter

Before reporting a candidate:

1. verify the referenced code is in scope and reachable;
2. search for validation or compensation elsewhere;
3. check language/framework semantics rather than relying on memory when uncertain;
4. distinguish a present defect from a future hardening idea;
5. calibrate priority by realistic consequence and likelihood.

Style, naming, and optional refactors are findings only when they cause ambiguity, broken conventions with concrete tooling impact, or meaningful maintenance risk.

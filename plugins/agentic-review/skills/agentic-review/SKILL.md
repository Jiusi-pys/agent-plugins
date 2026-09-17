---
name: agentic-review
description: Review local code changes or software design documents with risk-tiered depth, deterministic evidence, adversarial analysis, and explicit human decision gates. Use for working-tree, staged, commit, branch, file, directory, architecture proposal, RFC, ADR, or technical design reviews. Do not activate for ordinary implementation or editing unless the user also asks for a review.
---

# Agentic Review

Treat review as a trust-building activity, not a prose-generation task. The result is a set of sensors and evidence for a human owner; it is never permission to merge, publish, or modify the reviewed artifact.

## Operating contract

- Default to read-only inspection. Do not edit code or documents, install dependencies, publish comments, or change external state unless the user separately authorizes that action.
- Review the requested scope, not the entire repository by reflex. Preserve unrelated working-tree changes.
- Separate observed facts, inferred intent, and unresolved questions. Never present an inference as a repository fact.
- Prefer a small number of validated findings over speculative coverage. Before reporting a candidate, try to disprove it by tracing the relevant path, contract, test, or requirement.
- Treat test output and other automated checks as evidence, not as proof that the change is desirable or complete.
- Do not issue a bare approval such as "LGTM." If no actionable findings remain, state what was inspected, what was verified, what was not verified, and the residual risk.

## Choose the mode and scope

Use the user's explicit target and baseline. Otherwise:

- For a dirty Git worktree, review staged, unstaged, and relevant untracked files against `HEAD`.
- For a named commit or branch, use its merge-base or the baseline the user supplied.
- For named files or directories, stay within them while following directly relevant call sites, interfaces, and requirements.
- For a design artifact, review the document plus only the repository evidence needed to verify its claims.
- If no defensible target can be inferred, ask one concise question rather than silently reviewing an arbitrary scope.

For Git-backed code reviews, run `scripts/review_inventory.py` early when Python is available. It is read-only and emits patch-size and sensitive-path signals; these signals inform triage but do not determine risk by themselves.

## Establish the review basis

Before deep review, recover or record:

1. the intended outcome and non-goals;
2. the exact artifact scope and baseline;
3. constraints and externally visible behavior;
4. supplied verification evidence;
5. who or what can be harmed if the artifact is wrong.

Label intent as `stated` when it comes from the request, spec, ADR, commit message, or repository documentation, and as `inferred` otherwise. Missing intent is itself a reviewability risk, especially for broad or consequential changes.

Read [references/risk-model.md](references/risk-model.md) and assign the minimum justified tier. Raise the tier when uncertainty is material; do not lower it solely because checks are green.

## Apply the relevant review lenses

- For source code, configuration, migrations, tests, or local diffs, read and follow [references/code-review.md](references/code-review.md).
- For RFCs, ADRs, architecture notes, API proposals, schemas, rollout plans, or other software design documents, read and follow [references/design-review.md](references/design-review.md).
- If the target mixes design and implementation, apply both and cross-check whether the implementation actually realizes the design.

Perform distinct passes from the raw artifact rather than merely elaborating the first conclusion:

1. **Comprehension pass:** reconstruct intent, behavior, boundaries, and changed assumptions.
2. **Adversarial pass:** search for counterexamples, failure modes, abuse cases, and invalid assumptions.
3. **Verification pass:** inspect tests, checks, observability, rollout/rollback, and evidence gaps.

For Tier 3 work, explicitly recommend an independent reviewer with different priors or tooling when one has not been supplied. Do not simulate independence by claiming that repeated passes are different models.

## Fast-fail reviewability problems

Flag the artifact as `not ready for full review` when missing context or evidence makes a trustworthy deep review uneconomic, for example: an unexplained sprawling diff, absent or contradictory intent, generated noise dominating the change, no feasible validation story for consequential behavior, or weakened safeguards presented as a fix.

Still report high-confidence findings already established, but do not manufacture completeness. State the smallest concrete action that would make the artifact reviewable.

## Produce the report

Follow [references/report-contract.md](references/report-contract.md). Findings come first and are ordered by consequence. Every finding must connect evidence to a plausible failure scenario and a concrete verification or remedy.

When the Codex client supports inline code comments, attach concise actionable findings to the tightest relevant line range and keep the final summary self-contained. Do not create inline comments for praise, open questions without a defect, or style preferences with no material impact.

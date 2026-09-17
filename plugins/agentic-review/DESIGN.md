# Agentic Review for Codex

This plugin turns review into a risk-tiered evidence system for two local artifact types: code changes and software design documents. It is inspired by Addy Osmani's 2026 essay, “Agentic Code Review,” while remaining self-contained and usable without a hosted review service.

## Design principles

| Essay idea | Plugin behavior |
|---|---|
| Review depth should follow blast radius | A four-tier model also considers lifetime, shared understanding, reversibility, and uncertainty |
| Recover missing intent before reviewing implementation | The intake stage records intent as stated or inferred and can reject an unreviewable artifact |
| Push cheap deterministic gates early | Repository-provided validation, lint, types, and focused tests precede model conclusions |
| Different reviewers catch different failures | Codex performs distinct comprehension, adversarial, and verification passes; Tier 3 explicitly asks for a genuinely independent reviewer |
| Tests can be changed to bless broken behavior | Changed tests and weakened CI are reviewed as first-class risk surfaces |
| AI review is a sensor, not a verdict | Reports separate evidence, inference, residual risk, and named human decision points |
| Keep human attention for expensive mistakes | Findings are prioritized by consequence and risk tiers define the required human gate |

## Package layout

```text
agentic-review/
├── .codex-plugin/plugin.json
├── DESIGN.md
└── skills/agentic-review/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/
    │   ├── code-review.md
    │   ├── design-review.md
    │   ├── report-contract.md
    │   └── risk-model.md
    └── scripts/review_inventory.py
```

The single skill routes between code and design modes so mixed artifacts can be cross-checked without competing skill triggers. Detailed mode instructions are loaded only when relevant.

## Expected interaction

Example prompts:

- `Use $agentic-review to review my staged and unstaged changes against HEAD.`
- `Use $agentic-review to review commit abc123, focusing on compatibility and rollback.`
- `Use $agentic-review to review docs/payment-redesign.md and verify its claims against the repository.`

The default operation is read-only. Fixes, publishing comments, installing dependencies, or other mutations require a separate user request or authorization.

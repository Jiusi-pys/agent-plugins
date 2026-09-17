# Agentic Review

Review local code changes and software design documents using risk tiers, deterministic checks, adversarial analysis, and evidence-backed findings.

This package was imported from the installed personal `agentic-review` plugin, version `0.1.0`. Its skill and helper are preserved unchanged.

## Usage

Install `agentic-review` from this repository's `jiusi-agent-plugins` Codex marketplace, then ask:

- `Use $agentic-review to review my staged and unstaged changes against HEAD.`
- `Use $agentic-review to review this design document and check its claims against the code.`

The skill covers working-tree changes, commits, branches, and design documents. It reports evidence, uncertainty, and human decision points. See [DESIGN.md](DESIGN.md) for the review model and [SKILL.md](skills/agentic-review/SKILL.md) for the workflow.

## Contents

- `.codex-plugin/plugin.json`: Codex manifest and display metadata.
- `skills/agentic-review/`: Skill instructions, agent metadata, and review references.
- `skills/agentic-review/scripts/review_inventory.py`: Python helper for review inventory; run with `--help` for supported arguments.

The inventory helper uses the Python standard library and Git for repository inspection.

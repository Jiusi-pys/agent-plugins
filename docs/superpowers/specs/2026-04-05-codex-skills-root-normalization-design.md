# Codex Skills Root Normalization Design

Date: 2026-04-05

## Goal

Normalize the `openai` branch into a Codex-first skills repository by removing the remaining plugin container layer and exposing the retained OHOS skills directly under a repository-root `skills/` directory.

## Desired End State

The repository should read like a Codex skills repo, not a converted plugin repo.

After the change:

- the retained skills live at:
  - `skills/ohos-hdc`
  - `skills/ohos-cpp-style`
  - `skills/ohos-permission`
- `plugins/ohos-porting/` no longer exists
- the root `README.md` describes the repository as a Codex skills repository
- skill-internal relative references still work after the move
- retained skills still validate with the Codex skill validator

## Why This Layout

Direct root-level `skills/<skill-name>` paths are the cleanest shape for Codex skill installation and reuse.

Compared with `plugins/...` or `skills/ohos/...`, this layout:

- minimizes path depth
- matches the common self-contained Codex skill directory shape
- avoids keeping a leftover plugin abstraction in a branch that no longer ships plugins
- makes later copying or installing individual skills simpler

## In Scope

### Move the retained skills

Move these directories from `plugins/ohos-porting/skills/` to repository-root `skills/`:

- `ohos-hdc`
- `ohos-cpp-style`
- `ohos-permission`

### Remove the old plugin container

Delete the remaining `plugins/ohos-porting/` container once the skill move is complete.

### Rewrite repository docs

Update the root `README.md` so it no longer describes a converted plugin output and instead describes a root-level Codex skills repository.

## Out of Scope

- Renaming the three retained skills
- Splitting shared resources into a new shared `resources/` layer
- Reworking the internal content of the retained skills unless required by path updates
- Adding new skills beyond the three retained OHOS skills

## Design Decisions

### 1. Self-contained skill directories stay intact

Each moved skill remains self-contained. Its `SKILL.md`, `agents/openai.yaml`, `scripts/`, `references/`, `templates/`, and other local support files move together unchanged unless a path reference must be updated.

### 2. No additional namespace layer

The repository will use:

- `skills/ohos-hdc`
- `skills/ohos-cpp-style`
- `skills/ohos-permission`

and not:

- `skills/ohos/ohos-hdc`
- or any new `resources/ohos/` abstraction

This keeps the repository optimized for direct Codex skill consumption.

### 3. Documentation should describe current reality, not migration history

The root `README.md` should say this branch contains Codex skills. It may briefly mention the `main` vs `openai` split, but it should not center the repository around a now-removed plugin container.

## Planned File-Level Changes

### Create

- `skills/`
- `skills/ohos-hdc/`
- `skills/ohos-cpp-style/`
- `skills/ohos-permission/`

### Delete

- `plugins/ohos-porting/`

### Rewrite

- `README.md`

The rewritten root README should:

- identify the repo as a Codex skills repository on the `openai` branch
- mention the branch split only briefly
- list the three root-level skills
- stop referring to `plugins/ohos-porting` as the primary output location

## Path Integrity Requirements

Because the retained skills are mostly self-contained, relative links should continue to work after the move.

Still verify:

- relative links inside each `SKILL.md`
- paths mentioned in local `README.md` files
- scripts or docs that assume the old `plugins/ohos-porting/...` prefix

Any such reference should be updated to the new root-level `skills/...` path when necessary.

## Verification

The normalization is complete when all of the following are true:

1. `skills/ohos-hdc`, `skills/ohos-cpp-style`, and `skills/ohos-permission` exist.
2. `plugins/ohos-porting` no longer exists.
3. All retained shell scripts still pass `bash -n`.
4. All three retained skills still pass the Codex skill validator.
5. The root README describes root-level Codex skills rather than a plugin container layout.
6. Repository-wide search does not show stale references that still point users to `plugins/ohos-porting` as the installation or usage path.

## Risks

### Risk: stale path references after the move

Mitigation:

- search the repository for `plugins/ohos-porting`
- verify each retained skill's docs after relocation

### Risk: accidental over-normalization

Mitigation:

- do not refactor internal skill content beyond what is required for the directory move
- preserve each skill as a self-contained unit

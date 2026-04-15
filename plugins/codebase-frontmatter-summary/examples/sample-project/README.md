# Sample project fixture

This fixture now verifies the incremental sidecar-based indexer, not the old inline-frontmatter writer.

## One-command verification

From `plugins/codebase-frontmatter-summary/` run:

```bash
bash examples/sample-project/verify.sh
```

The script will:

1. Copy `input/` into `/tmp/repo-indexer-fixture`
2. Run `refresh` with the heuristic backend
3. Run `doctor`
4. Assert the key guide and sidecar outputs exist

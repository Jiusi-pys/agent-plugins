# Sample project fixture

Use this fixture to manually verify `scan_and_summarize.py` with deterministic local summaries.

## One-command verification

From `plugins/codebase-frontmatter-summary/` run:

```bash
bash examples/sample-project/verify.sh
```

## Generate a fresh output tree

From `plugins/codebase-frontmatter-summary/` run:

```bash
rm -rf /tmp/expected
cp -R examples/sample-project/input /tmp/expected
python3 skills/codebase-frontmatter-summary/scripts/scan_and_summarize.py \
  --root /tmp/expected \
  --backend heuristic \
  --write
```

## Compare with the checked-in expected output

```bash
diff -ru examples/sample-project/expected /tmp/expected
```

The temporary directory is named `expected` so the generated root `SUMMARY.md` matches the checked-in fixture exactly.

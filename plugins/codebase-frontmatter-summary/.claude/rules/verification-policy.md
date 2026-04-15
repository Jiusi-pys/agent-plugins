# Verification Policy

- Run `python3 tools/repo_indexer.py refresh --root <repo>` after structural changes.
- Run `python3 tools/repo_indexer.py doctor --root <repo>` before trusting a stale index.
- When guide or schema output changes, refresh and re-export the host guides.

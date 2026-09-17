---
name: ohos-remote-build
description: Linux-to-Linux remote OpenHarmony image build guidance. Use when Codex needs to sync local changes to a remote Linux host that already contains an OpenHarmony source tree and then run a product or target build there.
---

# OHOS Remote Build

Use this skill only for remote Linux build hosts that compile full OpenHarmony images or very large integrated targets.

## Workflow

1. Confirm the remote host alias, remote home, and OpenHarmony source root.
2. Sync only the changed files needed for the target build.
3. Run the remote build from the OpenHarmony source root.
4. Collect the build log and artifact paths.
5. Document the exact remote command and result in `working-records`.

## Example

```bash
rsync -avz ./subsystem/ cp:/kh_data/pengys/subsystem/
ssh cp 'cd /kh_data/pengys && ./build.sh --product-name rk3588 --ccache'
```

# OHOS Porting Plugin

Codex plugin for Linux-first OpenHarmony and KaihongOS porting work.

## Included Skills

- `ohos-porting-workflow`
- `ohos-hdc`
- `ohos-cpp-style`
- `ohos-permission`
- `ohos-cross-compile`
- `api-mapping`
- `compile-error-analysis`
- `porting-diagnostics`
- `runtime-debug`
- `stub-interposition`
- `working-records`
- `ohos-remote-build`
- `git-cicd-workflow`

## Environment Assumptions

- Linux host shell
- direct `hdc_std` or `hdc`
- OpenHarmony `command-line-tools`
- `openharmony_prebuilts`

## Notes

- This plugin does not ship legacy command shims or legacy agent wrappers.
- Repo-level Codex hooks provide OHOS-aware Bash guidance and guardrails.

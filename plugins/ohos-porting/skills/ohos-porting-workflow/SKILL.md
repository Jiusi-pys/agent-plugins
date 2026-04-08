---
name: ohos-porting-workflow
description: Linux-first OpenHarmony porting workflow guidance. Use when Codex needs to assess a Linux codebase, plan the port, prepare the OpenHarmony build environment, sequence code adaptation work, and close the loop with deploy and runtime validation.
---

# OHOS Porting Workflow

Use this skill for the top-level porting sequence.

## Workflow

1. Run `porting-diagnostics` to assess source portability and dependency risk.
2. Use `api-mapping` to replace Linux-only APIs.
3. Apply `ohos-cpp-style` while adapting native code.
4. Configure builds with `ohos-cross-compile`.
5. Deploy and test with `ohos-hdc`.
6. Debug runtime issues with `runtime-debug` and permission issues with `ohos-permission`.
7. Track milestones and blockers with `working-records`.

## Guardrails

- Keep test artifacts under `/data/local/tmp` until the port is stable.
- Require command output for each environment, build, deploy, and runtime claim.
- Treat integrated image builds as a separate track handled by `ohos-remote-build`.

# Project Constitution (Skill)

## Mission
Port rmw_dsoftbus from Ubuntu x86_64 to RK3588S aarch64 KaihongOS, then validate:
1) ferrium cross-compile + deploy pipeline works via a Hello World case
2) KaihongOS ROS2 and dsoftbus filesystem layout + version/dependency relations are understood and recorded
3) rmw_dsoftbus can be built and (eventually) validated against real dsoftbus capability

## Non-negotiable constraints
1) Target device: DO NOT modify system/vendor files not deployed by us.
2) If any change outside our workspace is unavoidable:
   - backup original first
   - record exact commands + file hashes
   - keep a rollback procedure
3) All writes on target MUST be under:
   - /data/robot (or /data/robot_work)
4) Prefer read-only inspection commands; avoid full-disk scanning:
   - no `find /` without narrowing to specific roots
5) Every claim about paths/versions MUST be backed by command output and written to ops/inventory/*.md.

## Operating discipline
- Reproducibility first: any repeated manual process must be scripted under ops/scripts/.
- Evidence first: no speculation about KaihongOS ROS2/dsoftbus. Mark unknowns explicitly.
- Small steps with gates:
  Gate A: ferrium Hello World deploy & run
  Gate B: ROS2 layout/version map on target
  Gate C: dsoftbus libs/headers/API entry points map
  Gate D: rmw_dsoftbus aarch64 build & link readiness

## Allowed tools and access
- Windows has hdc access to target; use MCP `hdc`.
- WSL Ubuntu can SSH to mirrors via `ssh rk` (read-only unless explicitly required).
- Any target-side command execution must be via hdc and must log outputs to /data/robot/logs or ops/journal.md.


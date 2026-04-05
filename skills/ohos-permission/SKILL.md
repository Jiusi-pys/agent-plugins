---
name: ohos-permission
description: DSoftBus session permission configuration guidance for OpenHarmony and KaihongOS. Use when Codex needs to configure, deploy, or verify DSoftBus session permission JSON and related device-side updates.
---

# OHOS Permission

Use this skill when editing, deploying, or validating DSoftBus session permission configuration.

## Verified Workflow

For production-scoped changes, start from `templates/minimal.json` and narrow only the fields you need.

```bash
cp templates/minimal.json /tmp/softbus_perm.json
./scripts/deploy_softbus_permission.sh <DEVICE_ID> /tmp/softbus_perm.json
hdc -t <DEVICE_ID> shell 'reboot'
./scripts/verify_softbus_permission.sh <DEVICE_ID>
```

## Core Rules

- The DSoftBus permission file must use a top-level JSON array.
- Do not wrap the data in an extra `trans_permission` object.
- Reboot is required after deployment before the permission change is active.
- Keep a backup before overwriting a device-side permission file.

## Correct Shape

```json
[
  {
    "SESSION_NAME": "com.huawei.ros2_rmw_dsoftbus.*",
    "REGEXP": "true",
    "DEVID": "NETWORKID",
    "SEC_LEVEL": "public",
    "APP_INFO": [
      {
        "TYPE": "native_app",
        "PKG_NAME": "com.huawei.ros2_rmw_dsoftbus",
        "ACTIONS": "create,open"
      }
    ]
  }
]
```

## Working Files

- `templates/minimal.json` for the safest production starting point
- `templates/dev.json` for development-only edits; narrow before deployment
- `templates/verified.json` for known-good reference data; wildcard or empty `PKG_NAME` fallback entries are non-production and must be narrowed before deployment
- `scripts/deploy_softbus_permission.sh` for device-side installation
- `scripts/verify_softbus_permission.sh` for validation

## Practical Workflow

1. Start from `templates/minimal.json` for production-scoped changes.
2. Use `templates/dev.json` or permissive `templates/verified.json` entries only as references or narrowed debug starting points.
3. Edit only the fields needed for the target package or session name.
4. Back up the current device file before deployment.
5. Deploy with the provided script.
6. Reboot the device before verification.
7. Run the verification script as a deployment sanity check.
8. After the reboot, run the actual DSoftBus/session functional flow and confirm it works end to end.

## AccessToken Notes

For KaihongOS API 11 verified-device workarounds only, see `examples/native_token.cpp` and the `RMW_DSOFTBUS_TOKEN_ID` and `RMW_DSOFTBUS_DISABLE_NATIVE_TOKEN` environment variables. Do not treat this as general OHOS permission guidance.

## Troubleshooting

- Permission denied after deployment usually means the JSON shape is wrong or the device has not restarted.
- If matching fails, check `REGEXP` and the exact package name or session name pattern.
- If the device rejects the file, validate the JSON structure before retrying.

---
name: ohos-permission
description: OpenHarmony and KaihongOS permission configuration guidance. Use when Codex needs to configure, deploy, or verify OHOS native permissions, especially DSoftBus session permissions, AccessToken-related setup, or device-side permission JSON updates.
---

# OHOS Permission

Use this skill when editing, deploying, or validating OpenHarmony permission configuration.

## Verified Workflow

Prefer the verified template and deployment scripts that already live in this skill.

```bash
cp templates/verified.json /tmp/softbus_perm.json
./scripts/deploy_softbus_permission.sh <DEVICE_ID> /tmp/softbus_perm.json
./scripts/verify_softbus_permission.sh <DEVICE_ID>
```

## Core Rules

- The DSoftBus permission file must use a top-level JSON array.
- Do not wrap the data in an extra `trans_permission` object.
- Device reboot may be required after updating the permission file.
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

- `templates/minimal.json` for the smallest valid starting point
- `templates/dev.json` for development-focused edits
- `templates/verified.json` for known-good deployment
- `scripts/deploy_softbus_permission.sh` for device-side installation
- `scripts/verify_softbus_permission.sh` for validation

## Practical Workflow

1. Pick the closest template.
2. Edit only the fields needed for the target package or session name.
3. Back up the current device file before deployment.
4. Deploy with the provided script.
5. Reboot if required by the target device.
6. Run the verification script and capture the output.

## Troubleshooting

- Permission denied after deployment usually means the JSON shape is wrong or the device has not restarted.
- If matching fails, check `REGEXP` and the exact package name or session name pattern.
- If the device rejects the file, validate the JSON structure before retrying.

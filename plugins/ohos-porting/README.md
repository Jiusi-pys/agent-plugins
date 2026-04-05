# OHOS Porting Skills

This directory contains Codex-facing OpenHarmony and KaihongOS skills.

## Included Skills

### `ohos-hdc`

Use for device discovery, shell access, file transfer, and log collection over HDC.

### `ohos-cpp-style`

Use for OpenHarmony C/C++ naming, file layout, formatting, and `BUILD.gn` guidance.

### `ohos-permission`

Use for OHOS permission JSON editing, deployment, and verification, especially for DSoftBus-related setups.

## Layout

```text
plugins
└── ohos-porting/
    ├── README.md
    └── skills/
        ├── ohos-cpp-style/
        ├── ohos-hdc/
        └── ohos-permission/
```

## Notes

- This directory keeps only the skills that remain useful in Codex.
- Legacy plugin commands, hooks, and agent definitions are intentionally removed here.
- Each retained skill includes the OpenAI agent manifest so Codex can surface it cleanly.

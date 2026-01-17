```markdown
---
name: remote-openharmony-build
description: Control remote servers exclusively for OpenHarmony image compilation. Use ONLY when building OpenHarmony system images. Requires syncing local code changes to remote before compilation. Supports multiple build servers.
---

# Remote OpenHarmony Image Compilation

## Server Configuration

| Host | Remote HOME | OpenHarmony Source |
|------|-------------|-------------------|
| cp | /kh_data/pengys | /kh_data/pengys |

Add more servers to this table as needed. OpenHarmony source path may differ from HOME.

## Usage Restriction

Remote servers are **ONLY** for OpenHarmony image compilation. Do NOT use for other compilation tasks.

## Parameters

- `<HOST>`: SSH config host name
- `<REMOTE_HOME>`: Remote home directory
- `<OH_SOURCE>`: OpenHarmony source path on remote
- `<product>`: Product name (e.g., rk3568)
- `<target>`: Build target component

## Workflow

### Step 1: Sync Local Changes to Remote

```bash
# Single file
scp <local_path> <HOST>:<OH_SOURCE>/<corresponding_path>

# Directory
scp -r <local_dir> <HOST>:<OH_SOURCE>/<corresponding_path>

# Rsync (recommended for incremental sync)
rsync -avz --progress <local_path> <HOST>:<OH_SOURCE>/<corresponding_path>
```

### Step 2: Compile Image

```bash
ssh <HOST> 'cd <OH_SOURCE> && ./build.sh --product-name <product> --ccache'
```

### Step 3: Retrieve Build Artifacts (Optional)

```bash
scp <HOST>:<OH_SOURCE>/out/<product>/packages/phone/images/<image_file> <local_dest>
```

## Build Commands

Full build:
```bash
ssh <HOST> 'cd <OH_SOURCE> && ./build.sh --product-name <product> --ccache'
```

Build specific component:
```bash
ssh <HOST> 'cd <OH_SOURCE> && ./build.sh --product-name <product> --build-target <target> --ccache'
```

Clean build:
```bash
ssh <HOST> 'cd <OH_SOURCE> && ./build.sh --product-name <product> --ccache --clean'
```

## Utility Commands

Check build output:
```bash
ssh <HOST> 'ls -la <OH_SOURCE>/out/<product>/packages/phone/images/'
```

Monitor build:
```bash
ssh <HOST> 'ps aux | grep build'
```

View build log:
```bash
ssh <HOST> 'tail -f <OH_SOURCE>/out/<product>/build.log'
```

Kill build:
```bash
ssh <HOST> 'pkill -f build.sh'
```

Check disk:
```bash
ssh <HOST> 'df -h <REMOTE_HOME>'
```
```

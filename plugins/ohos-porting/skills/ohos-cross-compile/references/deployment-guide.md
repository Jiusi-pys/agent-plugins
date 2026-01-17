# 部署指南

OpenHarmony 设备部署完整流程（WSL → Windows → 设备）。

## 部署方法概览

| 方法 | 复杂度 | 自动化 | 适用场景 |
|------|--------|--------|---------|
| GN 系统构建 | 低 | 高 | 生产集成 |
| HDC 手动传输 | 中 | 低 | 开发测试 |
| 自动化脚本 | 低 | 高 | 持续集成 |

---

## 方法 1: GN 系统构建（生产）

**源文件**: `rmw_dsoftbus/BUILD.gn`

### 配置

```gni
ohos_shared_library("mylib") {
    # ...
    install_enable = true
    install_images = ["system"]
    module_install_dir = "lib64"
}
```

### 构建和部署

```bash
cd $OHOS_ROOT
./build.sh --product-name rk3588 --build-target //myproject:mylib

# 输出位置
ls $OHOS_ROOT/out/rk3588/packages/phone/system/lib64/libmylib.so
```

### 自动安装

GN 构建会将库打包到系统镜像，刷机时自动安装到 `/system/lib64/`。

---

## 方法 2: HDC 手动传输（开发）

### WSL 环境部署流程

**关键**: WSL 路径对 Windows/HDC 不可见，必须经过 `/mnt/c/` 中转

### 完整步骤

```bash
#!/bin/bash
# deploy_manual.sh

# === 1. 准备 ===
BUILD_DIR="build-aarch64"
STAGING="/mnt/c/tmp/hdc_transfer"

# 创建中转目录
mkdir -p $STAGING
rm -f $STAGING/*

# === 2. 复制文件到 Windows 可见路径 ===
cp $BUILD_DIR/lib/libmylib.so.0.1.0 $STAGING/
cp $BUILD_DIR/bin/myapp $STAGING/

# === 3. 获取设备 ID（多设备环境）===
DEVICE_ID=$(powershell.exe -NoProfile -Command "hdc list targets" | head -1 | awk '{print $1}' | tr -d '\r\n')

if [ -z "$DEVICE_ID" ]; then
    echo "❌ No device connected"
    exit 1
fi

echo "Deploying to device: $DEVICE_ID"

# === 4. 传输库文件 ===
echo "Transferring library..."
powershell.exe -Command "hdc -t $DEVICE_ID file send 'C:\tmp\hdc_transfer\libmylib.so.0.1.0' '/data/lib/'"

# === 5. 传输可执行文件 ===
echo "Transferring executable..."
powershell.exe -Command "hdc -t $DEVICE_ID file send 'C:\tmp\hdc_transfer\myapp' '/data/bin/'"

# === 6. 设置权限 ===
powershell.exe -Command "hdc -t $DEVICE_ID shell 'chmod +x /data/bin/myapp'"

# === 7. 创建符号链接 ===
powershell.exe -Command "hdc -t $DEVICE_ID shell 'cd /data/lib && ln -sf libmylib.so.0.1.0 libmylib.so.0'"
powershell.exe -Command "hdc -t $DEVICE_ID shell 'cd /data/lib && ln -sf libmylib.so.0 libmylib.so'"

# === 8. 验证 ===
echo "=== Verification ==="
powershell.exe -Command "hdc -t $DEVICE_ID shell 'ls -lh /data/lib/libmylib.so*'"
powershell.exe -Command "hdc -t $DEVICE_ID shell 'file /data/bin/myapp'"

echo "✅ Deployment complete"
```

### 路径转换规则

| 来源 | WSL 路径 | Windows 路径 | HDC 参数 |
|------|----------|-------------|----------|
| WSL home | `/home/user/file` | ❌ 不可见 | - |
| WSL → Win | `/mnt/c/tmp/file` | `C:\tmp\file` | ✅ 可用 |
| 设备 | - | - | `/data/file` |

---

## 方法 3: 自动化部署脚本

**源文件**: 项目实战经验

### 高级部署脚本

```bash
#!/bin/bash
# deploy_to_device.sh
set -e

# === 配置 ===
BUILD_DIR="${BUILD_DIR:-build-aarch64}"
STAGING_DIR="/mnt/c/tmp/hdc_transfer"
DEVICE_LIB="${DEVICE_LIB:-/data/lib}"
DEVICE_BIN="${DEVICE_BIN:-/data/bin}"

# === 函数：获取设备 ID ===
get_device_id() {
    local device_id=$(powershell.exe -NoProfile -Command "hdc list targets" | head -1 | awk '{print $1}' | tr -d '\r\n')
    if [ -z "$device_id" ]; then
        echo "❌ No device connected" >&2
        return 1
    fi
    echo "$device_id"
}

# === 函数：传输文件 ===
transfer_file() {
    local local_file="$1"
    local remote_path="$2"
    local device_id="$3"

    local filename=$(basename "$local_file")
    local win_path="C:\\tmp\\hdc_transfer\\$filename"

    echo "Transferring: $filename → $remote_path"

    powershell.exe -Command "hdc -t $device_id file send '$win_path' '$remote_path'"

    if [ $? -ne 0 ]; then
        echo "❌ Transfer failed: $filename" >&2
        return 1
    fi
}

# === 主流程 ===
main() {
    echo "=== OpenHarmony Deployment Script ==="

    # 获取设备 ID
    DEVICE_ID=$(get_device_id)
    echo "Target device: $DEVICE_ID"

    # 准备中转目录
    mkdir -p "$STAGING_DIR"
    rm -f "$STAGING_DIR"/*

    # 复制库文件
    echo "Copying libraries..."
    cp $BUILD_DIR/lib/*.so* "$STAGING_DIR/"

    # 复制可执行文件
    echo "Copying executables..."
    cp $BUILD_DIR/bin/* "$STAGING_DIR/" 2>/dev/null || true

    # 传输库文件
    echo "=== Transferring libraries ==="
    for lib in "$STAGING_DIR"/*.so*; do
        [ -f "$lib" ] || continue
        transfer_file "$lib" "$DEVICE_LIB/" "$DEVICE_ID"
    done

    # 传输可执行文件
    echo "=== Transferring executables ==="
    for exe in "$STAGING_DIR"/*; do
        [ -f "$exe" ] || continue
        [[ "$exe" == *.so* ]] && continue  # 跳过库文件

        transfer_file "$exe" "$DEVICE_BIN/" "$DEVICE_ID"

        # 设置执行权限
        local filename=$(basename "$exe")
        powershell.exe -Command "hdc -t $DEVICE_ID shell 'chmod +x $DEVICE_BIN/$filename'"
    done

    # 创建符号链接
    echo "=== Creating symlinks ==="
    powershell.exe -Command "hdc -t $DEVICE_ID shell 'cd $DEVICE_LIB && for f in *.so.*.*; do [ -f \$f ] && ln -sf \$f \${f%.*} && ln -sf \${f%.*} \${f%.*.*}; done'"

    # 验证
    echo "=== Verification ==="
    powershell.exe -Command "hdc -t $DEVICE_ID shell 'ls -lh $DEVICE_LIB/*.so* $DEVICE_BIN/*' 2>&1 | head -20"

    echo "✅ Deployment complete!"
}

main "$@"
```

### 使用

```bash
# 默认配置
./deploy_to_device.sh

# 自定义配置
BUILD_DIR=build-test DEVICE_LIB=/data/myproject/lib ./deploy_to_device.sh
```

---

## 多设备管理

### 设备 ID 管理

```bash
# 列出所有设备
powershell.exe -Command "hdc list targets -v"

# 输出示例:
# ec290041...  Connected
# aa123456...  Connected

# 设置环境变量
export DEVICE1="ec290041..."
export DEVICE2="aa123456..."

# 部署到不同设备
powershell.exe -Command "hdc -t $DEVICE1 file send 'C:\file' '/data/'"
powershell.exe -Command "hdc -t $DEVICE2 file send 'C:\file' '/data/'"
```

### 批量部署脚本

```bash
#!/bin/bash
# deploy_to_all_devices.sh

# 获取所有设备 ID
DEVICES=($(powershell.exe -Command "hdc list targets" | grep -v Empty | awk '{print $1}' | tr -d '\r\n'))

echo "Found ${#DEVICES[@]} devices"

for device_id in "${DEVICES[@]}"; do
    echo "=== Deploying to $device_id ==="
    DEVICE_ID=$device_id ./deploy_to_device.sh
done

echo "✅ All devices deployed"
```

---

## 验证和测试

### 部署后验证

```bash
# 1. 检查文件存在
powershell.exe -Command "hdc -t $DEVICE_ID shell 'ls -lh /data/lib/libmylib.so*'"

# 2. 检查架构
powershell.exe -Command "hdc -t $DEVICE_ID shell 'file /data/bin/myapp'"
# 期望: ARM aarch64

# 3. 检查依赖
powershell.exe -Command "hdc -t $DEVICE_ID shell 'ldd /data/bin/myapp'"

# 4. 检查权限
powershell.exe -Command "hdc -t $DEVICE_ID shell 'ls -l /data/bin/myapp'"
# 期望: -rwxr-xr-x
```

### 运行测试

```bash
# 基本运行
powershell.exe -Command "hdc -t $DEVICE_ID shell '/data/bin/myapp --version'"

# 带 LD_LIBRARY_PATH
powershell.exe -Command "hdc -t $DEVICE_ID shell 'LD_LIBRARY_PATH=/data/lib /data/bin/myapp'"

# 捕获输出
powershell.exe -Command "hdc -t $DEVICE_ID shell '/data/bin/myapp 2>&1'" > output.log
```

---

## 部署路径选择

| 路径 | 权限要求 | 持久性 | 用途 |
|------|---------|--------|------|
| `/data/` | 普通用户 | 重启保留 | 开发测试（推荐）|
| `/data/myproject/lib/` | 普通用户 | 重启保留 | 隔离部署 |
| `/system/lib64/` | root + remount | 永久 | 生产部署 |
| `/tmp/` | 普通用户 | 重启丢失 | 临时测试 |

**推荐**: 开发阶段使用 `/data/`，生产使用 GN 构建到 `/system/`

---

## 部署清单

**部署前**:
- [ ] 已运行 device_survey.sh（检查库名冲突）
- [ ] 二进制是 aarch64 架构（`file mybinary`）
- [ ] 所有依赖库已准备（`ldd` 或 `readelf -d`）
- [ ] RPATH 配置正确或准备设置 LD_LIBRARY_PATH
- [ ] 如使用动态 libc++，已准备 libc++_shared.so

**部署后**:
- [ ] 文件成功传输（`hdc shell ls`）
- [ ] 可执行权限设置（`chmod +x`）
- [ ] 符号链接创建（`.so.1 -> .so.1.2.3`）
- [ ] 库依赖满足（`ldd` 无 not found）
- [ ] 能成功运行（`hdc shell './myapp'`）

---

## 故障排查

### 问题: 传输失败

**现象**: `Error: file not found` 或 `access denied`

**解决**:
```bash
# 检查 Windows 路径
ls /mnt/c/tmp/hdc_transfer/
# 确保文件存在

# 检查设备连接
powershell.exe -Command "hdc list targets"

# 检查设备空间
powershell.exe -Command "hdc shell 'df -h /data'"
```

### 问题: 权限拒绝

**现象**: `Permission denied` 执行时

**解决**:
```bash
# 设置执行权限
powershell.exe -Command "hdc -t $DEVICE_ID shell 'chmod 755 /data/bin/myapp'"

# 检查 SELinux
powershell.exe -Command "hdc -t $DEVICE_ID shell 'ls -Z /data/bin/myapp'"
```

### 问题: 库找不到

**现象**: `libmylib.so: not found` 运行时

**解决**:
```bash
# 方法 1: 检查 RPATH
readelf -d mybinary | grep RPATH

# 方法 2: 使用 LD_LIBRARY_PATH
powershell.exe -Command "hdc shell 'LD_LIBRARY_PATH=/data/lib /data/bin/myapp'"

# 方法 3: 复制到标准路径
powershell.exe -Command "hdc shell 'cp /data/lib/libmylib.so /system/lib64/'"
```

---

## 参考脚本

详见: `scripts/deploy.sh` (待创建)

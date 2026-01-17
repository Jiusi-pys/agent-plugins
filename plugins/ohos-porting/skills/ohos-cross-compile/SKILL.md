---
name: ohos-cross-compile
description: OpenHarmony (aarch64) cross-compilation toolkit for porting x86_64 software. Use when (1) cross-compiling C/C++ projects for OpenHarmony/KaihongOS, (2) configuring OHOS SDK Clang toolchain, (3) writing BUILD.gn or CMake for OHOS targets, (4) diagnosing aarch64-linux-ohos build errors, (5) managing dynamic library paths and RPATH, (6) surveying target device environment before deployment.
---

# OpenHarmony Cross-Compilation Skill

## 前置要求

**在任何编译之前，必须完成：**

1. 读取并设置 `ohos_toolchain_config.json`
2. 运行 `scripts/device_survey.sh` 调查设备环境
3. 运行 `scripts/check_toolchain.sh` 验证工具链

## 关键工作流

```
1. Device Survey    ← 必须第一步！
   ↓
2. Config Setup     ← 创建 ohos_toolchain_config.json
   ↓
3. Toolchain Verify ← 运行 scripts/check_toolchain.sh
   ↓
4. Build & Deploy
```

### 为什么设备调查是第一步？

跳过会导致：
- ❌ 系统库覆盖 → 设备变砖
- ❌ 同名库冲突 → 系统服务崩溃
- ❌ 依赖不匹配 → 运行时失败

**必须运行**: `scripts/device_survey.sh` 通过 HDC/ADB

---

## 快速开始

### 最快编译路径（GCC Linaro）

```bash
# 设置环境变量
export TOOLCHAIN=/path/to/gcc-linaro-7.5.0/bin/aarch64-linux-gnu-g++

# 编译
$TOOLCHAIN -std=c++17 -O2 -fPIC \
    -static-libstdc++ -static-libgcc \
    mycode.cpp -o mybinary \
    -lpthread -ldl

# 验证
file mybinary  # 应显示: ARM aarch64
```

### GN 构建（OpenHarmony 原生）

```bash
cd $OHOS_ROOT
./build.sh --product-name rk3588 --build-target //your_project:target
```

详见: `references/gn-templates.md`

---

## 工具链选择

| 工具链 | 目标 | C++ 运行时 | 推荐场景 |
|--------|------|-----------|----------|
| **GCC Linaro 7.5.0** | aarch64-linux-gnu | 静态 libstdc++ | 独立开发（推荐）|
| **OHOS SDK Clang 15.0.4** | aarch64-unknown-linux-ohos | 动态 libc++ | OHOS 系统集成 |

### GCC Linaro 快速配置

```bash
export TOOLCHAIN_ROOT=/home/jiusi/M-DDS/openharmony_prebuilts/gcc-linaro-7.5.0
export CXX=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-g++
export AR=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-ar
```

详见: `references/toolchain-setup.md` (待创建)

### OHOS Clang 快速配置

```bash
export OHOS_SDK_ROOT=/path/to/ohos-sdk/linux/11/native
export CXX=$OHOS_SDK_ROOT/llvm/bin/aarch64-unknown-linux-ohos-clang++
```

---

## 关键编译标志

| 标志 | 用途 | 详细说明 |
|------|------|----------|
| `-fvisibility=default` | 导出符号（dlopen）| `references/compilation-flags.md` |
| `-static-libstdc++` | 静态 C++ 运行时 | `references/linking-strategies.md` |
| `-Wl,-rpath,/data` | 运行时库路径 | `references/linking-strategies.md` |
| `-fuse-ld=lld` | 使用 LLVM 链接器 | `references/toolchain-setup.md` |

---

## WSL/HDC 部署

### 快速部署模板

```bash
# 1. 复制到 Windows 可见路径
mkdir -p /mnt/c/tmp/hdc_transfer
cp build/libmylib.so /mnt/c/tmp/hdc_transfer/

# 2. 获取设备 ID
DEVICE_ID=$(powershell.exe -Command "hdc list targets" | head -1 | awk '{print $1}' | tr -d '\r\n')

# 3. 传输
powershell.exe -Command "hdc -t $DEVICE_ID file send 'C:\tmp\hdc_transfer\libmylib.so' '/data/lib/'"

# 4. 执行
powershell.exe -Command "hdc -t $DEVICE_ID shell 'LD_LIBRARY_PATH=/data/lib /data/bin/myapp'"
```

完整流程: `references/deployment-guide.md` (待创建)

---

## 详细文档索引

### 构建系统
- **GN 模板**: `references/gn-templates.md` (已有)
- **CMake 模板**: `references/cmake-templates.md` (已有)
- **Makefile 模板**: `asserts/Makefile.template` (已有)

### 编译配置
- **工具链设置**: `references/toolchain-setup.md` (待创建)
- **编译标志详解**: `references/compilation-flags.md` (待创建)
- **链接策略**: `references/linking-strategies.md` (待创建)

### 部署和测试
- **部署指南**: `references/deployment-guide.md` (待创建)
- **验证方法**: `references/verification.md` (待创建)
- **故障排查**: `references/troubleshooting.md` (已补充)

---

## 何时查阅详细文档

| 场景 | 查阅文档 |
|------|----------|
| 设置工具链环境 | `references/toolchain-setup.md` |
| 编写 BUILD.gn | `references/gn-templates.md` |
| 编写 Makefile | `asserts/Makefile.template` |
| 配置链接选项 | `references/linking-strategies.md` |
| 部署到设备 | `references/deployment-guide.md` |
| 调试编译错误 | `references/troubleshooting.md` |
| 理解编译标志 | `references/compilation-flags.md` |

---

## 常见问题快速解答

### Q: 使用哪个工具链？

**A**: 默认使用 **GCC Linaro 7.5.0**（静态 C++ 运行时，无部署依赖）

切换到 OHOS Clang 的场景：
- OHOS 系统集成（GN 构建）
- 需要 C++20 特性
- 需要 LLVM 优化

### Q: 为什么需要 -fvisibility=default？

**A**: dlopen/dlsym 需要导出符号

```cpp
// 无此标志 → dlsym 返回 NULL
void* sym = dlsym(handle, "func");  // NULL!

// 有此标志 → dlsym 成功
void* sym = dlsym(handle, "func");  // ✓
```

详见: `references/compilation-flags.md`

### Q: 如何部署到多个设备？

**A**: 使用设备 ID 明确指定

```bash
DEVICE_ID=$(powershell.exe -Command "hdc list targets" | head -1)
powershell.exe -Command "hdc -t $DEVICE_ID file send ..."
```

详见: `references/deployment-guide.md`

---

## 验证清单

部署前检查：

- [ ] Binary 是 aarch64 ELF (`file myapp`)
- [ ] 无系统库名称冲突（已运行 device_survey.sh）
- [ ] RPATH 配置正确（或准备设置 LD_LIBRARY_PATH）
- [ ] 如使用动态 libc++，已部署 libc++_shared.so
- [ ] 文件权限设置（chmod +x）

详细清单: `references/deployment-guide.md`

---

## Scripts 工具

| 脚本 | 用途 |
|------|------|
| `scripts/check_toolchain.sh` | 验证工具链完整性 |
| `scripts/device_survey.sh` | 调查设备环境（防止冲突）|
| `scripts/deploy.sh` | 自动化部署到设备 |

---

## 模板文件

| 文件 | 用途 |
|------|------|
| `asserts/BUILD.gn.template` | GN 构建文件模板 |
| `asserts/Makefile.template` | Makefile 模板 |
| `asserts/ohos-aarch64.cmake` | CMake 工具链文件 |
| `asserts/ohos.build.template` | OHOS 组件注册模板 |

---

## 相关文档

### Skill 内部
- `ohos_toolchain_config.json` - 工具链路径配置
- `references/` - 详细技术参考（7 个文档）
- `asserts/` - 模板文件（4 个模板）
- `scripts/` - 实用脚本（3 个脚本）

### 项目文档
- `docs/00_核心技术文档/OHOS_GN_BUILD_GUIDE.md` - GN 构建深入指南
- `docs/00_核心技术文档/OPENHARMONY_PORTING_GUIDE.md` - 移植方法论
- `rmw_dsoftbus/BUILD.gn` - 生产 GN 配置参考

---

**版本**: v2.0 (2026-01-15)
**更新**: 新增多工具链支持、WSL/HDC 部署流程、详细编译标志说明

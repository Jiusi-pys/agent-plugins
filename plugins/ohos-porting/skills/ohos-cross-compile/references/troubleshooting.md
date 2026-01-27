# OpenHarmony Cross-Compilation Troubleshooting

## Compilation Errors

### E001: Header not found

**Symptom:**
```
fatal error: 'stdio.h' file not found
fatal error: 'bits/libc-header-start.h' file not found
```

**Cause:** Sysroot not configured or incorrect.

**Fix:**
```bash
# Verify sysroot exists
ls $OHOS_SDK_ROOT/sysroot/usr/include/stdio.h

# Use wrapper script (auto-configures sysroot)
$OHOS_SDK_ROOT/llvm/bin/aarch64-unknown-linux-ohos-clang++

# Or manually specify
clang++ --sysroot=$OHOS_SDK_ROOT/sysroot --target=aarch64-linux-ohos
```

---

### E002: CRT objects not found

**Symptom:**
```
ld.lld: error: cannot open crti.o: No such file or directory
ld.lld: error: cannot open Scrt1.o: No such file or directory
```

**Cause:** Linker cannot find C runtime startup objects.

**Fix:**
```bash
# Verify CRT objects exist
ls $OHOS_SDK_ROOT/sysroot/usr/lib/aarch64-linux-ohos/*.o

# Expected files: Scrt1.o, crt1.o, crti.o, crtn.o

# If missing, SDK is incomplete - re-download
```

---

### E003: Cannot find -lc

**Symptom:**
```
ld.lld: error: unable to find library -lc
ld.lld: error: unable to find library -lm
```

**Cause:** Sysroot not passed to linker.

**Fix:**
```bash
# Ensure --sysroot is set
clang++ --sysroot=$OHOS_SDK_ROOT/sysroot ...

# Or use wrapper script which includes this
aarch64-unknown-linux-ohos-clang++ ...
```

---

### E004: Undefined reference (link time)

**Symptom:**
```
undefined reference to `some_function'
```

**Cause:** Missing library in link command.

**Diagnose:**
```bash
# Find which library provides the symbol
nm -D /path/to/libs/*.so | grep some_function
```

**Fix:**
```bash
# Add library to link command
clang++ ... -lmissing_lib

# Or in CMake
target_link_libraries(myapp PRIVATE missing_lib)

# Or in GN
deps = [ "//path/to:missing_lib" ]
```

---

### E005: Multiple definition

**Symptom:**
```
multiple definition of `global_var'
```

**Cause:** Global variable defined in header (not declared).

**Fix:**
```cpp
// WRONG - header.h
int global_var = 0;  // Definition in header

// CORRECT - header.h
extern int global_var;  // Declaration only

// source.cpp
int global_var = 0;  // Definition in one source file
```

---

### E006: Target triple mismatch

**Symptom:**
```
error: unknown target triple 'aarch64-linux-ohos'
```

**Cause:** Non-OHOS Clang being used.

**Fix:**
```bash
# Use OHOS SDK Clang, not system Clang
which clang++
# Should be: $OHOS_SDK_ROOT/llvm/bin/clang++

# Verify OHOS build
$OHOS_SDK_ROOT/llvm/bin/clang --version
# Should contain: OHOS
```

---

## Runtime Errors

### R001: Shared library not found

**Symptom:**
```
Error loading shared library libxxx.so: No such file or directory
```

**Diagnose:**
```bash
# Check what libraries are needed
llvm-readelf -d myapp | grep NEEDED

# Check RPATH
llvm-readelf -d myapp | grep -E "(RPATH|RUNPATH)"

# On device, check if library exists
ls /system/lib64/libxxx.so
ls /data/libxxx.so
```

**Fix:**

Option A: Set RPATH at build time
```bash
clang++ -Wl,-rpath,/data -Wl,-rpath,/system/lib64 ...
```

Option B: Set LD_LIBRARY_PATH at runtime
```bash
export LD_LIBRARY_PATH=/data:/system/lib64
./myapp
```

Option C: Copy library to searched path
```bash
hdc file send libxxx.so /system/lib64/
# or
hdc file send libxxx.so /data/
```

---

### R002: Symbol not found (runtime)

**Symptom:**
```
Error relocating ./myapp: some_function: symbol not found
```

**Cause:** Library version mismatch or ABI incompatibility.

**Diagnose:**
```bash
# Check if symbol exists in library
llvm-nm -D libxxx.so | grep some_function

# Check library version
llvm-readelf -V libxxx.so
```

**Fix:**
- Rebuild all dependencies with same toolchain
- Ensure libraries are not mixed from different SDK versions

---

### R003: dlopen fails

**Symptom:**
```cpp
void* h = dlopen("libplugin.so", RTLD_LAZY);
// h is NULL, dlerror() returns "library not found"
```

**Cause:** RPATH does not affect dlopen().

**Fix:**
```cpp
// Option 1: Use full path
dlopen("/data/myproject/lib/libplugin.so", RTLD_LAZY);

// Option 2: Set LD_LIBRARY_PATH
setenv("LD_LIBRARY_PATH", "/data/myproject/lib", 1);
dlopen("libplugin.so", RTLD_LAZY);
```

---

### R004: Segmentation fault on startup

**Cause:** Usually libc or C++ runtime mismatch.

**Diagnose:**
```bash
# Check dependencies
llvm-readelf -d myapp | grep NEEDED

# Verify runtime exists on device
hdc shell ls -la /system/lib64/libc.so
hdc shell ls -la /system/lib64/libc++*.so
```

**Fix:**
- Deploy libc++_shared.so to device
- Ensure musl libc version matches

---

### R005: SIGILL (Illegal instruction)

**Cause:** Binary compiled for wrong architecture or CPU features.

**Diagnose:**
```bash
file myapp
# Should show: ARM aarch64

# Check for unsupported instructions
objdump -d myapp | grep -E "(illegal|undefined)"
```

**Fix:**
```bash
# Use conservative architecture flags
clang++ -march=armv8-a ...

# Avoid newer instruction sets unless device supports them
```

---

## Device Deployment Issues

### D001: Permission denied

**Symptom:**
```
hdc shell ./myapp
./myapp: Permission denied
```

**Fix:**
```bash
# Make executable
hdc shell chmod +x /data/myapp

# Or on host before transfer
chmod +x myapp
hdc file send myapp /data/
```

---

### D002: Cannot write to /system

**Symptom:**
```
hdc file send libxxx.so /system/lib64/
error: read-only file system
```

**Fix:**
```bash
# Remount system partition
hdc shell mount -o remount,rw /system

# After copying
hdc shell mount -o remount,ro /system
```

**Warning:** Modifying /system may brick device. Use /data for development.

---

### D003: Library overwrites system lib

**Prevention:**
```bash
# BEFORE deploying, check for conflicts
hdc shell ls /system/lib64/libmylib.so

# Use unique names
libmyproject_utils.so  # Instead of libutils.so
```

**Recovery if system damaged:**
- Factory reset or reflash firmware
- Boot into recovery mode if available

---

## Diagnostic Commands

### Check binary architecture
```bash
file myapp
# Expected: ELF 64-bit LSB executable, ARM aarch64
```

### List dependencies
```bash
llvm-readelf -d myapp | grep NEEDED
```

### Check RPATH
```bash
llvm-readelf -d myapp | grep -E "(RPATH|RUNPATH)"
```

### List exported symbols
```bash
llvm-nm -D libmylib.so | grep " T "
```

### Check for undefined symbols
```bash
llvm-nm -u libmylib.so
```

### Verify library compatibility
```bash
# Check required glibc/musl version
llvm-readelf -V myapp
```

### Debug loading issues (on device)
```bash
LD_DEBUG=libs ./myapp 2>&1 | head -50
```

---

## WSL/HDC 特定问题

### W001: HDC 命令在 WSL 中找不到

**现象**:
```bash
bash: hdc: command not found
```

**原因**: HDC 安装在 Windows 上，WSL 中不可见

**解决**:
```bash
# 通过 PowerShell 调用
powershell.exe -NoProfile -Command "hdc list targets"

# 执行 shell 命令
DEVICE_ID="ec290041..."
powershell.exe -Command "hdc -t $DEVICE_ID shell 'ls /data'"
```

### W002: 文件传输失败

**现象**:
```
Error: C:\path\to\file not accessible
```

**原因**: WSL 路径对 Windows/HDC 不可见

**解决**（三步骤）:
```bash
# 1. 复制到 Windows 可见路径
mkdir -p /mnt/c/tmp/hdc_transfer
cp /home/user/libmylib.so /mnt/c/tmp/hdc_transfer/

# 2. 使用 Windows 路径传输
powershell.exe -Command "hdc file send 'C:\tmp\hdc_transfer\libmylib.so' '/data/lib/'"

# 3. 清理
rm /mnt/c/tmp/hdc_transfer/libmylib.so
```

### W003: 多设备时传输失败

**现象**:
```
[Fail]HdcServer CreateConnect
```

**原因**: 多个设备连接，HDC 需要明确指定设备 ID

**解决**:
```bash
# 获取设备 ID
DEVICE_ID=$(powershell.exe -Command "hdc list targets" | head -1 | awk '{print $1}' | tr -d '\r\n')

# 所有命令都使用 -t 指定设备
powershell.exe -Command "hdc -t $DEVICE_ID file send 'C:\file' '/data/'"
powershell.exe -Command "hdc -t $DEVICE_ID shell 'ls /data'"
```

---

## 符号可见性问题

### S001: dlsym 返回 NULL

**现象**:
```cpp
void* sym = dlsym(handle, "my_function");
// sym is NULL, dlerror() returns "undefined symbol"
```

**原因**: 库编译时使用了 `-fvisibility=hidden`

**诊断**:
```bash
# 检查符号是否导出
nm -D libmylib.so | grep my_function

# 检查符号可见性
readelf -s libmylib.so | grep my_function
# 应显示: GLOBAL DEFAULT
```

**解决**:
```gni
# BUILD.gn
cflags_cc = ["-fvisibility=default"]  # 导出所有符号

# 或在函数上使用属性
__attribute__((visibility("default")))
int my_function() { ... }
```

### S002: C++ 名称修饰问题

**现象**:
```cpp
dlsym(handle, "MyClass::method")  // 返回 NULL
```

**原因**: C++ 名称修饰（name mangling）

**解决**:

```cpp
// 方法 1: 使用 extern "C"
extern "C" {
    int my_c_compatible_function() { ... }
}

// 方法 2: 查找修饰后的名称
nm -D libmylib.so | grep method
// 输出: _ZN7MyClass6methodEv

void* sym = dlsym(handle, "_ZN7MyClass6methodEv");
```

---

## 静态链接问题

### T001: 静态链接失败

**现象**:
```
ld.lld: error: unable to find library -lstdc++_static
```

**原因**: OHOS SDK 可能不提供静态 C++ 库

**解决**:
```bash
# 使用 GCC Linaro（支持静态链接）
TOOLCHAIN=/path/to/gcc-linaro-7.5.0
$TOOLCHAIN/bin/aarch64-linux-gnu-g++ \
    -static-libstdc++ -static-libgcc \
    mycode.cpp -o myapp
```

### T002: 静态二进制过大

**现象**: 二进制 >10 MB

**优化**:
```bash
# 1. 使用 -Os 优化大小
CXXFLAGS += -Os

# 2. 移除未使用代码
LDFLAGS += -Wl,--gc-sections
CXXFLAGS += -ffunction-sections -fdata-sections

# 3. Strip 调试符号
aarch64-linux-gnu-strip --strip-all myapp

# 4. 检查结果
ls -lh myapp
```

---

## GN 构建问题

### G001: part_name 未定义

**现象**:
```
ERROR at //myproject/BUILD.gn:10:3: Assignment had no effect.
  part_name = "mypart"
```

**原因**: 缺少 subsystem_name 或 GN 模板不支持

**解决**:
```gni
ohos_shared_library("mylib") {
    part_name = "mypart"              # 必需
    subsystem_name = "mysubsystem"    # 必需
    # ...
}
```

### G002: external_deps 找不到

**现象**:
```
ERROR: Unable to resolve dependency "hilog:libhilog"
```

**原因**: 组件未在 OHOS 系统中注册

**解决**:
```bash
# 检查组件是否存在
ls $OHOS_ROOT/out/rk3588/obj/utils/hilog/

# 确认 external_deps 格式正确
external_deps = ["hilog:libhilog"]  # ✓ 正确格式
external_deps = ["hilog"]            # ✗ 错误格式
```

---

## 权限和安全问题

### P001: SELinux 阻止执行

**现象**:
```bash
hdc shell /data/myapp
Permission denied
```

**诊断**:
```bash
# 检查 SELinux 上下文
hdc shell ls -Z /data/myapp
# 如果显示: u:object_r:unlabeled:s0 → 问题

# 检查 dmesg 中的 AVC denials
hdc shell dmesg | grep avc | tail -20
```

**解决**:
```bash
# 选项 1: 通过 init service 启动（推荐）
# 在 /system/etc/init/myapp.cfg 中配置

# 选项 2: Temporarily set permissive mode (测试用)
hdc shell setenforce 0
```

### P002: dsoftbus 权限被拒绝

**现象**: CreateSessionServer 返回 -1，errno=13

**诊断流程**: 见 `permission-config.md` 中的三层诊断

**快速检查**:
```bash
# Layer 1: Transport permission
hdc shell cat /system/etc/communication/softbus/softbus_trans_permission.json

# Layer 2: Native token
hdc shell ls /system/etc/token_sync/

# Layer 3: Process context
hdc shell ps -o label | grep myapp
# 不应显示 u:r:su:s0 或 u:r:shell:s0
```

---

## 性能问题

### F001: 二进制运行缓慢

**诊断**:
```bash
# 检查优化级别
readelf -p .comment myapp | grep -E "(O0|O1|O2|O3)"
```

**优化**:
```makefile
# 使用 -O2 或 -O3
CXXFLAGS += -O2

# 启用 LTO（链接时优化）
CXXFLAGS += -flto
LDFLAGS += -flto

# 特定架构优化
CXXFLAGS += -march=armv8-a -mtune=cortex-a76
```

---

## Checklist for Deployment

- [ ] Binary is aarch64 ELF (`file myapp`)
- [ ] All NEEDED libraries available on device
- [ ] RPATH points to library locations
- [ ] libc++_shared.so deployed (if dynamically linked)
- [ ] No name conflicts with system libraries
- [ ] File permissions set (chmod +x)
- [ ] Device environment surveyed first
- [ ] SELinux context correct (not su:s0 or shell:s0)
- [ ] All three permission layers configured (if using dsoftbus)
- [ ] Tested with LD_LIBRARY_PATH if RPATH not working

---

## ABI 兼容性问题

### 问题根源

musl ABI 不兼容通常发生在以下情况：

1. **混用不同的 C++ 标准库**（libc++ vs libstdc++）
2. **混用不同版本的 sysroot**（SDK sysroot vs OpenHarmony 源码 sysroot）
3. **工具链和库文件来源不一致**

### C1: musl libc 版本不匹配

**现象**:
```
error: version `GLIBC_2.38' not found (required by ./myapp)
```

**诊断**:
```bash
# 查看二进制所需的 libc 版本
readelf -V myapp | grep libc

# 检查设备上的 libc 版本
hdc shell /system/lib64/libc.so
```

**根本原因**:
- 编译时使用的 sysroot 中 libc 版本 > 设备上 libc 版本
- OHOS 设备使用 musl libc，glibc 特定版本号不适用

### C2: libc++ 与 libstdc++ 混用

**现象**:
```
undefined reference to `std::__cxx11::basic_string<...>'
Error relocating ./myapp: undefined symbol in std::
```

**诊断**:
```bash
# 检查二进制依赖的 C++ 库
readelf -d myapp | grep NEEDED | grep -E "(libc\+\+|libstdc)"

# 检查库链接的 C++ 库
ldd ./myapp | grep -E "(libc\+\+|libstdc)"
```

**解决方案**:

```bash
# 方案 1: 使用 SDK 的 libc++（推荐）
SDK_ROOT=$(find ~ -type d -path "*command-line-tools/sdk/*/openharmony/native" 2>/dev/null | head -1)
if [ -z "$SDK_ROOT" ]; then
  echo "未找到 SDK，请检查安装位置"
  # 备选查找位置
  SDK_ROOT=$(find /opt -type d -name "openharmony" 2>/dev/null | head -1)
fi

export LLVM_ROOT="$SDK_ROOT/llvm"
export SYSROOT="$SDK_ROOT/sysroot"

# 编译时指定
clang++ -stdlib=libc++ \
    -I$LLVM_ROOT/include/libcxx-ohos/include/c++/v1 \
    -L$LLVM_ROOT/lib/aarch64-linux-ohos \
    -lc++ -lc++abi mycode.cpp -o myapp

# 方案 2: 使用 GCC Linaro 的 libstdc++（静态链接）
TOOLCHAIN_ROOT=$(find ~ -type d -path "*gcc-linaro*" 2>/dev/null | head -1)
if [ -z "$TOOLCHAIN_ROOT" ]; then
  TOOLCHAIN_ROOT=$(find /opt -type d -name "gcc-linaro*" 2>/dev/null | head -1)
fi

$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-g++ \
    -static-libstdc++ -static-libgcc \
    mycode.cpp -o myapp
```

### C3: 完整 SDK 一致性检查清单

编译成功的关键是**所有工具和库都来自同一个 SDK**：

```bash
# 1. 找到 SDK 根目录
SDK_ROOT=$(find ~ -type d -path "*command-line-tools/sdk/*/openharmony/native" 2>/dev/null | head -1)
echo "SDK_ROOT: $SDK_ROOT"

# 2. 验证编译器
LLVM_BIN="$SDK_ROOT/llvm/bin/clang++"
ls -la "$LLVM_BIN" || echo "❌ clang++ 未找到"

# 3. 验证 sysroot
SYSROOT="$SDK_ROOT/sysroot"
ls -la "$SYSROOT/usr/include/stdio.h" || echo "❌ sysroot 不完整"

# 4. 验证 C++ 头文件
LIBCXX_INCLUDE="$SDK_ROOT/llvm/include/libcxx-ohos/include/c++/v1"
ls -la "$LIBCXX_INCLUDE/__vector" || echo "❌ libc++ 头文件缺失"

# 5. 验证 C++ 运行时库
LIBCXX_LIB="$SDK_ROOT/llvm/lib/aarch64-linux-ohos"
ls -la "$LIBCXX_LIB/libc++.a" || echo "❌ libc++ 库缺失"
ls -la "$LIBCXX_LIB/libc++_shared.so" || echo "❌ libc++_shared.so 缺失"

# 6. 验证系统库
SYSROOT_LIB="$SYSROOT/usr/lib/aarch64-linux-ohos"
ls -la "$SYSROOT_LIB/libc.so" || echo "❌ musl libc 缺失"
```

### C4: BUILD.gn 中的关键配置

```gni
# 从单一 SDK 的所有组件
_sdk_root = exec_script("find_sdk_root.py", [], "string")
_llvm_root = "$_sdk_root/llvm"
_sysroot = "$_sdk_root/sysroot"

# 编译时指定 target triple 和 sysroot
_common_flags = "--target=aarch64-linux-ohos --sysroot=$_sysroot"

# C++ 头文件使用 SDK 中的 libc++
_common_cflags = "$_common_flags -I$_llvm_root/include/libcxx-ohos/include/c++/v1"

# 链接时使用 SDK 中的 libc++ 和 libc++abi
_common_ldflags = "$_common_flags -L$_llvm_root/lib/aarch64-linux-ohos -lc++ -lc++abi"

shared_library("mylib") {
    cflags_cc = _common_cflags
    ldflags = _common_ldflags
}
```

配套的 `find_sdk_root.py`:
```python
#!/usr/bin/env python3
import os
import glob

# 搜索 SDK 根目录
patterns = [
    os.path.expanduser("~/command-line-tools/sdk/*/openharmony/native"),
    "/opt/openharmony/sdk/native",
    os.getenv("OHOS_SDK_ROOT", "")
]

for pattern in patterns:
    if pattern:
        matches = glob.glob(pattern)
        if matches:
            print(matches[0])
            exit(0)

exit(1)
```

### C5: 编译产物的依赖链验证

```bash
# 验证编译产物使用了正确的库
readelf -d myapp | grep NEEDED

# 预期输出：
#   NEEDED: libc++_shared.so    # SDK 的 C++ 运行时
#   NEEDED: libc.so             # musl libc
#   NOT: libstdc++.so           # ✓ 确保没有混用 libstdc++
```

### C6: 常见错误配置 vs 正确配置

| 配置项 | ❌ 错误（导致 ABI 不兼容） | ✓ 正确 |
|--------|-------------------------|--------|
| **sysroot** | OpenHarmony 源码树的 sysroot | SDK 的 sysroot |
| **编译器路径** | 系统 clang 或不同版本 | SDK 的 clang |
| **C++ 库** | libstdc++ 或混用 | SDK 的 libc++ |
| **编译器 target** | aarch64-linux-gnu | aarch64-linux-ohos 或 aarch64-unknown-linux-ohos |
| **库搜索路径** | 混用多个 SDK 的路径 | 仅一个 SDK 的路径 |

### C7: 为什么之前遇到问题

**错误的配置示例**:

```bash
# ❌ 错误 1: 使用 OpenHarmony 源码树的工具链（目标架构不匹配）
/path/to/M-DDS/OpenHarmony/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang

# ❌ 错误 2: 混用不同的 sysroot
--sysroot=/path/to/OpenHarmony/prebuilts/ohos-sdk/linux/11/native/sysroot
# 与
--sysroot=/path/to/command-line-tools/sdk/default/openharmony/native/sysroot

# ❌ 错误 3: 使用静态 C++ 库可能导致符号冲突
-lc++_static  # 可能与系统库冲突
```

### C8: 正确的环境配置脚本

```bash
#!/bin/bash
# setup_ohos_env.sh - 自动定位 SDK 并配置编译环境

# 1. 自动查找 SDK 根目录
find_sdk_root() {
    local patterns=(
        "$HOME/command-line-tools/sdk/*/openharmony/native"
        "/opt/openharmony/sdk/native"
        "$OHOS_SDK_ROOT"
    )

    for pattern in "${patterns[@]}"; do
        for match in $pattern; do
            if [ -d "$match/llvm/bin" ] && [ -d "$match/sysroot" ]; then
                echo "$match"
                return 0
            fi
        done
    done

    echo "❌ 无法找到 OpenHarmony SDK" >&2
    return 1
}

# 2. 获取 SDK 路径
SDK_ROOT=$(find_sdk_root) || exit 1
echo "✓ SDK 路径: $SDK_ROOT"

# 3. 设置编译环境变量
export OHOS_SDK_ROOT="$SDK_ROOT"
export LLVM_ROOT="$SDK_ROOT/llvm"
export SYSROOT="$SDK_ROOT/sysroot"
export CC="$LLVM_ROOT/bin/clang"
export CXX="$LLVM_ROOT/bin/clang++"
export AR="$LLVM_ROOT/bin/llvm-ar"

# 4. 编译标志
export CXXFLAGS="--target=aarch64-linux-ohos --sysroot=$SYSROOT -stdlib=libc++ -O2"
export LDFLAGS="-L$LLVM_ROOT/lib/aarch64-linux-ohos -lc++ -lc++abi"

echo "✓ 编译环境已配置"
echo "  CC: $CC"
echo "  CXX: $CXX"
echo "  SYSROOT: $SYSROOT"
```

### C9: 快速诊断脚本

```bash
#!/bin/bash
# diagnose_abi.sh - ABI 兼容性诊断

binary="$1"

echo "=== ABI 兼容性诊断 ==="
echo ""

# 1. 检查架构
echo "1. 架构检查:"
file "$binary" | grep -q "aarch64" && echo "   ✓ 正确架构 (aarch64)" || echo "   ❌ 错误架构"

# 2. 检查依赖库
echo ""
echo "2. 依赖库检查:"
readelf -d "$binary" | grep NEEDED

# 3. 检查是否混用了 libstdc++
echo ""
echo "3. C++ 库混用检查:"
if readelf -d "$binary" | grep -q "libstdc++"; then
    echo "   ⚠ 警告: 检测到 libstdc++ 依赖（可能与 libc++ 冲突）"
else
    echo "   ✓ 无 libstdc++ 混用"
fi

# 4. 检查符号要求
echo ""
echo "4. libc 版本要求:"
readelf -V "$binary" 2>/dev/null || echo "   (无版本符号表)"
```

---

## 参考文档

- `rmw_dsoftbus/BUILD.gn` - GN 构建配置示例
- `docs/02_dsoftbus诊断体系/dsoftbus权限问题快速修复指南.md` - 权限诊断
- `docs/00_核心技术文档/OHOS_GN_BUILD_GUIDE.md` - GN 构建详解

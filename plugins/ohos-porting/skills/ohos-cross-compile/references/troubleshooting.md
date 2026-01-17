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

## 参考文档

- `rmw_dsoftbus/BUILD.gn` - GN 构建配置示例
- `docs/02_dsoftbus诊断体系/dsoftbus权限问题快速修复指南.md` - 权限诊断
- `docs/00_核心技术文档/OHOS_GN_BUILD_GUIDE.md` - GN 构建详解

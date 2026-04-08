# 工具链设置详解

## GCC Linaro 7.5.0 配置

**源文件**: `rmw_dsoftbus/Makefile.aarch64`, `rmw_dsoftbus/cross_compile_phase3.sh`

### 完整环境设置

```bash
# 工具链根目录
export TOOLCHAIN_ROOT=/home/jiusi/M-DDS/openharmony_prebuilts/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu

# 编译器
export CC=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-gcc
export CXX=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-g++
export AR=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-ar
export RANLIB=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-ranlib
export STRIP=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-strip
export NM=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-nm
export OBJDUMP=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-objdump
export READELF=$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-readelf

# 目标架构
export TARGET=aarch64-linux-gnu

# Sysroot
export SYSROOT=$TOOLCHAIN_ROOT/aarch64-linux-gnu/libc

# 编译标志
export CFLAGS="--sysroot=$SYSROOT"
export CXXFLAGS="--sysroot=$SYSROOT -std=c++17"
export LDFLAGS="--sysroot=$SYSROOT"

# 添加到 PATH
export PATH=$TOOLCHAIN_ROOT/bin:$PATH
```

### 验证安装

```bash
# 检查工具链版本
$CXX --version
# 输出: aarch64-linux-gnu-g++ (Linaro GCC 7.5.0-2019.12) 7.5.0

# 检查目标架构
$CXX -dumpmachine
# 输出: aarch64-linux-gnu

# 检查 sysroot
ls $SYSROOT/usr/include/stdio.h
# 应存在
```

### 优势和限制

**优势**:
- 静态 C++ 运行时支持（-static-libstdc++）
- 成熟稳定（GCC 7.5.0）
- 与 musl libc 兼容
- 无需部署 libstdc++.so

**限制**:
- C++17 only（部分 C++20 不支持）
- 需使用 `<string.h>` 而非 `<cstring>`
- 二进制较大（+2MB for static runtime）

---

## OHOS SDK Clang 15.0.4 配置

### 完整环境设置

```bash
# SDK 根目录
export OHOS_SDK_ROOT=/home/jiusi/M-DDS/OpenHarmony/prebuilts/ohos-sdk/linux/11/native

# 编译器（使用包装脚本）
export CC=$OHOS_SDK_ROOT/llvm/bin/aarch64-unknown-linux-ohos-clang
export CXX=$OHOS_SDK_ROOT/llvm/bin/aarch64-unknown-linux-ohos-clang++
export AR=$OHOS_SDK_ROOT/llvm/bin/llvm-ar
export RANLIB=$OHOS_SDK_ROOT/llvm/bin/llvm-ranlib
export STRIP=$OHOS_SDK_ROOT/llvm/bin/llvm-strip
export NM=$OHOS_SDK_ROOT/llvm/bin/llvm-nm
export OBJDUMP=$OHOS_SDK_ROOT/llvm/bin/llvm-objdump
export READELF=$OHOS_SDK_ROOT/llvm/bin/llvm-readelf

# 目标架构
export TARGET=aarch64-unknown-linux-ohos

# Sysroot
export SYSROOT=$OHOS_SDK_ROOT/sysroot

# 编译标志
export CFLAGS="--sysroot=$SYSROOT -D__MUSL__"
export CXXFLAGS="--sysroot=$SYSROOT -D__MUSL__ -std=c++17 -stdlib=libc++"
export LDFLAGS="--sysroot=$SYSROOT -fuse-ld=lld -lc++ -lc++abi"

# 添加到 PATH
export PATH=$OHOS_SDK_ROOT/llvm/bin:$PATH
```

### libc++ 运行时部署

```bash
# libc++ 共享库位置
LIBCXX_SHARED=$OHOS_SDK_ROOT/llvm/lib/aarch64-linux-ohos/libc++_shared.so

# 部署到设备
powershell.exe -Command "hdc file send '$LIBCXX_SHARED' '/system/lib64/'"
```

### 优势和限制

**优势**:
- 官方 OpenHarmony 工具链
- 现代 Clang 15.0.4（C++17/20 支持好）
- LLVM 优化（lld 链接器更快）
- 完整 musl sysroot

**限制**:
- 需要部署 libc++_shared.so (1.3 MB)
- 二进制依赖动态 libc++

---

## 工具链比较

| 特性 | GCC Linaro | OHOS Clang |
|------|-----------|-----------|
| C++ 版本 | C++17 | C++17/20 |
| 运行时 | libstdc++ (静态) | libc++ (动态) |
| 链接器 | GNU ld | LLVM lld |
| 二进制大小 | 较大 (+2MB) | 较小 |
| 部署复杂度 | 简单 | 需部署 libc++_shared.so |
| 编译速度 | 中等 | 快（lld） |
| 优化质量 | 好 | 更好 (LLVM) |

**推荐**:
- 独立开发 → GCC Linaro
- OHOS 集成 → OHOS Clang

---

## 参考源文件

- `rmw_dsoftbus/Makefile.aarch64` - GCC Linaro 配置
- `rmw_dsoftbus/Makefile.ohos` - OHOS Clang 配置
- `rmw_dsoftbus/cross_compile_phase3.sh` - 编译脚本示例

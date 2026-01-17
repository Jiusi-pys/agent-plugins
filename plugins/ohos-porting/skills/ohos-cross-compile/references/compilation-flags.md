# 编译标志详解

从 rmw_dsoftbus 生产配置中提取的编译标志详细说明。

## 关键标志速查

| 标志 | 用途 | 何时必需 |
|------|------|---------|
| `-fvisibility=default` | 导出符号 | dlopen 模式 |
| `-static-libstdc++` | 静态 C++ 运行时 | GCC Linaro（推荐）|
| `-Wl,-rpath,/data` | 嵌入库路径 | 动态链接 |
| `-fPIC` | 位置无关代码 | 共享库 |
| `-fuse-ld=lld` | LLVM 链接器 | OHOS Clang |

---

## -fvisibility=default

**源文件**: `rmw_dsoftbus/BUILD.gn:35`, `rmw_dsoftbus/test/phase2_udp_discovery_test.cpp`

### 作用

导出所有 C++ 符号，使其可被 dlopen/dlsym 查找。

### 何时使用

1. **库需要被 dlopen 加载**:
```cpp
void* handle = dlopen("libmylib.so", RTLD_NOW);
void* sym = dlsym(handle, "my_function");  // 需要 -fvisibility=default
```

2. **测试可执行文件**（可能被动态加载）

3. **GN 构建中有 external_deps**

### 对比

```bash
# 无此标志（默认 hidden）
$CXX -fvisibility=hidden mylib.cpp -shared -o libmylib.so
nm -D libmylib.so | grep my_function
# (无输出 - 符号未导出)

# 有此标志
$CXX -fvisibility=default mylib.cpp -shared -o libmylib.so
nm -D libmylib.so | grep my_function
# 00000abc T my_function  (✓ 符号已导出)
```

### GN 配置

```gni
cflags_cc = ["-fvisibility=default"]
```

### Makefile 配置

```makefile
CXXFLAGS += -fvisibility=default
```

---

## -static-libstdc++ -static-libgcc

**源文件**: `rmw_dsoftbus/Makefile.aarch64:39`, `rmw_dsoftbus/BUILD.gn:179`

### 作用

将 C++ 标准库和 GCC 运行时静态链接到二进制中。

### 何时使用

**推荐场景**:
- OpenHarmony 目标设备（避免运行时依赖）
- 设备上没有 libstdc++.so
- 需要最大兼容性

### 效果对比

**动态链接**（无此标志）:
```bash
$CXX myapp.cpp -o myapp
ldd myapp
    libstdc++.so.6 => /usr/lib/libstdc++.so.6
    libgcc_s.so.1 => /lib/libgcc_s.so.1
```
- 二进制小（~500 KB）
- 需要在设备上有对应版本的库

**静态链接**（有此标志）:
```bash
$CXX myapp.cpp -o myapp -static-libstdc++ -static-libgcc
ldd myapp
    # libstdc++.so 和 libgcc_s.so 不在列表中
```
- 二进制大（~2.5 MB）
- 无运行时依赖

### 配置

```makefile
LDFLAGS = -static-libstdc++ -static-libgcc
```

### 验证

```bash
# 检查是否静态链接
ldd mybinary | grep -E "(libstdc|libgcc)"
# 应该无输出

# 或使用 readelf
readelf -d mybinary | grep NEEDED
# 不应出现 libstdc++.so 或 libgcc_s.so
```

---

## -Wl,-rpath,/data

**源文件**: `rmw_dsoftbus/Makefile.aarch64:40`

### 作用

在二进制中嵌入运行时库搜索路径。

### 语法

```makefile
# 单个路径
LDFLAGS += -Wl,-rpath,/data

# 多个路径（用冒号分隔）
LDFLAGS += -Wl,-rpath,/data:/system/lib64
```

### 效果

运行时动态链接器会在这些路径中查找依赖库：
1. /data
2. /system/lib64
3. 系统默认路径（/lib, /usr/lib）

### 好处

无需设置 LD_LIBRARY_PATH：

```bash
# 无 RPATH
LD_LIBRARY_PATH=/data:/system/lib64 /data/bin/myapp  # 必须设置

# 有 RPATH
/data/bin/myapp  # 直接运行
```

### 重要限制

**RPATH 对 dlopen() 不生效**:

```cpp
// dlopen 不使用 RPATH
dlopen("libplugin.so", RTLD_LAZY);  // ✗ 找不到

// 必须用完整路径或设置 LD_LIBRARY_PATH
dlopen("/data/lib/libplugin.so", RTLD_LAZY);  // ✓
```

### 验证

```bash
readelf -d mybinary | grep RPATH
# 0x000000000000000f (RPATH)  Library rpath: [/data:/system/lib64]
```

---

## -fPIC

### 作用

生成位置无关代码（Position Independent Code）。

### 何时必需

**必需**:
- 编译共享库 (.so)
- 代码会被加载到任意内存地址

**可选**:
- 可执行文件（但推荐使用）

### 配置

```makefile
# 共享库（必需）
CXXFLAGS += -fPIC
$CXX -fPIC -shared mylib.cpp -o libmylib.so

# 可执行文件（可选，但推荐）
$CXX -fPIC myapp.cpp -o myapp
```

---

## -fuse-ld=lld

**源文件**: `rmw_dsoftbus/Makefile.ohos`

### 作用

使用 LLVM 链接器（lld）代替 GNU ld。

### 何时使用

- OHOS SDK Clang 工具链
- 需要快速链接
- LLVM 特定优化

### 配置

```makefile
LDFLAGS += -fuse-ld=lld
```

### 优势

- 链接速度快（比 GNU ld 快 2-3 倍）
- 更好的错误信息
- LLVM 生态一致性

---

## 优化标志

### 优化级别

| 标志 | 效果 | 二进制大小 | 性能 | 用途 |
|------|------|-----------|------|------|
| `-O0` | 无优化 | 最大 | 最慢 | 调试 |
| `-O1` | 基础优化 | 大 | 慢 | 开发 |
| `-O2` | 标准优化 | 中 | 快 | 生产（推荐）|
| `-O3` | 激进优化 | 中 | 最快 | 性能关键 |
| `-Os` | 大小优化 | 最小 | 中 | 嵌入式 |

**推荐**: `-O2`（性能与大小平衡）

### 调试标志

```makefile
# 调试模式
CXXFLAGS += -g -O0

# 发布模式
CXXFLAGS += -O2 -DNDEBUG

# Strip 符号（进一步减小大小）
$STRIP --strip-all mybinary
```

### 链接时优化（LTO）

```makefile
CXXFLAGS += -flto
LDFLAGS += -flto

# 效果：跨文件优化，减小 5-15% 大小
```

---

## 架构特定标志

### ARM64 优化

```makefile
# 通用 ARMv8-A
CXXFLAGS += -march=armv8-a

# Cortex-A76 (rk3588s)
CXXFLAGS += -march=armv8-a -mtune=cortex-a76

# NEON SIMD
CXXFLAGS += -march=armv8-a+simd
```

---

## 完整配置示例

### GCC Linaro 生产配置

```makefile
CXXFLAGS = -std=c++17 \
           -O2 \
           -Wall -Wextra -Werror \
           -fPIC \
           -fvisibility=default \
           --sysroot=$SYSROOT

LDFLAGS = -static-libstdc++ -static-libgcc \
          -Wl,-rpath,/data -Wl,-rpath,/system/lib64 \
          -Wl,--as-needed \
          -Wl,--gc-sections \
          -lpthread -ldl
```

### OHOS Clang 生产配置

```makefile
CXXFLAGS = -std=c++17 \
           -O2 \
           -Wall -Wextra \
           -fPIC \
           -fvisibility=default \
           --sysroot=$SYSROOT \
           -D__MUSL__ \
           -stdlib=libc++

LDFLAGS = -fuse-ld=lld \
          -lc++ -lc++abi \
          -lpthread -ldl
```

---

## 参考源文件

- `rmw_dsoftbus/BUILD.gn` - GN 编译配置
- `rmw_dsoftbus/Makefile.aarch64` - GCC Linaro 标志
- `rmw_dsoftbus/Makefile.ohos` - OHOS Clang 标志
- `rmw_dsoftbus/compile_official_style.sh` - 编译脚本

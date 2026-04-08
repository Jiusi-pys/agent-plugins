# 链接策略详解

OpenHarmony 交叉编译中的各种链接策略和最佳实践。

## 策略概览

| 策略 | 二进制大小 | 运行时依赖 | 灵活性 | 推荐度 |
|------|-----------|-----------|--------|--------|
| 动态链接 + 静态 C++ | 中 | 少 | 中 | ⭐⭐⭐⭐⭐ |
| 完全动态链接 | 小 | 多 | 高 | ⭐⭐⭐ |
| 完全静态链接 | 大 | 无 | 低 | ⭐⭐ |
| dlopen 动态加载 | 小 | 中 | 极高 | ⭐⭐⭐⭐ |

---

## 策略 1: 动态链接 + 静态 C++ 运行时（推荐）

**源文件**: `rmw_dsoftbus/Makefile.aarch64`

### 配置

```makefile
LDFLAGS = -static-libstdc++ -static-libgcc \
          -Wl,-rpath,/data -Wl,-rpath,/system/lib64 \
          -lpthread -ldl

$CXX -shared mylib.cpp -o libmylib.so $LDFLAGS
```

### 效果

**链接的库**:
- libstdc++, libgcc: 静态链接（无运行时依赖）
- pthread, dl: 动态链接（系统保证存在）

**验证**:
```bash
ldd libmylib.so
    linux-vdso.so.1 (0x...)
    libpthread.so.0 => /lib/libpthread.so.0
    libdl.so.2 => /lib/libdl.so.2
    libc.so => /lib/ld-musl-aarch64.so.1
    # 注意：无 libstdc++.so 和 libgcc_s.so
```

### 优势

- ✅ 无需部署 C++ 运行时
- ✅ 最大兼容性
- ✅ 二进制可直接运行

### 劣势

- 二进制较大（+2-3 MB）

---

## 策略 2: 完全动态链接

### 配置

```makefile
LDFLAGS = -Wl,-rpath,/data \
          -lpthread -ldl -lstdc++ -lgcc_s
```

### 效果

**所有库都动态链接**:
```bash
ldd libmylib.so
    libstdc++.so.6 => /system/lib64/libstdc++.so.6
    libgcc_s.so.1 => /system/lib64/libgcc_s.so.1
    libpthread.so.0 => /lib/libpthread.so.0
```

### 优势

- 二进制小

### 劣势

- ❌ 需要在设备上部署 libstdc++.so.6
- ❌ 版本匹配问题（设备库版本可能不同）

---

## 策略 3: 完全静态链接

**源文件**: `rmw_dsoftbus/compile_fully_static.sh`

### 配置

```bash
$CXX -static myapp.cpp -o myapp -lpthread -ldl
```

### 效果

**所有库静态链接**（除 musl libc）:
```bash
file myapp
# statically linked

ldd myapp
# not a dynamic executable
```

### 优势

- ✅ 最大可移植性
- ✅ 无任何运行时依赖

### 劣势

- ❌ 二进制非常大（10-20 MB）
- ❌ 无法共享代码段
- ❌ 更新库需要重新编译

---

## 策略 4: dlopen 动态加载

**源文件**: `rmw_dsoftbus/test/softbus_dlopen_shim.cpp`

### 原理

**编译时**: 不链接库，只声明函数指针

**运行时**: 使用 dlopen/dlsym 加载库和符号

### 实现

```cpp
#include <dlfcn.h>

// 函数指针类型
typedef int (*CreateSession_t)(const char*);

// 全局函数指针
static CreateSession_t _CreateSession = nullptr;

// 构造函数自动加载
__attribute__((constructor))
void load_library() {
    void* handle = dlopen("/system/lib64/libsoftbus_client.z.so", RTLD_NOW);
    if (handle) {
        _CreateSession = (CreateSession_t)dlsym(handle, "CreateSession");
    }
}

// 包装函数
int CreateSession(const char* name) {
    if (_CreateSession) {
        return _CreateSession(name);
    }
    return -1;  // 未加载
}
```

### 编译配置

```makefile
CXXFLAGS += -fvisibility=default  # 必需：导出包装函数
LDFLAGS += -ldl                     # 必需：链接 libdl
```

### 优势

- ✅ 无编译时依赖
- ✅ 运行时选择库版本
- ✅ 避免 .z.so 链接问题

### 劣势

- 代码复杂度增加
- 运行时开销（dlopen）

---

## RPATH vs LD_LIBRARY_PATH

### RPATH（推荐）

**配置**:
```makefile
LDFLAGS += -Wl,-rpath,/data -Wl,-rpath,/system/lib64
```

**效果**: 嵌入二进制，自动搜索

**验证**:
```bash
readelf -d mybinary | grep RPATH
```

**限制**: 对 dlopen() **不生效**

### LD_LIBRARY_PATH（备选）

**配置**:
```bash
export LD_LIBRARY_PATH=/data/lib:/system/lib64
./mybinary
```

**效果**: 环境变量，全局生效

**限制**: 需要每次运行前设置

### 结合使用

```bash
# RPATH 用于主程序依赖
LDFLAGS += -Wl,-rpath,/data

# LD_LIBRARY_PATH 用于 dlopen
export LD_LIBRARY_PATH=/data/plugins
# 然后 dlopen("libplugin.so") 会在 /data/plugins 中查找
```

---

## 版本化共享库

**源文件**: `rmw_dsoftbus/Makefile.aarch64:25-30`

### SONAME 机制

```makefile
# 创建版本化库
$CXX -shared mylib.cpp -o libmylib.so.1.2.3 \
    -Wl,-soname,libmylib.so.1

# 创建符号链接
ln -sf libmylib.so.1.2.3 libmylib.so.1
ln -sf libmylib.so.1 libmylib.so
```

### 部署结构

```
/data/lib/
├── libmylib.so.1.2.3  # 实际文件（版本 1.2.3）
├── libmylib.so.1      -> libmylib.so.1.2.3  # 主版本号链接
└── libmylib.so        -> libmylib.so.1      # 开发链接
```

### 用途

- 链接时: 使用 `libmylib.so`
- 运行时: 加载 `libmylib.so.1`（SONAME）
- 可同时安装多个主版本（libmylib.so.1 和 libmylib.so.2）

### 验证 SONAME

```bash
readelf -d libmylib.so.1.2.3 | grep SONAME
# 0x000000000000000e (SONAME)  Library soname: [libmylib.so.1]
```

---

## 特殊链接标志

### --as-needed

**源文件**: `rmw_dsoftbus/Makefile.aarch64:40`

```makefile
LDFLAGS += -Wl,--as-needed
```

**效果**: 只链接实际使用的库，减小 NEEDED 列表

### --gc-sections

```makefile
CXXFLAGS += -ffunction-sections -fdata-sections
LDFLAGS += -Wl,--gc-sections
```

**效果**: 移除未使用的函数和数据，减小二进制 10-30%

### --allow-shlib-undefined

**源文件**: `rmw_dsoftbus/CMakeLists.txt`

```makefile
LDFLAGS += -Wl,--allow-shlib-undefined
```

**效果**: 允许共享库有未定义符号（运行时解析）

---

## 配置对比

### GCC Linaro 推荐配置

```makefile
LDFLAGS = -static-libstdc++ -static-libgcc \
          -Wl,-rpath,/data -Wl,-rpath,/system/lib64 \
          -Wl,--as-needed \
          -Wl,--gc-sections \
          -lpthread -ldl
```

**特点**: 静态 C++，RPATH，优化大小

### OHOS Clang 推荐配置

```makefile
LDFLAGS = -fuse-ld=lld \
          -lc++ -lc++abi \
          -Wl,-rpath,/system/lib64 \
          -lpthread -ldl
```

**特点**: 动态 libc++，LLVM 链接器

---

## 参考源文件

- `rmw_dsoftbus/Makefile.aarch64` - GCC Linaro 链接配置
- `rmw_dsoftbus/Makefile.ohos` - OHOS Clang 链接配置
- `rmw_dsoftbus/test/softbus_dlopen_shim.cpp` - dlopen 模式实现
- `rmw_dsoftbus/BUILD.gn` - GN 链接配置

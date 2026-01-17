---
description: OHOS 交叉编译。使用 OHOS 工具链编译目标软件。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task
---

# OHOS Build: $ARGUMENTS

## 目标

交叉编译 `$ARGUMENTS` 到 aarch64-ohos 目标平台。

## 前置检查

### 环境变量
```bash
echo "OHOS_SDK: ${OHOS_SDK:-未设置}"
```

### 工具链验证
```bash
${OHOS_SDK}/native/llvm/bin/clang --version
ls -la ${OHOS_SDK}/native/sysroot
```

## 编译流程

### Step 1: 确定构建系统

检测项目使用的构建系统：
- CMake (CMakeLists.txt)
- Makefile
- Meson (meson.build)
- GN (BUILD.gn)

### Step 2: 配置交叉编译

**CMake 项目:**
```bash
mkdir -p build && cd build
cmake .. \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DCMAKE_C_COMPILER=${OHOS_SDK}/native/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=${OHOS_SDK}/native/llvm/bin/clang++ \
  -DCMAKE_SYSROOT=${OHOS_SDK}/native/sysroot \
  -DCMAKE_C_FLAGS="--target=aarch64-linux-ohos" \
  -DCMAKE_CXX_FLAGS="--target=aarch64-linux-ohos"
```

**Makefile 项目:**
```bash
make \
  CC="${OHOS_SDK}/native/llvm/bin/clang --target=aarch64-linux-ohos --sysroot=${OHOS_SDK}/native/sysroot" \
  CXX="${OHOS_SDK}/native/llvm/bin/clang++ --target=aarch64-linux-ohos --sysroot=${OHOS_SDK}/native/sysroot"
```

### Step 3: 执行编译

```bash
make -j$(nproc) 2>&1 | tee build.log
```

### Step 4: 错误处理

若编译失败，启动 compile-debugger agent：

```
"分析 build.log 中的编译错误:
1. 分类错误类型
2. 给出修复方案
3. 优先处理高影响错误"
```

### Step 5: 输出结果

```
╔════════════════════════════════════════════════════════╗
║         编译结果                                        ║
╠════════════════════════════════════════════════════════╣
║ 状态: {成功/失败}                                       ║
║ 耗时: {X} 秒                                            ║
╚════════════════════════════════════════════════════════╝

[成功时]
产出物:
  - {binary_path}
  - {library_path}

[失败时]
错误数: {N}
首个错误:
  {error_message}

建议: 使用 compile-debugger agent 进行诊断
```

---
name: ohos-cpp-style
description: "OpenHarmony/KaihongOS C/C++ 编程规范。当 Claude 需要为 OpenHarmony、KaihongOS、dsoftbus、ROS2-KaihongOS 移植项目编写或审查 C/C++ 代码时使用。涵盖：(1) 代码格式化（clang-format 配置），(2) 命名规范，(3) GN 构建配置，(4) 文档注释规范，(5) dsoftbus API 规范，(6) 权限配置，(7) 线程同步，(8) CDR 序列化。使用前需读取 config.json 获取项目路径配置。"
---

# OpenHarmony C/C++ 编程规范

## 配置文件

使用前先读取 `config.json` 获取路径配置：

```json
{
    "paths": {
        "openharmony_source": "/home/jiusi/M-DDS/OpenHarmony",
        "openharmony_prebuilts": "/home/jiusi/M-DDS/openharmony_prebuilts",
        "output_dir": "/home/jiusi/M-DDS/out/rk3588s"
    },
    "toolchain": {
        "gcc_linaro": "gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu",
        "clang": "clang_linux-x86_64-81cdec-20240308"
    },
    "target": {
        "cpu": "arm64",
        "os": "ohos",
        "board": "rk3588s"
    },
    "project": {
        "part_name": "communication_dsoftbus",
        "subsystem_name": "communication"
    }
}
```

---

## 快速参考

### 文件头模板

```cpp
/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * ...
 */

/**
 * @file session_manager.h
 * @brief Session management for dsoftbus
 * @since 1.0
 * @version 1.0
 */

#ifndef RMW_DSOFTBUS__SESSION_MANAGER_H_
#define RMW_DSOFTBUS__SESSION_MANAGER_H_

// Your code

#endif  // RMW_DSOFTBUS__SESSION_MANAGER_H_
```

完整模板: `asserts/template.h`

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 命名空间 | CamelCase | `namespace OHOS { }` |
| 类/结构体 | CamelCase | `class SessionManager` |
| C API 函数 | CamelCase | `CreateSessionServer()` |
| 成员函数 | camelCase | `initialize()` |
| 成员变量 | snake_case_ | `initialized_`, `sessions_` |
| 宏/常量 | UPPER_SNAKE_CASE | `RMW_DSOFTBUS_IDENTIFIER` |
| 文件名 | snake_case | `session_manager.cpp` |

### 格式化配置

```bash
# 使用项目 clang-format
clang-format -style=file -i file.cpp
```

**关键参数**: 4 空格缩进，120 字符行宽，指针右对齐

配置文件: `asserts/.clang-format`

### GN 构建快速模板

```gni
import("//build/ohos.gni")

ohos_shared_library("mylib") {
    sources = ["src/file.cpp"]

    cflags_cc = ["-std=c++17", "-fvisibility=default"]

    external_deps = [
        "c_utils:utils",
        "hilog:libhilog",
        "dsoftbus:softbus_client",
    ]

    part_name = "mycomponent"           # 必需
    subsystem_name = "communication"    # 必需
    install_enable = true
    install_images = ["system"]
}
```

完整模板: `asserts/BUILD.gn`

---

## 详细内容索引

### 基础规范
- **格式化**: 见 `asserts/.clang-format`
- **代码模板**: 见 `asserts/template.h` 和 `asserts/template.cpp`
- **GN 构建**: 见 `references/gn-templates.md`

### 高级模式（新增）
- **权限配置**: 见 `references/permission-config.md`
  - dlopen 动态加载模式
  - AccessToken API 初始化
  - 三层权限架构详解

- **线程同步**: 见 `references/thread-patterns.md`
  - Meyer's Singleton 模式
  - Lock Ordering 文档规范
  - Condition Variable 用法
  - 原子操作模式

- **CDR 序列化**: 见 `references/serialization.md`
  - Buffer 管理（双模式）
  - 字节序处理
  - 对齐计算
  - 复合类型序列化

### 何时查阅详细文档

| 场景 | 查阅文档 |
|------|----------|
| 配置 dsoftbus 权限 | `references/permission-config.md` |
| 编写多线程代码 | `references/thread-patterns.md` |
| 实现消息序列化 | `references/serialization.md` |
| 编写 BUILD.gn | `references/gn-templates.md` |
| 错误处理模式 | `references/error-handling.md` (待创建)|

---

## 代码审查清单

使用前快速检查：

- [ ] Apache 2.0 许可证头
- [ ] 头文件 include guard
- [ ] 命名符合规范
- [ ] 文档注释完整
- [ ] clang-format 格式化
- [ ] BUILD.gn 配置正确（part_name, subsystem_name）
- [ ] external_deps 格式正确
- [ ] 错误处理完整
- [ ] 资源正确释放（RAII）

详细检查清单: 见各 references/ 文档末尾

---

## 提交消息格式

```
[subsystem] brief summary (type)

详细说明（可选）
- 要点 1
- 要点 2
```

**类型**: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `build`

---

## 相关资源

### Skill 内部文件
- `config.json` - 项目路径配置（必须先设置）
- `asserts/` - 模板文件（.clang-format, template.h, BUILD.gn）
- `references/` - 详细参考文档（权限、线程、序列化等）

### 项目文档
- `docs/00_核心技术文档/OPENHARMONY_CPLUSPLUS_STANDARDS.md` - 官方编码规范
- `docs/00_核心技术文档/OHOS_GN_BUILD_GUIDE.md` - GN 构建指南
- `docs/02_dsoftbus诊断体系/dsoftbus权限问题快速修复指南.md` - 权限配置

### 源代码参考
- `rmw_dsoftbus/src/` - 生产代码示例
- `rmw_dsoftbus/include/rmw_dsoftbus/` - 头文件设计
- `rmw_dsoftbus/BUILD.gn` - GN 构建配置

---

**版本**: v2.0 (2026-01-15)
**更新**: 新增权限配置、线程同步、CDR 序列化等高级模式的详细参考文档

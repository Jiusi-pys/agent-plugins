---
name: ohos-cpp-style
description: "OpenHarmony/KaihongOS C/C++ 编程规范。当 Claude 需要为 OpenHarmony、KaihongOS 移植项目编写或审查 C/C++ 代码时使用。涵盖：(1) 代码格式化（clang-format 配置），(2) 命名规范，(3) GN 构建配置，(4) 文档注释规范，(5) 权限配置，(6) 线程同步。"
---

# OpenHarmony C/C++ 编程规范

## 配置文件

使用前先读取 \`config.json\` 获取路径配置：

\`\`\`json
{
    "paths": {
        "openharmony_source": "/path/to/OpenHarmony",
        "openharmony_prebuilts": "/path/to/openharmony_prebuilts",
        "output_dir": "/path/to/out/<board>"
    },
    "toolchain": {
        "clang": "clang_linux-x86_64-<version>"
    },
    "target": {
        "cpu": "arm64",
        "os": "ohos",
        "board": "rk3588s"
    },
    "project": {
        "part_name": "<your_part_name>",
        "subsystem_name": "<your_subsystem>"
    }
}
\`\`\`

---

## 快速参考

### 文件头模板

\`\`\`cpp
/*
 * Copyright (c) 2024-2026 Your Organization
 * Licensed under the Apache License, Version 2.0 (the "License");
 * ...
 */

/**
 * @file module_name.h
 * @brief Brief description of the module
 * @since 1.0
 * @version 1.0
 */

#ifndef PROJECT__MODULE_NAME_H_
#define PROJECT__MODULE_NAME_H_

// Your code

#endif  // PROJECT__MODULE_NAME_H_
\`\`\`

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 命名空间 | CamelCase | \`namespace OHOS { }\` |
| 类/结构体 | CamelCase | \`class SessionManager\` |
| C API 函数 | CamelCase | \`CreateSession()\` |
| 成员函数 | camelCase | \`initialize()\` |
| 成员变量 | snake_case_ | \`initialized_\`, \`data_\` |
| 宏/常量 | UPPER_SNAKE_CASE | \`MAX_BUFFER_SIZE\` |
| 文件名 | snake_case | \`module_name.cpp\` |

### 格式化配置

\`\`\`bash
# 使用项目 clang-format
clang-format -style=file -i file.cpp
\`\`\`

**关键参数**: 4 空格缩进，120 字符行宽，指针右对齐

配置文件: \`asserts/.clang-format\`

### GN 构建快速模板

\`\`\`gni
import("//build/ohos.gni")

ohos_shared_library("mylib") {
    sources = ["src/file.cpp"]
    
    cflags_cc = ["-std=c++17", "-fvisibility=default"]
    
    external_deps = [
        "c_utils:utils",
        "hilog:libhilog",
    ]
    
    part_name = "mycomponent"           # 必需
    subsystem_name = "mysubsystem"      # 必需
    install_enable = true
    install_images = ["system"]
}
\`\`\`

---

## 详细内容索引

### 基础规范

- **格式化**: 见 \`asserts/.clang-format\`
- **代码模板**: 见 \`asserts/template.h\` 和 \`asserts/template.cpp\`
- **GN 构建**: 见 \`references/gn-templates.md\`

### 高级模式

- **权限配置**: 见 \`references/permission-config.md\`
  - dlopen 动态加载模式
  - AccessToken API 初始化
  - 权限架构详解
  
- **线程同步**: 见 \`references/thread-patterns.md\`
  - Meyer's Singleton 模式
  - Lock Ordering 文档规范
  - Condition Variable 用法
  - 原子操作模式

- **序列化**: 见 \`references/serialization.md\`
  - Buffer 管理
  - 字节序处理
  - 对齐计算

### 何时查阅详细文档

| 场景 | 查阅文档 |
|------|----------|
| 配置系统权限 | \`references/permission-config.md\` |
| 编写多线程代码 | \`references/thread-patterns.md\` |
| 实现消息序列化 | \`references/serialization.md\` |
| 编写 BUILD.gn | \`references/gn-templates.md\` |

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

---

## 提交消息格式

\`\`\`
[subsystem] brief summary (type)

详细说明（可选）
- 要点 1
- 要点 2
\`\`\`

**类型**: \`feat\`, \`fix\`, \`refactor\`, \`docs\`, \`test\`, \`perf\`, \`build\`

---

## 常用 external_deps

\`\`\`gni
# 基础工具库
"c_utils:utils"

# 日志
"hilog:libhilog"

# IPC
"ipc:ipc_core"

# Samgr (系统服务管理)
"samgr:samgr_proxy"

# 分布式软总线 (如需使用)
"dsoftbus:softbus_client"

# 安全
"access_token:libaccesstoken_sdk"
"access_token:libnativetoken"
\`\`\`

---

## 相关资源

### Skill 内部文件

- \`config.json\` - 项目路径配置（使用前设置）
- \`asserts/\` - 模板文件（.clang-format, template.h, BUILD.gn）
- \`references/\` - 详细参考文档

### OHOS 官方文档

- OpenHarmony 编码规范
- GN 构建系统指南
- 子系统开发指南

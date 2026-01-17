# ohos-cpp-style Skill 说明文档

## 📝 概述

本 skill 是基于 rmw_dsoftbus 项目实战经验总结的 OpenHarmony/KaihongOS C++ 编码规范指南。它从项目中提取了经过验证的最佳实践，为 OHOS C/C++ 开发提供全面的编码规范和模式参考。

## 🎯 核心功能

### 1. 文件组织和格式化
- Apache 2.0 标准许可证头模板
- Doxygen 风格文档注释规范
- clang-format 配置（基于 Google 风格，4空格缩进）
- 头文件包含顺序规范

### 2. 命名规范
- 命名空间：CamelCase (OHOS, rmw_dsoftbus)
- 类名：CamelCase (SessionManager)
- 成员变量：snake_case_ (initialized_, sessions_)
- 函数：snake_case (register_subscription)
- 常量/宏：UPPER_SNAKE_CASE (RMW_DSOFTBUS_PACKAGE_NAME)

### 3. 权限配置模式
- dlopen 动态加载系统库的完整实现
- AccessToken API 使用模式
- __attribute__((constructor)) 自动初始化
- 多路径尝试和 fallback 机制
- 详细错误日志和诊断信息

### 4. 错误处理和日志
- fprintf(stderr, ...) 统一日志格式
- 错误信息包含完整上下文
- 使用 ✅ ⚠️ ❌ 标记区分日志级别
- 提供针对性错误提示

### 5. GN 构建配置
- ohos_shared_library / ohos_executable 模板使用
- external_deps 正确配置
- 符号可见性控制 (-fvisibility=default)
- part_name 和 subsystem_name 声明

### 6. dsoftbus API 使用
- CreateSessionServer 完整流程
- OpenSession 参数配置
- SendBytes 错误处理
- 回调函数设置模式

### 7. 类和结构体设计
- 线程安全单例模式
- RAII 资源管理
- 默认成员初始化
- 拷贝/赋值禁用模式

### 8. 兼容性和可移植性
- C 标准库 vs C++ 标准库选择
- 标准整数类型使用
- 平台特定代码隔离

## 📚 来源分析

### 分析的文件和文档

#### 核心代码文件
1. `rmw_dsoftbus/src/session_manager.cpp` - Session 管理实现
2. `rmw_dsoftbus/src/native_token.cpp` - 权限配置实现
3. `rmw_dsoftbus/test/softbus_dlopen_shim.cpp` - dlopen 动态加载模式
4. `rmw_dsoftbus/test/softbus_permission_bypass_dlopen.cpp` - 权限绕过实现

#### 头文件
1. `rmw_dsoftbus/include/rmw_dsoftbus/session_manager.h` - 接口设计
2. `rmw_dsoftbus/include/rmw_dsoftbus/native_token.h` - 权限接口

#### 构建配置
1. `rmw_dsoftbus/BUILD.gn` - GN 构建配置

#### 文档
1. `docs/00_核心技术文档/OPENHARMONY_CPLUSPLUS_STANDARDS.md` - 官方编码规范
2. `docs/00_核心技术文档/OHOS_GN_BUILD_GUIDE.md` - GN 构建指南
3. `docs/02_dsoftbus诊断体系/dsoftbus权限问题快速修复指南.md` - 权限配置实践

## 🔧 提取的最佳实践

### 1. dlopen 模式（关键改进点）

从 `softbus_dlopen_shim.cpp` 中提取的经过验证的 dlopen 模式：
- 使用 `__attribute__((constructor))` 自动加载
- 尝试多个库路径提高兼容性
- 提供 fallback 实现
- 详细错误诊断

```cpp
__attribute__((constructor))
void load_library() {
    const char* lib_paths[] = {
        "/system/lib64/chipset-pub-sdk/libfoo.z.so",
        "/system/lib64/platformsdk/libfoo.z.so"
    };
    // ... 尝试加载逻辑
}
```

### 2. 权限配置流程（核心功能）

从 `native_token.cpp` 和权限配置文档中总结的标准流程：
1. 加载 AccessToken 库
2. 准备权限参数（aplStr="system_basic"）
3. 获取 Token ID
4. 设置进程 Token
5. 错误处理和日志

### 3. 错误处理模式（实用改进）

统一的错误处理模式：
- 前置条件检查
- 系统调用返回值检查
- 详细错误信息（包含参数值）
- 针对已知错误提供提示
- 成功日志确认

### 4. GN 构建配置（关键知识）

从 `BUILD.gn` 和构建文档中提取的配置要点：
- `external_deps` 格式：`"component:library"`
- 符号可见性：`-fvisibility=default`（dlopen 必需）
- `part_name` 和 `subsystem_name` 必须声明
- 安装配置：`install_images`, `module_install_dir`

### 5. 命名规范（项目实践）

从实际代码中归纳的命名模式：
- 成员变量使用后缀下划线（C++ 风格）
- 函数使用 snake_case（C API 兼容）
- 常量使用 kCamelCase 或 UPPER_SNAKE_CASE
- 命名空间结束注释包含命名空间名

## 🆕 相比基础规范的改进

### 1. 新增权限配置章节
- 完整的 dlopen 实现模板
- AccessToken 初始化流程
- 多路径尝试和 fallback 机制
- 实战验证的代码示例

### 2. 新增 dsoftbus API 使用模式
- CreateSessionServer 完整示例
- OpenSession 参数配置
- Session 名称构造规范（包含 PID）
- 回调函数设置

### 3. 增强错误处理规范
- 统一日志格式（使用 emoji 标记）
- 完整上下文信息
- 错误恢复和 fallback 模式
- 针对性错误提示

### 4. 完善 GN 构建指南
- 完整的 BUILD.gn 模板
- external_deps 正确用法
- 符号可见性配置说明
- 常见错误和解决方案

### 5. 新增兼容性指南
- C 标准库 vs C++ 标准库选择原则
- gcc-linaro 兼容性考虑
- 平台特定代码隔离模式

## 📋 使用场景

### 何时使用此 Skill

1. **编写 OHOS C++ 代码时**
   - 需要符合 OpenHarmony 编码规范
   - 使用 dsoftbus 进行通信
   - 需要配置权限和 AccessToken

2. **审查代码时**
   - 检查命名规范
   - 验证错误处理是否完善
   - 确认构建配置正确

3. **调试权限问题时**
   - 参考 dlopen 加载模式
   - 查看 AccessToken 初始化流程
   - 使用错误日志模板

4. **配置 GN 构建时**
   - 编写 BUILD.gn 文件
   - 配置 external_deps
   - 设置编译选项

### 典型工作流

```
1. 阅读 skill 了解规范
2. 使用代码模板开始编写
3. 参考命名规范检查代码
4. 使用错误处理模板
5. 配置 BUILD.gn
6. 运行 clang-format 格式化
7. 检查清单验证
```

## 🔍 检查清单

使用此 skill 时，请确保：

- [ ] 文件包含 Apache 2.0 许可证头
- [ ] 头文件有正确的 include guard
- [ ] 命名符合规范
- [ ] 使用 namespace 避免全局污染
- [ ] 错误处理完整
- [ ] dlopen 使用 fallback 机制
- [ ] BUILD.gn 配置正确
- [ ] 符号可见性配置正确
- [ ] 文档注释完整

## 🎓 学习路径

### 初学者
1. 阅读"命名规范"章节
2. 学习"文件头和许可证"
3. 了解"代码格式化"规则

### 中级开发者
1. 掌握"类和结构体设计"
2. 学习"错误处理和日志"
3. 理解"GN 构建配置"

### 高级开发者
1. 精通"权限配置模式"
2. 掌握"dsoftbus API 使用"
3. 理解"兼容性和可移植性"

## 📖 相关资源

### 项目文档
- OPENHARMONY_CPLUSPLUS_STANDARDS.md - 官方规范
- OHOS_GN_BUILD_GUIDE.md - 构建指南
- dsoftbus权限问题快速修复指南.md - 权限配置

### 示例代码
- rmw_dsoftbus/src/session_manager.cpp
- rmw_dsoftbus/src/native_token.cpp
- rmw_dsoftbus/test/softbus_dlopen_shim.cpp

### 构建文件
- rmw_dsoftbus/BUILD.gn

## 🔄 更新记录

### v1.0.0 (2026-01-15)
- 初始版本
- 基于 rmw_dsoftbus 项目实战经验
- 涵盖 10 大主题
- 包含完整代码模板和示例

## 📞 反馈和改进

如果发现规范中的问题或有改进建议，请：
1. 检查实际代码是否符合新的最佳实践
2. 更新 skill.md 中的相应章节
3. 在 README.md 中记录更新

---

**创建日期**: 2026-01-15
**基于项目**: rmw_dsoftbus (M-DDS)
**分析代码行数**: 约 3000+ 行
**参考文档数**: 10+ 篇

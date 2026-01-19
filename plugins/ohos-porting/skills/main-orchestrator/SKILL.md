# OHOS Porting Orchestrator

## 概述

OpenHarmony/KaihongOS 通用移植编排器。管理从 Linux 到 OHOS 的移植项目全生命周期。

**适用场景**:
- Linux 库/应用移植到 OpenHarmony
- ROS2 组件移植到 KaihongOS
- 第三方 C/C++ 库适配
- 嵌入式系统软件迁移

---

## 移植流程框架

### Phase 1: 评估 (Assessment)

**目标**: 确定移植可行性和工作量

**检查点**:
- [ ] 源码可获取性
- [ ] 依赖库 OHOS 可用性
- [ ] API 兼容性初评
- [ ] 许可证兼容性

**输出**: 移植可行性报告 (A/B/C/D 评级)

### Phase 2: 准备 (Preparation)

**目标**: 搭建开发环境和工具链

**检查点**:
- [ ] OHOS SDK 安装验证
- [ ] 交叉编译工具链配置
- [ ] 目标设备连接 (hdc)
- [ ] 依赖库预构建

**输出**: 开发环境就绪确认

### Phase 3: 适配 (Adaptation)

**目标**: 代码修改和构建系统适配

**检查点**:
- [ ] 平台特定 API 替换
- [ ] 构建系统配置 (CMake/GN/Makefile)
- [ ] 头文件路径调整
- [ ] 链接库配置

**输出**: 可编译的适配代码

### Phase 4: 验证 (Validation)

**目标**: 功能测试和性能验证

**检查点**:
- [ ] 交叉编译成功
- [ ] 设备部署成功
- [ ] 基础功能测试通过
- [ ] 性能基准测试

**输出**: 测试报告

---

## 约束条件

### 目标设备操作约束

```
1. 禁止修改 /system /vendor 目录（除非明确授权）
2. 所有部署文件放置在:
   - /data/local/tmp (临时测试)
   - /data/app/<project> (应用部署)
3. 修改系统配置前必须:
   - 备份原文件
   - 记录操作命令
   - 准备回滚方案
```

### 开发规范约束

```
1. 可复现性: 手动操作必须脚本化
2. 证据优先: 所有结论必须有命令输出支撑
3. 小步迭代: 每个阶段有明确检查点
4. 版本控制: 所有修改必须提交并记录
```

---

## 工具和访问

### 设备访问

| 工具 | 用途 | 示例 |
|------|------|------|
| hdc | 设备连接管理 | `hdc list targets` |
| hdc shell | 远程命令执行 | `hdc shell ls /data` |
| hdc file | 文件传输 | `hdc file send local remote` |

### 构建工具

| 工具 | 用途 |
|------|------|
| OHOS SDK clang | 交叉编译 |
| CMake | 构建系统 |
| GN | OHOS 原生构建 |

### 调试工具

| 工具 | 用途 |
|------|------|
| hilog | 系统日志 |
| lldb | 远程调试 |
| strace | 系统调用追踪 |

---

## 文档结构

```
project/
├── docs/
│   ├── porting-assessment.md      # 移植评估报告
│   ├── adaptation-guide.md        # 适配指南
│   └── test-report.md             # 测试报告
├── ops/
│   ├── scripts/                   # 自动化脚本
│   ├── inventory/                 # 设备/环境清单
│   └── journal.md                 # 操作日志
└── src/
    └── ...                        # 适配后源码
```

---

## 检查点模板

### Gate A: 环境就绪

```markdown
## 环境检查清单
- [ ] OHOS SDK 版本: ___
- [ ] 工具链验证: clang --version
- [ ] 目标设备连接: hdc list targets
- [ ] Hello World 编译部署测试
```

### Gate B: 依赖就绪

```markdown
## 依赖检查清单
- [ ] 依赖库列表确认
- [ ] OHOS 可用依赖: ___
- [ ] 需要移植依赖: ___
- [ ] 依赖构建脚本准备
```

### Gate C: 编译就绪

```markdown
## 编译检查清单
- [ ] 构建系统配置完成
- [ ] 编译命令确定
- [ ] 编译通过 (0 errors, N warnings)
- [ ] 产出物验证 (file/readelf)
```

### Gate D: 部署就绪

```markdown
## 部署检查清单
- [ ] 文件推送成功
- [ ] 权限配置完成
- [ ] 依赖库部署完成
- [ ] 基础运行测试通过
```

---

## 项目示例

### 示例 1: 简单库移植

```bash
# 评估
/ohos-port libfoo

# 构建
/ohos-build libfoo

# 部署
/ohos-deploy libfoo --device=<DEVICE_ID>
```

### 示例 2: 复杂应用移植

```bash
# 完整流程
/ohos-port-dev myapp

# 分步执行
# 1. 评估
/ohos-port myapp

# 2. 构建 (可能多次迭代)
/ohos-build myapp
# 如有错误，compile-debugger 自动介入

# 3. 部署测试
/ohos-deploy myapp
# 如有运行时问题，runtime-debugger 自动介入
```

---

## 参考

- OHOS 编程规范: `skills/ohos-cpp-style/`
- 交叉编译指南: `skills/ohos-cross-compile/`
- 权限配置: `skills/ohos-permission/`
- HDC 操作: `skills/hdc-kaihongOS/`

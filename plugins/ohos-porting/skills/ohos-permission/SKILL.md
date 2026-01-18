# OHOS Permission Skill

## 概述

OpenHarmony/KaihongOS 特有的权限配置技术。涵盖 DSoftBus Session 权限、AccessToken 处理、配置文件格式规范等关键知识点。

**适用场景**:
- rmw_dsoftbus ROS2 中间件开发
- DSoftBus 分布式软总线应用
- Native 应用权限配置
- 跨设备通信调试

**验证状态**: ✅ 2026-01-19 rk3588s KaihongOS API 11 真机验证通过

---

## 快速开始 (3 步配置)

```bash
# 1. 准备配置文件
cp templates/verified.json /tmp/softbus_perm.json

# 2. 部署到设备
./scripts/deploy_softbus_permission.sh <DEVICE_ID> /tmp/softbus_perm.json

# 3. 验证 (设备重启后)
./scripts/verify_softbus_permission.sh <DEVICE_ID>
```

---

## 核心知识点

### 1. DSoftBus 权限配置格式

**配置文件位置**:
```
/system/etc/communication/softbus/softbus_trans_permission.json
```

#### ✅ 正确格式（纯数组）

```json
[
  {
    "SESSION_NAME": "com.huawei.ros2_rmw_dsoftbus.*",
    "REGEXP": "true",
    "DEVID": "NETWORKID",
    "SEC_LEVEL": "public",
    "APP_INFO": [
      {
        "TYPE": "native_app",
        "PKG_NAME": "com.huawei.ros2_rmw_dsoftbus",
        "ACTIONS": "create,open"
      }
    ]
  }
]
```

**关键要点**:
- 根元素必须是 **数组** \`[...]\`
- 不能有 \`trans_permission\` 外层包装
- \`REGEXP: "true"\` 启用正则匹配
- 配置修改后 **必须重启设备**

#### ❌ 错误格式（导致权限拒绝 -426442715）

```json
{
  "trans_permission": [
    { "id": 1, "data": [...] }
  ]
}
```

### 2. PKG_NAME 配置策略

| 方案 | 配置 | 适用场景 |
|------|------|----------|
| 精确匹配 | \`"PKG_NAME": "com.huawei.ros2_rmw_dsoftbus"\` | 生产环境 |
| 空字符串绕过 | \`"PKG_NAME": ""\` | 开发调试 |

**原理**: DSoftBus 源码 \`permission_entry.c:374\` 对空字符串跳过包名校验

### 3. Session 命名规范

**代码定义**:
```cpp
#define RMW_DSOFTBUS_PACKAGE_NAME "com.huawei.ros2_rmw_dsoftbus"
#define RMW_DSOFTBUS_SESSION_PREFIX "com.huawei.ros2_rmw_dsoftbus."
```

**生成规则**:
```
Session Name = <PREFIX><topic_name>_<pid>

示例:
- Topic: chatter, PID: 12345
- Session Name: com.huawei.ros2_rmw_dsoftbus.chatter_12345
```

**权限匹配**:
```json
{
  "SESSION_NAME": "com.huawei.ros2_rmw_dsoftbus.*",
  "REGEXP": "true"
}
```

### 4. AccessToken/NativeToken 处理

#### KaihongOS API Level 11 限制

AccessToken 库不导出 C 风格符号，无法直接调用：
```cpp
// 期望的 C API (不可用)
uint64_t GetAccessTokenId(NativeTokenInfoParams* params);

// 实际可用: C++ mangled symbols
OHOS::Security::AccessToken::AccessTokenKit::GetTokenTypeFlag()
```

#### ioctl 绕过方案

```cpp
bool try_init_native_token() {
    uint64_t token_id = 671463243;  // 默认 token
    
    // 从环境变量获取（可选）
    const char* env = std::getenv("RMW_DSOFTBUS_TOKEN_ID");
    if (env) token_id = strtoull(env, nullptr, 0);
    
    // 使用 ioctl 设置
    int fd = open("/dev/access_token_id", O_RDWR);
    if (fd < 0) return false;
    
    ioctl(fd, ACCESS_TOKENID_SET_TOKENID, &token_id);
    close(fd);
    return true;
}
```

**环境变量**:
```bash
export RMW_DSOFTBUS_TOKEN_ID=671437365      # 自定义 token
export RMW_DSOFTBUS_DISABLE_NATIVE_TOKEN=1  # 禁用 token 设置
```

---

## 部署流程

### 自动部署（推荐）

```bash
./scripts/deploy_softbus_permission.sh <DEVICE_ID> <CONFIG_FILE>
```

**脚本自动执行**:
1. 验证 JSON 格式（必须以 \`[\` 开头）
2. 备份原配置文件
3. 传输新配置
4. MD5 校验验证
5. 设置文件权限 (644)
6. 提示重启设备

### 手动部署

```bash
# 1. 挂载可写
hdc shell 'mount -o rw,remount /'

# 2. 备份
hdc shell 'cp /system/etc/communication/softbus/softbus_trans_permission.json \
               /system/etc/communication/softbus/softbus_trans_permission.json.bak'

# 3. 传输
hdc file send local_config.json /system/etc/communication/softbus/softbus_trans_permission.json

# 4. 权限
hdc shell 'chmod 644 /system/etc/communication/softbus/softbus_trans_permission.json'

# 5. 重启（必需！配置只在启动时加载）
hdc shell 'reboot'
```

---

## 错误码速查

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| \`-426442715\` | SOFTBUS_PERMISSION_DENIED | 配置格式错误或未重启 |
| \`-426442743\` | SOFTBUS_TRANS_PERMISSION_DENIED | JSON 解析失败 |
| \`-426115004\` | SOFTBUS_TRANS_SESSION_NAME_NO_EXIST | Listener 未启动或网络 ID 错误 |

### 错误排查流程

```bash
# 1. 检查配置格式（第一个字符必须是 [）
hdc shell 'head -1 /system/etc/communication/softbus/softbus_trans_permission.json'

# 2. 验证 JSON 语法
hdc shell 'cat /system/etc/communication/softbus/softbus_trans_permission.json' | python3 -m json.tool

# 3. 检查 softbus_server 进程
hdc shell 'ps -ef | grep softbus_server'
# 预期: dsoftbus 1110 1 ... softbus_server

# 4. 查看系统日志
hdc shell 'logcat | grep -i "softbus\|permission"'
```

---

## 权限校验机制

```
应用进程 (CreateSessionServer)
    ↓ IPC 调用
SoftBus Service (softbus_server)
    ↓ CheckTransPermission()
    ├── IPCSkeleton::GetCallingTokenID()     ← 获取调用者 token
    ├── AccessTokenKit::GetTokenTypeFlag()   ← 识别 token 类型
    ├── CalcPermType() → NATIVE_APP          ← 确定权限类型
    └── CheckPermissionEntry()               ← 匹配 JSON 配置
        ↓
    返回 SOFTBUS_OK 或 SOFTBUS_PERMISSION_DENIED
```

---

## 验证清单

### 部署前
- [ ] 配置文件是纯数组格式（以 \`[\` 开头）
- [ ] JSON 语法正确（无尾逗号、引号正确）
- [ ] PKG_NAME 与代码中定义一致

### 部署后
- [ ] **设备已重启**（最常遗忘！）
- [ ] softbus_server 进程运行中
- [ ] 配置文件权限为 644

### 运行时
- [ ] LD_LIBRARY_PATH 包含库路径
- [ ] 两设备在同一网段
- [ ] 网络 ID 为 64 字符

---

## 配置模板

| 模板 | 用途 | 文件 |
|------|------|------|
| verified | 真机验证通过的完整配置 | \`templates/verified.json\` |
| minimal | 仅 rmw_dsoftbus 最小配置 | \`templates/minimal.json\` |
| dev | 开发调试（完全开放） | \`templates/dev.json\` |

---

## 真机验证结果 (2026-01-19)

**测试环境**: 2 × rk3588s (KaihongOS API Level 11)

| 测试项 | 结果 |
|--------|------|
| CreateSessionServer | ✅ server_id=0 |
| OpenSession | ✅ session_id=1 |
| 消息传输 | ✅ 9/9 (100%) |
| 平均延迟 | 53.69 ms |

---

## 最佳实践

1. **使用部署脚本**: 避免手动操作遗漏步骤
2. **配置版本管理**: 保留验证通过的配置备份
3. **开发时用空 PKG_NAME**: 加快调试迭代
4. **生产时精确匹配**: 提高安全性
5. **重启后验证**: 确认 softbus_server 正常启动

---

## 参考

- DSoftBus 源码: \`permission_entry.c\`
- AccessToken 源码: \`accesstoken_kit.cpp\`
- 代码位置: \`src/native_token.cpp:184-260\`

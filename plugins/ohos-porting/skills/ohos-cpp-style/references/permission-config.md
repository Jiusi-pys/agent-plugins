# OpenHarmony 权限配置详解

本文档详细说明 OpenHarmony dsoftbus 三层权限架构的配置方法。

## 三层权限架构

```
┌─────────────────────────────────────────┐
│  Layer 1: SoftBus Transport Permission  │
│  /system/etc/communication/softbus/     │
│  softbus_trans_permission.json          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Layer 2: Native Token                  │
│  /system/etc/token_sync/*.json          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Layer 3: Init Service Configuration    │
│  /system/etc/init/*.cfg                 │
└─────────────────────────────────────────┘
```

## Layer 1: SoftBus Transport Permission

**文件**: `/system/etc/communication/softbus/softbus_trans_permission.json`

**完整示例**（`rmw_dsoftbus/config/softbus_trans_permission.json`）:

```json
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
```

**字段说明**:

- `SESSION_NAME`: Session 名称模式（支持正则）
  - 示例: `"com.rmw.discovery.*"` 匹配 `com.rmw.discovery.peer_sync`

- `REGEXP`: 是否启用正则匹配
  - `"true"`: 启用正则
  - `"false"`: 精确匹配

- `PKG_NAME`: 包名（必须与代码中的 pkgName 参数一致）

- `ACTIONS`: 允许的操作
  - `"create"`: 允许 CreateSessionServer
  - `"open"`: 允许 OpenSession
  - `"create,open"`: 两者都允许

**常见错误**:

❌ Session 名称不匹配正则:
```
代码中: "com.rmw.sync.discovery"
配置:   "SESSION_NAME": "com.rmw.discovery.*"
结果:   Permission denied
```

✅ 修复:
```json
"SESSION_NAME": "com.rmw.*"  // 更宽松的模式
```

## Layer 2: Native Token Configuration

**文件**: `/system/etc/token_sync/rmw_dsoftbus.json`

**完整示例**:

```json
{
    "processName": "rmw_discovery_daemon",
    "APL": "system_core",
    "tokenId": "537854093",
    "tokenAttr": "0",
    "dcaps": [],
    "permissions": [
        {
            "name": "ohos.permission.DISTRIBUTED_DATASYNC",
            "granted": true,
            "userCancellable": false
        },
        {
            "name": "ohos.permission.DISTRIBUTED_SOFTBUS_CENTER",
            "granted": true,
            "userCancellable": false
        },
        {
            "name": "ohos.permission.ACCESS_SERVICE_DM",
            "granted": true,
            "userCancellable": false
        }
    ],
    "nativeAcls": [
        "ohos.permission.ACCESS_SERVICE_DM"
    ]
}
```

**APL 级别**:

| APL | 数值 | 用途 |
|-----|-----|------|
| `system_core` | 3 | 系统核心服务 |
| `system_basic` | 2 | 系统应用 |
| `normal` | 1 | 普通应用 |

**代码中使用**（`rmw_dsoftbus/src/native_token.cpp`）:

```cpp
NativeTokenInfoParams params = {
    .permsNum = 3,
    .perms = perms,
    .processName = "rmw_discovery_daemon",
    .aplStr = "system_core"  // APL=3
};
```

## Layer 3: Init Service Configuration

**文件**: `/system/etc/init/rmw_discovery_daemon.cfg`

**完整示例**（`rmw_dsoftbus/system_service/init/rmw_discovery_daemon.cfg`）:

```json
{
    "services": [{
        "name": "rmw_discovery_daemon",
        "path": ["/system/bin/rmw_discovery_daemon"],
        "uid": "root",
        "gid": ["system"],
        "secon": "u:r:rmw_discovery_daemon:s0",
        "permission": [
            "ohos.permission.DISTRIBUTED_DATASYNC",
            "ohos.permission.DISTRIBUTED_SOFTBUS_CENTER"
        ],
        "permission_acls": [
            "DISTRIBUTED_DATASYNC",
            "DISTRIBUTED_SOFTBUS_CENTER"
        ],
        "start-mode": "boot",
        "bootphase": "system_init"
    }]
}
```

**关键字段**:

- `name`: 服务名称（与 processName 一致）
- `path`: 可执行文件路径
- `uid/gid`: 运行身份
- `secon`: SELinux 上下文（避免使用 su:s0 或 shell:s0）
- `permission_acls`: 权限 ACL

## dlopen 加载模式

**源文件**: `rmw_dsoftbus/test/softbus_dlopen_shim.cpp`

**完整实现**:

```cpp
#include <dlfcn.h>
#include <stdio.h>

// 函数指针类型定义
typedef uint64_t (*GetAccessTokenId_t)(NativeTokenInfoParams*);
typedef int (*SetSelfTokenID_t)(uint64_t);

static GetAccessTokenId_t _GetAccessTokenId = nullptr;
static SetSelfTokenID_t _SetSelfTokenID = nullptr;

__attribute__((constructor))
void load_nativetoken_api() {
    const char* lib_paths[] = {
        "/system/lib64/chipset-pub-sdk/libaccesstoken_sdk.z.so",
        "/system/lib64/platformsdk/libaccesstoken_sdk.z.so",
        "/system/lib64/libtokenid_sdk.z.so"
    };

    void* handle = nullptr;
    for (const char* path : lib_paths) {
        handle = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
        if (handle) {
            fprintf(stderr, "[NativeToken] ✅ Loaded: %s\n", path);
            break;
        }
    }

    if (!handle) {
        fprintf(stderr, "[NativeToken] ❌ No library found\n");
        for (const char* path : lib_paths) {
            fprintf(stderr, "  Tried: %s\n", path);
        }
        fprintf(stderr, "  Error: %s\n", dlerror());
        return;
    }

    _GetAccessTokenId = (GetAccessTokenId_t)dlsym(handle, "GetAccessTokenId");
    _SetSelfTokenID = (SetSelfTokenID_t)dlsym(handle, "SetSelfTokenID");

    if (!_GetAccessTokenId || !_SetSelfTokenID) {
        fprintf(stderr, "[NativeToken] ❌ Required symbols not found\n");
        dlclose(handle);
        return;
    }

    fprintf(stderr, "[NativeToken] ✅ All symbols loaded\n");
}

// 包装函数
uint64_t GetAccessTokenId(NativeTokenInfoParams* tokenInfo) {
    if (_GetAccessTokenId) {
        return _GetAccessTokenId(tokenInfo);
    }
    fprintf(stderr, "[NativeToken] ❌ API not loaded\n");
    return 0;
}

int SetSelfTokenID(uint64_t tokenId) {
    if (_SetSelfTokenID) {
        return _SetSelfTokenID(tokenId);
    }
    fprintf(stderr, "[NativeToken] ❌ API not loaded\n");
    return -1;
}
```

## 环境变量配置

**源文件**: `rmw_dsoftbus/src/native_token.cpp`

支持的环境变量:

| 变量 | 类型 | 用途 |
|------|------|------|
| `RMW_DSOFTBUS_DISABLE_NATIVE_TOKEN` | boolean | 禁用 native token |
| `RMW_DSOFTBUS_TOKEN_ID` | uint64 | 指定 token ID |

**实现**:

```cpp
bool is_truthy(const char* value) {
    if (!value || value[0] == '\0') return false;
    return strcmp(value, "1") == 0 ||
           strcmp(value, "true") == 0 ||
           strcmp(value, "TRUE") == 0;
}

bool try_init_native_token() {
    // 检查是否禁用
    const char* disable_env = std::getenv("RMW_DSOFTBUS_DISABLE_NATIVE_TOKEN");
    if (is_truthy(disable_env)) {
        return false;
    }

    // 解析 token ID
    uint64_t token_id = 0;
    const char* token_env = std::getenv("RMW_DSOFTBUS_TOKEN_ID");
    if (token_env && token_env[0] != '\0') {
        errno = 0;
        char* end = nullptr;
        unsigned long long parsed = strtoull(token_env, &end, 0);
        if (errno == 0 && end && *end == '\0') {
            token_id = static_cast<uint64_t>(parsed);
        } else {
            fprintf(stderr, "Invalid token ID: %s\n", token_env);
            return false;
        }
    }

    return InitializeNativeToken("my_process");
}
```

## 诊断流程

### 权限问题诊断

**现象**: `CreateSessionServer` 返回 -1 或 `OpenSession` 失败

**步骤**:

```bash
# 1. 检查 Layer 1 配置
hdc shell cat /system/etc/communication/softbus/softbus_trans_permission.json

# 验证:
# - SESSION_NAME 正则匹配你的 session 名称
# - PKG_NAME 匹配代码中的 pkgName 参数

# 2. 检查 Layer 2 配置
hdc shell ls /system/etc/token_sync/*.json

# 验证:
# - processName 与你的进程名一致
# - 包含所需的三个权限

# 3. 检查进程上下文
hdc shell ps -o label | grep my_app

# 验证:
# - ❌ 如果显示 u:r:su:s0 或 u:r:shell:s0 → 错误
# - ✅ 应显示自定义上下文: u:r:my_app:s0
```

## 最佳实践

1. **使用 dlopen 加载系统库** - 避免版本冲突
2. **多路径尝试** - 提高不同 OHOS 版本的兼容性
3. **详细日志** - 记录加载过程和失败原因
4. **环境变量覆盖** - 提供调试和测试灵活性
5. **线程安全初始化** - 使用 static mutex 保证单次初始化

## 参考文档

- `docs/02_dsoftbus诊断体系/dsoftbus权限问题快速修复指南.md`
- `docs/02_dsoftbus诊断体系/权限配置教程.md`
- `rmw_dsoftbus/src/native_token.cpp` - 参考实现

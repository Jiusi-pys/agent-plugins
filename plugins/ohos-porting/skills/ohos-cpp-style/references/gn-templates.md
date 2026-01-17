# OpenHarmony GN 构建模板参考

> 路径变量来自 `config.json`：
> - `${OHOS_ROOT}` = `paths.openharmony_source`
> - `${PREBUILTS}` = `paths.openharmony_prebuilts`
> - `${OUT_DIR}` = `paths.output_dir`

## 编译命令

```bash
# 生成构建脚本
${PREBUILTS}/gn gen ${OUT_DIR} \
    --args='target_cpu="arm64" target_os="ohos" is_clang=true'

# 编译特定目标
${PREBUILTS}/ninja -C ${OUT_DIR} //foundation/communication/dsoftbus:libsoftbus_core

# 查看编译参数
cat ${OUT_DIR}/args.gn
```

---

## 共享库模板

```gni
import("//build/ohos.gni")

ohos_shared_library("library_name") {
    sources = [
        "src/source1.cpp",
        "src/source2.cpp",
    ]

    include_dirs = [
        "include",
        "//third_party/xxx/include",
    ]

    cflags_cc = [
        "-std=c++17",
        "-fvisibility=default",
        "-Wall",
        "-Werror",
        "-g",
        "-O2",
    ]

    deps = [
        ":internal_target",
        "//path/to/dep:target",
    ]

    external_deps = [
        "hilog:libhilog",
        "c_utils:utils",
        "ipc:ipc_core",
        "samgr:samgr_proxy",
    ]

    part_name = "subsystem_component"
    subsystem_name = "subsystem"

    install_enable = true
    install_images = [ "system" ]
}
```

## 静态库模板

```gni
ohos_static_library("static_lib") {
    sources = [
        "src/impl.cpp",
    ]

    include_dirs = [
        "include",
    ]

    cflags_cc = [
        "-std=c++17",
        "-Wall",
    ]

    part_name = "subsystem_component"
}
```

## 可执行文件模板

```gni
ohos_executable("binary_name") {
    sources = [
        "main.cpp",
    ]

    include_dirs = [
        "include",
    ]

    deps = [
        ":mylib",
    ]

    external_deps = [
        "hilog:libhilog",
    ]

    part_name = "subsystem_component"

    install_enable = true
    install_images = [ "system" ]
    module_install_dir = "bin"
}
```

## 头文件库模板

```gni
ohos_source_set("headers") {
    sources = []

    public_configs = [ ":public_config" ]
}

config("public_config") {
    include_dirs = [
        "interfaces/innerkits",
    ]
}
```

## 测试模板

```gni
import("//build/test.gni")

ohos_unittest("module_test") {
    module_out_path = "subsystem/component"

    sources = [
        "test/unittest/test_main.cpp",
    ]

    deps = [
        ":mylib",
    ]

    external_deps = [
        "googletest:gtest_main",
    ]
}
```

---

## 常用 external_deps

| 组件 | external_deps |
|------|---------------|
| 日志 | `hilog:libhilog` |
| 工具类 | `c_utils:utils` |
| IPC | `ipc:ipc_core`, `ipc:ipc_single` |
| SAMGR | `samgr:samgr_proxy` |
| JSON | `json:nlohmann_json` |
| SQLite | `sqlite:sqlite` |
| dsoftbus | `dsoftbus:softbus_client` |
| EventHandler | `eventhandler:libeventhandler` |

---

## bundle.json 配置

```json
{
    "name": "@ohos/component_name",
    "description": "Component description",
    "version": "1.0",
    "license": "Apache-2.0",
    "component": {
        "name": "component_name",
        "subsystem": "subsystem_name",
        "syscap": [],
        "features": [],
        "adapted_system_type": [ "standard" ],
        "rom": "1024KB",
        "ram": "2048KB",
        "deps": {
            "components": [
                "hilog",
                "c_utils"
            ],
            "third_party": []
        },
        "build": {
            "group_type": {
                "base_group": [],
                "fwk_group": [],
                "service_group": [
                    "//path/to/component:target"
                ]
            },
            "inner_kits": [],
            "test": []
        }
    }
}
```

---

## 工具链路径

从 `config.json` 读取：

| 工具 | 配置路径 |
|------|---------|
| GCC-Linaro | `${PREBUILTS}/${toolchain.gcc_linaro}/` |
| Clang | `${PREBUILTS}/${toolchain.clang}/` |
| GN | `${PREBUILTS}/${toolchain.gn}` |
| Ninja | `${PREBUILTS}/${toolchain.ninja}` |

/*
 * Copyright (c) 2024-2025 [Your Organization]
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "module_name.h"

#include <cstdlib>
#include <cstring>

#include "securec.h"
#include "softbus_log.h"

namespace OHOS {
namespace ModuleName {

namespace {
constexpr int32_t DEFAULT_TIMEOUT = 5000;
constexpr const char *TAG = "ModuleName";
}  // namespace

class ModuleImpl {
public:
    ModuleImpl() = default;
    ~ModuleImpl() = default;

    int32_t Init(const ModuleConfig *config);
    void Deinit();
    int32_t Process(const uint8_t *data, uint32_t dataLen,
                    uint8_t *output, uint32_t *outputLen);

private:
    bool initialized_ = false;
    ModuleConfig config_ = {};
};

int32_t ModuleImpl::Init(const ModuleConfig *config)
{
    if (config == nullptr) {
        SOFTBUS_LOGE(TAG, "Invalid config");
        return MODULE_ERR_INVALID_PARAM;
    }

    if (memcpy_s(&config_, sizeof(config_), config, sizeof(*config)) != EOK) {
        SOFTBUS_LOGE(TAG, "memcpy_s failed");
        return MODULE_ERR_FAILED;
    }

    initialized_ = true;
    SOFTBUS_LOGI(TAG, "Module initialized: %s", config_.name);
    return MODULE_SUCCESS;
}

void ModuleImpl::Deinit()
{
    if (!initialized_) {
        return;
    }

    (void)memset_s(&config_, sizeof(config_), 0, sizeof(config_));
    initialized_ = false;
    SOFTBUS_LOGI(TAG, "Module deinitialized");
}

int32_t ModuleImpl::Process(const uint8_t *data, uint32_t dataLen,
                            uint8_t *output, uint32_t *outputLen)
{
    if (data == nullptr || output == nullptr || outputLen == nullptr) {
        SOFTBUS_LOGE(TAG, "Invalid parameters");
        return MODULE_ERR_INVALID_PARAM;
    }

    if (!initialized_) {
        SOFTBUS_LOGE(TAG, "Module not initialized");
        return MODULE_ERR_FAILED;
    }

    if (*outputLen < dataLen) {
        SOFTBUS_LOGE(TAG, "Output buffer too small");
        return MODULE_ERR_INVALID_PARAM;
    }

    if (memcpy_s(output, *outputLen, data, dataLen) != EOK) {
        SOFTBUS_LOGE(TAG, "memcpy_s failed");
        return MODULE_ERR_FAILED;
    }

    *outputLen = dataLen;
    return MODULE_SUCCESS;
}

// Global instance
static ModuleImpl g_moduleImpl;

}  // namespace ModuleName
}  // namespace OHOS

// C API implementations
int32_t ModuleInit(const ModuleConfig *config)
{
    return OHOS::ModuleName::g_moduleImpl.Init(config);
}

void ModuleDeinit(void)
{
    OHOS::ModuleName::g_moduleImpl.Deinit();
}

int32_t ModuleProcess(const uint8_t *data, uint32_t dataLen,
                      uint8_t *output, uint32_t *outputLen)
{
    return OHOS::ModuleName::g_moduleImpl.Process(data, dataLen, output, outputLen);
}

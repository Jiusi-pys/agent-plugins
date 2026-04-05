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

/**
 * @addtogroup ModuleName
 * @{
 *
 * @brief Brief description of the module.
 *
 * Detailed description of what this module provides.
 *
 * @since 1.0
 * @version 1.0
 */

/**
 * @file module_name.h
 *
 * @brief Brief description of this header file.
 *
 * @since 1.0
 * @version 1.0
 */

#ifndef MODULE_NAME_H
#define MODULE_NAME_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Maximum buffer size for data.
 *
 * @since 1.0
 * @version 1.0
 */
#define MAX_BUFFER_SIZE 1024

/**
 * @brief Error codes for the module.
 *
 * @since 1.0
 * @version 1.0
 */
typedef enum {
    /** Operation succeeded */
    MODULE_SUCCESS = 0,
    /** Invalid parameter */
    MODULE_ERR_INVALID_PARAM = -1,
    /** Out of memory */
    MODULE_ERR_NO_MEMORY = -2,
    /** Operation failed */
    MODULE_ERR_FAILED = -3,
} ModuleErrorCode;

/**
 * @brief Configuration structure.
 *
 * @since 1.0
 * @version 1.0
 */
typedef struct {
    /** Configuration name */
    char name[64];
    /** Configuration value */
    int32_t value;
    /** Enable flag */
    bool enabled;
} ModuleConfig;

/**
 * @brief Initialize the module.
 *
 * This function initializes the module with the given configuration.
 *
 * @param config Pointer to the configuration structure. Must not be NULL.
 * @return Returns {@link MODULE_SUCCESS} if successful;
 *         returns {@link MODULE_ERR_INVALID_PARAM} if config is NULL;
 *         returns {@link MODULE_ERR_FAILED} if initialization fails.
 * @since 1.0
 * @version 1.0
 */
int32_t ModuleInit(const ModuleConfig *config);

/**
 * @brief Deinitialize the module.
 *
 * @since 1.0
 * @version 1.0
 */
void ModuleDeinit(void);

/**
 * @brief Process data.
 *
 * @param data Input data buffer.
 * @param dataLen Length of input data.
 * @param output Output buffer.
 * @param outputLen Pointer to output buffer length. On input, contains buffer size;
 *                  on output, contains actual data length.
 * @return Returns {@link MODULE_SUCCESS} if successful;
 *         returns an error code otherwise.
 * @since 1.0
 * @version 1.0
 */
int32_t ModuleProcess(const uint8_t *data, uint32_t dataLen,
                      uint8_t *output, uint32_t *outputLen);

#ifdef __cplusplus
}
#endif

/** @} */

#endif /* MODULE_NAME_H */

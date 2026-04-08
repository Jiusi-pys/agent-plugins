/**
 * native_token.cpp - KaihongOS AccessToken ioctl 绕过方案
 * 
 * 背景:
 *   KaihongOS API Level 11 的 AccessToken 库不导出 C 风格符号，
 *   无法直接调用 GetAccessTokenId/SetSelfTokenID 等函数。
 *   本实现通过 ioctl 直接设置进程的 token_id，绕过 AccessToken 校验。
 * 
 * 使用方法:
 *   1. 在程序初始化时调用 try_init_native_token()
 *   2. 可选：设置环境变量 RMW_DSOFTBUS_TOKEN_ID 指定 token
 *   3. 可选：设置 RMW_DSOFTBUS_DISABLE_NATIVE_TOKEN=1 禁用
 * 
 * 验证状态: ✅ 2026-01-19 rk3588s KaihongOS API 11 真机验证通过
 */

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>

// ioctl 命令定义 (来自内核头文件)
#define ACCESS_TOKEN_ID_IOCTL_BASE 'A'
#define ACCESS_TOKENID_GET_TOKENID _IOR(ACCESS_TOKEN_ID_IOCTL_BASE, 1, uint64_t)
#define ACCESS_TOKENID_SET_TOKENID _IOW(ACCESS_TOKEN_ID_IOCTL_BASE, 2, uint64_t)

// 设备节点路径
#define ACCESS_TOKEN_DEV "/dev/access_token_id"

// 默认 token ID (经验证有效)
#define DEFAULT_TOKEN_ID 671463243ULL

/**
 * 尝试初始化 native token
 * 
 * @return true 成功, false 失败
 */
bool try_init_native_token() {
    // 检查是否禁用
    const char* disable_env = std::getenv("RMW_DSOFTBUS_DISABLE_NATIVE_TOKEN");
    if (disable_env && (strcmp(disable_env, "1") == 0 || strcmp(disable_env, "true") == 0)) {
        // 用户主动禁用
        return true;
    }
    
    // 确定要使用的 token ID
    uint64_t token_id = DEFAULT_TOKEN_ID;
    
    const char* token_env = std::getenv("RMW_DSOFTBUS_TOKEN_ID");
    if (token_env && token_env[0] != '\0') {
        char* endptr = nullptr;
        uint64_t parsed = strtoull(token_env, &endptr, 0);
        if (endptr != token_env && *endptr == '\0') {
            token_id = parsed;
        }
    }
    
    // 打开设备节点
    int fd = open(ACCESS_TOKEN_DEV, O_RDWR);
    if (fd < 0) {
        // 设备节点不存在或无权限
        // 在非 OHOS 系统上这是正常的
        return false;
    }
    
    // 设置 token ID
    int ret = ioctl(fd, ACCESS_TOKENID_SET_TOKENID, &token_id);
    close(fd);
    
    if (ret < 0) {
        return false;
    }
    
    return true;
}

/**
 * 获取当前进程的 token ID
 * 
 * @return token ID, 失败返回 0
 */
uint64_t get_current_token_id() {
    int fd = open(ACCESS_TOKEN_DEV, O_RDONLY);
    if (fd < 0) {
        return 0;
    }
    
    uint64_t token_id = 0;
    int ret = ioctl(fd, ACCESS_TOKENID_GET_TOKENID, &token_id);
    close(fd);
    
    if (ret < 0) {
        return 0;
    }
    
    return token_id;
}

/*
 * 使用示例:
 * 
 * int main() {
 *     // 初始化 token (在调用 DSoftBus API 之前)
 *     if (!try_init_native_token()) {
 *         // 非 OHOS 系统或初始化失败
 *         // 可以继续运行，但 DSoftBus 权限校验可能失败
 *     }
 *     
 *     // 现在可以调用 DSoftBus API
 *     // CreateSessionServer(...);
 *     // OpenSession(...);
 *     
 *     return 0;
 * }
 * 
 * 环境变量:
 *   RMW_DSOFTBUS_TOKEN_ID=671437365           # 使用指定 token ID
 *   RMW_DSOFTBUS_DISABLE_NATIVE_TOKEN=1       # 禁用 token 设置
 */

# 线程同步模式参考

本文档详细说明 OpenHarmony C++ 开发中的线程同步最佳实践。

## Meyer's Singleton 模式

**源文件**: `rmw_dsoftbus/src/session_manager.cpp:33-40`

### 基本实现

```cpp
class SessionManager {
public:
    // 线程安全的单例获取（C++11 保证）
    static SessionManager& instance() {
        static SessionManager instance;  // C++11 静态局部变量线程安全
        return instance;
    }

    // 禁用拷贝和赋值
    SessionManager(const SessionManager&) = delete;
    SessionManager& operator=(const SessionManager&) = delete;

private:
    // 私有构造函数
    SessionManager() = default;
    ~SessionManager() { shutdown(); }
};
```

### 为什么线程安全？

C++11 标准保证：
- 静态局部变量的初始化是线程安全的
- 如果多个线程同时第一次调用，只有一个线程会执行初始化
- 其他线程会等待初始化完成

### 与传统 Double-Checked Locking 比较

```cpp
// ❌ 传统 DCL（容易出错）
class Singleton {
    static Singleton* instance_;
    static std::mutex mutex_;

public:
    static Singleton* getInstance() {
        if (instance_ == nullptr) {  // 第一次检查（无锁）
            std::lock_guard<std::mutex> lock(mutex_);
            if (instance_ == nullptr) {  // 第二次检查（有锁）
                instance_ = new Singleton();
            }
        }
        return instance_;
    }
};

// ✅ Meyer's Singleton（更简洁、更安全）
class Singleton {
public:
    static Singleton& getInstance() {
        static Singleton instance;
        return instance;
    }
};
```

## Mutex 保护操作

**源文件**: `rmw_dsoftbus/src/session_manager.cpp`

### 幂等操作模式

```cpp
class SessionManager {
    std::mutex mutex_;
    bool initialized_{false};

public:
    bool initialize() {
        std::lock_guard<std::mutex> lock(mutex_);

        // 幂等检查（可以多次调用）
        if (initialized_) {
            return true;
        }

        fprintf(stderr, "[SessionManager] Initializing...\n");

        // 初始化逻辑
        if (!InitializeNativeToken("process_name")) {
            fprintf(stderr, "[SessionManager] ❌ Token init failed\n");
            return false;
        }

        initialized_ = true;
        fprintf(stderr, "[SessionManager] ✅ Initialized\n");
        return true;
    }

    void shutdown() {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!initialized_) {
            return;  // 幂等
        }

        // 清理资源
        for (auto& pair : sessions_) {
            CloseSession(pair.first);
        }
        sessions_.clear();

        initialized_ = false;
    }
};
```

**模式要点**:
- 使用 `std::lock_guard` 自动解锁
- 幂等检查（多次调用安全）
- 早返回（减少锁持有时间）

## Condition Variable 模式

**源文件**: `rmw_dsoftbus/include/rmw_dsoftbus/types.h`

### 生产者-消费者队列

```cpp
class MessageQueue {
    std::queue<MessageItem> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    size_t max_depth_{10};

public:
    // 生产者：添加消息
    void push(const MessageItem& msg) {
        {
            std::lock_guard<std::mutex> lock(mutex_);

            // 队列满则丢弃最旧消息
            if (queue_.size() >= max_depth_) {
                queue_.pop();
            }

            queue_.push(msg);
        }  // 锁在此处释放

        // 在锁外通知（减少锁竞争）
        cv_.notify_one();
    }

    // 消费者：等待消息（带超时）
    bool wait_and_pop(MessageItem* msg_out,
                     std::chrono::milliseconds timeout) {
        std::unique_lock<std::mutex> lock(mutex_);

        // 等待条件满足或超时
        bool has_msg = cv_.wait_for(lock, timeout, [this] {
            return !queue_.empty();
        });

        if (has_msg) {
            *msg_out = queue_.front();
            queue_.pop();
            return true;
        }

        return false;  // 超时
    }

    // 消费者：非阻塞尝试
    bool try_pop(MessageItem* msg_out) {
        std::lock_guard<std::mutex> lock(mutex_);

        if (queue_.empty()) {
            return false;
        }

        if (msg_out) {
            *msg_out = queue_.front();
        }
        queue_.pop();
        return true;
    }
};
```

**关键点**:
- `std::unique_lock` 用于条件变量（支持 unlock）
- Lambda 谓词检查条件（避免虚假唤醒）
- 锁外通知（`notify_one()` 在锁释放后）

## Lock Ordering（锁顺序）

**源文件**: `rmw_dsoftbus/src/discovery_manager.cpp:43-57`

### 为什么需要锁顺序？

多个锁时容易产生死锁：

```cpp
// ❌ 死锁示例
// Thread 1:
{
    std::lock_guard<std::mutex> lock1(mutex_a);
    std::lock_guard<std::mutex> lock2(mutex_b);  // 等待 Thread 2
}

// Thread 2:
{
    std::lock_guard<std::mutex> lock1(mutex_b);
    std::lock_guard<std::mutex> lock2(mutex_a);  // 等待 Thread 1
}
// → 死锁！
```

### 锁顺序文档模板

```cpp
// ============================================================
// Lock Ordering Documentation
// ============================================================
//
// 必须按此顺序获取锁，防止死锁：
//   1. GraphCache::mutex_      (最高优先级)
//   2. peer_mutex_
//   3. seq_mutex_
//   4. liveness_mutex_         (最低优先级)
//
// 规则：
// - 不要在持有高优先级锁时获取低优先级锁
// - 尽量缩短锁持有时间
// - 释放锁后再调用 GraphCache 方法（避免嵌套锁）
//
// ✅ 正确用法:
//   {
//       std::lock_guard<std::mutex> lock1(peer_mutex_);  // 高优先级
//       std::lock_guard<std::mutex> lock2(seq_mutex_);   // 低优先级
//       // ... 执行操作 ...
//   }
//
// ❌ 错误用法:
//   {
//       std::lock_guard<std::mutex> lock1(seq_mutex_);   // 先获取低优先级
//       std::lock_guard<std::mutex> lock2(peer_mutex_);  // 死锁风险！
//   }
// ============================================================
```

### 实际应用

```cpp
void DiscoveryManager::handlePeerUpdate(const std::string& peer_id) {
    // 按顺序获取锁
    std::lock_guard<std::mutex> peer_lock(peer_mutex_);     // 优先级 2
    std::lock_guard<std::mutex> seq_lock(seq_mutex_);       // 优先级 3

    // 安全：不会死锁
    peers_[peer_id].last_seen = get_timestamp();
    sequence_numbers_[peer_id]++;
}
```

## 原子操作

**源文件**: `rmw_dsoftbus/include/rmw_dsoftbus/types.h`

### 原子计数器

```cpp
#include <atomic>

// 全局 ID 生成器
inline uint64_t generate_unique_id() {
    static std::atomic<uint64_t> counter{0};
    return counter.fetch_add(1, std::memory_order_relaxed);
}
```

**内存顺序说明**:

| 顺序 | 用途 |
|------|------|
| `memory_order_relaxed` | 简单计数（最快） |
| `memory_order_acquire` | 读取同步点 |
| `memory_order_release` | 写入同步点 |
| `memory_order_seq_cst` | 顺序一致性（最安全但最慢）|

### 原子布尔标志

```cpp
class ServiceManager {
    std::atomic<bool> running_{false};

public:
    void start() {
        bool expected = false;
        // CAS (Compare-And-Swap)
        if (running_.compare_exchange_strong(expected, true)) {
            // 首次启动
            run_service_loop();
        } else {
            // 已经在运行
            fprintf(stderr, "Service already running\n");
        }
    }

    void stop() {
        running_.store(false, std::memory_order_release);
    }

    bool is_running() const {
        return running_.load(std::memory_order_acquire);
    }
};
```

## 最佳实践总结

1. **优先使用 Meyer's Singleton** - 而非手动 DCL
2. **使用 std::lock_guard** - 而非手动 lock/unlock
3. **文档化锁顺序** - 在多锁场景中必须
4. **缩短锁持有时间** - 只保护必要的代码
5. **锁外通知** - condition_variable 在锁外 notify
6. **幂等操作** - 允许多次调用不出错
7. **原子操作优先** - 简单计数器使用 atomic

## 参考资料

- `rmw_dsoftbus/src/session_manager.cpp` - 单例和 mutex 实现
- `rmw_dsoftbus/src/discovery_manager.cpp` - Lock ordering 文档
- `rmw_dsoftbus/include/rmw_dsoftbus/types.h` - 消息队列和原子操作

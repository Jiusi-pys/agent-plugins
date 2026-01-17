# CDR 序列化指南

本文档说明 Common Data Representation (CDR) 序列化在 rmw_dsoftbus 中的实现模式。

## CDR 概述

CDR 是 OMG 定义的数据表示标准，用于跨平台、跨语言的数据交换。

**特点**:
- 字节序独立（可在大端/小端系统间交换）
- 对齐规则明确（uint32_t 对齐到 4 字节边界）
- 结构紧凑（minimal overhead）

## Buffer 管理模式

**源文件**: `rmw_dsoftbus/include/rmw_dsoftbus/cdr_serializer.h:67-153`

### 双模式 Buffer

```cpp
class CdrBuffer {
protected:
    std::vector<uint8_t> buffer_;         // 序列化：拥有 buffer
    const uint8_t* external_data_{nullptr};  // 反序列化：外部数据
    size_t position_{0};
    size_t capacity_{0};
    bool owns_buffer_{false};

public:
    // 模式 1: 序列化（创建新 buffer）
    explicit CdrBuffer(size_t initial_capacity = 256)
        : buffer_(initial_capacity),
          position_(0),
          capacity_(initial_capacity),
          owns_buffer_(true) {}

    // 模式 2: 反序列化（包装外部数据）
    CdrBuffer(const uint8_t* data, size_t size)
        : external_data_(data),
          position_(0),
          capacity_(size),
          owns_buffer_(false) {}

    // 访问器
    const uint8_t* data() const {
        return owns_buffer_ ? buffer_.data() : external_data_;
    }

    uint8_t* mutable_data() {
        if (!owns_buffer_) return nullptr;  // 外部数据不可变
        return buffer_.data();
    }

    size_t size() const {
        return owns_buffer_ ? position_ : capacity_;
    }

    size_t remaining() const {
        return capacity_ - position_;
    }
};
```

**使用场景**:

```cpp
// 序列化：创建新 buffer
CdrSerializer serializer(256);
serializer.serialize(42);
serializer.serialize("hello");
const uint8_t* data = serializer.data();
size_t len = serializer.size();

// 反序列化：包装接收到的数据
CdrDeserializer deserializer(received_data, received_len);
uint32_t value;
std::string str;
deserializer.deserialize(&value);
deserializer.deserialize(&str);
```

### 容量管理（倍增策略）

```cpp
bool ensure_capacity(size_t additional) {
    if (!owns_buffer_) return false;

    if (position_ + additional > capacity_) {
        // 倍增策略：减少重新分配次数
        size_t new_cap = capacity_ * 2;

        // 如果倍增不够，继续倍增
        while (new_cap < position_ + additional) {
            new_cap *= 2;
        }

        buffer_.resize(new_cap);
        capacity_ = new_cap;
    }
    return true;
}
```

**为什么倍增**:
- 减少 `vector::resize()` 调用次数
- 时间复杂度：O(log n) 次重新分配
- 空间代价：最多浪费 50% 容量

## 对齐计算

### 位操作技巧

```cpp
// CDR 对齐计算（位操作）
static size_t align(size_t pos, size_t alignment) {
    return (pos + alignment - 1) & ~(alignment - 1);
}
```

**原理**:

```
对齐到 4 字节:
pos = 5
alignment = 4

步骤:
1. pos + alignment - 1 = 5 + 4 - 1 = 8
2. ~(alignment - 1) = ~3 = 0xFFFFFFFC (binary: ...11111100)
3. 8 & 0xFFFFFFFC = 8

结果: 5 → 8（对齐到下一个 4 的倍数）
```

**示例**:

```
align(0, 4) = 0
align(1, 4) = 4
align(4, 4) = 4
align(5, 4) = 8
align(7, 4) = 8
align(8, 4) = 8
```

### 对齐规则

| 类型 | 大小 | 对齐 |
|------|------|------|
| `char`, `int8_t` | 1 | 1 |
| `int16_t` | 2 | 2 |
| `int32_t`, `float` | 4 | 4 |
| `int64_t`, `double` | 8 | 8 |
| `string` | N+4 | 4（长度字段）|

### 对齐填充

```cpp
void align_to(size_t alignment) {
    size_t aligned = align(position_, alignment);

    if (aligned > position_) {
        // 需要填充
        ensure_capacity(aligned - position_);

        // 填充字节设为 0
        memset(buffer_.data() + position_, 0, aligned - position_);
        position_ = aligned;
    }
}
```

## 字节序处理

**源文件**: `rmw_dsoftbus/include/rmw_dsoftbus/cdr_serializer.h:206-220`

### 运行时字节序检测

```cpp
inline bool is_little_endian() {
    uint16_t test = 0x0001;
    return *reinterpret_cast<uint8_t*>(&test) == 0x01;
}
```

**原理**:

```
大端系统:
  test = 0x0001
  内存: [00] [01]
  *ptr = 0x00

小端系统:
  test = 0x0001
  内存: [01] [00]
  *ptr = 0x01
```

### 序列化（考虑字节序）

```cpp
class CdrSerializer : public CdrBuffer {
    bool little_endian_;

public:
    CdrSerializer() : CdrBuffer(), little_endian_(is_little_endian()) {}

    void serialize(uint32_t value) {
        align_to(4);  // 4 字节对齐
        ensure_capacity(4);

        if (little_endian_) {
            // 小端字节序
            buffer_[position_++] = value & 0xFF;
            buffer_[position_++] = (value >> 8) & 0xFF;
            buffer_[position_++] = (value >> 16) & 0xFF;
            buffer_[position_++] = (value >> 24) & 0xFF;
        } else {
            // 大端字节序
            buffer_[position_++] = (value >> 24) & 0xFF;
            buffer_[position_++] = (value >> 16) & 0xFF;
            buffer_[position_++] = (value >> 8) & 0xFF;
            buffer_[position_++] = value & 0xFF;
        }
    }

    void serialize(uint64_t value) {
        align_to(8);  // 8 字节对齐
        ensure_capacity(8);

        for (int i = 0; i < 8; ++i) {
            int shift = little_endian_ ? (i * 8) : ((7 - i) * 8);
            buffer_[position_++] = (value >> shift) & 0xFF;
        }
    }
};
```

### 反序列化（考虑字节序）

```cpp
class CdrDeserializer : public CdrBuffer {
    bool little_endian_;

public:
    CdrDeserializer(const uint8_t* data, size_t size)
        : CdrBuffer(data, size),
          little_endian_(is_little_endian()) {}

    bool deserialize(uint32_t* value_out) {
        if (!value_out) return false;

        // 对齐到 4 字节
        size_t aligned = align(position_, 4);
        if (aligned + 4 > capacity_) {
            return false;  // 数据不足
        }
        position_ = aligned;

        const uint8_t* ptr = external_data_ + position_;

        if (little_endian_) {
            *value_out = static_cast<uint32_t>(ptr[0]) |
                        (static_cast<uint32_t>(ptr[1]) << 8) |
                        (static_cast<uint32_t>(ptr[2]) << 16) |
                        (static_cast<uint32_t>(ptr[3]) << 24);
        } else {
            *value_out = (static_cast<uint32_t>(ptr[0]) << 24) |
                        (static_cast<uint32_t>(ptr[1]) << 16) |
                        (static_cast<uint32_t>(ptr[2]) << 8) |
                        static_cast<uint32_t>(ptr[3]);
        }

        position_ += 4;
        return true;
    }
};
```

## 字符串序列化

### 带长度前缀的字符串

```cpp
void serialize(const std::string& str) {
    // 1. 序列化长度（包含 null 终止符）
    uint32_t length = static_cast<uint32_t>(str.length() + 1);
    serialize(length);  // 调用 serialize(uint32_t)

    // 2. 序列化字符（无需对齐）
    ensure_capacity(length);
    memcpy(buffer_.data() + position_, str.c_str(), length);
    position_ += length;
}

bool deserialize(std::string* str_out) {
    if (!str_out) return false;

    // 1. 反序列化长度
    uint32_t length = 0;
    if (!deserialize(&length)) {
        return false;
    }

    // 2. 边界检查
    if (position_ + length > capacity_) {
        return false;
    }

    // 3. 提取字符串（不包含 null 终止符）
    const char* str_ptr = reinterpret_cast<const char*>(external_data_ + position_);
    str_out->assign(str_ptr, length - 1);

    position_ += length;
    return true;
}
```

## 复合类型序列化

### 结构体示例

```cpp
struct Point {
    float x;
    float y;
    float z;
};

void serialize(const Point& point) {
    serialize(point.x);  // 对齐到 4
    serialize(point.y);  // 已对齐
    serialize(point.z);  // 已对齐
}

bool deserialize(Point* point_out) {
    return deserialize(&point_out->x) &&
           deserialize(&point_out->y) &&
           deserialize(&point_out->z);
}
```

### 数组序列化

```cpp
template<typename T>
void serialize_array(const std::vector<T>& vec) {
    // 1. 序列化元素数量
    serialize(static_cast<uint32_t>(vec.size()));

    // 2. 序列化每个元素
    for (const T& item : vec) {
        serialize(item);
    }
}

template<typename T>
bool deserialize_array(std::vector<T>* vec_out) {
    // 1. 反序列化数量
    uint32_t count = 0;
    if (!deserialize(&count)) {
        return false;
    }

    // 2. 预分配容量
    vec_out->clear();
    vec_out->reserve(count);

    // 3. 反序列化元素
    for (uint32_t i = 0; i < count; ++i) {
        T item;
        if (!deserialize(&item)) {
            return false;
        }
        vec_out->push_back(item);
    }

    return true;
}
```

## 性能优化

### 1. 预分配容量

```cpp
// ✅ 好：预分配
CdrSerializer serializer(1024);  // 预分配 1KB
for (int i = 0; i < 100; ++i) {
    serializer.serialize(i);  // 无重新分配
}

// ❌ 差：频繁重新分配
CdrSerializer serializer(16);    // 仅 16 字节
for (int i = 0; i < 100; ++i) {
    serializer.serialize(i);  // 多次倍增
}
```

### 2. 检测时初始化字节序

```cpp
class CdrSerializer {
    bool little_endian_;  // 成员变量，只检测一次

public:
    CdrSerializer()
        : CdrBuffer(),
          little_endian_(is_little_endian()) {}  // 构造时检测

    void serialize(uint32_t value) {
        // 使用缓存的字节序，不再检测
        if (little_endian_) {
            // ...
        }
    }
};
```

### 3. 批量操作

```cpp
// ✅ 好：批量 memcpy
void serialize_bytes(const uint8_t* data, size_t len) {
    ensure_capacity(len);
    memcpy(buffer_.data() + position_, data, len);
    position_ += len;
}

// ❌ 差：逐字节复制
for (size_t i = 0; i < len; ++i) {
    buffer_[position_++] = data[i];
}
```

## 错误处理

### 边界检查

```cpp
bool deserialize(uint32_t* value_out) {
    if (!value_out) {
        fprintf(stderr, "[CDR] ❌ Null output pointer\n");
        return false;
    }

    size_t aligned = align(position_, 4);
    if (aligned + 4 > capacity_) {
        fprintf(stderr, "[CDR] ❌ Buffer underrun: need %zu, have %zu\n",
                aligned + 4, capacity_);
        return false;
    }

    // ... 反序列化逻辑 ...
    return true;
}
```

### 版本兼容性

```cpp
struct MessageHeader {
    uint8_t magic[4];     // "CDR\0"
    uint8_t version;      // 序列化版本
    uint8_t endianness;   // 0=big, 1=little
    uint16_t reserved;
};

bool deserialize_header(MessageHeader* header) {
    if (remaining() < sizeof(MessageHeader)) {
        return false;
    }

    memcpy(header, data() + position_, sizeof(MessageHeader));
    position_ += sizeof(MessageHeader);

    // 验证魔数
    if (memcmp(header->magic, "CDR\0", 4) != 0) {
        fprintf(stderr, "[CDR] ❌ Invalid magic number\n");
        return false;
    }

    // 检查版本
    if (header->version > CURRENT_VERSION) {
        fprintf(stderr, "[CDR] ⚠️  Future version: %u\n", header->version);
    }

    return true;
}
```

## 完整示例

### 复杂消息序列化

```cpp
struct DiscoveryMessage {
    uint64_t gid;
    std::string topic_name;
    std::string type_name;
    uint32_t qos_reliability;
    std::vector<std::string> partitions;
};

void serialize(const DiscoveryMessage& msg) {
    // GID (8 字节)
    serialize(msg.gid);

    // Topic 名称（字符串）
    serialize(msg.topic_name);

    // Type 名称（字符串）
    serialize(msg.type_name);

    // QoS（4 字节）
    serialize(msg.qos_reliability);

    // Partitions（字符串数组）
    serialize(static_cast<uint32_t>(msg.partitions.size()));
    for (const auto& partition : msg.partitions) {
        serialize(partition);
    }
}

bool deserialize(DiscoveryMessage* msg_out) {
    // GID
    if (!deserialize(&msg_out->gid)) return false;

    // Topic 名称
    if (!deserialize(&msg_out->topic_name)) return false;

    // Type 名称
    if (!deserialize(&msg_out->type_name)) return false;

    // QoS
    if (!deserialize(&msg_out->qos_reliability)) return false;

    // Partitions
    uint32_t partition_count = 0;
    if (!deserialize(&partition_count)) return false;

    msg_out->partitions.clear();
    msg_out->partitions.reserve(partition_count);

    for (uint32_t i = 0; i < partition_count; ++i) {
        std::string partition;
        if (!deserialize(&partition)) return false;
        msg_out->partitions.push_back(partition);
    }

    return true;
}
```

## CDR 对齐常量

```cpp
constexpr size_t CDR_ALIGN_1 = 1;   // char, int8_t, uint8_t
constexpr size_t CDR_ALIGN_2 = 2;   // int16_t, uint16_t
constexpr size_t CDR_ALIGN_4 = 4;   // int32_t, uint32_t, float
constexpr size_t CDR_ALIGN_8 = 8;   // int64_t, uint64_t, double
```

## 调试技巧

### Hex Dump

```cpp
void print_hex_dump(const uint8_t* data, size_t len) {
    fprintf(stderr, "Hex dump (%zu bytes):\n", len);
    for (size_t i = 0; i < len; ++i) {
        if (i % 16 == 0) {
            fprintf(stderr, "%04zx: ", i);
        }
        fprintf(stderr, "%02x ", data[i]);
        if (i % 16 == 15) {
            fprintf(stderr, "\n");
        }
    }
    fprintf(stderr, "\n");
}
```

### 序列化验证

```cpp
// 序列化
CdrSerializer ser;
ser.serialize(42);
ser.serialize("hello");

// 验证：反序列化应该得到相同值
CdrDeserializer deser(ser.data(), ser.size());
uint32_t value;
std::string str;

assert(deser.deserialize(&value) && value == 42);
assert(deser.deserialize(&str) && str == "hello");
```

## 参考资料

- `rmw_dsoftbus/include/rmw_dsoftbus/cdr_serializer.h` - 完整实现
- `rmw_dsoftbus/src/cdr_serializer.cpp` - 实现细节
- OMG CDR Specification - 官方标准

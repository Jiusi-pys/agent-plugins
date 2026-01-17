# Commit Message 规范

## 格式

```
[Track/Stage/Phase] 简短描述（50 字符内）(type)

详细说明（可选，72 字符换行）：
- 改动点 1
- 改动点 2

Phase: <phase-name>
Stage: <stage-name>
Track: <track-name>

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Type 说明

| Type | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | 添加 Publisher 实现 |
| `fix` | Bug 修复 | 修复内存泄漏 |
| `refactor` | 重构 | 重构 Session 管理 |
| `docs` | 文档 | 更新 API 文档 |
| `test` | 测试 | 添加单元测试 |
| `build` | 构建 | 更新 BUILD.gn |
| `perf` | 性能 | 优化序列化速度 |

## 示例

```
[track1/stage2/phase1] 实现 Publisher API (feat)

添加 Publisher 的创建、发布和销毁功能。

改动：
- 新增 src/rmw_publisher.cpp
- 新增 include/rmw_dsoftbus/publisher.h
- 实现 rmw_create_publisher()
- 实现 rmw_publish()

Phase: publisher-create
Stage: pubsub-implementation
Track: rmw-dsoftbus-development

Co-Authored-By: Claude <noreply@anthropic.com>
```

# 阅读器 US 四项失败已关闭

后续用户授权修复已完成，阅读器提交为 [`b134b73`](https://github.com/Jiusi-pys/ebooks/commit/b134b73d3d2acec6f3061be62b75eb7256819798)，已推送 `codex/shared-core-delivery-automation`。原来的 [49 通过 / 4 失败记录](2026-10-11-reader-us-integration-validation.md) 保留为历史红灯证据。

- 先在 US 重新运行原 53 项，再次得到 49 通过、4 失败。
- 新增两项 Rust 路由和两项 Hono/原生差分回归，在旧实现上验证缺失 updatedAt 被错误接受。
- Mirror 笔记创建/更新复用已有字段校验；合法回执夹具补齐时间，明确验证 200 / 200 / 409；快照 begin/finish 使用现代墙钟，保留逻辑时钟及回滚、冲突断言。没有修改历史迁移或 MySQL 严格模式。
- 修复后 US **55/55 通过，0 失败、0 跳过**（32.69 秒），含原 53 项与新增两项。实际 MySQL/Hono↔原生 SQLite 同步的 Rust 子测试通过。
- 本地 Web check/lint/build、703 项常规测试、Linux Rust service 86 项默认测试、15 项部署测试通过。本地 55 项 Web 环境跳过已由 US 补齐；其余四项显式 Rust 外部环境测试未运行，详见阅读器记录。
- 临时库、账号、容器、服务和上传文件已清理，生产容器 ID、镜像、启动时间及状态前后一致。

完整命令、先失败后通过的原始 JSON、二进制和源码 SHA-256 见阅读器的 [TDD 验收记录](https://github.com/Jiusi-pys/ebooks/blob/b134b73d3d2acec6f3061be62b75eb7256819798/docs/reviews/2026-10-11-us-integration-fixes.md)。本次提交只包含后端修复、相关测试和文档；已有 EPUB 前端适配仍为本地未提交改动，未部署生产，也未测试真实账号 UI。

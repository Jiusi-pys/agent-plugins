# us 服务器：此前跳过的 53 项集成测试

> 后续 [插件仓库 US 全仓回归](2026-10-11-plugin-us-full-suite.md) 已完成，但本报告属于独立的阅读器仓库；下述 49 通过、4 失败仍为该次实际结果。本轮插件测试与推送未修复或重跑这些失败。

2026-10-11，用户授权通过 SSH 在 `us.jiusi.org` 实测。当前阅读器基线为 `2ffca98c6b64e6f0a21c89ad24c06b96c2114330`，包含本地未提交的 EPUB 适配改动。**53 项全部执行：49 通过、4 失败、0 跳过；8 文件中 6 通过、2 失败。** 应用源码、原有测试和生产部署均未修改；失败交给用户修复。

## 执行范围与环境

- us：Linux x86_64、MySQL 8.4.11、临时 Node 22.23.2 容器，Vitest 4.1.11、Vite 7.3.0。保留 MySQL 严格模式。
- 当前工作树的 616 个源码文件按 SHA-256 在服务器逐个校验，文件清单保存在本地 `.local/reader-adaptation/us-tests/evidence/source-manifest.json`。依赖子集沿用当前 `app/package-lock.json` 中的精确版本及传递依赖。
- 使用新建的隔离 MySQL 数据库和临时测试账号，账号只拥有测试库及迁移夹具命名空间的权限。正常业务库未作为测试输入。迁移准备实际执行全部 16 个迁移。
- 原生 REST 服务使用独立 SQLite 工作区、合成 token、服务器 loopback 临时端口；Hono 旧接口通过原测试的 `v1.request` 在 us 进程内执行。
- us 根分区原仅余约 281 MiB，未下载镜像或在服务器编译 Rust。当前源码在本机 Linux Docker 完成 `cargo build --locked --release -p shufang-service` 和 `cargo test --locked --release -p shufang-service --test old_v2 --no-run`，生成程序随后上传并在 us 实际运行。
- `native.mysql.test.ts` 的 `CARGO` 指向参数严格检查的执行器，运行真正的当前源码 Linux `old_v2` 测试二进制；未模拟 Cargo 成功、同步服务或任何断言。Rust 子测试结果为 1 passed / 0 failed / 0 ignored，实际完成 us 上 MySQL/Hono 与原生 SQLite 的双向 HTTP 同步及跨块原文件传输。
- 原生服务 SHA-256：`0b2f580541edd1dfbeb0ec10aaf7ef909916ed08695265bece48072225bd9d85b`；Rust 测试程序 SHA-256：`c7fc8de2e9584aabf8accdcc71c41d833eda7cfbd8fb33b7033c19ae3d4ee96fb`。

从 `app/` 执行：

```sh
node node_modules/vitest/vitest.mjs run \
  api/library.mysql.integration.test.ts \
  api/v1.mysql.integration.test.ts \
  api/v1.native-differential.test.ts \
  api/lib/migration-mysql.integration.test.ts \
  api/lib/rust-migration.mysql.integration.test.ts \
  api/sync/native.mysql.test.ts \
  api/sync/snapshots.mysql.test.ts \
  api/sync/store.mysql.test.ts \
  --no-file-parallelism --maxWorkers 1 --pool=threads \
  --testTimeout 120000 --hookTimeout 120000 \
  --reporter=verbose --reporter=json --outputFile.json=/work/results.json
```

启用 `RUN_MYSQL_INTEGRATION=1`、`RUN_NATIVE_DIFFERENTIAL=1`、`RUN_MYSQL_MIGRATION_FIXTURE=1`、`RUN_RUST_MYSQL_MIGRATIONS=1`；配置独立 `DATABASE_URL`、`SYNC_TEST_DATABASE_URL`、`NATIVE_SYNC_TEST_DATABASE_URL`、`NATIVE_TEST_ORIGIN`、`NATIVE_TEST_TOKEN` 和 `OPEN_API_KEY`。凭据未写入本报告或版本库，测试后删除临时凭据文件及账号。

| 测试文件（阅读器 `app/`） | 通过 | 失败 | 跳过 |
| --- | ---: | ---: | ---: |
| `api/library.mysql.integration.test.ts` | 3 | 0 | 0 |
| `api/v1.mysql.integration.test.ts` | 6 | 0 | 0 |
| `api/v1.native-differential.test.ts` | 29 | 1 | 0 |
| `api/lib/migration-mysql.integration.test.ts` | 1 | 0 | 0 |
| `api/lib/rust-migration.mysql.integration.test.ts` | 3 | 0 | 0 |
| `api/sync/native.mysql.test.ts` | 1 | 0 | 0 |
| `api/sync/snapshots.mysql.test.ts` | 0 | 3 | 0 |
| `api/sync/store.mysql.test.ts` | 6 | 0 | 0 |
| 合计 | 49 | 4 | 0 |

原测试运行耗时 32.05 秒、退出码 1。首次环境准备遗漏 `tsconfig.server.json`，该次为 0 tests 的加载失败；补全原配置后才得到上述 53 项结果，未计入应用缺陷。原始记录保存在 `attempt-1/`。

## 两个需处理的问题

### 1. 原生 Mirror 接口未遵守笔记事件的必填字段校验

位置：阅读器 `base/crates/service/src/legacy.rs:892`；旧接口契约见 `app/api/lib/mirror-event.ts:280`；失败测试见 `app/api/v1.native-differential.test.ts:303`。

发送 `note.created`，`data` 为 `{extId, title, content}`、缺少 `updatedAt`。Hono 返回 `400 invalid_event_data`，issue 明确指向 `updatedAt`；原生默认 Mirror 接口返回 `200 {ok:true, mirrored:true}`。原生事件标准化只在 `SyncEntities` 分支调用，Mirror 分支跳过该校验。

应使 Mirror 事件必填字段和旧接口一致，并为缺少时间字段保留拒绝回归。原回执测试的夹具本身也缺少 `updatedAt`，所以它在第一次请求就失败，尚未覆盖后续重放。另以完整事件在 us 验证，首次提交、精确重放、不同载荷重放两端状态码分别一致为 **200 / 200 / 409**；不能将当前失败误报成已证实的重放去重故障。原始响应见诊断 JSON。

### 2. 三项快照测试使用 MySQL TIMESTAMP 无法接受的夹具时间

位置：阅读器 `app/api/sync/snapshots.mysql.test.ts:56`、`:123`、`:149`；写入位置 `app/api/sync/snapshots.ts:69`、`:82`；列定义 `app/db/migrations/0014_workspace_sync.sql:11`。

这三处向 `IncomingSnapshots.begin` 传入 `now=1`，经 `new Date(now)` 写为 `1970-01-01 00:00:00.001`。真实 MySQL 的 `created_at TIMESTAMP` 在严格模式下报 `ER_TRUNCATED_WRONG_VALUE / 1292`，测试均在 staging 之前中止，恢复、原子合并和游标冲突断言未执行。

应将夹具墙钟替换为 MySQL 可表示的现代时间，相关完成时间使用相对偏移，保留逻辑操作时钟的原语义。无需通过关闭严格模式或改写历史迁移来掩盖夹具问题。独立诊断保持同一 SQL_MODE，用当前时间实际完成空快照的 begin / stage / finish 和游标验证；这不等于原三项完整测试已通过。

## 证据、清理与边界

- [原 53 项 JSON 结果](2026-10-11-reader-us-integration-results.json)
- [诊断响应与 MySQL 类型/模式](2026-10-11-reader-us-diagnostics.json)
- [执行与清理前后状态](2026-10-11-reader-us-execution.json)
- 本地原始日志、逐文件哈希、Linux 构建日志、执行器及诊断夹具：`.local/reader-adaptation/us-tests/`。额外诊断为独立的 **3 项通过**，不能据此把原结果改成 53 项通过。

每次运行后删除当次测试数据库及账号；迁移夹具自行清理，前后数据库名称集合一致。临时 Node 容器、原生服务进程、工作区、依赖和上传文件均已清理。三个原生产容器的 ID、镜像、启动时间、运行状态逐项前后一致，没有重启或部署替换。清理后根分区可用约 278 MiB。

这次补跑的是此前 53 项跳过测试；没有重跑此前全部 703 项本地通过测试，也没有开展生产账号 UI 或跨设备 EPUB 图片同步验收。失败来自既有后端契约/测试夹具，不能据此推断为本次 EPUB 前端改动引入。

# 插件仓库 US 全仓回归与发布检查

2026-10-11，在 `us.jiusi.org` 对 `agent-plugins-openai` 当前 `openai` 工作树运行全部自动发现的测试：**287 项，279 通过、8 跳过、0 失败、0 错误**。随后在 Windows 用真实 Calibre/Pandoc 补跑这 8 项，**8/8 通过**，其中转换矩阵为 **90/90 个方向**。在本次测试范围内未发现新增回归；不能把两台机器的结果合称为 Linux 287 项全部通过。

## 范围与复现

测试快照基于提交 `1f3f42e9be4e2906910e717b9d02caf5a8dccf14`，包括本次 EPUB 转换、图注/注释编排、翻译器依赖适配和 WeRead 修复的未提交源码及测试。通过 `git ls-files --cached --others --exclude-standard` 收集 169 个文件，服务器运行前、运行后均校验 SHA-256 一致。随后仅更新文档与验收证据，源码和测试未再修改；[快照清单](2026-10-11-plugin-us-source-manifest.json) 中的旧文档哈希不是提交后文档的哈希。

自动枚举仓库所有 `test_*.py` 所在目录，共 22 个测试文件、5 个测试目录；各目录独立 Python 进程运行，避免同名测试模块相互覆盖。`agentic-review` 和保留的 `multi-review` 没有自动发现的测试。没有把 `create_demo.py` 或需要实际 Codex 安装的 `smoke_install.py` 算入 unittest。

```sh
python3 -B -m unittest discover -s plugins/book-translator/tests -v
python3 -B -m unittest discover -s plugins/epub-editor/tests -v
python3 -B -m unittest discover -s plugins/fenbi-exporter/tests -v
python3 -B -m unittest discover -s plugins/video-text-extract/skills/video-text-extract/tests -v
python3 -B -m unittest discover -s plugins/weread-exporter/tests -v
```

执行器使用相同的 `unittest.defaultTestLoader.discover`，额外保存每项跳过原因、错误、退出码和耗时，详见 [US 原始汇总 JSON](2026-10-11-plugin-us-full-suite-results.json)。未使用 mock 替代浏览器进程；WeRead 的 19 项包含真实 Chromium 离线页面回归。测试中针对账号网站、模型服务或下载的 mock 仍为原有测试设计，不等于线上服务验收。

## US 结果

环境：Ubuntu 24.04.4、Linux 6.8.0-107、Python 3.12.3、lxml 6.1.3、Pillow 12.3.0、Playwright 1.63.0、Chromium Headless Shell 153.0.8010.12。

| 插件 | 发现 | 通过 | 跳过 | 失败/错误 | 秒 |
| --- | ---: | ---: | ---: | ---: | ---: |
| book-translator | 64 | 64 | 0 | 0 | 10.214 |
| epub-editor | 141 | 133 | 8 | 0 | 2.319 |
| fenbi-exporter | 34 | 34 | 0 | 0 | 13.097 |
| video-text-extract | 29 | 29 | 0 | 0 | 0.957 |
| weread-exporter | 19 | 19 | 0 | 0 | 38.888 |
| 合计 | 287 | 279 | 8 | 0 | 65.475 |

所有测试目录退出码均为 0。运行时未修改生产应用、账号或数据库；三个原生产容器的 ID、启动时间、运行状态前后一致。

## 仍在 US 跳过的 8 项

共同的测试跳过条件是未设置 `TEST_CALIBRE` 和 `TEST_PANDOC`。US 未安装这两个引擎，根分区仅剩约 279 MiB，临时依赖加 Chromium 已占 `/dev/shm` 约 450 MiB；未继续在此生产服务器安装大体积转换工具。未删除或放宽测试断言。

以下前七项位于 `plugins/epub-editor/tests/test_conversion_integration.py`，最后一项位于 `test_reading_pipeline_integration.py`：

| 测试方法 | 验证内容 | 本机补跑 |
| --- | --- | --- |
| `test_all_90_cross_format_directions_read_back` | 十格式 90 个方向、读回正文和顺序 | 通过 |
| `test_container_formats_keep_the_referenced_image_on_readback` | 容器格式保留被引用图片 | 通过 |
| `test_document_note_links_point_to_content_after_round_trip` | 往返转换后注释链接及内容 | 通过 |
| `test_docx_cannot_read_external_synthetic_file` | DOCX 包外文件读取拒绝 | 通过 |
| `test_explicit_gb18030_text_is_decoded_without_replacement` | GB18030 明确解码 | 通过 |
| `test_images_and_non_spine_notes_survive_pandoc_outputs` | 图片与非 spine 注释保留 | 通过 |
| `test_remote_images_and_fb2_css_do_not_make_http_requests_or_publish` | 远程资源零请求且不发布输出 | 通过 |
| `test_html_to_standard_epub_and_export_preserves_image_notes_and_captions` | HTML→EPUB→标准编排→导出保留图片、注释和图注 | 通过 |

本机补跑为 Python 3.13.9、Calibre 9.16.0、Pandoc 3.8，8 项用时 59.793 秒，退出码 0。设置两个引擎环境变量后执行：

```text
python -B -m unittest discover -s plugins/epub-editor/tests -p '*integration.py' -v
```

[本轮转换矩阵 JSON](2026-10-11-plugin-release-conversion-matrix.json) 保存 90 个方向。该补跑证明当前源码在本机引擎下通过，不代替 Linux 实际转换兼容性验证。

## 与此前阅读器 53 项的区别

此前的 53 项属于另一个仓库 `Jiusi-pys/ebooks`，不是这里的 287 项。它们已在 US 执行过，结果为 **49 通过、4 失败、0 跳过**：一个原生 Mirror 必填字段校验差异，加三个 MySQL TIMESTAMP 测试夹具失败。见 [阅读器原测试记录](2026-10-11-reader-us-integration-validation.md)。本轮未修改或重跑该仓库，不能把这些失败写成已修复，也不能把插件仓库推送视为阅读器部署。

## 证据与边界

- WeRead 两轮先失败后通过及独立复审见 [TDD 记录](2026-10-11-weread-review-fixes.md)；US 再次运行全部 19 项通过。
- 文档同步后再跑五个插件的包装/入口契约检查，共 21 项通过；源码哈希复核确认 US 测试后没有修改非 Markdown 的原测试快照文件。`git diff --check` 通过。
- 本地原始日志、执行器和归档在 `.local/us-full-suite/`，不随插件发布；可分享的结果、跳过列表、矩阵及源码哈希随本报告提交。
- 环境准备首次在 tmpfs 内同时下载和解压 Chromium 时空间不足，改用专用 `/tmp` 目录暂存下载后成功；缺少的系统动态库仅解包到测试私有目录。这些均发生在测试前，不计作测试失败或跳过。
- 回收了服务器全部本轮临时目录、依赖及浏览器；`/dev/shm` 恢复至仅用 12 KiB，根分区仍可用约 279 MiB。未安装系统包或重启生产容器。
- 未测试真实 WeRead/Fenbi 账号、实际视频语音模型、EPUBCheck、桌面插件重载或阅读器生产站点。本次推送只更新 `openai` 源码分支。

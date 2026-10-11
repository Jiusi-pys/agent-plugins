# 视频文本提取

`video-text-extract` 0.1.0 将视频链接中的语音转为轻度整理的 UTF-8 TXT：

**cat-catch 下载 → FFmpeg 音频 → Whisper large-v3 → 本地 Qwen 27B 纠错 → gpt-6-luna / max 终审 → 视频标题.txt**。

纠正识别错误与标点，删除明显赘词及无意义重复，保留原意、数字、否定和不确定表达。不总结、不翻译，不提取画面 OCR。

## 安装与运行

从本仓库 `openai` 分支的 `jiusi-agent-plugins` 市场选择 `video-text-extract`。插件提供一个同名技能，可直接提出视频链接转文字请求，或使用：

```text
$video-text-extract 提取这个视频链接的文字，按视频标题保存 TXT。
```

需要 Windows、Python 3.11+、Node.js >=22、PATH 中的 FFmpeg/FFprobe，以及本机已有的 cat-catch、Whisper Vulkan 构建与 llama.cpp Vulkan 构建。网页捕获使用 cat-catch 安装的 Playwright/Chromium。最后一轮需要 Codex 子代理工具支持 `gpt-6-luna / max`；不需要额外 OpenAI API key。

原生工具默认位于 `%USERPROFILE%\Documents\codes`，可通过当前任务进程的 `VIDEO_TEXT_EXTRACT_CODES` 配置根目录：

| 依赖 | 相对工具根目录的位置 |
| --- | --- |
| cat-catch | `cat-catch/cli/bin.js` |
| Whisper | `whisper.cpp/build-vulkan/bin/Release/whisper-cli.exe` |
| Whisper 完整模型 | `whisper.cpp/models/ggml-large-v3.bin` |
| llama.cpp | `llama.cpp/build-vulkan/bin/Release/llama-server.exe` |
| 本地纠错模型 | `llama.cpp/models/Qwen3.8-27B-Q4_K_M.gguf` |

该运行配置已针对 RX 7900 XTX 验证；设备检查明确要求 Vulkan0 为此显卡，其他显卡尚未适配。插件不包含模型权重、原生工具、账号信息或视频样本，也不会修改常驻模型服务。

默认输出根目录为 `%USERPROFILE%\Documents\video-text-extract`，可用 `VIDEO_TEXT_EXTRACT_HOME` 调整。所有任务文件位于该目录下，不写入插件安装缓存。脚本入口为 `skills/video-text-extract/scripts/video_extract.py`，运行时从实际安装位置解析其绝对路径。

## 命名、复核与清理

优先使用已核实的用户标题，其次捕获资源标题、网页视频元数据和页面标题；文件名保留中文并处理 Windows 非法字符、保留设备名及长度限制。没有可用标题的直链会明确报告回退到链接文件名，支持 `--title` 指定已核实标题。错误页、访问验证页标题不会冒充视频标题；已有同名 TXT 不覆盖。

网页、媒体直链及 cat-catch 支持的 HLS/DASH 可进入流程。候选无法区分时询问；分离音轨下载后检查真实音轨并合并，不能只信站点 MIME。直播须指定时长；登录失效、无音轨、缺块或明显截断会停止交付。

Whisper 与 llama.cpp 串行加载并退出。本地纠错使用 Vulkan、4096 上下文、单并发、batch 256、micro-batch 128、Flash Attention，关闭思考与多模态投影。按适配器真实占用预留至少3072 MiB，必要时减少 GPU 卸载层数，不结束其他任务进程。

本地处理完成后，worker 保持运行，等待一个独立上下文 Luna 子代理逐块复核。主代理检查正文、数字、否定、不确定表达和边界，再执行 `finish`；JSON、哈希及块数检查不能代替语义复核。

成功任务只保留最终 TXT：音频验证后删除下载媒体，转写验证后删除音频，发布后删除原稿、本地稿、分块与日志。失败或取消只保留简短错误记录，重试从头开始。异常遗留仅清理本技能标记且没有活动锁的临时目录；路径范围和链接检查保护原有文件及其他任务。

完整操作与终审提示见 [技能说明](skills/video-text-extract/SKILL.md)、[运行配置](skills/video-text-extract/references/runtime.md)及[终审模板](skills/video-text-extract/references/final-review.md)。

## 验证

```powershell
python -X utf8 -m unittest discover -s plugins/video-text-extract/skills/video-text-extract/tests -p 'test_*.py' -v
```

CI 在 Windows 上执行无需模型的单元测试与包完整性检查。原生媒体验证和真实模型验证需手动运行，不能把单元测试通过称为在线视频测试通过：

2026-10-11 的 US Ubuntu 全仓复测中，本插件 29 项自动化测试全部通过，无跳过（0.957 秒）。这只验证流程与包装契约，不将 Linux 测试解释为 Windows 原生媒体链路或真实模型验收。完整结果在仓库 `docs/reviews/2026-10-11-plugin-us-full-suite.md`。

```powershell
python -X utf8 plugins/video-text-extract/skills/video-text-extract/tests/media_validation.py
python -X utf8 plugins/video-text-extract/skills/video-text-extract/tests/live_validation.py --home <独立验证目录> --kind short
python -X utf8 plugins/video-text-extract/skills/video-text-extract/tests/live_validation.py --home <独立验证目录> --kind chinese --source <已授权本地视频>
```

真实模型测试停在 `review_ready`，须按技能实际调用 Luna、主代理复核后发布；不自动伪造审核。

2026-10-11 的原始全局技能在本机完成短视频、三分钟中文样本及[完整12分49秒在线中文视频](https://www.bilibili.com/video/BV1Ria76WEFN/)验证。在线任务最终仅留下标题命名的 TXT，三次尝试的临时目录均删除，失败尝试仅留错误记录。该网页自动取标题受站点限制，使用站点接口核实后指定标题，未计为自动取标题成功。网页捕获、HLS、分离音轨及中文空格路径另有原生工具验证。插件打包后的验证范围为单元测试、包完整性及原生媒体测试，未重新执行整段视频的模型终审。

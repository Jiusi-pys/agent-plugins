---
name: video-text-extract
description: 从用户提供的视频网页或媒体链接提取语音文本。使用本机 cat-catch、FFmpeg、Whisper large-v3 和 llama.cpp 27B，再交给 gpt-6-luna 子代理复核，交付轻度整理的 TXT 并删除中间文件。适用于视频链接转文字，不用于画面 OCR 或摘要。
---

# 视频文本提取

固定流程：cat-catch 下载 → FFmpeg 音频 → Whisper large-v3 → llama.cpp 本地27B保守纠错 → **一个 gpt-6-luna / max 子代理**终审 → TXT。必须实际完成各阶段，不能用摘要或某一轮草稿代替最终结果。

依赖、显存配置及命令见 [本地运行说明](references/runtime.md)。使用任务专属临时进程串行加载两个本地模型，不修改常驻 MCP 配置。

## 启动任务

入口是本技能目录下的 `scripts/video_extract.py`。先从实际安装的 SKILL.md 路径解析脚本绝对路径，不依赖当前工作目录，不把任务文件写入插件缓存。运行环境为 Windows、Python 3.11+；原生工具和模型从 `VIDEO_TEXT_EXTRACT_CODES` 指定目录寻找，默认用户 Documents/codes。

```powershell
python -X utf8 '<技能目录>/scripts/video_extract.py' run 'https://example.com/video'
```

通过支持后台会话的命令工具执行，保留 session_id 并读取增量输出。**worker 在资源选择和终审期间保持运行，不要因等待而终止会话。** 输出是简短 JSON 事件。默认自动识别语言，不翻译；用户指定语言、术语、输出目录或登录文件时传入对应参数。

- `selection_required`：根据页面上下文确定主视频及独立音轨。不同视频无法区分时展示具体候选并询问；不只凭最大文件选择。运行 `select --job-dir PATH --resource-id ID [--audio-id ID]`，不用重新嗅探以免ID改变。

- `waiting_for_gpu`：等待显存余量恢复，不更换模型或结束其他任务进程。超过五分钟清理并返回失败。
- `chunk_corrected`：本地纠错进度。
- `review_ready`：本地模型已退出，音视频已删除，开始子代理终审。
- `failed` / `cleanup_failed`：报告真实失败；清理失败要说明仍存在的任务目录，不声称只剩TXT。

某些站点将音频专用 MP4 标成 video/mp4，候选 category 可能误报。可以明确选择该资源为 audio-id，脚本会检查下载文件的真实音轨后再合并；不要仅凭 MIME 或旧捕获ID判断。每次重跑都使用新捕获的ID。

默认等资源选择十分钟、等终审一小时，可调整超时；长稿启动前把 review-timeout 设足够长。直播先明确时长再传 duration。需要登录时仅使用用户指定或本次已授权的会话文件；失效则请求更新，不输出凭据。

最终文件名为“视频标题.txt”：优先用户已明确提供的标题（`--title`），其次捕获资源标题、网页视频元数据标题及页面标题。媒体直链无法提供视频标题时使用链接文件名；`title_fallback` 会明确报告这一情况，能从用户或页面确认真实标题时用 `--title`。多视频页面选定目标后核对标题属于该视频。清理 Windows 非法字符、保留中文，保护已有同名文件，不覆盖。

## Luna 终审

出现 review_ready 后读取 [终审任务模板](references/final-review.md)。用 `collaboration.spawn_agent` 创建**一个**子代理，参数固定 `model="gpt-6-luna"`、`reasoning_effort="max"`、`fork_turns="none"`。

消息只提供模板、该任务 job.json 和 review.json 的绝对路径及用户明确给出的术语，不传下载网址、Cookie、捕获文件、API key 或无关历史。子代理逐块对照原稿和本地稿，独立纠错并轻度整理，写出规定的 review.json。使用 Codex 子代理，无需另配 OpenAI API key。若工具不可用或无法指定该模型，报告阻碍并取消worker清理，不能静默改用其他模型或宣称完成。

子代理完成后主代理实际对照 job.json 与 review.json，检查全部块、数字、否定、不确定表达、边界衔接，以及是否新增事实或压缩成摘要。哈希/覆盖/长度检查不能证明语义准确。有明显问题时让**同一个**子代理修正受影响分块。

审阅完成后：

```powershell
python -X utf8 '<技能目录>/scripts/video_extract.py' finish --job-dir 'TASK_PATH'
```

finish仅提交通过检查的结果。继续读取原worker会话，直到 complete事件且正常退出。以事件中的 final_path 为实际交付路径，确认标题命名的TXT非空、任务临时目录已删除，再用绝对路径链接交付TXT。默认TXT仅包含正文与自然段，不附处理记录、模型推理、Markdown标题或时间戳。

## 清理

音频验证后立即删除视频，转写验证后删除音频，终审发布TXT后删除原稿、本地稿及分块。成功任务输出目录只保留标题命名的TXT。失败/取消清理中间文件，只保留简短error.txt，重试从头开始。

结束任务用 `cancel --job-dir PATH` 并等待原worker退出；异常遗留用 recover，只清理本技能拥有且没有活动锁的目录。不要手动删除父目录、用户登录文件、模型或其他视频。保护已有同名TXT，不得加覆盖选项。下载与终审可独立进行，本地GPU阶段采用独占锁。

# 本机运行接口

Python 辅助脚本只使用标准库。需要现有 Node.js >=22、FFmpeg、FFprobe 以及以下相对于工具根目录的文件。工具根目录由 `VIDEO_TEXT_EXTRACT_CODES` 指定，默认 `%USERPROFILE%\Documents\codes`：

| 组件 | 本机位置 |
| --- | --- |
| cat-catch CLI | `cat-catch\cli\bin.js` |
| Whisper CLI | `whisper.cpp\build-vulkan\bin\Release\whisper-cli.exe` |
| Whisper 模型 | `whisper.cpp\models\ggml-large-v3.bin` |
| llama.cpp server | `llama.cpp\build-vulkan\bin\Release\llama-server.exe` |
| 本地纠错权重 | `llama.cpp\models\Qwen3.8-27B-Q4_K_M.gguf` |

本流程使用任务专属 native 进程，因为现有 MCP 纠错服务配置的是其他模型且缺少完整的临时任务生命周期控制。不修改那些服务。

## 命令

`run URL` 开始任务并等待选择及终审。参数：`--output-dir PATH`（最终TXT父目录）、`--title TEXT`（已核实的视频标题）、`--resource-id ID`、`--audio-id ID`、`--storage-state PATH` 或 `--cookies PATH`、重复的 `--click CSS`、`--wait SECONDS`（默认15）、`--duration SECONDS`、`--language LANG`（默认auto）、`--glossary TEXT`、`--selection-timeout SECONDS`（默认600）、`--review-timeout SECONDS`（默认3600）。资源ID以本次捕获为准；优先在持续运行的任务中用 select 选择。

```text
status --job-dir PATH
select --job-dir PATH --resource-id ID [--audio-id ID]
finish --job-dir PATH
cancel --job-dir PATH
recover
```

默认运行目录：`%USERPROFILE%\Documents\video-text-extract`。临时文件在 `.work\job-<uuid>`；成功 TXT 在 `outputs\<日期时间-任务后缀>\<视频标题>.txt`。测试可设置进程环境变量 `VIDEO_TEXT_EXTRACT_HOME`，不更改用户设置。临时根目录不能作为最终输出目录。

worker 在选择和终审期间保持锁。finish 验证 review.json 并发送带内容哈希的完成信号；worker 再次验证，再通过同卷硬链接原子发布完整 TXT，保护已有同名 TXT，随后清理。目标文件系统需支持硬链接（本机 NTFS 支持）。失败保存简短错误记录；临时诊断日志随任务清理删除。

## 显存预算

Whisper：完整 large-v3、自动识别语言、beam size / best of 均为5、Vulkan设备0、Flash Attention。

llama.cpp：本地 GGUF、Vulkan0、单并发、context4096、batch256、micro-batch128、Flash Attention、reasoning off、关闭多模态投影和跨请求缓存。gpu-layers auto、fit on；通过 DXGI 定位显卡并查询 Windows 适配器实际占用，以3072 MiB为剩余显存目标。若 Vulkan 预算高于实际余量，将差值加入 fit-target，必要时减少卸载层数，保持同一个模型。采用真实模板分词，输入上限1792 tokens，输出上限2048 tokens；超限或格式失败进行最多三级拆分重试。

本地纠错输出最小字符串替换提案，只应用置信度>=0.85、在正文唯一出现且无重叠的替换。仍需 Luna 语义复核。

检查 Vulkan0 确实为7900 XTX。Whisper前至少8192 MiB可用显存、llama前至少6144 MiB。27B启动后确认剩余>=3072 MiB，不满足则结束本任务模型进程。动态新增负载仍可能影响运行，不能保证零负载或永不失败。

每个子进程及其后代绑定独立 Windows Job Object，关闭句柄终止该进程组；worker 意外退出也释放这些句柄。不会按进程名批量结束其他服务。

## 验证

```powershell
python -X utf8 -m unittest discover -s '<技能目录>/tests' -v
python -X utf8 '<skill-creator目录>/scripts/quick_validate.py' '<技能目录>'
```

`tests/media_validation.py` 使用临时 localhost 样本验证网页捕获、HLS 和分离音视频；不加载模型。`tests/live_validation.py --home PATH --kind short|chinese` 执行真实模型链，停在终审等待处，由主代理按技能完成 Luna 复核及发布。中文样本必须用 `--source PATH` 提供已授权的视频，默认验证其前三分钟，不修改原视频。测试不会自动伪造复核结果。

文件名由视频标题生成：网页读取 og:title、twitter:title 或页面标题；直链缺少标题时采用 URL 文件名并报告回退。`--title` 优先于自动获取的标题。Windows 非法字符替换为下划线，处理保留设备名、末尾点和空格，并将标题限制到120个 UTF-16 单元。标题读取复用 cat-catch 的 Playwright 依赖及本任务授权的登录文件；失败不输出凭据，不影响媒体下载。

---
name: fenbi-export
description: 下载用户可访问的粉笔指定课程讲义、助教笔记等附件，或导出行测、申论做题历史为 Markdown、JSON 和本地图片，保留答题卡不确定标注与收藏。使用本地 Playwright，可首次手动登录并复用本机登录状态。
---

# 粉笔资料与记录导出

使用本技能目录上两级的 `scripts/fenbi.py`。解析为实际安装目录下的绝对路径，不能依赖当前工作目录，也不能修改安装缓存。运行环境为 Python 3.11+；依赖见插件根目录的 `requirements.txt`。

## 准备

1. 确认用户要课程资料、做题记录或恢复任务；优先使用用户给出的链接和输出位置。默认输出到用户文档目录下的 `FenbiExports`，禁止把用户资料放入插件目录或仓库。
2. 检查 Python、Playwright 和 Chromium。缺少时安装本插件 `requirements.txt`，并运行 `python -m playwright install chromium`。
3. 首次使用运行 `python <脚本绝对路径> login`。让用户在独立 Chromium 窗口自行登录；不要询问、读取或输出密码、验证码、Cookie、令牌。不从日常 Chrome 复制 Cookie。
4. 配置默认在 `%LOCALAPPDATA%/fenbi-exporter/browser`。支持 `--profile` 指定专用目录；同一配置目录同时只运行一个任务。后续默认可见运行，用户要求时可加 `--headless`。

## 调用

```text
python <script> course <课程链接或ID> --output <目录>
python <script> history --subject all --output <目录>
python <script> history --subject xingce --from 2026-10-01 --to 2026-10-11 --output <目录>
python <script> history --record-url <真实解析链接> --output <目录>
python <script> resume --run <任务ID> --output <原输出目录>
python <script> verify --output <目录>
```

课程支持 `--group`、`--lesson` 按完整名称筛选。`--limit` 仅用于用户要求的小范围处理或验收；不能给全量请求自动加上限。历史的 `--limit` 按每个类别限制，必须在报告中说明。日期为北京时间且包含起止日。多个详情链接可以重复指定 `--record-url`。

课程遍历课时集、科目、课时以及每个课程资料附件。历史包括行测练习/试卷、申论练习批改/套卷批改/小模考。只读取用户有权访问的内容；不点击开始考试、重做、提交、标注、收藏、笔记编辑、购买等控件。不要播放或下载课程和解析视频。

## 校验与交付

- 检查命令结果中的 `status`、任务清单以及 `verify` 结果。`complete` 只代表报告所列范围；`limited=true` 不能称为全量完成。
- 失败或中断后使用同一任务 ID 恢复；新一次同步使用原导出命令，以刷新旧记录标记和批改状态。不要通过删除旧快照“修复”状态。
- Windows 浏览器在下载时崩溃或返回 `TargetClosedError` 时，可在导出或恢复命令加 `--fresh-session` 重试一次。它在内存中复用本插件专用配置的登录状态，使用临时浏览器会话；仍默认显示窗口。登录失效时运行普通 `login`，不删除配置或降低浏览器安全设置。
- `uncertain_marked` 是不确定标注，`favorited` 是收藏；两者独立，可同时为真。未知是 `null`，不能改成否。状态表示采集时页面状态。
- Markdown 引用本地图片。缺图、题数不符、标记冲突或无法读取本人答案必须作为缺口报告，不能用参考答案补齐。截图替代原图时保留 `method=rendered_capture`。
- 遇到需登录/验证/访问限制，保留进度并让用户处理；不绕过限制，不反复刷请求。页面结构变化应修复源码及对应测试，不直接操作插件缓存。
- 返回输出目录、总索引、数量和缺口。账号数据、完整签名地址与浏览器状态只能留在用户本机私有位置，不加入版本控制、安装包或聊天日志。

更多输出结构及状态语义见插件根目录 `README.md`。

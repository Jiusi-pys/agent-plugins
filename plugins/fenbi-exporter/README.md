# 粉笔资料与记录导出

本地技能和 Python/Playwright 脚本。课程附件保持原格式；做题记录保存 Markdown、JSON、本地图片，以及独立的不确定标注和收藏状态。支持 Windows，使用专用 Chromium 配置目录。

## 安装和登录

插件已登记在仓库 `openai` 分支的 `jiusi-agent-plugins` 市场。注册仓库后安装：

```powershell
codex plugin marketplace add <本仓库绝对路径>
codex plugin add fenbi-exporter@jiusi-agent-plugins
```

以下依赖及登录命令在插件根目录执行；在 Codex 中直接提出导出请求即可，技能会解析实际安装目录中的脚本路径。本机开发验收曾使用独立的 `fenbi-local` 市场，它不是使用本仓库插件所需的安装源。

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
python scripts/fenbi.py login
```

首次登录由本人在浏览器中完成。配置默认位于 `%LOCALAPPDATA%/fenbi-exporter/browser`；不要提交、分享或同时打开该配置。登录状态过期时重新运行 `login`。不需要手工导出 Cookie。

## 使用

```powershell
python scripts/fenbi.py course 775995
python scripts/fenbi.py course 775995 --group 科学推理 --lesson 力学基础
python scripts/fenbi.py course 775995 --group 判断推理 --lesson 论证模型1 --fresh-session
python scripts/fenbi.py history --subject all
python scripts/fenbi.py history --subject xingce --from 2026-10-01 --to 2026-10-11
python scripts/fenbi.py history --record-url '<粉笔解析页面链接>'
python scripts/fenbi.py resume --run '<输出中的任务ID>'
python scripts/fenbi.py resume --run '<输出中的任务ID>' --fresh-session
python scripts/fenbi.py verify
```

默认导出到用户文档目录下的 `FenbiExports`。所有命令支持 `--output`；联网命令支持 `--profile` 和 `--headless`。日期按北京时间，包含起止日。课程和历史支持验收用 `--limit`，历史按每类限制数量，清单会标记 `limited`；不代表全量完成。

本机 Windows Chromium 在复用配置后出现过下载时进程崩溃。此时给 `course`、`history` 或 `resume` 增加 `--fresh-session`：从本插件专用配置中在内存里取得登录状态，关闭该窗口，再用临时会话导出。不会生成 Cookie 文件；临时会话的状态变更不写回专用配置，登录过期仍用普通 `login` 恢复。

## 文件和语义

- `index.md` / `index.json`：总索引。
- `courses/<课程ID>/`：按课时集、科目、课时组织附件及来源索引；同名文件使用哈希区分。
- `assets/`：按内容哈希保存的附件和图片。Markdown 使用相对路径，可以连同整个目录离线搬移。
- `snapshots/<科目-作答ID>/`：不可覆盖的 JSON/Markdown 版本。再次同步会刷新旧记录状态，只在内容变化时增加版本。
- `runs/<任务ID>.json`：范围、发现进度、分页证明、成功项和失败项。恢复只重试未成功项目；重新同步则重新检查全部选定记录。

JSON `schema_version=1`。每个作答具有独立 ID，同一道题的重复作答不会被合并。题目保留 `user_answer`、`correct_answer`、`blocks`、`sections`、申论逐字 `grading`、答题卡和工具栏证据。`uncertain_marked` 和 `favorited` 是独立三态值，未知为 `null`，反映采集时状态。图片 `method` 区分原图和页面截图。已校验图片的来源域名轮换不会产生新快照，内容哈希变化才会被视为图片更新。

页面响应仅被动观察，用来核实分页游标和作答标识；不会猜测或绕过私有接口。页面尚未返回成功响应时的“无内容”不代表空历史。课程科目列表会滚动加载，并与页面显示的课时总数核对；未加载完整时报告失败，不将前 20 节误认为全部。附件地址在下载时从页面重新取得，签名不会写入清单。视频、自动答题及线上状态修改不在功能范围内。

最终状态包括 `complete`、`partial`、`auth_required`、`user_action_required`、`blocked`、`failed`。进程退出码：0 完成；2 部分完成；3 登录/验证需要用户处理；1 失败。任务清单给出具体缺口。模拟测试与真实账号验收分别记录，网页可能更新，不能据单个样本宣称所有类别已实测。

未完成或状态尚未识别的练习只保存历史列表信息，并标记 `partial`；不会为提取详情进入答题页。申论“套卷批改”等类别为空时，只有成功响应明确给出结束游标才记作空列表。下载器只观察点击附件后出现的文件响应，拒绝网站样式、脚本及登录错误页。

页面会在题目出现后异步加载标注、收藏和笔记。脚本等待对应页面自身发出的响应，并交叉核对答题卡与工具栏。未加载、请求失败、页面未提供状态或证据冲突时记录 `null` 及原因，不把初始空白图标当成否。部分申论页面没有可确认的收藏状态，此时正文仍会保存，但整体状态为 `partial`。

## 开发验证

```powershell
python -m unittest discover -s plugins/fenbi-exporter/tests -v
```

测试包括纯数据契约、真实 Chromium 中的合成 DOM、分页结束判定、文件校验、图片引用、快照及插件包装。独立工作流 `.github/workflows/validate-fenbi-exporter.yml` 在 Windows 和 Linux 上执行这些测试。测试不依赖个人账号，不包含真实 Cookie 或真实作答。真实验收文件始终放在源码目录之外。

## 2026-10-11 本机验收

- 34 项自动化测试通过，包含临时会话登录复用及实际下载、课程滚动加载及中途停滞、延迟加载状态、CDN 轮换、旧快照保护，以及下载事件、PDF 跳转、新窗口、签名过期重取和大文件 XHR 转下载。
- 课程 `775995`：合集讲义、合集参考答案、普通讲义、助教笔记均已实际保存。四份 PDF 分别为 266、10、11、67 页，可由 PDF 解析器读取；合集讲义约 127 MiB。
- “判断推理”实际滚动加载 41 节后，已下载“论证模型1、2、3、4+原因解释及日常结论”的 4 份讲义及 4 份助教笔记，共 205 页；文件哈希及 PDF 解析校验通过。本机复用配置下载时发生过进程崩溃，改用临时会话后完成这 8 份资料。
- 实际列表分页：行测练习 20 页、申论练习批改 5 页均抵达结束游标；按作答 ID 去重，未以题目名称合并。
- 图形题现场核对了标注和收藏的四种组合。连续两次导出复用同一快照和图片；标记改变后新增快照及失败保护由合成测试覆盖，验收过程不修改线上标记。
- 已抽查行测练习、试卷，申论练习批改、小模考的正文、本人答案、材料、解析及批改。套卷批改只有空列表，正文未实测；多课时集的实际遍历也缺少现场样本。

完整分页校验不等于所有历史正文均已导出。交付的是小范围验收资料；全量运行不使用 `--limit`。包含未知状态或未完成练习的验收任务会保留 `partial`，详见输出清单，不能据合成测试宣称未出现的类别已实测。

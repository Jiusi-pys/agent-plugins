# 古文精译 0.2.0 验收记录

日期：2026-09-27；基线 `e83c364`，工作分支 `codex/book-translator`。本次新增能力仅位于 book-translator 内，Agentic Review 和 EPUB 编排源码未改动。

## 已实现范围

- 新增 classical-translate 技能；主入口识别古译今任务并转入该模式，内部 reviewer 扩展出处独立复核。
- 支持粘贴后保存、UTF-8 TXT/Markdown 与古文 EPUB。文本输出对照/详注 Markdown，EPUB 输出现代文及可点击原文对照、详注和校读依据。
- 来源登记含原典/古注/现代研究分类、作者或注家归属、实见版本、卷篇定位、实际阅读范围、访问方法、URL/本地图版、证据快照与 SHA-256。
- 逐段断句、古义、用典、异文和不确定性记录；解释注各自附引文与支持关系，有据异说公开保留，未解问题阻止交付。
- 章节及全局 reviewer 独立复读全部引用来源；缺 source_checks、来源变动、伪造引文和过期稿件不能通过。

## 结构与安装证据

| 项目 | 结果 |
| --- | --- |
| 新插件 unittest | PASSED，50 项（含 16 项古译今用例） |
| 现有 EPUB 编排 unittest | PASSED，26 项 |
| 失败测试先行 | 已实测新增模块缺失、古译今 skill 未注册、无空行的 Markdown 标题未分章及用户输出暴露内部标签等 RED，修复后 GREEN |
| 古译今 EPUB 调用真实 EPUB 编排 | PASSED，输出读回含原文对照、校读依据、文献定位与链接；报告明确这是合成测试证据 |
| 三个 skill 与 plugin manifest 校验 | PASSED |
| ZIP 解包后校验 | PASSED，单插件、三个技能、无缓存/研究素材/其他插件 |
| 隔离 Codex CLI 安装 0.2.0 与 EPUB 编排 | PASSED，缓存目录和 CLI 预检实际执行 |
| 原有身份/元数据/提示词保留检查 | PASSED，两个原提示词及顺序保持，追加一个古译今提示词 |
| 原有两个外部插件变更检查 | 无差异 |

最终安装证据在工作区 `.local/classical-install-release/install-evidence.json`。使用子进程的专用配置目录，不改用户通常使用的 marketplace 配置。成品检查修正引文结尾重复句号后，重新运行 50 项插件测试、隔离安装和实际导出，均通过。

归档为 `.local/dist/book-translator-0.2.0.zip`，33 个文件，72,385 字节；SHA-256：`abb23aa1778841e0d73c22b783df3e01c0b6e60bb065fa219e6d956d46fad4c5`。

## 实际原典核读

研究者 `/root/classical_sources` 实际打开并通过 HTTP 获取以下数字古籍，保存页面、机械提取文本、所读连续摘录与工具轨迹；未把检索摘要当成原文。

| 材料 | 实读范围与版本层级 |
| --- | --- |
| [春秋左氏傳·隱公](https://zh.wikisource.org/wiki/春秋左氏傳/隱公) | 隐公元年郑庄公、颍考叔叙事及“君子曰”论赞；数字页面 oldid=2675995 |
| [詩經·既醉](https://zh.wikisource.org/wiki/詩經/既醉) | 全诗八章，重点第五章及上下文；数字页面 oldid=8738411 |
| [春秋左傳正義卷01](https://zh.wikisource.org/wiki/春秋左傳正義/卷01) | 杜注、音义与孔疏相关段，纯、施及、匮、锡、类及引诗说明；数字页面 oldid=1691748 |
| [毛詩正義卷十七](https://zh.wikisource.org/wiki/毛詩正義/卷十七) | 《既醉》序与八章注疏，重点毛传、郑笺、孔疏第五至六章；数字页面 oldid=2633043 |

具体刊本底本均未确认，未做原刻图版核对；这些是不同古籍文本而非“四个独立校勘版本”。ctext 的正文访问曾返回 403，未使用其检索摘要冒充实读，改用上述可访问原籍。

实际研究纠正了容易产生的过度概括：毛传释“类”为善，郑笺释族类并讨论推广孝道、还引颍考叔；左传孔疏按当前传文解释为同具孝心的一类人。不能简单宣称《既醉》原义唯一指生物学子孙，也不能将“施，延也”伪称为亲见杜注原句。

研究材料保存在 `.local/classical-demo/research/`：sources-proposal.json、tool-trace.txt、capture-manifest.json、research-notes.txt 及实际文本摘录。

## 真实译者与独立复审

样本作业：`.local/classical-demo/job`。输入是实际原典中的颍考叔引诗评语，1 个片段。研究、译者、章节 reviewer 与全局 reviewer 分别为不同实例：

- 研究：`/root/classical_sources`。
- 译者：`/root/classical_translate`。
- 专属章节 reviewer：`/root/classical_review`。
- 独立全局 reviewer：`/root/classical_global`。

译者已完整译出该段并编写 17 条详注；章节 reviewer 实际逐项对照 59 处注释引文及 4 处正文校读引用，独立再次打开四份原籍/古注并核对页面修订信息。章节报告 `approved`，实际 `check-chapter` 返回 `reviewed=true`；不把“原诗类义只有子孙”之类过度概括纳入译稿。

当前稿件摘要：`a5a7a014dd6e2a8b8e92802b84ed2ee6e3dfb6186390d50ef8d2dd844b24e397`。全局 reviewer 独立完整核读原文、译文、17 条详注和四份实际原籍，报告 `approved`，未借章节审核结论代替原典复读。实际 `check-global` 通过，bundle：`f705c1b774cb56bb623a49d6f01ae47f66706b412fd07eaf5cf8beed9c0b7d0a`。

使用最终隔离安装缓存中的脚本实际导出 `.local/classical-demo/颍考叔-古文精译详注.md`，交付报告为 `completed`；SHA-256：`e83b23c2b5124c842fb3d65ce2ac70263989ecc356a8583116cf95b0fea3aec0`。读回确认 17 条中文标注、原文对照、现代文、出处和版本限制均存在。输入文件与作业中的源文件逐字节一致，SHA-256 均为 `c0a276646cc6a567c12bb25e1790783f3b36c82ec313cfc7f9245b8194a10fa5`。

## 插件更新与读回

通过 Plugin Creator 更新原有[书籍翻译](https://chatgpt.com/plugins/plugins_6ab85f37cf908191aead7c312a262d6a)，没有另建插件。版本为 `0.2.0`，状态 `updated`；release：`pluginrel_6ab8686448ec8191b55f244aacc4f657`。

更新后读回两个 manifest 及 14 个受影响的技能、脚本、测试和说明文件，共 16 个文件。15 个文件与本地最终源码文本一致；服务端对兼容 manifest 调整了 JSON 键序、Unicode 转义及 skills 路径末尾斜线，解析并规范化路径后全部字段等价。确认读回 release 与更新回执相同，插件身份、作者、许可、关键词及原有两个提示词和顺序保留。原有可见范围保持不变。回执、源码读回及比较结果保存在 `.local/dist/classical-plugin-update-result.json`、`.local/dist/classical-plugin-readback.json` 和 `.local/dist/classical-readback-verification.json`。

本工作区的 marketplace 入口保持原有路径，不改用户全局 marketplace 配置；本验收记录生成时，仓库中的新能力尚未提交或推送，不把已发布的插件更新当成 Git 远程同步。后续 Git 状态以实际提交与远程分支为准。新会话可加载更新后的插件能力。

## 边界

引文在快照中命中、hash 与 JSON 完整，只能证明数据相符，不能证明研究者实际阅读或解释正确。独立工具轨迹、逐条审稿与模型判断另列证据；不宣称绝对无错或出版级校勘。图版校勘、穷尽版本比较、完整长篇古籍语义质量、阅读器弹窗及远程 CI 不属于已通过的证据层。

方案见 [古文精译实施与审核方案](../plans/2026-09-27-classical-chinese.md)。

# 书籍翻译插件：实施方案与验收约定

状态：实现与 TDD 回归完成，实际安装及样本验收记录见文末链接。日期：2026-09-27。

本次确认：不改动仓库中的 Agentic Review。翻译专用终审作为 book-translator 内部 skill，不创建独立插件。EPUB 编排仍使用现有插件，不要求修改它；兼容检查由新插件的适配器承担。

## 1. 已对齐的需求

- 输入用户提供的外文 EPUB，输出新的简体中文 EPUB；保留原书。
- 用户已选择面向初学者：忠实翻译原文，增加解释与案例；不能以简化、概述取代作者原有论证。
- 书名、作者译名优先联网核实大众通行译法，记录来源、版本匹配依据及有争议的译名。
- 按内容划分章节，多个翻译 sub-agent 并行处理；每章有独立于译者的专属 reviewer sub-agent。
- 每章全文对照原文，检查缺漏、错译、逻辑、术语与中文通顺程度。
- 全书由本插件内部 translation-review skill 进行完整终审；通过后调用本仓库 EPUB 编排产生最终 EPUB。
- 用 Plugin Creator 的标准打包流程交付，并加入本仓库 Codex marketplace；跨插件集成必须有实际验证。
- 编程先计划、对齐与审核，再按 TDD 执行。该约束来自本次用户提供的 AGENTS.md。

## 2. 已验证的仓库与官方接口事实

- 当前原始工作目录在 `main`；README 与已配置 marketplace 表明 Codex 插件位于 `openai` 分支。
- 已配置 `jiusi-agent-plugins` 是 Git marketplace，跟踪 `openai`；本次读取的修订为 `f145ea79e09ff67bb7b4f1a70139b122814630d3`。
- 已基于 `origin/openai` 建立独立工作区。本次实现不把 Claude 的 `main` 与 Codex 的 `openai` 混合。
- `openai` 已有 `.agents/plugins/marketplace.json`、`plugins/agentic-review` 与 `plugins/epub-editor`，无需从安装缓存恢复源码。
- Agentic Review 当前仅支持代码与软件设计，不直接调用或修改它；在新插件内部实现翻译审核入口。
- EPUB 编排已有 `scripts/epub_editor.py`、元数据补丁、目录与注释处理，以及退出码 0/1/2；2 表示产生输出但仍有问题，不是通过。
- OpenAI 官方打包文档使用根目录 `plugin.json`、`skills/` 和 `extensions.com.openai`；仓库已有 `.codex-plugin/plugin.json` 兼容层，两份元数据需要同步。
- 官方 `agents/openai.yaml` 的 `dependencies.tools` 示例是 MCP 工具依赖，不是任意插件间依赖声明。未找到可以据此保证自动安装其他插件的接口。
- Codex 将安装内容复制到插件缓存；不能假定插件安装后仍是相邻目录，也不能从多个版本中取字典序最大的路径。

文档依据（本次已读取正文）：

- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/build/skills
- https://developers.openai.com/codex/subagents

## 3. 插件边界

新增 `book-translator`（显示名“书籍翻译”），首版支持具备本地文件、联网检索及 sub-agent 能力的 Codex 环境。

职责分配：

| 组件 | 职责 |
| --- | --- |
| book-translator 主技能 | 检索译名、制定全书译法、派发任务、收集证据、推进阶段、处理失败与恢复 |
| book-translator Python 工具 | EPUB 清点、章节/文本块映射、覆盖检查、版本绑定、重组中间 EPUB、调用编排与读回验证 |
| 章节 translator | 负责指定章节的译文、术语建议、解释与案例，不自行签发审核通过 |
| 章节 reviewer | 全量对照该章原文/译文，提交独立问题与覆盖记录；返工后复核同章 |
| book-translator 内部 translation-review | 全书终审：全文覆盖、跨章术语与论证一致性、注释准确性、问题闭环与证据完整性 |
| epub-editor | 从审核通过的中间 EPUB 输出新 EPUB，处理元数据、目录、脚注及格式结构 |

Python 不假装调用一个不存在的“插件 API”，也不负责调用付费翻译 API。翻译与语义审核由宿主提供的真实 sub-agent 完成。

## 4. 运行流程

`依赖预检 → 原书清点 → 译名检索/术语表/读者档案 → 按章翻译与独立复审 → 全书终审 → EPUB 编排 → 输出读回验证 → 交付`

### 4.1 依赖预检

1. 从当前会话已启用的 skill 清单获得EPUB 编排依赖的真实 SKILL.md 路径并读取，或在开发测试时显式传入仓库根路径。
2. 核对插件名、技能名、manifest 版本、所需文件与本次新增的应用层契约版本；路径解析后检查位于对应插件内。
3. 把所选根路径、版本、skill/script 摘要写入工作目录 `dependencies.lock.json`。此文件是本插件的运行记录，不是 Codex manifest 字段。
4. 同名歧义、插件缺失/未启用、缺少所需 CLI 能力或脚本损坏都在翻译开始前报出。不能静默改用主 agent 的审核代替必需依赖。
5. 安装指引使用真实 marketplace 名和 Codex CLI。安装动作不伪装成 manifest 自动依赖；开发验收使用独立配置目录验证安装后的布局。

### 4.2 原书清点与内容拆分

- 输入文件及每个原始资源计算 SHA-256；源文件只读，工作状态保存在独立作业目录。
- 阅读顺序来自 OPF spine；章节边界结合 nav/NCX 锚点和正文标题，不以 ZIP 文件名排序代替书的顺序。
- 支持一文件多章、同章多文件、无目录与超长章节。目录冲突需要证据定位；不按同名标题猜测。
- 以段落/标题/列表项/表格单元格等语义块建立稳定 `segment_id`，记录资源、DOM 位置与源文摘要。嵌套块只能归属一次。
- 行内标签、脚注引用、超链接、图像、公式和代码使用受保护标记。中文词序可在同一块内调整，保护标记必须数量一致、属性完整、嵌套有效。
- 清点所有 manifest 文本资源，包括非 spine 的原注、附录等；每项必须有“翻译/按约定保留/不支持”的明确记录。
- 标题、目录、图片替代文本、表格说明和原注都纳入覆盖范围。参考文献标识、代码、公式等按类型保留，不能被计作漏译或伪装成已翻译。
- 长章按小节和段落切成批次，并提供邻接上下文；仍归属于同一章节译者与专属 reviewer。超长单段需显式细分映射，不能截断。
- 对扫描图像中的正文、无法解析的固定版式或其他未支持内容，明确列为未覆盖，不能交付为“全文完成”。首版不承诺 OCR、解密或音视频转写。
- 不执行书中脚本、外链或指令；沿用并测试压缩包大小、路径与 XML 实体边界。

### 4.3 译名、术语与初学者注释

- 先以原书名、作者、ISBN/版次检索出版机构、图书馆等可靠书目来源，必要时交叉核对。无可靠结果时记录暂译，不编造“通行译名”。
- 检索仅用于书目与术语核验，不以网络上的既有整书译文替换本次翻译。
- 主 agent 建立版本化全书术语表、作者/人物表、文风与读者档案。译者只提术语变更建议，由主 agent 合并，避免并发改写全局文件。
- 解释重点是初学者可能欠缺的术语、隐含前提、否定/量词、因果与必要/充分条件，以及哲学立场之间的区别。
- 每条新增注释标明“译者注”或“辅助案例”，附所解释的原文 segment_id。例子不得被写成作者的原例或史实。
- 注释解释可能的歧义，不擅自替作者补出唯一结论；非显然事实需来源，纯假设例子明确注明是假设。
- 保留并翻译原书注释；新增注释独立命名，采用可点击语义与返回链接，避免与原注 ID 冲突。不承诺所有阅读器都显示弹窗。
- 中文书名与作者译名不等于某一正式中译本：不借用该中译本的译者、出版社或 ISBN。新产物使用自己的标识，并在来源说明保留原版书目信息。

### 4.4 并行翻译与专属复审

- 启动前检查真实 sub-agent 工具与并发容量；无工具时标为受阻，不声称已并行。
- 主 agent 维护队列，按宿主限制分批派发。章节 reviewer 必须与译者是不同的 agent 实例，身份和章节映射持久化。
- 每个 worker 仅写自己的章节/批次与审核文件；源文、术语表和其他章节只读。汇总文件只由主 agent 更新。
- 章节状态：`pending → translating → reviewing → revision_needed / approved`。
- reviewer 从原文开始逐段对照，检查覆盖、否定与条件、数字/引文、指代、概念一致性、中文通顺与注释。审核报告不能只是一段总体评价。
- 每次报告绑定源文、译文和术语表版本，列出已核对 segment_id、问题、证据与修订建议。译文改动后旧报告自动失效。
- 每章默认最多三轮自动修订；仍有实质问题则保留作业为待处理，报告具体问题，不能无限循环或降级为自动通过。
- 中断后从状态和摘要恢复；输入变化、术语变更影响的章节必须重新审核，不能复用旧通过状态。

### 4.5 插件内部 translation-review 全书终审

- 在 book-translator 的 skills/translation-review/ 中实现专用技能与书籍审核规范；原 Agentic Review 的全部文件保持原样。
- global reviewer 读取本插件内部 translation-review 技能文件、原文、译文、术语表、注释和章节报告。不能拿章节报告的摘要替代全书对照。
- 全书超出上下文时分批全量审核，以覆盖清单记录每个 segment；再进行跨章术语、指代、概念发展、引文和重复章节检查。
- 全局记录绑定最终候选译文与注释版本。覆盖不足、未解决的实质问题、过期报告或缺失证据都会阻止正式导出。
- 全局退回修改后，重新运行受影响章的 reviewer，并使全局批准失效直至补审完成。
- 报告继续区分观察事实、推断和未验证项；“完整终审”表示全量覆盖流程已执行，不宣称机器保证语义绝对无错。

### 4.6 EPUB 编排与交付

- 完成覆盖门禁后重建中间 EPUB。保留章节定位、插图、链接和非目标资源；更新中文正文语言、目录及选定元数据。
- 使用参数数组调用已解析出的 `epub-editor/scripts/epub_editor.py`，处理带空格/中文/特殊字符的 Windows 路径，不拼接 shell 命令。
- 仅当退出码为 0 且 `issues` 为空才进入交付校验；输出路径已存在、退出码 1 或 2、缺失/非 JSON 输出均不能通过。
- 读回最终 EPUB，验证与已审译文对应的语义内容、注释、目录链接、资源摘要和元数据；编排若改变已审文本则重新送审。
- 原文件与已有输出不得覆盖；最终文件只在验证成功后写入用户指定的最终位置。
- 内部结构校验与 EPUBCheck 分开记载。有可用 EPUBCheck 时运行；未运行时明确标为未验证，不能把 Python 测试代称为 EPUBCheck。
- 默认交付一份中文版 EPUB 和简明报告；断点与详细审计材料保留在工作目录，不把调试文件塞进电子书正文。

## 5. 文件与接口设计

```text
plugins/book-translator/
  plugin.json
  .codex-plugin/plugin.json
  README.md
  requirements.txt
  skills/book-translate/SKILL.md
  skills/book-translate/agents/openai.yaml
  skills/book-translate/references/{translation,job-contract,dependencies}.md
  skills/book-translate/templates/{translator,reviewer,global-reviewer}.md
  scripts/{book_translate,common,dependencies,epub_segments,review_gates}.py
  tests/                         # 自编短篇夹具，不收录用户书籍
  skills/translation-review/SKILL.md
  skills/translation-review/references/review-contract.md
  contracts/epub-editor.json     # 本插件对外部现有 CLI 的兼容要求
.agents/plugins/marketplace.json # 保留既有条目，追加 book-translator
README.md
.github/workflows/validate-codex-plugins.yml
```

新增契约文件仅由仓库工具读取，不假设 Codex 会识别自定义依赖字段。新插件的 manifest 与兼容层按变更同步；现有插件不改动。

工作目录：`job.json`、`inventory.json`（包含全部 segments）、`profile.json`（含书目证据及术语表）、`source.epub` 原文快照、`chapters/<id>/`、`reviews/`、`dependencies.lock.json`、`reports/`。中间 EPUB 位于导出时的临时目录。

实际 CLI 操作：`doctor`、`prepare`、`packet`、`assign`、`check-chapter`、`assign-global`、`global-packet`、`check-global`、`status`、`finalize`。各操作只做对应的确定性处理；review JSON 由实际 reviewer 产生。

## 6. TDD 与验收顺序

每组先写失败测试并运行证明 RED，再最小实现到 GREEN，最后重构并运行有关回归。

| 阶段 | 先写的失败案例 | 通过标准 |
| --- | --- | --- |
| A 依赖与打包 | 缺失依赖、缺少 CLI 能力、不相邻安装目录、错误 identity、带空格中文路径、重复安装来源 | 依赖预检明确失败；合法安装路径准确解析；无硬编码用户缓存路径 |
| B 内容清点 | ZIP 顺序不同于 spine、一文件多章、多文件一章、同名标题、无 nav、非 spine 原注、超长段落 | 文本与资源集合有完整且唯一的去向；切分可重建，无丢失/重复 |
| C 行内结构 | 混合 text/tail、嵌套强调、脚注、表格、图片 alt、公式/代码、保护标记缺失/重复 | 可翻译文本自然重组；受保护信息与有效链接保持完整 |
| D 审核门禁 | 缺译段、重复段、错版本、译者自审、报告缺覆盖、报告后改译文、术语变更 | 每种情况都无法进入下一阶段；修正并重新审核后通过 |
| E 初学者注释 | 原注与译者注混淆、孤立引用、ID 冲突、例子冒充原文、无说明的章节 | 注释独立标记、双向链接有效；复杂段落有解释或 reviewer 的明确无需注释理由 |
| F 编排集成 | 真实 epub-editor 退出 0/1/2、输出存在、最终文本改变、元数据回读、资源保留 | 仅正确通过可交付；原书不变；最终内容与审核版本一致 |
| G 安装验收 | fresh checkout、两个插件不同缓存目录、旧/新版本混用、市场源为 openai | 官方结构/技能校验通过；独立配置下 marketplace 能安装并发现全部技能 |
| H 真实 agent 冒烟 | 自编 2–3 章外文样本，含哲学/逻辑难段、原注、跨章术语与可发现错误 | 真实并行译者 + 独立逐章 reviewer + 内部 translation-review 全书终审 + EPUB 编排全流程 |

确定性测试只能证明结构与门禁。语义案例另以原文、译文、reviewer 证据验收。用户未提供真实书籍，本次不会声称已完成某本书的翻译。

## 7. 分发与完成定义

- Plugin Creator 产出符合规范的单插件包，包含真正用到的技能、脚本与参考文件；EPUB 编排作为唯一明确要求安装的外部配套组件。
- 按已调用 Plugin Creator 的创建流程创建私有插件，记录真实返回 ID/版本；失败时保留本地可安装包，准确报告创建状态。
- 仓库 marketplace 是主要可复现交付。注册/安装测试不覆盖现有用户全局 marketplace；使用隔离配置，保留现有 `openai` 来源。
- 以当前分支的差异交付，不自动推送、合并或公开发布。是否建立 PR 可在实现完成后由用户决定。
- 只有实际验证后才报告“已通过”。区分：结构测试、依赖集成、真实 agent 样本、EPUBCheck、阅读器展示及托管创建状态。

## 8. 方案审核与决策门

使用 Agentic Review 的理解、反例、验证三轮视角审核本方案；风险 Tier 2（跨插件接口、长任务状态、用户可见译文与产物完整性）。

已处理的设计问题：

1. **错误开发分支**：定位到 `openai`，使用其独立工作区，避免在 main 补造另一个 Codex 市场。
2. **依赖调用是空约定**：采用真实技能路径、身份/契约校验、参数化 CLI 与安装后集成测试。
3. **原 review 技能不支持译文**：新插件内部添加翻译专用审核技能，不能把代码审核报告当成翻译终审。
4. **按文件分章会漏内容**：内容边界与完整资源清单分离，所有源文都有唯一去向。
5. **模型返工后复用旧审核**：摘要绑定与版本失效规则覆盖章节、术语表、全局报告和导出后读回。
6. **初学者注释篡改作者意思**：原文与新增解释严格区分，注释单独审核，全文翻译不得缩写成讲义。

设计时验证状态：方案/官方接口/仓库阅读 `VERIFIED`；现有 EPUB 编排的 26 项基线测试 `PASSED`；新实现、跨插件安装、真实 agent 翻译、最终 EPUB 当时为 `NOT_RUN`。设计审核见 [审核记录](../reviews/2026-09-27-book-translator-design-review.md)，实现后的实际结果另见 [验收记录](../reviews/2026-09-27-book-translator-validation.md)。

已确认实施范围：新增书籍翻译插件及其内部审核技能，集成现有 EPUB 编排；Agentic Review 与 EPUB 编排源码均不改动。仅修改 `openai` 派生工作区。

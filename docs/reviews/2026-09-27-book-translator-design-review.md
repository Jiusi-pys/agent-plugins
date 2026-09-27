# 书籍翻译插件方案审核

日期：2026-09-27。

## 结论

方案已覆盖当时查明的接口问题，可作为 TDD 实施依据；用户已要求翻译审核完全内置于新插件。本文件保留实现前的设计结论，不构成插件可用性的结论；实现后的结果见 [验收记录](2026-09-27-book-translator-validation.md)。

审核使用 Agentic Review 的理解、反例与验证三个视角，由当前 agent 执行；没有将这三轮描述为独立模型审核。

## 已纳入方案的问题

| 问题 | 事实依据 | 方案中的解决约定 | 必须补上的执行证据 |
| --- | --- | --- | --- |
| 在错误分支实现会缺少目标依赖 | 原始 checkout 为 main；配置的市场跟踪 openai；origin/openai 包含目标插件 | 从 origin/openai 建立独立工作区 | 后续 diff/安装来源均针对该分支 |
| 通用代码审核不等于书籍翻译终审 | agentic-review 当前 SKILL.md 的适用范围仅列代码与软件设计 | 在新插件内部增加 translation-review 技能，保留 Agentic Review 原样 | 原文到译文的全量覆盖报告及真实技能执行 |
| 插件名称不能作为可执行 API | OpenAI 包格式未提供任意跨插件自动安装的已验证接口；缓存布局与源码布局不同 | 从启用技能解析真实路径，核对身份/契约，显式调用真实脚本 | 不相邻安装目录下的真实集成测试 |
| 按文件拆章及只看 spine 可漏原注 | EPUB 阅读顺序、目录锚点、manifest 资源各有不同职责 | 内容拆分与全资源覆盖清点分别记录 | 一文件多章、原注在非 spine 文件等测试 |
| 已通过的审核可因后续编辑失效 | 译文、术语和注释都可能在终审/编排前后改变 | 审核绑定摘要，返工使批准失效，编排后读回 | 过期审核、返工、实际输出变化的拒绝测试 |
| 产出文件不代表编排成功 | epub-editor 退出码 2 会留下带 issues 的输出 | 退出 0 且 issues 为空，之后读回对照 | 对退出 0/1/2 和异常输出的集成测试 |

## 审核范围与依据

- 意图：`stated`，来自用户本次创建插件请求及“面向初学者，增加解释与案例”的回复。
- 目标：[实施方案](../plans/2026-09-27-book-translator.md)。
- 软件基线：origin/openai，`f145ea79e09ff67bb7b4f1a70139b122814630d3`。
- 直接证据：现有 marketplace、Agentic Review 的适用范围、EPUB 编排的技能/manifest/脚本、Codex CLI 帮助与 marketplace 来源。外部运行依赖只有 EPUB 编排。
- 官方资料：OpenAI [插件打包](https://developers.openai.com/plugins/build/plugins)、[技能构建](https://developers.openai.com/plugins/build/skills)、[sub-agents](https://developers.openai.com/codex/subagents)。本次已读取页面正文。
- 不在本次设计审核结论中：新代码可运行性、某本实际书籍的翻译质量、所有阅读器的显示效果。

## 风险分级

Tier 2。理由是跨插件协作、长期作业状态和面向用户的文本完整性；原文件只读且使用新输出路径，修改可撤回。现有流程不需要修改系统配置、上传用户书籍到额外翻译服务或改动开发板。

## 设计审核时的证据清单

| 检查 | 结果 |
| --- | --- |
| 分支、市场来源及目标依赖核验 | PASSED |
| 已有 EPUB 编排测试：`python -m unittest discover -s plugins/epub-editor/tests -v` | PASSED，26 tests |
| 官方插件/技能/sub-agent 文档正文核查 | PASSED |
| 新插件失败测试与实现 | NOT_RUN，待实施 |
| 安装目录与跨插件运行验证 | NOT_RUN，待实施 |
| 真实译者、逐章 reviewer 和全局审核样本 | NOT_RUN，待实施 |
| 最终 EPUB / EPUBCheck / 阅读器验证 | NOT_RUN，待实施 |

## 需确认的产品决定与剩余风险

- 实施范围涉及新建 book-translator，及其内部翻译审核技能；现有 Agentic Review 不改动。
- 初学者注释为新增解释层，保留完整译文。注释数量由难点决定，不机械地为每个段落增加案例。
- “完整审核”以逐段覆盖和版本一致的证据定义，不承诺语义判断绝对无误；高难度/有争议译法可能仍需用户裁定。
- 首版明确识别不支持的内容，不能把扫描正文或不支持的资源计作完成。具体支持集由测试证明。
- 用户已修订审核范围并对齐；下一阶段开始 TDD，后续验收按各证据层单独报告。

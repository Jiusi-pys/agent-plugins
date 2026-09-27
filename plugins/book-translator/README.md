# 书籍翻译

把用户提供的外文 EPUB 翻译成新的简体中文 EPUB：联网核实书名/作者译名，按内容分章并行翻译，每章由独立 reviewer 全文复审，再经过本插件内部的全书终审，最后调用 **EPUB 编排** 输出文件。

默认面向初学者，以明确标注的“译者注”和“辅助案例（假设示例）”解释难点；原书论证、原注和插图保留。输入文件不会被覆盖。

## 组成与依赖

- `book-translate`：翻译作业协调、译名检索、并行调度与 EPUB 交付。
- `translation-review`：插件内部的章节/全书审核技能，默认不隐式触发，供翻译流程明确调用。
- Python 工具：内容清点、不可变原文快照、逐段覆盖/版本门禁及 EPUB 编排适配器。
- 唯一外部插件：已启用的 `epub-editor:epub-edit`（支持当前 `0.1.x` CLI）。**不修改、不依赖独立 Agentic Review 插件，也不添加一个独立的 translator-review marketplace 插件。**

运行环境需要 Codex 的本地文件、真实 sub-agent 与联网搜索能力，以及 Python 3.11+、`lxml` 和 `Pillow`。不需要单独的翻译 API key。没有 sub-agent 能力时会报告受阻，而不会假装已完成并行独立复审。

## 使用

先从本仓库 Codex marketplace 安装 `epub-editor` 和 `book-translator`。新插件尚未推送到远程前应使用本地开发来源；[依赖说明](skills/book-translate/references/dependencies.md) 给出了源检查与安装步骤。

在新聊天中提供 EPUB 路径，例如：

> 用书籍翻译将这本 EPUB 翻译为简体中文，面向初学者解释哲学和逻辑难点，逐章独立复审后输出新版 EPUB。

或：

> 继续这个翻译作业目录，检查哪些稿件或审核已过期，完成中文版 EPUB。

作业首次准备后需由 agent 根据真实检索填写 `profile.json`。用户无需手写这些 JSON；它们是透明可检查的中间材料。

## 实际流程与可验证边界

1. 检查当前启用的 EPUB 编排技能与真实脚本路径；锁定版本和文件摘要。
2. 按 spine、目录锚点和标题建立内容章节，清点非 spine 注释、目录、文本属性和保留资源。
3. 共享译名与术语表，按宿主并发上限派出多个 translator。每章专属 reviewer 与译者为不同实例。
4. 审核全文含义、中文通顺、初学者解释/例子和所有原样保留项目。默认最多三轮自动修订，不能自行降级通过。
5. 新的 global reviewer 加载本插件内部 skill，全文分批对照并检查跨章一致性。
6. 所有报告覆盖完整、无未解决问题且摘要匹配后，运行现有 EPUB 编排脚本；读回最终文本、元数据、资源、目录与脚注链接，再写入新的输出路径。

源文、inventory 或依赖发生改变须重新准备；profile 改变使旧译稿失效；改稿使旧章节审核失效；章节稿/报告改变使旧全局审核失效。检查不会接受“曾经通过”的陈旧记录。

身份和 coverage JSON 是可信协调者的工作记录，不能从数学上证明 agent 确实阅读或保证语义无误。因此结构测试、实际 sub-agent 轨迹和语义审核报告分别保留。

## 支持范围

支持单 rendition、未加密的可重排 EPUB 2/3、普通 XHTML 正文和 NCX/nav；支持一文件多章、续章跨文件、非 spine 注释、长段落分块。XML 标签、链接、公式/代码等受保护。章节切分存在歧义、目录损坏、重复锚点、固定版式、扫描正文或 SVG 文字需要明确处理，不能默认为全文完成。

输入压缩包最多 128 MiB，解压资源总量 256 MiB、单资源 32 MiB、最多 10,000 条目；拒绝加密、签名、路径异常、ZIP 符号链接及 XML 实体。不会执行书内脚本或自动读取其外链。

首版只输出简体中文。原封面图片保持原样，图中文字不会自动翻译；初学者案例明确是假设。新译本使用新标识，原书出版信息记为来源，不借用某个商业中文版的 ISBN/译者身份。

内部结构检查并非完整 EPUBCheck。`reports/delivery.json` 初始明确记载 `epubcheck: not_run`；如进一步运行 EPUBCheck，应保存单独的实际命令和结果。脚注语义支持点击/返回，弹窗由具体阅读器决定。

## 开发验证

```text
python -m unittest discover -s plugins/book-translator/tests -v
python -m unittest discover -s plugins/epub-editor/tests -v
python plugins/book-translator/tests/smoke_install.py --repository <checkout> --test-home <new-isolated-directory>
```

`smoke_install.py` 使用子进程的隔离 Codex 配置目录安装实际市场包，不更改用户常用配置。它检查安装缓存并调用缓存中的脚本验证 EPUB 编排依赖。

`tests/create_demo.py <new-demo-directory>` 生成自编短篇示例；它不是下载的版权书籍，也不是翻译质量证明。真实 sub-agent 翻译和独立审核轨迹需另外记录。

详细格式见 [作业契约](skills/book-translate/references/job-contract.md)，完整使用规则见 [主技能](skills/book-translate/SKILL.md)。

# 书籍翻译插件验收记录

日期：2026-09-27。实现分支：`codex/book-translator`，基线 `origin/openai` 的 `f145ea79e09ff67bb7b4f1a70139b122814630d3`。

## 结果与范围

新增 `book-translator` 0.1.0，显示名“书籍翻译”，包含主技能 `book-translate` 与内部审核技能 `translation-review`。内部审核没有单独的 marketplace 条目，默认不隐式触发。唯一外部插件依赖为已有 EPUB 编排。

`git diff --exit-code -- plugins/agentic-review plugins/epub-editor` 通过：两个现有插件的源码未改动。本次修改仅在从 `openai` 派生的工作区；原始 main checkout 未用于实现。marketplace 已追加新插件，未推送、合并或改写用户常用 marketplace 配置。

## 确定性验证

| 检查 | 实际结果 |
| --- | --- |
| `python -X utf8 -m unittest discover -s plugins/book-translator/tests -q` | PASSED，34 项 |
| `python -X utf8 -m unittest discover -s plugins/epub-editor/tests -q` | PASSED，26 项，现有源码不变 |
| 系统 plugin-creator `validate_plugin.py` | PASSED，工作区和最终 ZIP 解包目录均通过 |
| 系统 skill-creator `quick_validate.py` | PASSED，两个技能均通过；Windows 使用 UTF-8 模式 |
| 最终 ZIP 内 `test_packaging.py` | PASSED，3 项运行，1 项仓库 catalog 测试按设计跳过 |
| Codex CLI 实际注册本地市场并安装两个插件 | PASSED，隔离配置目录中执行 |
| 安装缓存中的新插件 `doctor` 调用另一缓存目录中的 EPUB 编排 | PASSED，核对真实 manifest、skill、脚本摘要及 CLI 参数 |
| 安装缓存中的新插件实际调用当前启用的 EPUB 编排导出样本 | PASSED，编排退出 0、issues 为空，导出后再 inspect |
| 最终正文、已有定位点、链接、资源与中文元数据读回 | PASSED；允许编排为原本无 ID 的标题新增合法定位点 |
| `git diff --check` | PASSED；Windows 的 LF/CRLF 提示不属于错误 |

TDD 顺序已实际执行：先出现缺少实现的 RED，再分组实现到 GREEN。后续回归先复现了替换节点尾部文字丢失、扫描正文误判、原译者署名继承、无效示例 PNG、文档标题章界归属、插画者与作者角色混淆、长段落无法添加注释、编排新增标题 ID 被误拒等问题，再分别修复并回归。最终测试没有把夹具中的人工 approval 当作真实 agent 审核证据。

跨插件调用采用显式的已启用 skill 路径和参数数组，不假定缓存相邻，不把 MCP 依赖字段当成插件自动安装。运行锁固定版本与文件 SHA-256；依赖被改动、CLI 退出 2 或输出有问题时不交付文件。

隔离安装命令：

```text
python -X utf8 plugins/book-translator/tests/smoke_install.py --repository . --test-home .local/install-test-verified
```

实际报告为工作区 `.local/install-test-verified/install-evidence.json`。测试对子进程设置专用 Codex 配置目录，未修改用户正常配置。

## 真实 sub-agent 样本

使用 `tests/create_demo.py` 生成的自编英文短文 Small Arguments，内容是理由、确定性、必要条件与充分条件。它是功能验证样本，不是用户提供的真实出版书。

| 角色 | 宿主实际任务名 | 实际覆盖 |
| --- | --- | --- |
| 第一章 translator | `/root/demo_translate_1` | 6 个片段，3 条新增注释 |
| 第二章 translator | `/root/demo_translate_2` | 8 个片段，6 条新增注释 |
| 第一章专属 reviewer | `/root/demo_review_1` | 新作业全部 6 个片段及注释，approved |
| 第二章专属 reviewer | `/root/demo_review_2` | 新作业全部 8 个片段及注释，approved |
| 独立全书 reviewer | `/root/demo_global_review` | 全部 14 个片段、9 条新增注释及 1 条原注，approved |

两个 translator 使用真实并行任务；reviewer 与译者是不同实例。global reviewer 未参与章节翻译或章节审核，收到 START 后读取全部原文、当前译稿、原注与新增注释，使用本插件内部 translation-review。其报告含每个 segment 的原文/译文证据与判断，不以章节报告摘要替代全书阅读。

第一次样本发现装饰 PNG 无效与页标题章节归属不当后，保留旧作业为失败证据，创建 `.local/demo-final/job` 新作业；两位 translator 和两位 reviewer 均实际重新核对。最终全局审核仅针对新作业。

最终样本和证据路径（相对于本次工作区）：

- `.local/demo-final/Small Arguments.epub`：原创输入。
- `.local/demo-final/job/chapters/c0001/{translation,review}.json`。
- `.local/demo-final/job/chapters/c0002/{translation,review}.json`。
- `.local/demo-final/job/reviews/global.json`：全文审核及逐段证据。
- `.local/demo-final/job/reports/delivery.json`：实际导出和读回结果。
- `.local/demo-final/小论证-中文版.epub`：最终样本。

源 EPUB SHA-256：`d98b6f10dd55cf37f53c0a58ff5dc6d8b1f489580fb773a852bf61c89ccc77c8`。导出后原文件和作业快照摘要相同。

全书批准 bundle SHA-256：`9a7196eddc7bd5ce1ebcdf9634db28c17abd5573d32dadc87b15de965517c161`。

输出 EPUB SHA-256：`c929d18a3501bc7069ccb2beb6f8bea0649d8dce45f822a5fcf928696ec53afe`。

输出元数据为《小论证》、示例作者、`zh-Hans`，使用新的 UUID 并保存原版来源。正文、9 条新注释和原注均保留；生成中文目录，10 个注释引用的本地目标有效。新增解释与假设案例分别明确标注，具备返回正文的链接。封面/插图资源保持原样。

## 打包与 Plugin Creator

最终 ZIP 为 `.local/dist/book-translator-0.1.0.zip`，共 26 个文件、50,862 字节；包含 portable manifest、兼容层、两个技能及所需脚本/模板/契约/自编测试，未包含缓存、用户书籍、作业报告、符号链接或其他插件。

ZIP SHA-256：`358b65f974ff897da0b84f3807e243aff966561f35ee7abc470a3e0c8ef91fbc`。

Plugin Creator 已实际创建私有插件，状态 `created`：

- 插件 ID：`plugins_6ab85f37cf908191aead7c312a262d6a`。
- 版本：`0.1.0`。
- Release ID：`pluginrel_6ab85f385f188191b148b84baf0b9ec2`。
- [查看书籍翻译](https://chatgpt.com/plugins/plugins_6ab85f37cf908191aead7c312a262d6a)。

托管创建成功表示包已保存，不能替代 Codex 本地运行能力或外部 EPUB 编排安装。本插件的实际运行仍要求本地 Python、联网检索和真实 sub-agent；不会假装通过 manifest 自动安装其他技能插件。

## 未验证项与适用边界

- **EPUBCheck：NOT_RUN**。本机未发现 Java/EPUBCheck；内部 XML、链接与资源检查不能替代它。
- **实际阅读器展示与脚注弹窗：NOT_RUN**。已验证引用/返回链接和语义标记，未承诺具体阅读器弹窗效果。
- **真实出版书的通行译名检索：NOT_RUN**。本样本为 original_sample；技能明确要求真实书先联网核实并记录出处。未把示例名称冒充大众译名。
- **完整长篇书籍的语义质量：NOT_RUN**。长段拆分/注释有确定性测试，但真实 agent 冒烟仅覆盖自编的两章短文。模型全文审核不能证明绝对无错。
- **Linux CI：NOT_RUN locally**。已添加 Ubuntu/Windows 的 GitHub Actions 配置，尚未在远程触发；本次实际测试运行于 Windows。
- **远程仓库分发：未执行**。marketplace 集成在 `codex/book-translator` 工作区中；用户常用 Git marketplace 在推送前不会自动获得这些源码变更。

计划与设计依据见 [实施方案](../plans/2026-09-27-book-translator.md) 和 [实现前设计审核](2026-09-27-book-translator-design-review.md)。

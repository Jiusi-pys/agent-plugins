---
name: book-translate
description: 将用户提供的外文 EPUB 翻译成带注释的简体中文 EPUB，或恢复已有翻译作业。联网核实书名作者，按内容分章并行派出 translator 和独立 reviewer，使用本插件内部 translation-review 全书终审，然后调用已安装的 EPUB 编排。适用于完整书籍翻译，不用于仅改元数据、摘要或网页书籍下载。
---

# 书籍翻译

默认读者为初学者。忠实保留作者完整论证，以清晰中文翻译；难点另加“译者注”与“辅助案例”。不把整书改写成摘要或讲义。

本插件自带 `../translation-review/SKILL.md`，它借鉴证据分层和反例复核的思路，但完全属于本插件。**不读取或改动另一个 agentic-review 插件来完成翻译终审，也不要求安装它。**

## 启动与依赖

1. 向用户简述工作流程。输入路径、输出要求已明确时直接执行。缺少实际 EPUB 时索取文件，不声称已翻译；已有工作目录则先运行 `status`，恢复已有作业。
2. 检查本地文件访问、网络搜索及真实 sub-agent 能力。缺少 sub-agent 时报告此阶段受阻；不能用主 agent 自演多个角色冒充并行或独立审核。使用宿主原生 sub-agent 工具，不创建用户侧的新聊天，不调用未经配置的翻译 API。
3. 从当前**已启用技能目录**定位 `epub-editor:epub-edit`，读取其 SKILL.md，得到实际插件根路径。若来源同名或未启用，明确报告；开发时可显式指定仓库内的路径。禁止猜测 `../epub-editor`、硬编码版本缓存路径或用“最大版本目录”替代当前启用版本。
4. 本技能所在目录向上两层是插件根目录。使用 `<book-root>/scripts/book_translate.py`。Python 环境需要 requirements.txt；缺失时在作业附近创建虚拟环境安装依赖，不修改全局 Python。记录实际解释器。
5. 运行：

   ```text
   python <book-root>/scripts/book_translate.py doctor --epub-editor-root <resolved-editor-root>
   python <book-root>/scripts/book_translate.py prepare <source.epub> <new-job-dir> --epub-editor-root <resolved-editor-root>
   ```

   预检验证身份、CLI 能力和文件摘要。缺失/不兼容依赖在耗费翻译工作之前解决。不要编造插件 API 或 manifest `dependencies` 字段。安装细节见 [依赖说明](references/dependencies.md)。

## 清点、译名与术语

- `prepare` 只读原书并生成不可变快照、inventory 和章节目录；按 spine 与顶层目录锚点切分，不按 ZIP 文件名。无目录时用标题；跨文件续章、非 spine 原注和导航辅助任务都必须处理。
- 查看清点输出与原书内容，确认章界适合本书。首版遇到错误目录、扫描正文、固定版式、SVG 文字等会拒绝或要求补充检查；不得手改 inventory 绕过检查。
- 阅读 [翻译规范](references/translation.md)，完成 `profile.json`：读者、文风、全书术语表、译名检索证据。优先查询出版社/图书馆的原文书名、作者、版次和 ISBN，交叉核对常用译名。真实书籍必须先尝试联网搜索；不能为了方便使用 `original_sample`。
- 找不到可靠译名时使用 `provisional`，记录检索及暂译依据；可继续翻译，交付前取得用户对暂译名的决定。`user_supplied` 仅用于用户直接指定的译名。不得臆造出版者、译者或中文版 ISBN。
- profile 由主 agent 单独维护；所有 translator 使用相同版本。改动 profile 会使旧稿失效，必须对所有章节重新确认、更新译稿输入摘要并复审，不能只改摘要掩盖未检查的术语变化。

## 按章并行与独立复审

1. 读取 `inventory.json` 的**全部**章节列表，包括 auxiliary 任务。为每章创建 translator 和不同实例的专属 reviewer；记录宿主返回的真实 agent ID/规范任务名。一章可分批读取，但不是跳过剩余内容。
2. 按当前宿主并发容量调度，多章译者可并行。控制活动数量、等待与回收；容量不足时排队，不把全书所有 agent 一次性派出。不要覆盖用户选定模型，未指定时继承当前模型。
3. 分别使用 [translator 任务模板](templates/translator.md) 和 [reviewer 模板](templates/reviewer.md)。worker 只写自己的章节文件。主 agent 独占 job.json、profile 和全局汇总的写入。
4. reviewer 初始可读取技能，但在主 agent 登记身份并发送 START 之前不得读取尚未完成的稿件。登记：

   ```text
   python <script> assign <job> <chapter> --translator <actual-translator-id> --reviewer <actual-reviewer-id>
   ```

5. 每章用 `packet <job> <chapter> --start 0 --count 12` 读取有界批次，推进到 `next_start == total_segments`；按上下文负载减小 count。同一章节的所有批次合并为唯一 `translation.json`，使用原子写入。保留所有受保护标签、代码、公式与链接；任何原样保留的文字必须逐段说明理由。
6. 主 agent 先运行 `check-chapter <job> <chapter> --draft-only`。成功后启动该章 reviewer，按内部审核 skill 全量对照原文、译文和注释，写 `review.json`。主 agent 再运行 `check-chapter`（不带 draft-only）。
7. reviewer 发现错译、缺漏、不通顺、解释不准确或初学者难点未得到解释时，返回译者修订；reviewer 只提证据与建议，不自行改稿或替译者签名。修改稿件后必须重新审核。
8. 默认每章最多三轮自动修订；仍有实质问题则保留作业与具体待决问题，不自动降低标准通过。一次中断不丢弃其他章节，恢复时运行 status；必要时更换 worker 后登记新 ID 并复审。

## 全书终审

全部章节通过后，派出新的独立 global reviewer，加载 **本插件** `../translation-review/SKILL.md` 的 global 模式。使用 [global 模板](templates/global-reviewer.md)。其身份不得属于任何章节的译者或 reviewer。

```text
python <script> assign-global <job> --reviewer <actual-global-reviewer-id>
python <script> global-packet <job>
python <script> check-global <job>
```

必须分批通读所有原文、译文与注释，再做跨章术语/概念/论证一致性检查。报告摘要和章节“已通过”不能替代全书阅读。global.json 绑定整个候选版本；返工后重跑受影响章审核与全局终审。详细数据格式见 [作业契约](references/job-contract.md)。

## EPUB 编排与最终交付

```text
python <script> finalize <job> <new-output.epub>
```

- 此命令再次验证依赖、章节/全局报告与版本，以参数数组调用真实 EPUB 编排脚本，并对最终文件做文本、元数据、链接与资源读回。退出 2、issues 非空或正文变化均不能交付。
- 中文 EPUB 是新的衍生产物，有新的标识与原版来源说明；封面图片和非目标资源原样保留，封面上原有外文可能仍然存在。若用户需要改封面，另依其图片和明确要求处理，不用自动生成图覆盖原封面。
- 运行可用的 EPUBCheck，保存命令、版本及输出；如未安装，清楚报告未运行，不把内部结构校验代称为 EPUBCheck。需要验证阅读器弹窗时实际打开样本；标准脚注语义不保证所有阅读器弹窗。
- 默认交付一个新的中文 EPUB 和简短结果说明。详细作业状态、原文映射与审核证据留在工作目录；不自动删除。明确区分结构验证、真实模型复审、EPUBCheck 与阅读器验证。
- 不承诺机器审核绝对无错。若缺少全文覆盖、需要裁定的译名、未解决问题或不支持内容，给出具体缺口，不把不完整稿件标为完成。

# 多格式书籍编排与转换方案

> 实施状态：十格式双向转换、依赖适配及回归已完成，当前插件版本 0.2.2。发布前 [US 全仓回归](../reviews/2026-10-11-plugin-us-full-suite.md) 为 279 通过、8 引擎测试跳过；本机补跑 8 项及 90 个转换方向全部通过。下文保留初始 0.2.0 方案，后续图注/阅读器能力见对应验收记录。

状态：已按独立设计审核、TDD、独立问题复测和真实引擎验收完成。用户已确认同时覆盖 TXT、EPUB、MOBI、HTML、Markdown、AZW3、DOCX、RTF、FB2、ODT 十种格式的导入与导出。十格式全部 90 个方向读回验证通过；完整结果与边界见 [验收记录](../reviews/2026-10-11-ebook-conversion-validation.md)。

## 目标和边界

- 保留 `epub-editor` 插件身份、`epub-edit` 技能及 `epub_editor.py` CLI，避免破坏 book-translator。新增 `ebook-convert` 技能和 `scripts/ebook_convert.py`。
- 新增统一 `convert(source, output, ...)`、`--doctor`、`--formats`，支持扩展名别名 `.htm`、`.markdown`，中文和空格路径；转换输出为新文件。十种格式任意跨格式组合经 EPUB 中转，原文件及已有输出不可覆盖。
- Calibre `ebook-convert` 负责容器格式、TXT、HTML 输入。Markdown 输入使用 Pandoc `markdown→epub3 --sandbox`：先验证并暂存输入目录内的图片，再在临时 Markdown 中替换为图片 data URI，避免 sandbox 读取外部文件并保留 fenced div、span 及标题 ID 语义。该修订解决真实 MD 往返中 Calibre 不识别 Pandoc 属性语法的问题。Pandoc 从 EPUB 输出 ODT、Markdown、HTML、RTF：均使用 `--sandbox`，HTML 为 `--standalone --embed-resources`，Markdown 为 `--extract-media=<output-stem>_assets`，RTF 必须 `--standalone`，利用 EPUB reader 的包内 mediabag 保留图片。引擎 warning 必须进入 `issues` 或失败状态，不能静默成功。RTF 输出采用 Pandoc 是真实验收后的修订：Calibre 自己导出的 RTF 再导入时报告新旧语法混用并不能转换部分属性；Pandoc standalone RTF 的同样样本可无诊断读回。
- 必要依赖可用 PATH、明确 CLI 路径或环境变量定位。缺少依赖要报可执行路径和安装方法，禁止自动改全局配置或把本机路径写入插件。真实验证使用工作区 `.local` 中的工具。
- 转换结果尽量保留章节顺序、正文、标题、图片及可承载的元数据。TXT 无法承载图片和样式，跨格式不能承诺无损；MOBI/RTF/Markdown/ODT 等降级在结构化 JSON 中说明。转换不自动套用 EPUB 目录/注释修复，编辑仍通过既有 CLI。

## 执行与资源发布

- 外部引擎采用参数数组与 `shell=False`，固定受支持格式和选项，设置超时，独立暂存目录及 Calibre 配置目录。诊断信息进入 JSON，真实失败、超时、缺少/空输出不能报告成功。
- 输出先暂存、校验，再以独占创建发布。HTML 图片内嵌为单文件，Markdown 图片发布到同目录 `<output-stem>_assets`，引用相对且不指向临时目录；资源目录冲突同样拒绝，失败需回滚本次新增输出。
- EPUB 输入沿用 `read_package` 拒绝加密、签名和异常压缩路径；产出 EPUB 验证包结构。解包资源必须限制体积、条目数和路径，禁止 ZIP 越界、符号链接、绝对路径和重复条目。明确区分结构检查与 EPUBCheck。
- 解包前同时拒绝 `.`、空路径段和 Windows 尾空格/尾点等路径别名，防止预检与引擎解包使用不同名称，产生隐藏资源覆盖。
- DOCX 全部 `.rels` 中的资源关系和 ODT 图片、字体、对象、manifest 目标在引擎前限定为已存在包内资源；DOCX 外部图片、`file://` 和包外路径拒绝。普通 HTTP(S)/mailto 超链接保留。所有容器 XML 禁止 DTD/entity/xml:base，FB2 样式与图片引用同样前置检查；用合成包外文件和本地 HTTP 服务验证拒绝不触发引擎与网络访问。
- HTML/Markdown 本地资源限定输入所在目录内，显式处理远程资源、不执行内嵌脚本，不接收任意过滤器或转换器命令。Pandoc sandbox 与图片嵌入存在冲突，必须以真实含图片样本确认方案，不以 sandbox 标签代替验证。
- EPUB 非 spine/non-linear 注释在 Pandoc 中转可能丢失：在仅供 Pandoc 读取的临时 EPUB 副本中将 `linear=no` XHTML 改为可读，并把正文 `noteref` 引用到的非 spine XHTML 注释文档加入阅读顺序，保留目标 ID 与引用锚点，报告此规范化步骤。无法解析的注释目标作为具体 `issue`，不能静默丢失后报告成功。原文件和 EPUB 编辑流程不改。HTML 产出需排除脚本、iframe、事件处理器与 javascript URL。远程资源 fixture 用本地 HTTP 计数检查不得产生请求；正常超链接可保留。
- 实际往返发现 Pandoc 的 RTF/ODT 输出没有供 Calibre 读入的原生书签：RTF 经受控 JSON AST 在实际内容范围写书签、映射名称并同步内部链接，图片从受限媒介目录转为 data URI；ODT section 补原生 bookmark 范围。每个引擎步骤继续使用 sandbox、fail-if-warnings 和共享总超时。临时 EPUB 的简单单图片 SVG 封面直接保留原始图片，复杂 SVG 打包为自含图像；不支持复杂 SVG 的 RTF 转换明确失败。

## OpenAI 包装

- 按官方文档保持根 `plugin.json` Agent Plugins 1.0 与 `extensions.com.openai`；兼容 manifest 同步身份、版本及展示信息，短描述不超过 30 字符。
- 保留图标、颜色、现有提示内容，补充多格式入口与转换损失说明。新增技能采用匹配文件夹的 YAML name/description，并把详细矩阵与依赖放到 references。
- 版本提升到 `0.2.0`。book-translator 依赖适配器在回归通过后允许 `0.2.x`；旧 CLI 和旧 `0.1.x` 仍受支持。不给其他插件增加转换行为。
- 修改 Git 管理源码，生成干净 ZIP；不改安装缓存，不在没有明确发布要求时推送或改线上共享版本。

## TDD 与验收

1. 先跑原有 EPUB 与 book-translator 测试获得基线。
2. 先添加格式别名、路由、依赖缺失、非法格式、输入/已有输出保护、超时/失败/假成功、资源冲突/越界、JSON CLI 与包装一致性的失败测试。
3. 实现到这些测试通过；另加真实引擎验收（显式开启，依赖不可用时不能冒充已运行）。
4. 使用自制含中文、英文、两章、图片、超链接的 EPUB/文本样本，覆盖十格式全部 90 个有向跨格式组合，均读回 EPUB 检查正文标记和章节顺序。单独检查可承载格式实际引用图片的尺寸、像素，以及正文跨文档引用的非 spine 注释、book-translator 风格 `linear=no` 注释和普通链接指向已标记注释：HTML/Markdown/ODT 输出中必须保留注释全文，引用链接有唯一目标。ODT/DOCX/MOBI 等不能只检查文件存在。
5. 全部插件回归、manifest/技能/ZIP 内容校验；保留验证记录及未验证的阅读器/平台行为。

## 官方依据

- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/build/skills
- https://manual.calibre-ebook.com/faq.html#what-formats-does-calibre-support-conversion-to-from
- https://manual.calibre-ebook.com/generated/en/ebook-convert.html
- https://pandoc.org/MANUAL.html

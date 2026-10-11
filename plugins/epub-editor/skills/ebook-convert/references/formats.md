# 格式、依赖与转换差异

插件 `epub-editor` 0.2.2 提供十种格式的导入与导出。任意两种不同格式均通过 EPUB 中转；输入本来就是 EPUB 时直接进入目标导出阶段。中间文件仅存在于隔离的临时目录，不修改原书。纯转换不自动应用 0.2.1 的标准图注/上标编排。

## 十种格式路由

| 格式 | 扩展名 | 导入到 EPUB | 从 EPUB 导出 | 需要注意的差异 |
| --- | --- | --- | --- | --- |
| TXT | `.txt` | Calibre 文本输入 | Calibre 文本输出 | 不承载图片、样式和交互注释；原文本没有的目录层次与元数据不能复原 |
| EPUB | `.epub` | 包结构检查后作为中间格式 | 校验后发布中间 EPUB | 保留可承载的结构，跨格式往返仍可能改变样式；内部检查不等于 EPUBCheck |
| MOBI | `.mobi` | Calibre MOBI 输入 | Calibre MOBI 输出 | 旧式排版、CSS 与目录能力有限；不保证阅读器弹窗注释 |
| HTML | `.html`、`.htm` | 检查本地资源后由 Calibre HTML 输入 | Pandoc 独立 HTML，内嵌图片 | 导出为单文件；脚本、事件处理器与不安全 URL 被排除，复杂 CSS 可能简化 |
| Markdown | `.md`、`.markdown` | Pandoc Markdown 输入，`--to=epub3 --sandbox` | Pandoc Markdown，提取图片 | 图片侧车目录为 `<output-stem>_assets`；EPUB CSS 和阅读器注释语义可能降级为链接 |
| AZW3 | `.azw3` | Calibre AZW3 输入 | Calibre AZW3 输出 | Kindle 格式及设备排版差异；仅处理未加密内容 |
| DOCX | `.docx` | Calibre DOCX 输入 | Calibre DOCX 输出 | 分页、表格、字体、脚注等复杂布局可能重排，不能据文件存在断言保真 |
| RTF | `.rtf` | Calibre RTF 输入 | Pandoc 独立 RTF，`--standalone --sandbox` | 样式、图片与复杂结构的承载能力有限，需检查实际产物 |
| FB2 | `.fb2` | Calibre FB2 输入 | Calibre FB2 输出 | 以 FictionBook XML 结构承载章节和元数据，EPUB CSS 和交互能力不完整 |
| ODT | `.odt` | Calibre ODT 输入 | Pandoc ODT，图片内嵌文档包 | 文档版式、分页与 EPUB CSS 不等价；注释需检查正文和引用目标 |

例如 `.docx` → `.md` 的路由为 Calibre → 临时 EPUB → Pandoc；`.md` → `.azw3` 为 Pandoc Markdown 输入 → 临时 EPUB → Calibre，需两个引擎；`.md` → `.epub` 由 Pandoc 生成并校验 EPUB 3，只需 Pandoc。目标格式由输出扩展名确定，不接受自定义引擎命令或任意过滤器。

## 编码与文件

- TXT、HTML、Markdown 默认以 UTF-8 读取；GB18030 原书使用 `--input-encoding gb18030`。输出文本使用 UTF-8。容器格式的包内编码由相应引擎处理，不能用文本编码参数修复损坏的容器。
- `.htm` 和 `.markdown` 只是别名，不增加格式种类。未知扩展名在运行引擎前被拒绝。
- 输出先写入临时目录并校验，再以独占创建发布；原文件、已有输出以及已有 `<output-stem>_assets` 目录均不覆盖。出现失败时回滚本次新增产物。
- Markdown 文件及图片侧车必须一起移动或交付，图片引用使用相对路径，不能指向临时目录。HTML 将图片嵌入输出单文件；ODT 使用包内图片资源。
- Markdown 输入保留 Pandoc 的 `fenced_divs`、`bracketed_spans`、标题 ID 与引用语义；不要为了清理外观删除影响正文定位的 ID。已核查的本地图片仅在临时输入副本中改为 data URI，供 Pandoc sandbox 读取；原文件及资源不修改。
- 本地资源限输入所在目录内；书内远程图片、脚本与异常路径不会被当作可自由访问的资源。转换结果不包含由插件主动下载的远程图片。

## 资源检查

DOCX/ODT 输入在运行引擎前检查，输出在发布前再次检查：

- DOCX 扫描全部 `.rels`。图片、字体、模板等资源 relationship 只能指向实际存在的包内目标，拒绝 `TargetMode=External`、文件 URI、绝对路径、包外和缺失目标；正常 HTTP(S)/mailto 的 hyperlink relationship 单独保留，不误当作图片资源。
- ODT 检查 `content.xml`、`styles.xml` 等包内 XML 的资源链接及 manifest 中的路径。图片、字体与嵌入对象需存在包内，嵌入对象目录需含包内文件；普通 HTTP(S)/mailto 超链接可以保留，外部资源或越界路径会被拒绝。
- DOCX/ODT XML 解析使用 `resolve_entities=False`、`no_network=True`，拒绝 entity/DTD 和 `xml:base` 重定向。检查仅使用包内字节，不打开外部文件或请求网络。
- FB2 的图片与 CSS stylesheet 在引擎运行前校验。资源 URL 仅接受经校验的图片 data URI 或存在的 `#binary` 图片，`url(...)`、`@import` 等指向外部 CSS/图片的引用会被拒绝，不读取目标内容。

## 依赖定位与安装

Python 依赖见插件根目录 `requirements.txt`，在工作目录虚拟环境中安装。转换引擎不在 Python requirements 内：

- Calibre：使用完整安装或便携版中的 `ebook-convert` / `ebook-convert.exe`。保持其运行库和资源目录完整，不只复制单个可执行文件。[官方安装](https://calibre-ebook.com/download)、[官方格式支持](https://manual.calibre-ebook.com/faq.html#what-formats-does-calibre-support-conversion-to-from)、[CLI 参数](https://manual.calibre-ebook.com/generated/en/ebook-convert.html)。
- Pandoc：Markdown 导入和 HTML、Markdown、ODT、RTF 导出需要 `pandoc` / `pandoc.exe`。[官方安装](https://pandoc.org/installing.html)、[官方手册](https://pandoc.org/MANUAL.html)。Markdown 导入使用 `--from=markdown --to=epub3 --sandbox`；RTF 导出使用 `--to=rtf --standalone --sandbox`，RTF 输入仍由 Calibre 读取。无需把 Pandoc 用于 Calibre 已处理的其余路由。

定位顺序为显式参数 `--calibre <actual-executable>` / `--pandoc <actual-executable>`、环境变量 `CALIBRE_EBOOK_CONVERT` / `PANDOC_PATH`、PATH、Windows 常见安装目录。用 `--doctor` 检查当前可执行文件与版本；输出 `available`、`path`、`version` 与 `issues`，缺失或不可执行时退出 `1`。检查不会自动安装工具或修改全局 PATH，也不把当前机器的路径写入 manifest 或技能。用户授权本地环境准备后，使用工作目录中的工具或虚拟环境，保持插件包独立于该环境。

`--doctor` 检查两个引擎，转换只要求当前路由用到的引擎。Markdown 输入需 Pandoc，其余非 EPUB 输入需 Calibre；HTML、Markdown、ODT、RTF 输出需 Pandoc；TXT、MOBI、AZW3、DOCX、FB2 输出需 Calibre。Markdown 转 EPUB 只需 Pandoc，Markdown 转 AZW3 需两个引擎。EPUB 输入转 HTML、Markdown、ODT、RTF 不依赖 Calibre，EPUB 输出直接发布已检查的中间 EPUB。

## 注释、降级和验收

转换成功退出 `0`，标准输出 JSON 包含 `output`、`input_format`、`output_format`、`engines`、`assets`、`warnings` 和空 `issues`。`warnings` 说明处理器已识别的格式能力差异或临时注释规范化。引擎 warning、非零退出、超时、缺少或空输出和结构错误均退出 `1`、报告 `issues` 并阻止发布；引擎普通转换进度不等同于 warning。

跨格式转换会改变容器、布局与阅读器语义。无法确认的特性不能标作无损保留。TXT 本身无法保存原书的图片和样式，从 TXT 转回 EPUB 也不会恢复它们。

Pandoc 的 EPUB reader 依阅读顺序读取内容。转 HTML、Markdown、ODT、RTF 时，处理器为临时副本中的 `linear=no` 注释补齐阅读顺序，把正文 `noteref` 指向的非 spine XHTML 注释加入可读序列，并保留目标格式可承载的引用和 ID。该步骤需要在报告中说明，原 EPUB 不改。找不到注释目标或无法唯一映射时必须报告具体问题，不能静默丢弃注释全文。

目标格式还需要以下适配，RTF/ODT 输入路由仍保持 Calibre：

- RTF 输出在受控 Pandoc AST 中，按被引用内容的目标范围写入原生书签；原 ID 映射为合法书签名，内部链接同步引用该名称。该步骤保留正文定位，不能仅用空锚点代替目标内容范围。
- ODT 输出在 section 内补原生 bookmark，使内部链接具有目标格式可识别的书签。真实读回时仍需检查目标是否唯一，以及其正文内容是否正确。
- 临时 EPUB 中的内联 SVG（包括已有封面）转为实际包内图像资源，再供 Pandoc 导出。HTML 将这些图像内嵌到单文件，Markdown 将它们写入图片侧车目录；原 EPUB 与原封面内容不修改。

用户要求图片下方图注、来源及小号上标时，先转成新暂存 EPUB，再调用 `epub_editor.py <imported.epub> <standard.epub> --reading-style standard`，必要时才从编排结果导出新目标文件。原有明确图注为 `figure/figcaption` 内的 `p`，来源用 `span epub:type=credit`，图注 `0.85em`；引用保留真实链接目标并使用 `0.75em` 单次上标。`preserve` 保留布局并补语义，`--metadata-only` 跳过布局。完整命令及报告阻断见 [reading-style.md](../../epub-edit/references/reading-style.md#非-epub-的标准编排)。每步退出码非零或外层 `issues` 非空都停止，转换和编排 JSON 分开保存。

EPUB 点击弹窗显示翻译依赖阅读器读取 `noteref` / `footnote` 与正文引用映射。Jiusi-pys/ebooks 的 2026-10-11 本地 Web 适配已验证包内插图、图注和小字号按钮/Popover，配套源码尚未部署；旧书需在新版中重新导入，布局缓存不跨设备同步。转换后保留注释文本或超链接，不能推出 HTML 浏览器、Markdown 预览器、Word、Kindle 或 ODT 阅读器采用相同弹窗行为。使用 [epub-edit 技能](../../epub-edit/SKILL.md) 的编排与阅读器契约，分别记录静态结构与实际交互证据。

真实验收应检查正文标记、章节顺序、图片实际存在及注释链接的目标内容，不能只检查输出文件存在。引擎 smoke test、内部结构检查、EPUBCheck 和特定阅读器测试应分别标注是否已执行。本插件不提供 DRM 解除或任意格式无损保证。

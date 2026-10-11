# EPUB 编排

`epub-editor` 0.2.2 在 TXT、EPUB、MOBI、HTML、Markdown、AZW3、DOCX、RTF、FB2、ODT 十种格式之间双向转换，同时提供 EPUB 元数据编辑、字数统计、目录定位、标准图注/来源、上标注释编排和用户封面替换。所有处理输出为新文件，保留原书；跨格式转换会受到目标格式限制，不能保证无损。

| 需求 | 技能与 CLI |
| --- | --- |
| 十种格式任意跨格式转换 | [ebook-convert](skills/ebook-convert/SKILL.md)，`scripts/ebook_convert.py` |
| EPUB 书名、作者、出版信息、字数、目录、图注、上标注释、用户封面 | [epub-edit](skills/epub-edit/SKILL.md)，`scripts/epub_editor.py` |

## 安装与依赖

从本仓库的 `jiusi-agent-plugins` Codex marketplace 安装 `epub-editor`。尚未发布的源码变更需要用实际本地 checkout 作为 marketplace 来源；安装缓存不会因修改仓库自动更新，不直接编辑缓存。

在工作目录的 Python 虚拟环境中安装依赖：

```sh
python -m venv .venv
# 激活虚拟环境后，在仓库根目录执行：
python -m pip install -r plugins/epub-editor/requirements.txt
```

Calibre `ebook-convert` 负责 EPUB、Markdown 以外的格式导入，以及 TXT、MOBI、AZW3、DOCX、FB2 导出；Pandoc 负责 Markdown 导入和 HTML、Markdown、ODT、RTF 导出，EPUB 输出为经过检查的中间 EPUB。Markdown 转 EPUB 只需 Pandoc，Markdown 转 AZW3 需两个引擎；EPUB 转 HTML、Markdown、ODT、RTF 只需 Pandoc，RTF 输入仍由 Calibre 处理。可使用已有安装、工作目录中的完整便携工具包或明确 CLI 路径，无需修改全局 PATH。插件不会自动安装工具或修改全局配置。安装来源、编码选择、格式别名与十格式路由见 [formats.md](skills/ebook-convert/references/formats.md)。

## 格式转换

向技能提供输入路径和目标格式，例如：“把这本 MOBI 转成带图片的 Markdown，保留原文件并报告格式差异。”

```text
python plugins/epub-editor/scripts/ebook_convert.py --formats
python plugins/epub-editor/scripts/ebook_convert.py --doctor --calibre <ebook-convert-path> --pandoc <pandoc-path>
python plugins/epub-editor/scripts/ebook_convert.py input.mobi output.md --calibre <ebook-convert-path> --pandoc <pandoc-path> --timeout 120
python plugins/epub-editor/scripts/ebook_convert.py input.md output.epub --pandoc <pandoc-path> --timeout 120
python plugins/epub-editor/scripts/ebook_convert.py input.md output.azw3 --pandoc <pandoc-path> --calibre <ebook-convert-path> --timeout 120
python plugins/epub-editor/scripts/ebook_convert.py input.epub output.rtf --pandoc <pandoc-path> --timeout 120
python plugins/epub-editor/scripts/ebook_convert.py input.txt output.epub --calibre <ebook-convert-path> --input-encoding gb18030
```

十种格式任意跨格式组合均经 EPUB 中转，`.htm`、`.markdown` 分别是 HTML、Markdown 别名。TXT、HTML、Markdown 输入默认 UTF-8，也可显式使用 GB18030。中文和空格路径应加引号或作为独立参数传入。

纯格式转换不自动应用标准图注/上标，也不自动修改元数据、统计字数或换封面；需要标准编排时按下方流程单独执行。

Markdown 输入由 Pandoc 生成 EPUB 3，保留 `fenced_divs`、`bracketed_spans` 及标题 ID 等语义。本地图片通过核查后仅在临时副本中改为 data URI，以便在 sandbox 中读取；原 Markdown 与资源目录不改。

Markdown 产物包含 `.md` 及同目录 `<output-stem>_assets` 图片目录，交付或移动时需保留相对位置。HTML 导出为内嵌图片的单文件；ODT 图片嵌入文档包。已有输出和资源目录均拒绝覆盖。TXT 无法承载图片、样式及可点击注释，MOBI、RTF 等也有各自的降级；成功 JSON 的 `warnings` 会报告处理器识别的差异。转换退出 `0` 表示已校验并发布，退出 `1` 则报告 `issues` 并阻止发布，引擎 warning 同样视为失败。

导出前会在临时 EPUB 中把封面等内联 SVG 转为实际包内图像资源，使现有封面与正文图片一同进入 HTML 的内嵌图像或 Markdown 图片侧车；原书不修改。RTF 输出通过受控 Pandoc AST 按目标内容范围写入原生书签，将原 ID 映射为合法书签名并同步内部链接；ODT 输出在 section 内补原生 bookmark。RTF/ODT 输入仍由 Calibre 读取。这些兼容处理仍需真实读回验证正文定位、图片和链接目标内容。

EPUB 转 HTML、Markdown、ODT、RTF 时，仅在临时副本中规范化 `linear=no` 和正文引用的非 spine 注释，以便 Pandoc 读取注释全文。报告会说明规范化步骤及未解析的问题。转换保留目标格式可承载的注释文本和引用目标，不保证目标阅读器弹窗显示翻译。书内脚本不执行，远程图片不下载，仅接受用户有权处理的未加密内容，不提供 DRM 解除。

DOCX 的所有 relationship 资源及 ODT 的图片、字体、对象资源必须实际存在文档包内；外部图片、文件 URI、绝对路径和越界目标会在引擎运行前拒绝。普通 HTTP(S)/mailto 超链接可以保留。DOCX/ODT 的包内 XML 禁止 entity/DTD 和 `xml:base` 重定向。FB2 的图片与 stylesheet 资源也在运行前检查，只接受经校验的内嵌图片或 `#binary` 目标，拒绝外部 CSS/图片地址。检查不会读取这些外部目标。

## EPUB 编排

```text
python plugins/epub-editor/scripts/epub_editor.py input.epub --inspect
python plugins/epub-editor/scripts/epub_editor.py input.epub output.epub --reading-style standard --recount
python plugins/epub-editor/scripts/epub_editor.py input.epub preserved.epub --reading-style preserve
python plugins/epub-editor/scripts/epub_editor.py input.epub output.epub --cover cover.png
python plugins/epub-editor/scripts/epub_editor.py input.epub metadata.epub --metadata changes.json --metadata-only
```

完整编排默认 `standard`。明确关联的独立图片采用 `figure` 与最后一个 `figcaption`，图注/来源原段落保留为 `p`；图注字号为正文的 `0.85em`、无首行缩进，明确来源在 phrasing `span` 上标记 `epub:type=credit`。已解析注释引用为 `0.75em` 单次上标，保留真实 `href`、唯一 ID、`noteref` / `doc-noteref` 与键盘焦点，不重复缩小或抬高现有上标，不改动同一上标内无关文字。标记跟在被注释文字或图片说明之后，不覆盖到图片内。

不补造图号、图注、来源或替代文本，不猜测普通相邻段落，不移动行内图片或封面。集合注释使用包含列表的 `doc-endnotes` 容器，不直接赋给 `ol`，条目不错误套用 `doc-footnote` 或已废弃的 `doc-endnote`。样式限定在已识别节点，重复编排不增加嵌套上标或重复图注。布局规则与依据见 [reading-style.md](skills/epub-edit/references/reading-style.md)。

`preserve` 保留现有布局和 CSS，仍补目录/注释语义与明确指定的编辑。仅修改 EPUB 3 元数据时使用 `--metadata-only`，跳过布局并逐字节保留 OPF 外全部资源；该模式不能同时换封面。元数据 JSON 字段见 [metadata.md](skills/epub-edit/references/metadata.md)。封面仅使用用户提供的 JPEG/PNG。

非 EPUB 同时要求标准编排时，按下列顺序调用，每个输出及报告均选择新路径，逐步检查后才运行下一步：

```text
python plugins/epub-editor/scripts/ebook_convert.py source.docx work/01-imported.epub --calibre <ebook-convert-path> --pandoc <pandoc-path> --timeout 120
python plugins/epub-editor/scripts/epub_editor.py work/01-imported.epub work/02-standard.epub --reading-style standard
python plugins/epub-editor/scripts/ebook_convert.py work/02-standard.epub work/03-final.md --pandoc <pandoc-path> --timeout 120
```

为三次调用分别保存 `01-import.json`、`02-layout.json`、`03-export.json` 标准输出，不合并报告。任一步非零退出或 `issues` 非空都阻断后续；编排退出 `2` 即使已有 EPUB 也不能继续导出。读转换报告的 `warnings/engines/assets`，以及编排报告的 `reading_layout.mode/applied/note_markers/figures/captions/credits/warnings/popup_behavior` 与外层 `issues`。不确定或缺少图注作为布局说明报告，不能凭空补充。完整 PowerShell 阻断示例见 [安全命令流程](skills/epub-edit/references/reading-style.md#非-epub-的标准编排)。输入已为 EPUB 时跳过首步，最终输出 EPUB 时跳过末步；不能跳过编排后把纯转换称为已应用这些规则。

Jiusi-pys/ebooks 的 2026-10-11 本地 Web 适配已完成：包内 PNG/JPEG/GIF/WebP、原图注和来源在主阅读、参考窗及双语原文显示；图片旁及正文引用以 0.65em 上标按钮弹出完整注释，图注为 0.85em。布局保存在本地缓存，不进入同步章节；旧书需在新版阅读器中重新导入。该阅读器改动尚未提交、推送或部署。支持 [阅读器契约](skills/epub-edit/references/reader-contract.md) 的阅读器可以弹窗查看注释，不保证所有阅读器有相同行为；实际“不跳转”需点击后验证 URL、章节、阅读位置及关闭/键盘行为，静态链接检查不能证明。

0.2.2 同步更新配套阅读器契约。原有零高度点击区域已在阅读器源码中修复，并使用插件实际输出、真实解析器、IndexedDB 和 ReaderView 在隔离浏览器中验证普通点击、Enter/Escape、焦点恢复与不跳转。正文 24px 时，标记 15.6px、图注 20.4px；参考窗、双语原文、分页、双栏及 390px 窄屏阅读布局已验证。未测试真实账号站点、原生端或其他阅读器。

EPUB 编排 CLI 的退出码 `0` 表示结构处理完成，`2` 表示已生成输出但仍有待处理问题，`1` 表示失败。book-translator 仍使用该 CLI，兼容 `0.1.x` 和 `0.2.x`；新转换入口不改变其翻译行为。内部结构检查不等于通过 EPUBCheck，标准 EPUB 输出也不等于目标阅读器已显示插图或实现弹窗。

## 验证

在仓库根目录执行：

```text
python -m unittest discover -s plugins/epub-editor/tests -v
python -m unittest discover -s plugins/book-translator/tests -v
```

单元测试覆盖原有 EPUB 处理、包装和转换执行边界。真实转换验收还需实际运行 Calibre/Pandoc，检查正文、章节顺序、图片、注释全文及引用目标；不能只检查输出文件存在。实际引擎版本、测试命令与结果应写入验收记录。未运行的真实引擎、EPUBCheck 或阅读器检查应分别明确标注为未验证。

0.2.1 的布局验收需覆盖上标有效字号只应用一次、已有上标去重、明确图注/来源顺序、正文及资源保留、普通相邻段落不误移、无图注不造内容、跨文件注释、集合角色、metadata-only/preserve 及重复处理。阅读器交互需使用插件实际生成的 EPUB，静态结构、实际浏览器和其他阅读器分别记录。仓库根 README 链接的 0.2.0 转换验收记录保留为此前证据，不能代替 0.2.1 的重新验收。

真实引擎测试默认跳过；在 PowerShell 会话中提供实际引擎路径后启用：

```powershell
$env:TEST_CALIBRE = '<ebook-convert-path>'
$env:TEST_PANDOC = '<pandoc-path>'
python -m unittest discover -s plugins/epub-editor/tests -p '*integration.py' -v
```

该验收覆盖十格式全部 90 个跨格式方向、EPUB 读回的中文正文和章节顺序、可承载格式的图片，以及非 spine / `linear=no` 注释的 HTML、Markdown、ODT 输出。

2026-10-11 最终源码在 US Ubuntu 发现 141 项测试，133 通过、8 跳过、0 失败/错误。服务器未安装 Calibre/Pandoc，且根分区仅余约 279 MiB；这 8 项随后在 Windows 使用真实 Calibre 9.16.0 / Pandoc 3.8 全部补跑通过，包括 90 方向矩阵和“转换→标准编排→导出”流程。Linux 实际引擎兼容性仍未验证。全仓结果为 279 通过、8 跳过，详见仓库 `docs/reviews/2026-10-11-plugin-us-full-suite.md`。

配套阅读器此前的 4 项服务集成失败已另行先复现、后修复，阅读器提交 `b134b73` 已推送开发分支；US 扩展后的 55 项全部通过，无失败或跳过。修改只涉及 Mirror 笔记事件校验、合法回执和快照时间夹具及回归。详见仓库 `docs/reviews/2026-10-11-reader-us-fixes.md`；EPUB 前端适配仍未提交，生产未部署。

插件保留 `epub-editor` 身份与原图标颜色。根 `plugin.json` 使用 Agent Plugins 1.0，OpenAI 展示信息位于 `extensions.com.openai`，并与 `.codex-plugin/plugin.json` 兼容 manifest 同步。技能名称匹配目录，详细路由置于 references；包装依据为 [OpenAI 插件文档](https://developers.openai.com/plugins/build/plugins) 与 [技能文档](https://developers.openai.com/plugins/build/skills)（2026-10-11 核实）。

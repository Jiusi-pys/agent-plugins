---
name: ebook-convert
description: 在 TXT、EPUB、MOBI、HTML、Markdown、AZW3、DOCX、RTF、FB2、ODT 十种常规书籍格式之间双向转换，保留原文件，检查本地依赖并报告格式差异。需要规范图片图注、来源或注释上标时，先转为新 EPUB 再调用 epub-edit，必要时再导出；纯转换不自动应用布局。仅编辑 EPUB 时使用 epub-edit。
---

# 书籍格式转换

用插件根目录下 `scripts/ebook_convert.py` 转换用户提供的书籍。完整路由、编码、依赖定位和格式限制见 [formats.md](references/formats.md)。支持十种格式之间的任意跨格式转换；输出格式由目标文件扩展名决定，`.htm` 等同 `.html`，`.markdown` 等同 `.md`。

## 执行

1. 确定输入文件、目标格式和新的输出路径。保留原文件，已有输出文件或图片资源目录不可覆盖。中文与空格路径要作为独立参数传给 CLI。没有实际输入时可以说明用法，不能声称已转换用户的书。
2. 先运行 `--formats` 查看支持格式，用 `--doctor` 检查本地 Calibre `ebook-convert` 和 Pandoc。Markdown 输入使用 Pandoc，其余非 EPUB 输入使用 Calibre；Markdown 转 EPUB 只需 Pandoc，Markdown 转 AZW3 需两个引擎。可传入实际可执行路径；禁止硬编码插件缓存或本机安装路径，也不自动安装工具、修改全局 PATH 或全局设置。缺失时说明当前路由缺少的引擎和 [安装来源](references/formats.md#依赖定位与安装)。用户授权准备本地环境时，可在工作目录获取工具或安装 Python 虚拟环境依赖。
3. TXT、HTML、Markdown 默认使用 UTF-8。用户的文件是 GB18030 时显式指定 `--input-encoding gb18030`；先核对正文片段，不能把乱码当作成功输出，也不能凭猜测批量改原文件编码。
4. 以实际插件根目录和可执行路径替换占位符：

   ```text
   python <plugin-root>/scripts/ebook_convert.py --formats
   python <plugin-root>/scripts/ebook_convert.py --doctor --calibre <ebook-convert-path> --pandoc <pandoc-path>
   python <plugin-root>/scripts/ebook_convert.py <source> <new-output> --calibre <ebook-convert-path> --pandoc <pandoc-path> --input-encoding utf-8 --timeout 120
   python <plugin-root>/scripts/ebook_convert.py <source.txt> <new-output.epub> --calibre <ebook-convert-path> --input-encoding gb18030 --timeout 120
   python <plugin-root>/scripts/ebook_convert.py <source.md> <new-output.epub> --pandoc <pandoc-path> --timeout 120
   python <plugin-root>/scripts/ebook_convert.py <source.md> <new-output.azw3> --pandoc <pandoc-path> --calibre <ebook-convert-path> --timeout 120
   python <plugin-root>/scripts/ebook_convert.py <source.epub> <new-output.rtf> --pandoc <pandoc-path> --timeout 120
   ```

5. 读取标准输出 JSON 和退出码。转换退出 `0` 表示产物已校验并发布，读取 `warnings` 中的能力损失与注释规范化说明；退出 `1` 时读取 `issues` 中的失败原因。任何非零退出或非空 `issues` 均阻断后续步骤；缺少依赖、引擎 warning、超时、空产物和结构检查失败均不发布产物。抽查中文正文、章节顺序、图片与注释链接；只报告实际运行的校验，内部结构检查不等于 EPUBCheck，也不证明特定阅读器已适配。
6. 若还要求图片下方图注/来源或小号注释上标，按 [标准编排流程](../epub-edit/references/reading-style.md#非-epub-的标准编排) 执行“非 EPUB → 新暂存 EPUB → `epub_editor.py --reading-style standard` → 必要时目标格式”。每步独立新路径和 JSON；已为 EPUB 或最终输出 EPUB 时仅跳过相应转换步骤，不能跳过编排。`preserve` 保留布局并补语义；仅改 EPUB 3 元数据用 `--metadata-only` 跳过布局。
7. 交付生成文件及各步独立 JSON 报告。转换 JSON `output` 是输出路径，`input_format` / `output_format` 为格式，`engines` 记录使用的引擎名称与路径，`assets` 为图片目录列表；编排 JSON 另读 `reading_layout` 与外层 `issues`。Markdown 图片位于同目录 `<output-stem>_assets`，需要与 `.md` 一起交付；HTML 为内嵌图片的单文件，ODT 将图片放入文档包。说明源格式无法提供的内容和目标格式承载不了的内容。

## 内容与注释

- 转换尽量保留正文、章节顺序、标题、图片和目标格式可承载的元数据，不承诺无损。TXT 会丢失图片、样式及可点击注释；MOBI、RTF 等格式有各自的排版与结构限制。
- 单纯转换不自动应用标准图注/上标，也不自动修改作者、ISBN、目录定位、统计字数或替换封面。用户另外要求 EPUB 编排时，读取 [epub-edit](../epub-edit/SKILL.md) 并单独完成该步骤；封面仍只使用用户提供的图片。标准图注为 `0.85em`，明确来源用 credit span，引用为有真实目标的 `0.75em` 单次上标；这些 EPUB 样式和语义在目标格式中可能降级。
- Markdown 输入通过 Pandoc 生成 EPUB 3，保留 `fenced_divs`、`bracketed_spans`、标题 ID 和引用目标。本地图片仅在核查后的临时副本中转为 data URI，以便在 sandbox 中读取；原 Markdown 及图片侧车不修改。
- EPUB 转 HTML、Markdown、ODT、RTF 时，为让 Pandoc 读取正文引用的非 spine 注释以及 `linear=no` 注释，处理器只规范化临时副本的阅读顺序并报告该步骤。无法解析或存在歧义的注释目标必须作为问题报告。保留目标格式可承载的注释文本与引用目标不保证所有目标格式或阅读器都能弹窗显示翻译；EPUB 的阅读器约定见 [reader-contract.md](../epub-edit/references/reader-contract.md)。
- Jiusi-pys/ebooks 的 2026-10-11 本地 Web 适配已验证插图、图注及小字号标记/Popover；需要配套新版阅读器，旧书重新导入，布局仅本地缓存，尚未部署。标准 EPUB 输出不能保证旧版 Jiusi 或其他阅读器弹窗；按 [阅读器契约](../epub-edit/references/reader-contract.md) 区分实际安装版本与本地验收。
- 输入限用户有权处理的未加密书籍，不执行书内脚本、不抓取远程图片、不解除 DRM。HTML、Markdown 的本地图片必须位于输入所在目录内；资源越界、异常压缩路径、加密或签名 EPUB 会被拒绝。
- DOCX 的全部 `.rels` 资源目标，以及 ODT 的图片、字体和对象资源必须实际存在包内；外部资源、文件 URI、绝对路径、越界或缺失目标在运行引擎前拒绝。普通 HTTP(S)/mailto 超链接保留。DOCX/ODT XML 禁止 entity/DTD 和 `xml:base` 重定向；FB2 图片与 stylesheet 的资源引用仅允许经校验的内嵌图片或 `#binary`，不访问外部 CSS/图片目标。细节见 [资源检查](references/formats.md#资源检查)。

## 自测

修改转换处理器前先补失败测试，再实现。在仓库根目录运行：

```text
python -m unittest discover -s <plugin-root>/tests -v
```

真实引擎验收需要可用的 Calibre 和 Pandoc，验证边界见插件 [README](../../README.md#验证)。未运行的引擎、阅读器或安装验收应明确标为未验证。

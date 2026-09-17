---
name: epub-edit
description: 编排 EPUB 电子书，编辑书名、作者、ISBN、出版信息等元数据，统计或修改字数，修复可点击目录与正文定位，规范点击弹出式注释，并用用户提供的图片替换封面。适用于输出仍为 EPUB 的电子书处理及 Jiusi-pys/ebooks 阅读器配合场景。
---

# EPUB 编排

使用插件根目录下 `scripts/epub_editor.py` 处理 EPUB。输入来自用户；输出为一个新的 `.epub`，不覆盖原文件，不额外生成网页阅读版。

## 执行

1. 确定输入 EPUB 的路径。用户要求换封面却没有给图片时，向用户索取图片；可以先完成独立的目录和注释工作。没有换封面要求时不询问、不修改封面。
2. 检查 Python 依赖 `lxml` 和 `Pillow`；缺失时在工作目录虚拟环境中安装根目录 `requirements.txt`，避免修改全局环境。
3. 若涉及书名、作者、出版信息、字数等元数据，先用 `--inspect` 读取现有值，按 [metadata.md](references/metadata.md) 生成只包含用户要求变更字段的 UTF-8 JSON。不要补造作者、ISBN、出版社或出版日期。用户说“统计字数”时用 `--recount`；明确给出字数时写 `word_count`。未要求统计或更改时保留原值。用户不必手写 JSON，由你在工作目录创建。
4. 选择尚不存在的输出路径。以插件实际根目录替换下面的路径：

   ```text
   python <plugin-root>/scripts/epub_editor.py <input.epub> <output.epub>
   python <plugin-root>/scripts/epub_editor.py <input.epub> <output.epub> --cover <user-cover.png>
   python <plugin-root>/scripts/epub_editor.py <input.epub> --inspect
   python <plugin-root>/scripts/epub_editor.py <input.epub> <output.epub> --metadata <changes.json> --metadata-only
   python <plugin-root>/scripts/epub_editor.py <input.epub> <output.epub> --metadata <changes.json> --recount
   ```

5. 仅修改元数据且输入是 EPUB 3 时，优先使用 `--metadata-only`，逐字节保留 OPF 外全部资源。该模式不兼容换封面；EPUB 2 需用普通流程转换导航为 EPUB 3。主标识符变更需要同步 NCX 时也必须使用普通流程。
6. 阅读标准输出 JSON：`toc_repaired`、`notes`、`cover_replaced`、`metadata.before/after/changed`、可选 `statistics` 和 `issues`。退出码 0 为结构处理完成，2 为已产生输出但仍有待处理问题，1 为失败。遇到 `issues` 时，不把书标记为完成；检查书内结构，用明确的原文证据消除对应歧义，再生成新的输出版本。不凭章节顺序或同名标题猜测对应关系。用 `--inspect` 读回最终 EPUB 确认元数据已写入。
7. 向用户交付输出 EPUB，简要说明已处理项和剩余问题。若统计字数，说明使用“汉字逐字＋其他连续字母数字串按词”的口径，排除有标记的非正文，并不是出版社排版字数。没有实际 EPUB 时可创建插件，但不能声称已经处理用户的书。

## 内容约束

- 目录支持 EPUB 3 nav 和 EPUB 2 NCX。错误链接只在标题与正文标题唯一匹配时自动修复；没有目录时从 NCX 或正文标题生成导航。重复标题、重复锚点等歧义必须保留并报告。
- 注释识别 `epub:type=noteref`、`role=doc-noteref`、`class=noteref/footnote-ref/endnote-ref`、`rel=footnote`，或指向已标记 footnote/endnote 的链接。跨文件目标会补齐语义。未带这些标记的普通数字和链接不能擅自当作注释；检查具体书籍，必要时先在工作副本中给已核实的注释补语义再处理。`notes=0` 不证明书中没有注释。
- 弹窗由阅读器实现，不能靠给 EPUB 注入脚本保证。不要声称未适配的阅读器一定弹窗。针对自定义阅读器的约定见 [reader-contract.md](references/reader-contract.md)。
- 封面只接受用户提供的 JPEG/PNG；不得搜索、生成或臆造封面。内部统一写成 JPEG，更新封面元数据和已有图片引用；无封面页时增加封面页。未指定 `--cover` 时保留封面资源。
- 原文、插图和非目标资源应保留；处理过程中不执行 EPUB 内的脚本，不访问其外链。拒绝加密、签名、多 rendition EPUB，以及超限或路径异常的压缩包。
- 输出使用 EPUB 3 包版本，补齐导航与修改时间。脚本不是完整的 EPUB 2 到 3 验证器；旧式 XHTML/OPF 的其他兼容问题需按书处理。若有 EPUBCheck，执行完整校验；未运行时明确区分“内部结构检查通过”和“EPUBCheck 通过”。

## 自测

修改处理器前先补失败测试，再实现。运行：

```text
python -m unittest discover -s <plugin-root>/tests -v
```

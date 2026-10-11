# EPUB 编排 0.2.1 图注与注释验收

> 本文保留 0.2.1 阶段的历史结果。后续阅读器本地适配见 [0.2.2 记录](2026-10-11-reader-adaptation-validation.md)，当前插件源码复测见 [US 全仓记录](2026-10-11-plugin-us-full-suite.md)：279 通过、8 引擎测试跳过，8 项已在 Windows 补跑通过。下文“未应用”“尚未修改”“未推送”描述的是当时状态，不代替后续记录。

本阶段插件源码与独立 ZIP 已完成；当时阅读器源码尚未修改，图片适配范围仍待用户回答。本记录保留这两个状态的区别。

## 实现与审核

依照 [方案](../plans/2026-10-11-ebook-annotations.md) 先对齐需求、独立审核，再补失败测试和实现。新增 `ebook_reading_layout.py`；完整编辑默认 `--reading-style standard`，也可显式选择 `preserve`，metadata-only 不修改正文或资源。纯转换入口仍不自动进行编排，技能提供独立路径、JSON 报告检查及失败阻断的三阶段命令。

明确关联的插图和原图注采用 `figure` / 最后一个 `figcaption`，内部保留段落，明确来源在 phrasing span 上标记 credit；图注为相对 `0.85em`、无首行缩进。已解析引用采用单层 `sup`、相对 `0.75em`，保留真实 href、ID 与 noteref 语义。数值是插件的排版策略，不能称为规范强制字号。不补造图号、来源或图注，不将普通相邻正文归入图注。歧义 tail、重复图注或会改变原文顺序的结构保持原样并报告 warnings。

独立审核后闭合了共享 sup 的无关文字、已有内联字体 shorthand、注释集合角色、导航误判、非 phrasing 图注内容和封面精确定位等问题。最后使用仅带 guide fragment、无 cover TYPE 的实际样本验证：仅保护目标及后代，同页普通插图正常规范；无片段仍保护整篇封面文档。最终插件审核 APPROVE，无本次范围剩余阻断。

EPUB TYPE footnote 可用于 endnotes 集合中的条目；保留该类型供现有阅读器识别。集合中不错误生成 ARIA doc-footnote/doc-endnote，doc-endnotes 仅用于包含列表的容器。标准依据：[HTML figure](https://html.spec.whatwg.org/multipage/grouping-content.html#the-figure-element)、[EPUB SSV footnote](https://www.w3.org/TR/epub-ssv-11/#footnote)、[DPUB ARIA doc-endnotes](https://www.w3.org/TR/dpub-aria-1.1/#doc-endnotes)。

book-translator 按编辑 CLI 的 help 能力检测显式传 `--reading-style preserve`，维持其既有严格正文验证；inspect 不传该标志，旧 CLI 和旧锁保持兼容。存在的布局辅助脚本纳入哈希锁，新增、删除或修改均要求重新准备依赖。未放宽正文验证器。

## 最终测试

环境为 Windows、Python 3.13.9、lxml 5.3.0、Pillow 12.0.0、Calibre 9.16.0、Pandoc 3.8。便携引擎仅用于本地验收，没有写入插件配置或修改全局 PATH。

| 检查 | 最终结果 | 证据 |
| --- | --- | --- |
| 插件完整套件，含实际引擎 | 141/141，74.168 秒，无跳过 | `.local/ebook-conversion-tools/annotations-full-release.txt` |
| 十格式跨格式实际转换与 EPUB 读回 | 90/90 个方向 | [独立矩阵](2026-10-11-ebook-annotations-matrix.json) |
| 新布局回归 | 31/31，包含封面 fragment | 完整套件及 `annotations-layout-independent-green.txt` |
| HTML→暂存 EPUB→标准编排→HTML | 通过；注释全文、目标、图注、图片字节/像素及来源文字保留，目录未误判 | `test_reading_pipeline_integration.py` |
| book-translator 回归 | 64/64，15.035 秒 | `.local/ebook-conversion-tools/annotations-translator-release.txt` |
| 两个技能 frontmatter 检查 | 均通过；Windows 使用 Python `-X utf8` | system skill-creator `quick_validate.py` |
| 独立 ZIP 解包运行 | 141 项发现，133 通过、8 实际引擎 opt-in 跳过 | `.local/dist/package-validation-0.2.1.txt` |

布局与适配器均保存先红后绿日志，分别为 `.local/ebook-conversion-tools/annotations-red.txt`、`annotations-adapter-red.txt`。此前 0.2.0 包和 [转换验收](2026-10-11-ebook-conversion-validation.md) 保留，未覆盖。

完整验收命令：

```powershell
$env:TEST_CALIBRE = '<本地 Calibre ebook-convert.exe 绝对路径>'
$env:TEST_PANDOC = '<本地 pandoc.exe 绝对路径>'
$env:CONVERSION_MATRIX_REPORT = '<新 JSON 证据路径>'
python -m unittest discover -s plugins/epub-editor/tests -v
python -m unittest discover -s plugins/book-translator/tests -v
```

测试验证合成夹具的正文/章节顺序、可承载格式的图片、跨文件与非 spine 注释及具体拒绝路径。TXT 等格式仍有固有降级，不能将 90 个成功方向推导为任意书籍均无损。

## 实际浏览器证据与阅读器限制

使用本插件编辑输出 `standard-reviewed.epub`，从中提取 XHTML、按 HTML 序列化并补 UTF-8 meta，仅用于独立布局预览。浏览器测得正文 24px、两个引用 18px（0.75 倍）且父元素为 sup；图注和来源 20.4px（0.85 倍）、缩进 0，位于实际 360×120 包内图片下方。原图注、来源和 alt 保留。此预览不是 Jiusi 阅读器弹窗验收。

![标准 EPUB 图注与上标预览](../../.local/annotation-browser/standard-epub-layout.jpg)

阅读器仓库为 `C:/Users/17715/Documents/codes/书籍管理`，remote `Jiusi-pys/ebooks`，提交 `2ffca98c6b64e6f0a21c89ad24c06b96c2114330`。读取实际 parseEpub、共享 EpubText 和样式，在隔离的本地 Vite 页面加载插件生成样本。没有写入正式书库、认证或同步数据。相关既有阅读器测试 5 文件共 16 项通过；完整登录阅读页面、全部窗格集成均未验收。

原组件正文 24px、标记 15.6px（0.65 倍），按钮继承 line-height 0，实际高度 0；普通鼠标点击失败。Tab/Enter 可以显示正确正文注释，Escape 关闭并恢复焦点，URL/章节/滚动位置保持不变。

候选复制件只增加 `lineHeight: 1`，按钮高度恢复至约 15.6px。普通点击正文和图片编号均打开正确完整注释，URL/章节/滚动不变、正文容器点击计数为 0；Escape 或关闭按钮关闭并恢复触发器焦点。[单行补丁](2026-10-11-jiusi-note-hit-area.patch) **未应用到阅读器仓库**。图片编号的文字虽可弹窗，实际图片数量仍为 0，不能声称图片已显示。

![未应用到阅读器的点击区域修复预览](../../.local/annotation-browser/jiusi-hit-area-preview.jpg)

浏览器完整测量为 `.local/annotation-browser/browser-evidence.json` 和 `layout-browser-evidence.json`。当前阅读器导入器忽略正文图片；图像资源导入、位置存储、共享视图显示与同步边界仍需另行实施。未执行 EPUBCheck、Linux CI、其他阅读器交互或所有目标格式的最终视觉检查。EPUB 语义允许阅读器自行提供交互行为，不能用静态 href 声称通用不跳转：[EPUB Reading Systems 3.3](https://www.w3.org/TR/epub-rs-33/#sec-structural-semantics)。

## 交付

- `.local/dist/epub-editor-0.2.1.zip`：27 文件，101316 字节。
- SHA-256：`6db1700dcb9015ca50d13db0f1a5e76abf2c9996ef1944aac57a799daede0749`。
- 包含便携 manifest、Codex 兼容 manifest、两项技能、脚本、依赖声明和测试；不包含便携引擎、缓存或本地临时输入。
- 仅源码和 ZIP；未提交、推送、发布或覆盖已安装插件缓存。无关 fenbi-exporter、marketplace 改动及阅读器未跟踪 JPG 均保留。

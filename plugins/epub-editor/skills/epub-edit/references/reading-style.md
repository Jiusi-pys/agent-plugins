# 标准图注、上标与执行流程

`epub-editor` 0.2.2 的完整编排默认使用 `--reading-style standard`；`preserve` 保留布局和 CSS，仍进行既有目录、注释语义及明确指定的编辑。`--metadata-only` 跳过布局，保留 OPF 外全部资源字节，不与换封面同时使用。

## 标准布局

- 只处理已明确关联的独立插图和图注：`figure` 的唯一 `figcaption` 放在最后，图注/来源原段落保留为 `p`，避免嵌套 `p`。图注相对字号 `0.85em`，取消首行缩进；明确来源在原 `p` 内用 phrasing `span epub:type="credit"` 标记。没有图注不补造图号、来源或说明，不把普通相邻段落、行内图片或封面移入图注。
- 已解析注释引用保留真实 `href`、唯一 ID、`epub:type="noteref"` 和 `role="doc-noteref"`，标记为 `0.75em` 单次上标。复用或规范已有上标，避免重复缩小、重复抬高；同一 `sup` 内无关注释的文字内容与样式保留。标记跟在被注释文字或图片说明之后，不把全文注释放在右上方，不覆盖图片内部，保留键盘焦点样式。
- 单个正文注释保留 `footnote` 目标语义；章末/书末集合采用包含列表的 `section` 与 `role="doc-endnotes"`，不把该角色直接赋给 `ol`，集合条目不再错误附加 `doc-footnote` 或已废弃的 `doc-endnote`。跨文件锚点和原内容保留，不全局隐藏注释，不注入脚本或改成无目标按钮。
- 样式仅用于插件识别的节点，不覆盖正文全局 CSS。反复编排不增加嵌套上标、重复图注或重复样式；不能确定的图注作为说明报告，未解析/歧义注释进入外层 `issues`。

这些结构依据 [HTML figure/figcaption](https://html.spec.whatwg.org/multipage/grouping-content.html#the-figure-element)、[EPUB noteref/footnote/credit](https://www.w3.org/TR/epub-ssv-11/) 和 [DPUB-ARIA endnotes](https://www.w3.org/TR/dpub-aria-1.1/#doc-endnotes)。字号是本插件的布局约定，不是标准规定的固定数值。

## 非 EPUB 的标准编排

纯 `ebook_convert.py` 不自动应用以上布局。用户要求转换同时规范图注/注释时，依次执行：原格式 → 新暂存 EPUB → 新标准编排 EPUB → 必要时新的最终格式。输入已为 EPUB 时跳过第一步；最终交付 EPUB 时跳过第三步。每次调用使用新的输出和独立 JSON 报告，不复用已有路径。

以下 PowerShell 示例在仓库根目录运行，把占位符换成实际路径；工作目录必须尚不存在。每一步先检查退出码和 JSON `issues`，失败立即阻断，不能凭已产生文件继续导出：

```powershell
$pluginRoot = (Resolve-Path 'plugins/epub-editor').Path
$calibrePath = '<ebook-convert-path>'
$pandocPath = '<pandoc-path>'
$stageDir = Join-Path (Get-Location) 'book-layout-001'
if (Test-Path -LiteralPath $stageDir) { throw '请选择新的工作目录' }
New-Item -ItemType Directory -Path $stageDir -ErrorAction Stop | Out-Null

function Invoke-BookStage {
    param([string]$Report, [string[]]$Arguments)
    if (Test-Path -LiteralPath $Report) { throw '报告路径已存在' }
    $stageJson = & python @Arguments
    $stageCode = $LASTEXITCODE
    $stageJson | Set-Content -LiteralPath $Report -Encoding utf8 -ErrorAction Stop
    if ($stageCode -ne 0) { throw "处理退出 $stageCode，请检查 $Report 及错误输出" }
    $stageReport = ($stageJson -join "`n") | ConvertFrom-Json -ErrorAction Stop
    if ($null -eq $stageReport -or $null -eq $stageReport.PSObject.Properties['issues']) {
        throw "报告无效，请检查 $Report"
    }
    if (@($stageReport.issues).Count -ne 0) { throw "尚有 issues，请检查 $Report" }
    $stageReport
}

$importedEpub = Join-Path $stageDir '01-imported.epub'
$styledEpub = Join-Path $stageDir '02-standard.epub'
$finalOutput = Join-Path $stageDir '03-final.md'
Invoke-BookStage -Report (Join-Path $stageDir '01-import.json') -Arguments @(
    "$pluginRoot/scripts/ebook_convert.py", '<source.docx>', $importedEpub,
    '--calibre', $calibrePath, '--pandoc', $pandocPath, '--timeout', '120'
)
Invoke-BookStage -Report (Join-Path $stageDir '02-layout.json') -Arguments @(
    "$pluginRoot/scripts/epub_editor.py", $importedEpub, $styledEpub,
    '--reading-style', 'standard'
)
Invoke-BookStage -Report (Join-Path $stageDir '03-export.json') -Arguments @(
    "$pluginRoot/scripts/ebook_convert.py", $styledEpub, $finalOutput,
    '--calibre', $calibrePath, '--pandoc', $pandocPath, '--timeout', '120'
)
```

TXT/HTML/Markdown 原书需按实际编码补 `--input-encoding utf-8` 或 `gb18030`；引擎依赖按 [格式路由](../../ebook-convert/references/formats.md) 选择。Markdown 导出还需交付 `03-final_assets` 图片目录。最终目标可能降级 EPUB 样式与注释语义，标准编排不等于目标格式无损或弹窗保证。

分别读取三个报告：转换报告的 `warnings/engines/assets`；编排报告的 `reading_layout`（`mode/applied/note_markers/figures/captions/credits/warnings/popup_behavior`）及已有 `notes/toc_repaired/metadata`；每份报告的外层 `issues`。缺少或不确定图注可出现在 `reading_layout.warnings`，不能据此补造；任何非零退出或非空 `issues` 必须查明后重新生成新的结果。编排退出 `2` 即使已有 EPUB 也不能当作完成。

## 弹窗与验收

EPUB 标准允许阅读器自行决定结构语义的行为，静态锚点或上标不能证明点击后不跳转。[EPUB Reading Systems 3.3](https://www.w3.org/TR/epub-rs-33/#sec-structural-semantics)

Jiusi-pys/ebooks 现有共享 `EpubText` 使用相对小字号上标和按钮/Popover 显示注释纯文本，保留键盘交互和关闭行为；它的显示字号由阅读器控制，不会直接复用 EPUB 的 `0.75em`。2026-10-11 本地 Web 适配支持包内插图、裸图注、来源及图片旁引用，并经过主阅读、参考窗、双语原文、分页与窄屏验收；尚未部署。旧书需在新版阅读器重新导入，布局缓存只保存在本地。详见 [阅读器契约](reader-contract.md)。

原注释按钮高度为 0 的缺陷已经修复到配套阅读器源码；真实插件输出经解析、IndexedDB 保存和共享阅读组件后，鼠标与键盘打开/关闭均已验证。该结果限于隔离本地 Web 运行，不能替代真实部署版本验收。

实际验证需使用本插件生成的 EPUB：标记小于正文、位于上方；点击显示正确注释，URL、章节及阅读位置不变；关闭后焦点恢复。浏览器交互、内部结构检查、EPUBCheck 和其他格式/阅读器分别报告，未执行的项目标为未验证。

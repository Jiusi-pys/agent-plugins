# EPUB 编排 0.2.0 多格式转换验收

> 本文保留 0.2.0 阶段的历史结果和当时交付状态。当前 0.2.2 源码的发布前复测见 [US 全仓回归记录](2026-10-11-plugin-us-full-suite.md)：US 279 通过、8 引擎测试跳过；8 项已在 Windows 全部补跑通过，90 个转换方向重新验证。历史“未推送”不表示后续分支发布状态。

## 范围

用户确认支持 TXT、EPUB、MOBI、HTML、Markdown、AZW3、DOCX、RTF、FB2、ODT 十种格式双向转换。保留 `epub-editor` 身份、图标、既有 EPUB 编排 CLI，并适配 book-translator 的 `0.2.x` 依赖检查。

实现先形成 [方案](../plans/2026-10-11-ebook-conversion.md)，由独立代理审核后进入 TDD。当前工作仅修改 Git 管理源码，未推送、发布或编辑已安装插件缓存。

## 环境和执行方式

- Windows，Python 3.13.9，lxml 5.3.0，Pillow 12.0.0。
- 实际转换引擎：Calibre 9.16.0 完整便携工具包，Pandoc 3.8。工具位置仅用于本次本地验收，未写入插件配置或技能。
- 单元与回归：`python -m unittest discover -s plugins/epub-editor/tests -v`、`python -m unittest discover -s plugins/book-translator/tests -v`。
- 真实引擎：在会话中设置 `TEST_CALIBRE`、`TEST_PANDOC` 后执行 `python -m unittest discover -s plugins/epub-editor/tests -p test_conversion_integration.py -v`；默认没有这两个环境变量时跳过实际引擎测试。

## TDD 和独立复测

转换执行器、格式路由、失败/超时、输出保护、资源侧车、ZIP 路径别名、注释锚点和包装一致性均先补失败测试再实现。容器资源校验单独使用 no-op 临时实现获得 46 个失败子场景，再实现到 19 项测试通过。

独立审核用合成文件发现并复测关闭五项具体问题：

1. ZIP 的 `.` 路径别名可能覆盖预检后的内容：解包前拒绝别名与 Windows 名称碰撞。
2. Markdown 回转中结构属性和引用目标可能丢失：使用 Pandoc 输入并保留受支持的 ID 语义。
3. 普通链接指向已标记注释时，非 spine 注释可能丢失：仅在临时 EPUB 副本补齐阅读顺序与目标 ID。
4. DOCX 外部图片关系可读取包外文件：在引擎前拒绝，真实回归确认无产物、引擎调用为零，合成包外文件字节不变。
5. FB2 样式 `@import` 可触发远程请求：在引擎前检查样式与二进制资源，真实回归确认无产物、引擎调用为零，本地服务全部 HTTP 方法计数为零。

正常 HTTP(S)/mailto 超链接保留。资源检查不主动读取包外文件或联网。上述证据仅覆盖这些具体夹具，不能推导任意输入都没有问题。

## 真实转换验收设计

矩阵从自制双章节 EPUB 生成十种源格式，覆盖全部 90 个有向跨格式组合。每个结果均再次读回 EPUB，核对中文/英文正文标记存在及两章顺序；原 EPUB 的 SHA-256 不变。不能只以引擎退出码或文件存在断言成功。

另外独立验证：

- HTML、Markdown、ODT 的实际图片引用：解析 data URI、侧车文件或包内图像，核对 31×47 尺寸及测试像素。
- MOBI、AZW3、DOCX、RTF、FB2 读回 EPUB 后，正文实际引用的测试图像仍能解码，尺寸/像素符合夹具。
- 非 spine、`linear=no`、普通链接指向已标记注释三类输入：HTML、Markdown、ODT 中注释全文仍在，引用链接对应唯一且含注释内容的目标。
- RTF/ODT 原生书签读回 HTML：唯一链接目标对应实际注释内容，不能以空占位锚点代替目标。
- GB18030 TXT 显式解码后的中文正文。
- HTML/EPUB 远程图片、FB2 远程 CSS：不发布输出，HTTP 请求计数为零。
- DOCX 合成包外 `file://` 图片：拒绝且不发布。

## 最终结果

最终源码被冻结后运行完整验证，全部通过：

| 检查 | 实际结果 |
| --- | --- |
| EPUB 插件完整测试，含真实引擎 | 109/109，62.325 秒 |
| 转换单元测试 | 46/46，均包含在上面的完整测试中 |
| DOCX/ODT 容器资源单元测试 | 19/19，包含在完整测试中 |
| 原 EPUB 编辑与元数据回归 | 29/29，包含在完整测试中 |
| manifest、技能与包装一致性 | 8/8，包含在完整测试中 |
| 真实引擎场景 | 7/7，包含在完整测试中；其中矩阵覆盖 90/90 个有向组合 |
| book-translator 回归 | 55/55，10.880 秒 |
| 系统 skill-creator quick_validate | ebook-convert、epub-edit 两个技能均通过 |
| CLI --formats / --doctor | 十格式声明完整；两个实际引擎 available=true、issues=[] |
| ZIP 解包后的独立目录测试 | 109 项发现，102 项通过，7 项实际引擎测试按设计跳过 |
| ZIP 内容检查 | 单一 epub-editor 根目录、23 个文件，含隐藏兼容 manifest；资源引用完整，无缓存与引擎工具包 |
| git diff --check | 通过 |

[矩阵 JSON](2026-10-11-ebook-conversion-matrix.json) 保留全部 90 个方向与正文/顺序读回检查的列表。矩阵以外的图片、注释、编码和拒绝行为由其余六个实际引擎测试覆盖。

实际验收还推动了三项兼容修订：临时副本处理 Calibre 封面 SVG 的图片打包；保留无命名空间 type 标记的注释内容；为 RTF 和 ODT 写原生书签，并在 RTF 的受控 JSON 中内嵌经检查的图片。RTF 不支持的复杂 SVG 继续报告引擎失败，不静默省略。

交付 ZIP：工作区 `.local/dist/epub-editor-0.2.0.zip`，77,175 字节。SHA-256：

```text
c01077183e26f0b2b9d0d469d15c4ea7f721f9fab060a539bca9452b1ff84c6f
```

ZIP 不包含 Calibre/Pandoc；这两个引擎应通过实际安装路径、PATH 或环境变量提供。Python 依赖保留在包内 requirements.txt。

## 限制

上述样本验收验证正文标记、顺序及专门设计的图像/注释场景，不能证明任意书籍、全部文字、复杂布局或元数据都无损。TXT 无法承载图片和样式；其他格式也有能力差异，处理器在 JSON `warnings` 中说明。异常资源、未支持语法和引擎诊断作为失败处理，不静默发布。

本次没有执行 EPUBCheck、特定浏览器/阅读器显示或弹窗测试，也没有在 Linux 实际运行 CI 新增作业。安装缓存仍为原版本；源码或 ZIP 的成功不等于桌面插件已经重新加载。

## 包装依据

根 `plugin.json` 使用 Agent Plugins 1.0，OpenAI 展示信息位于 `extensions.com.openai`，兼容 `.codex-plugin/plugin.json` 同步身份、版本与展示字段。新增技能匹配目录名，详细依赖与路由位于 references，引用资源保留在插件包内。

- [OpenAI 插件文档](https://developers.openai.com/plugins/build/plugins)
- [OpenAI 技能文档](https://developers.openai.com/plugins/build/skills)
- [Calibre CLI](https://manual.calibre-ebook.com/generated/en/ebook-convert.html)
- [Pandoc 手册](https://pandoc.org/MANUAL.html)

官方文档核实日期：2026-10-11。

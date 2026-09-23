# Jiusi-pys/ebooks 阅读器约定

仓库：https://github.com/Jiusi-pys/ebooks

2026-09-17 的本地适配在原始提交 `33c8fd0` 的基础上完成，尚未推送或部署。最初的导入器仅保存段落纯文本；仅编排 EPUB 无法让旧版阅读器获得弹窗。

适配后的导入流程：

- `parseEpub.ts` 读取正文和非 spine 注释文档，交由 `epubContent.ts` 解析。
- nav 的 `epub:type=toc` 或 NCX 目录转换成 `ParsedBook.outline`，包含章节 ID、段落下标和层级；导入时保存到本地书籍对象。
- `Chapter.paragraphs` 保持字符串数组；可选 `Chapter.footnotes` 包含 `paraIndex/start/end/content`。起止位置是归一化正文的 UTF-16 偏移，内容为纯文本。
- `EpubText.tsx` 在正文原位置渲染注释按钮，弹窗显示纯文本，不注入原始 HTML。普通阅读、参考窗格和双语原文使用同一组件。
- 旧书的已导入纯文本无法恢复已丢失的锚点和注释，应重新导入处理后的 EPUB；不要自动删除旧书或批注。
- 本次范围是 EPUB 处理与本地导入阅读；不承诺旧 API 客户端或跨设备同步恢复额外阅读信息。

回归测试包含插件生成的 EPUB 样本，覆盖导入、目录点击回调和注释弹窗。浏览器隔离页面验证了真实 Paragraph 和 OutlinePanel 的交互；完整登录应用因本地 MySQL 不可用未验证。

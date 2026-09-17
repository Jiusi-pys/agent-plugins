# 元数据编辑

通过用户自然语言要求创建一个 UTF-8 JSON 补丁；JSON 放在工作目录，不作为默认交付文件。省略字段即保留，显式 `null` 删除可空的标量，`[]` 清空作者/贡献者/分类列表。书名不能清空，语言列表不能清空。未知字段报错，避免拼错字段名后无声忽略。

## 字段

| JSON 字段 | 内容与写入位置 |
| --- | --- |
| `title` | 主书名；`dc:title`，作为首个书名并标记 main |
| `subtitle` | 副标题；`dc:title` + title-type=subtitle；可为 null |
| `authors` | 作者列表；每项为字符串或 `{name, sort_as}`；`dc:creator` + aut |
| `contributors` | `{name, role, sort_as?}` 列表；支持 translator/trl、editor/edt、illustrator/ill、narrator/nrt、compiler/com、photographer/pht、other/ctb、author/aut |
| `publisher` | 出版社；`dc:publisher` |
| `published_date` | 出版时间；YYYY、YYYY-MM、YYYY-MM-DD；`dc:date`，校验实际日历日期 |
| `languages` | BCP 47 语言标签列表，例如 zh-CN、zh-Hant、en；`dc:language` |
| `subjects` | 分类/主题/标签列表；`dc:subject` |
| `description` | 简介纯文本，支持换行；`dc:description` |
| `rights` | 版权/授权说明；`dc:rights` |
| `source` | 来源信息；`dc:source` |
| `coverage` | 时间或地域范围；`dc:coverage` |
| `book_type` | 资源类型；`dc:type` |
| `format` | 格式说明；`dc:format`，不会改变实际 EPUB 格式 |
| `isbn` | ISBN-10/13，允许空格和连字符，验证校验位后规范化；`dc:identifier` + identifier-type |
| `identifiers` | 其他标识符映射，如 `{"DOI":"10.1234/example","ASIN":"B012345678"}`；只替换指定类型，其余保留；指定类型为 null 时删除，但不能删除 EPUB 主标识符 |
| `series` | `{name, position?}`，卷序为非负数字；EPUB belongs-to-collection + collection-type + group-position；null 删除标准与 Calibre 旧式丛书字段 |
| `edition` | 版次文本，如“第 2 版”；Schema.org bookEdition |
| `page_count` | 正整数或 null；Schema.org numberOfPages；只接受用户提供的纸书/固定版式页数，不从可重排 EPUB 虚构页数 |
| `word_count` | 非负整数或 null；Schema.org wordCount；手填时统计口径标记为 user-supplied |

作者与贡献者列表各自整体替换；修改作者时保留原有非作者角色，修改贡献者时替换所有非作者贡献者。支持的角色使用 MARC relator 编码写入。

ISBN 与 `identifiers.ISBN` 不能同时指定。更改某标识符类型会合并该类型的重复项，但保留主标识符元素及其 ID。主标识符作为 ISBN 更新后，普通流程同时同步 NCX 的 dtb:uid；只改 OPF 的模式会拒绝这种需要同时修改 NCX 的情况。

`--inspect` 返回规范化的元数据快照；其 `identifiers` 是包含 scheme/value/primary 的记录列表，**不是可直接作为输入补丁的格式**。只挑用户要求修改的字段生成补丁，不要把整个检查输出原样作为补丁。

## 示例

以下只是格式示例，不是用户书籍信息；实际使用时仅填写已知、用户授权修改的字段：

```json
{
  "title": "新的书名",
  "subtitle": "副标题",
  "authors": [{"name": "作者姓名", "sort_as": "排序用姓名"}],
  "contributors": [{"name": "译者姓名", "role": "translator"}],
  "publisher": "出版社名称",
  "published_date": "2024-06",
  "languages": ["zh-CN"],
  "subjects": ["文学", "小说"],
  "description": "图书简介",
  "rights": "版权说明",
  "series": {"name": "丛书名称", "position": 2},
  "edition": "修订版",
  "page_count": 320
}
```

运行时加 `--recount` 自动统计字数；或在 JSON 中提供 `"word_count": 123456`。两者不可同时使用，避免用户给定值被覆盖。

## 自动统计口径

1. 仅遍历 spine 中 linear 不为 no 的文档，每个文档只统计一次，排除 manifest 中标记的导航文档。
2. 排除 script/style/nav/svg/math、显式 hidden/aria-hidden/内联 display:none 等内容，以及标记为目录、封面、扉页、前后记区域、注释、参考文献或索引的区域。引用明确指向的注释节点和引用符号也排除。
3. 汉字（含 CJK 扩展区）每个计 1；其他连续 Unicode 字母/数字串按词计 1，词内部的连字符与英文撇号保留。标点与空白不计词数。普通正文标题计入。
4. 另外报告汉字数、其他词数及非空白字符数；字符数包含标点。word_count 是前两者相加。
5. 不执行脚本或外部样式表。缺少语义标记的版权页、注释等可能被统计，需先检查书籍结构；不是中文分词算法，也不等于出版社版面字数。

字数写入 `schema:wordCount`，统计方法写入 `urn:epub-editor:metadata:word-count-method` 对应扩展属性。已有前缀被占用时选择其他前缀，不改写无关命名空间。

## 保留与验证

- 未指定字段以及未知厂商元数据保留；替换字段时移除指向被删字段的 refinement 链，避免失效引用。
- `--metadata-only` 适用于 EPUB 3，除了 OPF 所有 ZIP 条目内容保持原样；不可同时换封面。EPUB 2 通过普通流程升级导航后再编辑。
- 修改时间自动更新。新文件不覆盖原书或已有输出。
- 输出读取成功不代表通过完整 EPUBCheck；如环境有 EPUBCheck，再执行完整格式校验。
- 新增字数、页数等字段写在 EPUB 文件中。此插件更新未增加 ebooks 阅读器的对应展示控件，不保证所有阅读器展示扩展字段。

依据：[EPUB 3.3 元数据](https://www.w3.org/TR/epub-33/)、[Schema.org wordCount](https://schema.org/wordCount)、[numberOfPages](https://schema.org/numberOfPages)、[bookEdition](https://schema.org/bookEdition)。

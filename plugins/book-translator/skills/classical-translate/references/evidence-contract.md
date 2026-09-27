# 古译今证据契约（在作业契约 v1 上扩展）

模式由 prepare 固定为 `classical_chinese`。profile 同时含 mode 和 `classical: {base_edition: "具体版本、抄录与限制", parallel_original: true}`。其余字段沿用 [原作业契约](../../book-translate/references/job-contract.md)。禁止借用 original_sample 标签跳过真实古籍核验。

## 真实调度与候选证据

必须执行 [实时调度与择优](live-research.md)。每章两路独立 research worker、两名独立 translator 和专属 reviewer 均用宿主实际身份；全局 reviewer 为另一新实例。协调者在 `job/research/dispatch.md` 保存对应原文/问题的任务范围、实际工具轨迹、来源访问范围、当前输入版本、冲突及补查结果。各角色只写分配给自己的路径，不能同时覆盖总账。

两名 translator 在 `job/research/<chapter>/candidates/` 下写不同候选文件，内容使用正式 translation.json 格式，分别填写本人真实 translator_id 和同一当前 input_digest；独立初稿完成前不互读。候选只作研究过程记录，不直接调用正式稿的身份门禁或导出。登记的主译者在双稿完成后写 `selection.md`，逐段说明采用、修订及重要舍弃理由，再生成正式的章节 translation.json；正式 assign、review、global 数据结构不变。

协调者与两级 reviewer 必须核对这些文件对应真实宿主调用，覆盖当前输入且问题已经解决。Python 检查器不解析 dispatch.md/selection.md，也无法证明 agent 实际执行；即使结构门禁通过，缺真实实时研究、独立双稿或择优记录也不得宣布完成或运行 finalize。不能通过伪造 ID、补写“已读”声明或复用开发样例绕过。过程记录发生实质修订时要通知 reviewer 重新核查，不把未纳入程序摘要的记录误称为自动防篡改。

## 来源：主 agent 注册

```json
{
  "id": "zuo-yin1",
  "work": "实际书名",
  "attribution": "实际原作者、注家或传统归属及限制",
  "edition": "实见版本；若未标底本应明确写未知",
  "locator": "卷、篇、年、页或行等真实定位",
  "url": "https://example.org/replace-with-actually-opened-page",
  "kind": "primary_text",
  "accessed": "2026-09-27",
  "access_method": "web",
  "read_evidence": "实际工具或浏览阅读的范围及未核部分"
}
```

示例不可用于真实证据。kind 为 primary_text / ancient_commentary / modern_scholarship；access_method 为 web / http / browser / local_scan；本地图版用 local_reference 替代 url。注册调用 `record-source <job> <metadata.json> <actual-capture.txt>`，自动保存 UTF-8 快照和摘要。来源 ID 仅用小写字母、数字和连字符，不覆盖已有 ID。新版本/新证据使用新 ID。

`sources.json` 与 `sources/<id>.txt` 都属于研究依据。快照 SHA 不符直接拒绝；来源元数据或集合变化使当前所有译稿输入摘要过期。每批先完成检索并固定候选来源，翻译/复审中仍可回派研究；新增来源时协调者串行登记并通知所有受影响章节，按新 packet 重新核对两份候选和正式稿，不能偷偷改摘要。

## 译者逐段增补

每个 translation.json 的 segment 增加 classical 对象：

```json
{
  "reading": "断句、古义、语法及本次选择依据",
  "allusions": "发现何典故与其在本文的作用，或具体说明无需典故考证",
  "variants": "实查到的字形/异文、版本关系、取舍与未核范围",
  "status": "verified",
  "uncertainty": "尚存解释边界，不能空写绝对正确",
  "citations": [{
    "source_id": "zuo-yin1",
    "quote": "实际证据中的连续原文",
    "locator": "该条的准确卷篇定位",
    "relevance": "这段证据具体支持何义，以及不能支持什么"
  }]
}
```

主记录至少一条原典或古注证据。所有引用都须存在于已登记快照中（仅忽略空白，不偷偷转换繁简异体或标点）。有据异说可用 disputed，必须另含 alternatives 和可见的 textual 注；unresolved 不得交付。

原 notes 字段仍需 kind、text、source_quote、rationale；explanation 另需 category 与 citations。category 为 allusion / lexical / institution / textual / grammar / context。allusion 和 textual 注须有原典或古注证据，其余解释也要有来源；不能用一条无关原句替整段长注背书。每条 source_quote 必须落在当前源文片段。假设案例 kind=example 可无文献，但明确是假设，不可借此绕过古籍解释的来源要求。

## reviewer 的独立出处复核

章节 review.json 和全局 reviews/global.json 均增加：

```json
{
  "source_checks": [{
    "source_id": "zuo-yin1",
    "sha256": "当前 sources.json 的摘要",
    "method": "web",
    "locator": "实际复读的位置与范围",
    "conclusion": "实际核对引文、上下文、注家归属和解释支持关系的结论；有何限制"
  }]
}
```

必须恰好覆盖稿件实际引用到的所有 source_id，不能只勾全部来源。method 取实际 web/http/browser/local_scan，不接受“复制译者报告”。报告源摘要与稿件版本均须匹配。机器仍无法证明签名者实际阅读；工具轨迹、逐条判断和相互独立的 agent 实例另行保留。

文本 Unicode start/end 基于 UTF-8 解码后的原始内容，保留 CRLF，不是字节位置。Markdown 文件按原始文字处理，并不执行其中 HTML/代码。最终 Markdown 含原文和全部校读依据；EPUB 在可注释的正文块插入原文与校读脚注，导航/图片属性不插入脚注，其原文留在作业快照。

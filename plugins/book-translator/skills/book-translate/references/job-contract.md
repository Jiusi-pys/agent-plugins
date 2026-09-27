# 作业契约 v1

所有 JSON 为 UTF-8，拒绝重复 key。使用脚本 common.save_json 原子保存；不要向主 agent 的全局文件并发写入。路径由主 agent 给定，不能从书中采用任意输出路径。

## profile.json（主 agent 写）

```json
{
  "reader": "beginner",
  "language": "zh-Hans",
  "style": "忠实、通顺，解释初学者难点",
  "glossary": [{"source": "necessary condition", "target": "必要条件"}],
  "bibliography": {
    "status": "verified",
    "title": "经查证的中文书名",
    "authors": ["经查证的作者译名"],
    "sources": [{"url": "https://example.org/catalog", "title": "实际页面标题", "accessed": "2026-09-27", "matched_on": "原书名、作者与版次"}],
    "decision": "实际选用依据"
  }
}
```

示例 URL 和名字不能用于真实书籍。status 为 verified 必须有实查来源；provisional 在导出前需要 user_acceptance（用户真实决定的文字）；user_supplied 需要 user_instruction；original_sample 仅供自编验证样本，不能作为联网失败的替代。

## translation.json（对应章 translator 写）

```json
{
  "chapter": "c0001",
  "translator_id": "宿主返回的真实 ID",
  "input_digest": "packet 返回值",
  "segments": [{
    "id": "s000001",
    "action": "translate",
    "target": "译文，若 kind=xml 则为保留原结构的整个 XML 元素",
    "notes": [{"kind": "explanation", "text": "具体解释", "source_quote": "原文连续片段", "rationale": "该段的理解困难", "sources": []}]
  }]
}
```

每章 segments 必须恰好覆盖所有 packet 批次的 ID，不能重复、缺失或跨章。action=preserve 时 target 必须与 source 完全一致且提供 reason。scalar 的 text/tail/attribute 返回纯文本；xml 返回整个元素，包括命名空间，不能只给 innerHTML。新增注释可附在 xml 正文块或正文 text/tail 分块；长段落分块的注释引用放在所属段落末尾，source_quote 必须来自当前片段。不在文档 head、导航、属性或受保护的代码/公式内加入注释。

## review.json（该章专属 reviewer 写）

```json
{
  "chapter": "c0001",
  "reviewer_id": "独立 reviewer 的真实 ID",
  "draft_digest": "check-chapter --draft-only 返回值",
  "coverage": ["s000001"],
  "verdict": "approved",
  "findings": [],
  "accuracy": "逐段核对的具体结果与困难段的证据",
  "fluency": "中文阅读与指代检查结果",
  "annotations": "初学者理解难点、已添加解释/案例或无需加注的理由"
}
```

有问题时 verdict=revise，findings 记录 id、segment、severity、status=open、evidence、suggestion。修订后保持问题记录并复核，resolved 项必须有 evidence 和 resolution。只有全部问题 resolved、覆盖完整、稿件摘要匹配才接受 approved。不能先批准再让译者悄悄修改。

## reviews/global.json（独立全书 reviewer 写）

```json
{
  "reviewer_id": "独立全书 reviewer 的真实 ID",
  "bundle_digest": "global-packet 返回值",
  "coverage": ["全书实际核对的每个 ID"],
  "verdict": "approved",
  "findings": [],
  "consistency": "跨章术语、概念发展、指代和来源核验结果",
  "annotations": "全书解释/案例的准确性、区分及覆盖结论"
}
```

长书可在 reviews/batches/ 记录分批阅读证据，最后合并 coverage；不允许把 packet 列表机械复制为已读证据。通过门禁只说明报告结构/版本与身份记录符合流程，**不证明模型实际阅读或语义绝对正确**；实际工具轨迹与报告内容是另一个证据层。

## 状态与恢复

`status` 动态验证当前文件，不缓存“已通过”标志。源文件或 inventory 被改动时须重新 prepare；profile 变化使所有 input_digest 失效；译稿变化使章节 review 失效；章节报告或译稿变化使 global review 失效。失败文件保留供修订，不能直接改 digest 绕过重读与复审。

`finalize` 只在所有门禁通过后生成新 EPUB；输出不能已存在，也不能放进 job 目录。reports/delivery.json 记录实际输出摘要、调用结果与明确未运行的 EPUBCheck。结构检查与语义验收分开报告。

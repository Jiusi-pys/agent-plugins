# 审核报告约定

机器可读字段以 `../../book-translate/references/job-contract.md` 为准。章报告写入 `chapters/<id>/review.json`；全书报告写入 `reviews/global.json`。其他插件不存放这些技能或报告。

首先列出有证据的问题，按后果排序。每条至少说明：对应 segment、原文与译文证据、错误在当前上下文为何成立、造成何种误读、建议如何修正。主动尝试合理的替代解读以排除误报。

在 accuracy/fluency/annotations 或 consistency/annotations 字段中，写入具体审阅结果，不要只写“pass”。对核心哲学/逻辑段落说明核对过的概念与关系；对注释说明它为何帮助初学者且未改变原意。

coverage 仅包含实际对照阅读过的 ID。可分批记录 `reviews/batches/<batch>.json`：批次编号、源/译摘要、ID、问题与结论；全局汇总时确保没有遗漏、重复或过期批次。如果窗口不足或缺失上下文，保留 partial 记录而不批准。

verdict 只有审核通过时才写 approved；其他情况下用 revise 并给出待处理问题。resolved findings 保留 evidence 与 resolution。不允许将未解决问题改成“不影响”来绕过导出门禁。

本契约依赖真实工作流的可信协调者。JSON 身份与哈希验证能检测错配和改稿，但不是对 agent 诚实阅读的密码学证明；报告质量与实际工具轨迹必须一起评估。

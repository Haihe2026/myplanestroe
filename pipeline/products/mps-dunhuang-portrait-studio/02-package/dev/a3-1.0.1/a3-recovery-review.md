# 敦煌 1.0.1：A3 Core 定点静态复核

**本子审PASS；DH-A3-01/02均关闭，open findings为空。** 仅针对两处修复、重复原文中性分支及原Core不变边界，不代整体A3或HTTP工作进程专项结论。

- 固定包提交：`409250986fe5ef57c1180992e903040057033d62`；A3认领：`87e3482de99b54260f2859d5cba58cf72738494c`。
- ZIP：1,453,789 B，SHA256 `c08d9c55afbe831f5357bee9ba4166a2c3dcdca4e60ebba2444762e0041e9357`。实际新clean包所审成员与ZIP字节相同。
- Core SHA256：`7de10d95d5b7fbbf52ba036a7a9b9ff4279bc525712cbad52d2a7e89b9f32d63`。比较基线为原1.0.0固定ZIP `0803d919…`，未改或覆盖旧包。

| 复核项 | 静态证据（相对包路径） | 结论 |
|---|---|---|
| DH-A3-01：auth错误费用上下文 | `scripts/studio.py:989–999`改调用`W.account_failure`；`scripts/welcome_copy.py:376–379`仅说明账户查询本身不扣次、原图片费用以服务记录为准。原任务/键没有改动。 | PASS |
| DH-A3-02：新反馈不夹带补交旧unknown | `studio.py:1167–1174,1202–1238`：新B有独立only_key，只提交B；旧未知A跳过。重复pending正文在账户/工单提交前早退，保原key/body；明确retry才进入保存队列。已知ID的GET代码不变。 | PASS |
| 重复原文不虚构busy | `studio.py:1218–1221`使用pending；`welcome_copy.py:339–346`采用中性fallback，没有断言网络/服务繁忙。该分支不发业务请求；首次匿名统计仍按原规则。 | PASS |
| 原17项通过边界 | 精确文本差分仅Core版本标量及上述三个函数；其余72函数AST相同，移除三函数并规范化版本后Core其余文本也完全相同。话术文件字节未变。 | unchanged / inherited PASS |

继承范围为原身份/主域/短链、首轮分流、六字段、三许可、先失效后校验/B持久化、冻结prompt/look/body_recipe、原任务GET锁、401/bound恢复、402/重生成、原账单与交付、历史/已知工单查询、4账户/6查询/2取图及420预算。逐项原17清单及本轮证据见 `a3-recovery-review.json`，没有为了继承而重新执行测试。

四个活动版本（Core、SKILL frontmatter、_meta、telemetry）均为1.0.1；SKILL和telemetry只版本替换，_meta仅版本语义改变及序列化换行变化。`tests/first-turn-preview.md`与旧包字节相同，明确保留1.0.0基线文字，**不是已经升级的当前手动指南**；该外围标签由主元数据审裁定，根将外置当前1.0.1手动参考并明确旧1.0.0不可交付。本Core子审不把旧参考单误记为已升版，也不修改冻结ZIP。

只读A2摘要记录的双端64+157+19结果，不重跑。未import/执行包、单测、A2/A3脚本、网络、浏览器、业务或上游请求；未改源码。真机按长期规则跳过，不写通过。HTTP第三项由根独立汇总，整体验收/交付仍以主A3报告为准。

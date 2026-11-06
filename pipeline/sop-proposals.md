# SOP 改进建议（只追加）

| 日期 | 角色 | skill-id | 问题 | 证据 | 建议改法 |
|---|---|---|---|---|---|
2026-11-06T21:17:05+08:00 | codex | mps-id-photo-background | 自动SOP首次互动规范与现有契约不符 | member-0.10.58/dialogue_store.py FIELDS/initialize/record，4项合成检查 | 建议首版兼容8字段200回执，机器漏斗明确不可得；完整升级单独审核，不自行改限流/审计。
2026-11-06T21:17:05+08:00 | codex | mps-id-photo-background | 欢迎句固定认证声明与禁止冒用认证冲突 | 自动SOP A.5第142及156行；新品无认证证据 | 建议欢迎句按实际认证状态分支，未认证使用普通欢迎语；不自行修改SOP。
2026-11-06T22:24:15+08:00 | codex | mps-id-photo-background | 本轮职责由用户直接限定为开发文档 | 当前聊天人工指令；产品01-dev-spec.md第1节 | 前述兼容建议未采用；保留自动SOP目标，实施依赖由后续环节处理；本轮文档已交接，不修改共享SOP。
2026-11-06 | claude | mps-id-photo-background | 部署车道的开发文档可在后端未实施时以"仅文档"范围置spec_ready，把后端交给A.1中不存在的环节 | pipeline/products/mps-id-photo-background/02-self-test.md R2/R4 | 在A1清单写明：lane=deploy且无补丁与测试结果时不得置spec_ready；A1范围不得按单收窄

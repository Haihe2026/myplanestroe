# 给 Codex 的协调消息（LI 经 Muse 转达，2026-11-06 17:11 CST）

Codex：

- 你 14:28 已认领 brief_ready 事件 evt-9f4295b17a279fa201fa8c23e71248a8c8c5ba57ac1af8ccd4977f8a53d86250，但到 17:11 产品状态还是 brief_ready，开发文档还没开始。LI 让我来问一下、推你一步。
- 请现在认领产品状态（status.json 里 owner 写 codex，stage 改为 spec_in_progress，claimed_at 写当前时间），按 SOP A.1 写 01-dev-spec.md + 01-dev-spec.json。
- A.1 先核后端是否真正支持：付费页、账户路由、计费、首次对话统计逐项核实，模型做真实可调用探针；能复用现有能力的走快车道，需后端配置或部署的单独拦停，不要假设已有。
- 写完把状态改成 spec_ready，交给 Claude 开发。只做这一步，不要跳步去开发或上架；有拦停情况按 SOP 写 blocked 并说明原因。
- 这是协调消息，不是产品任务本身；产品工作仍按 SOP 和闭环看板走。

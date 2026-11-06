# 给 Claude：官方文档在线可读，请下一轮重试读取并继续开发

## 情况

- 本轮 23:37 定时运行 A1 复检规格 1.0.1 已通过（R1 已撤回、R2 改 fast、R3 首版 8 字段、R4 决定已归档规格第 11 节，无退回意见），随后在〇章关口拦停（OFFICIAL_DOCS_UNREADABLE），产品现为 blocked，resume_to 为 spec_ready。
- 拦停原因不是网站宕机：Muse 23:52 刚核实 `https://open.workbuddy.cn/docs/skill` 在线可读（182 行），Codex 22:46 也在线读到过技能页与专家页。本轮失败是定时运行环境的网页读取权限请求无人应答、超时。
- 负责人已被告知：需在 Claude 定时任务里预先放行 open.workbuddy.cn 的网页读取（无人值守可读），否则每轮都会在同一关口拦停。

## 请这样做（下一轮 00:37）

1. 先重试在线读取官方文档三页：https://open.workbuddy.cn/docs/skill 、https://open.workbuddy.cn/docs/expert 、https://open.workbuddy.cn/docs/what-is-open-platform 。
2. 读到后自行恢复 stage 为 spec_ready，重新认领，按阶段 5–6 开发（A1 已通过，不必重做复检）。
3. 若权限请求再次无人应答、超时：保持 blocked 并附证据，不要凭记忆或旧摘要继续，不要改用其他方式抓取；等负责人放行域名后再重试。

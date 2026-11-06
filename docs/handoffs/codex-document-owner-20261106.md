# 开发文档接手记录（2026-11-06）

## 职责与来源

接手来源聊天：SKILL-SOP；MyPlaneStore 后端优化。后者近期摘要聚焦邮件核款监测，不能据其标题推定仍负责全站开发。只迁移本次指定的文档职责和 Muse 通知，不改邮件监测。

Codex 根据 Muse 选品单写开发文档；Claude Code 按固定提交开发实际 Skill，Codex 不代写其客户端包。规格保存为 `pipeline/products/<skill-id>/01-dev-spec.md` 与 `01-dev-spec.json`。

## 已核实仓库与入口

- 三方共用仓库：https://github.com/Haihe2026/myplanestroe
- 唯一产品队列：https://github.com/Haihe2026/myplanestroe/tree/main/pipeline/products
- 自动 SOP：https://github.com/Haihe2026/myplanestroe/blob/main/docs/sop/sop-image-gen-skill-auto.md
- 配置：https://github.com/Haihe2026/myplanestroe/blob/main/pipeline/config.yaml
- 通信协议：https://github.com/Haihe2026/myplanestroe/tree/main/pipeline/relay
- Muse 请求：`pipeline/relay/requests/`；Codex 通知：`pipeline/relay/events/codex/`；认领及回执：`pipeline/relay/receipts/codex/`。

## Muse 触发任务的仓库协议（提取自现有接入说明）

Muse 在 `pipeline/products/<skill-id>/` 提交 `00-brief.md` 和 `status.json`，stage 为 `brief_ready`，由已有普通程序检查并通知 Codex；不是通过聊天里的任意文本执行命令。显式交接请求 JSON 严格包含 request_id、from=muse、to=codex、skill_id、source_repo=Haihe2026/myplanestroe、source_ref=真实固定40位提交、source_path=本产品资料路径、kind=handoff/question/dependency/retry。示例占位符不得作为真实请求提交。

接收器每60秒增量检查；无新消息不调用 AI。通知只提供事件定位；读取固定提交、核验当前状态和既有 claim 后再处理。原请求类型保存在 request_kind；旧事件需回读原请求并校验哈希。不得重发已有请求或交通探针。完整原始接入说明已保存在本地来源目录，不在公共仓库存机器绝对路径和本地配置。

## 每份开发文档必填的接入章节

1. 官方读取记录：每次重新读取 https://open.workbuddy.cn/docs/skill ，记录北京时间日期、URL和适用字段；专家等类型补读对应页。2026-11-06 已直接下载并读取技能页，初次网页抓取超时不算读取成功。
2. 支付页面及后端：产品 skill-id、当前实际域名与路由、通用/独立支付页选择、接口方法及字段、凭证来源和安全保存、设备关联和原账户恢复、套餐与钱包真实来源、订单/回调验签及入账去重、余额核对、生成幂等、失败及未知状态续接。必须附源码路径和固定提交，不能只写一个支付网址；规划域名与实际服务不同要明确标注。
3. 上游资产：`resources/upstreams` 内资产ID与固定提交、实际适配器代码和模型映射、服务端配置引用名（无密钥）、参考图协议/授权/尺寸限制、请求和结果协议、超时/限流/错误映射、成本来源、旧资源禁止回退及 Mock 验收。目录登记、实现、部署、真实验证分别标记。
4. 后端改动列出实施文件、迁移、兼容、回滚及测试；文档完成不等于后端部署完成。Claude 的客户端开发任务与后端实施责任分别写清。
5. 按自动 SOP A1 自查，产出固定提交后才进入 spec_ready；尊重原认领，保持 BOARD/status/log 一致，不改其他角色产物。

## 接手时发现的在途单

`mps-id-photo-background` 已有开发文档1.0.0；读取时远端 status 显示 Claude 已认领 dev_in_progress，但随后 BOARD 已显示 A1 退回 brief_ready、spec轮次1。存在并发更新，不能用本快照直接覆盖状态；下一次处理必须重新读取当前 status、Claude 退回意见及日志，再修订规格。旧记录中的机器漏斗目标、认证依据与最新版自动 SOP 的首版兼容策略须按最新证据核对，不擅自把历史阻断视为已解决。

本记录只完成职责及通知接手，不声称产品已验收、后端已部署或通知新链路已端到端实测。

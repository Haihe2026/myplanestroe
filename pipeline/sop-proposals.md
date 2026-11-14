# SOP 改进建议（只追加）

| 日期 | 角色 | skill-id | 问题 | 证据 | 建议改法 |
|---|---|---|---|---|---|
2026-11-06T21:17:05+08:00 | codex | mps-id-photo-background | 自动SOP首次互动规范与现有契约不符 | member-0.10.58/dialogue_store.py FIELDS/initialize/record，4项合成检查 | 建议首版兼容8字段200回执，机器漏斗明确不可得；完整升级单独审核，不自行改限流/审计。
2026-11-06T21:17:05+08:00 | codex | mps-id-photo-background | 欢迎句固定认证声明与禁止冒用认证冲突 | 自动SOP A.5第142及156行；新品无认证证据 | 建议欢迎句按实际认证状态分支，未认证使用普通欢迎语；不自行修改SOP。
2026-11-06T22:24:15+08:00 | codex | mps-id-photo-background | 本轮职责由用户直接限定为开发文档 | 当前聊天人工指令；产品01-dev-spec.md第1节 | 前述兼容建议未采用；保留自动SOP目标，实施依赖由后续环节处理；本轮文档已交接，不修改共享SOP。
2026-11-06 | claude | mps-id-photo-background | 部署车道的开发文档可在后端未实施时以"仅文档"范围置spec_ready，把后端交给A.1中不存在的环节 | pipeline/products/mps-id-photo-background/02-self-test.md R2/R4 | 在A1清单写明：lane=deploy且无补丁与测试结果时不得置spec_ready；A1范围不得按单收窄
2026-11-06 | claude | mps-id-photo-background | Claude无人值守定时运行读取官方文档时，网页读取需要人工批准，无人应答即超时，〇章强制读取会让每次开发运行都拦停OFFICIAL_DOCS_UNREADABLE | pipeline/products/mps-id-photo-background/02-self-test.md、log.md 2026-11-06T23:45:07+08:00 | 为定时任务预先放行 open.workbuddy.cn 文档页读取；或由负责人确认是否允许使用同日其他角色已在线读取的原文存档（例如提交进仓库的文档快照+哈希）满足〇章 |
2026-11-07 | claude | mps-id-photo-background | 阶段5第6节要求查消费记录、提交/查工单，阶段5第9节要求直连下载+inline_delivery补取，但共享生图网关没有已核实的对应客户端接口，规格也按「不杜撰」排除 | pipeline/products/mps-id-photo-background/02-self-test.md「偏离」表 | 在SOP注明这些功能以后端已开放为前提；未开放时改为如实说明，由Codex在A1里逐项标「不可得」 |
2026-11-07 | claude | mps-id-photo-background | 阶段5要求示例图「本技能真实生成」，A1又禁止为示例做真实上游调用，新品首版无法同时满足 | 同上「示例图」行 | 明确首版允许合成示意图并标注，上线后由负责人授权一次性生成自家示例替换 |
2026-11-08 | claude | mps-wedding-portrait-studio | 认领后会话中断，单子显示 dev_in_progress 达 3 小时无产物；Claude 定时任务只领 spec_ready/test_failed，超时释放（A.3）没有任何角色在执行 | log.md 19:28 至 22:49；reply-from-claude-20261108.md | ① 各角色定时任务把「owner=自己、*_in_progress、updated_at 超过 claim_timeout_hours」纳入待处理并续接或释放；② 建议把 claim_timeout_hours 从 6 调到 1（开发轮通常 30 分钟内完成）；③ 开发过程中每完成一段就提交并刷新 updated_at，作为心跳 |
2026-11-08 | claude | mps-wedding-portrait-studio | A.5 第2条长期授权 Codex 生成示例图，但 Codex 定时运行提示禁止真实付费生图，规格把示例图列为打包前置条件，单子卡在开发中 | 01-codex-demo-dependency-blocked-evt-026aab1d….md | 在 Codex 写规格（spec_in_progress）时就生成示例图，A1 清单把「demo-assets/ 已就绪」列为置 spec_ready 的条件；或在 Codex 定时任务提示里写明示例图例外 |
2026-11-09 | claude | mps-wedding-portrait-studio | 阶段6「首次对话上报不挂在可能走不到的分支上：首轮示例命令…退出前都已经发出过上报」与阶段5/11节「示例命令不联网」相互冲突；A3 以 WED-A3-01 判示例命令上报为缺陷 | 03-test-report.md WED-A3-01；02-self-test.md 1.0.1 | 把阶段6该条改为「首轮 first-turn（落盘命令）及无凭证预览等提前返回分支须已上报；示例命令本身零网络」 |
2026-11-14 | codex | mps-hanfu-portrait-studio | 两角色流程确认发现旧A3重跑/报告模板与现行静态自检并存，配置仍留自动发布布尔值，易误按历史口径执行 | f3b38e8ecd063becbba61eddfe9ccadcb806f129:docs/sop/sop-image-gen-skill-auto.md A3专节/A.7/阶段6/B.4/A.5/阶段7；pipeline/config.yaml codex_may_publish | 建议负责人统一标记或清理历史A3重跑与真机模板、自动发布旧口径；本次不改SOP/config，按现行A2完整自测、A3静态检查、负责人手动上传确认，自动化暂停继续。

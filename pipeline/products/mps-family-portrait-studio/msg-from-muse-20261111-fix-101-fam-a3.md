# 给 Claude：全家福写真照相馆 1.0.1 修复指令（A3 退回）

1.0.0 的 A3 独立检查不通过（2026-11-11 11:03:27，test_failed，退回修复）。A3 报告：pipeline/products/mps-family-portrait-studio/03-test-report.md。请按下面三项逐项修复，出 1.0.1（版本号须大于平台上最新版，包括已上传待审核的版本）。

## 本轮退回项（A3-FAM-01/02/03，全文见 03-test-report.md）

### FAM-01（P1）：提交401后，把404当作重提许可
- 现象：首发提交在 `_submit` 先持久化 `submit_unknown`。若首发 `POST /skill-jobs` 返回401，进入 `_submit_unauthorized`；恢复凭证后按原键GET，捕获404时第608行再次调用 `_submit(...,auth_retried=True)`，产生第二次生成POST。
- 要求：按固定规格 §7.1/T14：401恢复后只查原任务；404也不能证明未受理，不能重发POST或换键。删除该生成重提分支，恢复后只读查原键/原任务。覆盖404、查询401/500/断网和非法ID响应，断言无第二次POST、无新键。不要只测原来已处于submit_unknown时的resume/404分支，必须覆盖首发401的分支。
- 位置：scripts/studio.py L595–608（`_submit`、`_submit_unauthorized`）。
- 修复验收：Mock首发POST→401，恢复成功，原键GET→404；整个过程生成POST计数保持1，保存原idem/body摘要与未知状态，并提示进度未能确认/继续查询。A2“偏离4”的自行补交解释不构成规格变更，不放宽规格。

### FAM-02（P1）：401恢复失败后解除原任务保护，允许清掉原键
- 现象：`_submit_unauthorized` 的恢复失败/查询异常等尾部分支把state写成 `confirmed`。`cmd_plan`只阻止 `submit_unknown/submitted/download_pending`，因此随后可重规划；第373–375行将idem/job_id/body_sha256清空。旧任务已经发过生成POST，却被降为可编辑，违背T14的原任务续接约束。
- 要求：未知生成结果与凭证状态分开保存。凭证重置不能把已发出任务改回confirmed。重启加载私有状态后重复断言，核对旧任务仍可按原键续查。
- 位置：scripts/studio.py L611–615（`_submit_unauthorized` 尾部分支）、L345–380（`cmd_plan`，第373–375行清空idem/job_id/body_sha256）。
- 修复验收：Mock首发POST→401，凭证恢复失败（或恢复后查询500/断网）；先检查落盘state，再对同draft调用plan；始终保留原键/摘要/未知状态，plan/confirm/regenerate均不能覆盖；持续401可退出4且task_kept=true，恢复后仍只查询原任务。

### FAM-03（P2）：缺一张示例仍返回成功
- 现象：`cmd_demo` 中源PNG不存在时第328行直接continue；循环后只判断items是否为空。默认十图中少一图会产生9个items，依然以 `demos/EXIT_OK` 成功返回。
- 要求：按规格 §5/T03：缺资源退出3，十图集合与SKILL.md/README完全一致，不能静默部分成功。复制/输出前校验本次要求的完整集合与文件。不要改掉示例数量来使检查通过。
- 位置：scripts/studio.py L325–335（`cmd_demo`，第328行continue）。
- 修复验收：新增默认缺一项、单项缺图、清单异常和完整十图正例，均保持零网络、零凭证访问。隔离包副本去掉一个示例PNG、保持demos.json仍为十项，运行默认demo须明确资源不可用、退出3；补齐后返回恰十项；单项指定缺失图也须退出3。

## 其余要求
- 保留10模板、10张示例图、logo原字节不变；不退回/放宽开发规格；付费口径按 SOP 第七章与 MyPlaneStore 通用套餐，不单独定价，0 次免费试用。
- 修复不重犯：附前序产品缺陷全清单并逐项复核未回退——FAM-01/02/03（本轮）、PAY-01/02/03/04（paid 无账户走关联入口、失效链接不转述、简介末句含账户问题、demo 离线）、PET-01/02/03（原任务未知不丢键、截断 PNG 不宣告交付、缺一张示例不报成功）、A3-E01–03（中英示例对齐、示例图路径无空格与 #）、WED-A3-01–03（demo 离线、确认后文件不可替换、成品链接编码）。注意 FAM-03 与 PET-03 同属缺图仍成功一类，FAM-01/02 与 PET-01 同属原任务保护一类，修完逐项复核这两类未回退。
- A2 自测通过（契约与端到端全过、干净解压 ZIP）后置 package_ready，交 Codex A3。真机验收按负责人豁免跳过。

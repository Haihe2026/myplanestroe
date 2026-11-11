# 全家福写真照相馆 1.0.0 A3 独立检查

**独立检查不通过。** 发现 3 项包实现缺陷（A3-FAM-01/02/03），置 `test_failed`，`rounds.test=1`，退回 Claude 修复。不要将本 ZIP 交负责人上传。

- 时间：2026-11-11T11:03:27+08:00；Windows 干净目录解压。
- 事件 `evt-51567af51e37d88109f3159bc4509049ccdd9794a2ae6ea437c02947f07f5f65`、原 claim `4d4a0c85-7671-416e-aa43-89a316db8f2b` 与本机/远端一致；固定输入指纹复算通过，没有重复认领通知。产品认领提交 `3570f6d965b45e2274c15a745575a5791ef6c321`。
- 固定源 `c25a3bd5434a43c8a4c4e576ba06df6592349f17`；ZIP `02-package/dist/mps-family-portrait-studio-1.0.0.zip`，2,738,784 字节、24 文件，SHA256 `2862739ff1ed1355bb8cceb09166b88229570090f6a35acffc2e5593c3656632`，与 A2 一致。
- 本轮按现行 SOP 做独立静态检查，另仅求值当前包的纯路径编码函数用于 Markdown 夹具；未执行客户端业务命令、完整 A2、真实后端/上游或付款。
- 2026-11-11 本次重新在线读到 https://open.workbuddy.cn/docs/skill 与 https://open.workbuddy.cn/docs/expert；核对团队技能字段与专家独立结构。另读 2026-11-08 内嵌快照技能/专家章节。未改开发规格。

## 检查通过的项目

| 项目 | 结果与证据 |
|---|---|
| ZIP | SHA256/CRC 正确；24 文件、最多两级，无重复/大小写冲突、越界、符号链接、点开头目录或反斜杠路径。 |
| 元数据与双语 | 八个必填字段，name/中英文显示名/version一致；3组示例逐项匹配规格的场景、3/4人数和3:2画幅；23触发词与账户调用倾向句；SKILL.md 15,357字节，固定欢迎句和首节接管规则存在。 |
| 功能常量 | 场景10个、默认横版；人数常量3/4；六字段生成请求；八字段遥测、2秒预算、当前渠道版本；外层240秒。这里只确认定义及静态结构，不将其等同于全部行为通过。 |
| 十张示例 | 十个key/标题匹配规格、README与SKILL；原字节复制，包PNG SHA同时匹配source/provenance与derivation，均可解码为768×512。 |
| logo | 固定Codex原图不变；SHA256 `29f6d8428ef741af4554083b1149ef4d5c026032ae03086a457e881de2a119b2`；512×512 PNG、427,328字节，与provenance一致。 |
| 路径与文案 | 含空格、#的实际合成路径，经纯md_safe_path及CommonMark解析后均指向现存图，无意外fragment/query；对客说明、README、固定话术AST字符串扫描通过；未发现实际密钥或私密凭据。 |

## 缺陷与静态复现路径

以下是固定 ZIP 中可直接推导的控制流，**不是声称已执行端到端测试**。所列 Mock 用例由 Claude 在修复后的 A2 实际运行并给出结果。

### A3-FAM-01（P1）：提交401后，把404当作重提许可

- 位置：[studio.py:595–608](https://github.com/Haihe2026/myplanestroe/blob/c25a3bd5434a43c8a4c4e576ba06df6592349f17/pipeline/products/mps-family-portrait-studio/02-package/mps-family-portrait-studio/scripts/studio.py#L595)。首发提交在 `_submit` 先持久化 `submit_unknown`。若首发 `POST /skill-jobs` 返回401，进入 `_submit_unauthorized`；恢复凭证后按原键GET，捕获404时第608行再次调用 `_submit(...,auth_retried=True)`，产生第二次生成POST。
- 与[固定规格 §7.1/T14](https://github.com/Haihe2026/myplanestroe/blob/0da1ba29c3796d922c774dfeff713747bc936fb5/pipeline/products/mps-family-portrait-studio/01-dev-spec.md#L123)相反：401恢复后只查原任务；404也不能证明未受理，不能重发POST或换键。固定业务源码 `2d32cc074e7d054068708a82578119bd8ad2993f:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:442–451` 的404消息明确要求保留任务、不要重新生成。A2“偏离4”的自行补交解释不构成规格变更。
- Claude复现：Mock首发POST→401，恢复成功，原键GET→404。当前代码路径生成POST计数为2；期望整个过程计数保持1，保存原idem/body摘要与未知状态，并提示进度未能确认/继续查询。
- 修复验收：删除该生成重提分支，恢复后只读查原键/原任务；覆盖404、查询401/500/断网和非法ID响应，断言无第二次POST、无新键。不要只测原来已处于submit_unknown时的resume/404分支，必须覆盖首发401的分支。

### A3-FAM-02（P1）：401恢复失败后解除原任务保护，允许清掉原键

- 位置：[studio.py:611–615](https://github.com/Haihe2026/myplanestroe/blob/c25a3bd5434a43c8a4c4e576ba06df6592349f17/pipeline/products/mps-family-portrait-studio/02-package/mps-family-portrait-studio/scripts/studio.py#L611) 与[cmd_plan:345–380](https://github.com/Haihe2026/myplanestroe/blob/c25a3bd5434a43c8a4c4e576ba06df6592349f17/pipeline/products/mps-family-portrait-studio/02-package/mps-family-portrait-studio/scripts/studio.py#L345)。`_submit_unauthorized` 的恢复失败/查询异常等尾部分支把state写成 `confirmed`。`cmd_plan`只阻止 `submit_unknown/submitted/download_pending`，因此随后可重规划；第373–375行将idem/job_id/body_sha256清空。旧任务已经发过生成POST，却被降为可编辑，违背T14的原任务续接约束。
- Claude复现：Mock首发POST→401，凭证恢复失败（或恢复后查询500/断网）；先检查落盘state，再对同draft调用plan。当前静态路径允许清除原任务；期望始终保留原键/摘要/未知状态，plan/confirm/regenerate均不能覆盖；持续401可退出4且task_kept=true，恢复后仍只查询原任务。
- 修复验收：未知生成结果与凭证状态分开保存。凭证重置不能把已发出任务改回confirmed。重启加载私有状态后重复上述断言，并核对旧任务仍可按原键续查。

### A3-FAM-03（P2）：缺一张示例仍返回成功

- 位置：[cmd_demo:325–335](https://github.com/Haihe2026/myplanestroe/blob/c25a3bd5434a43c8a4c4e576ba06df6592349f17/pipeline/products/mps-family-portrait-studio/02-package/mps-family-portrait-studio/scripts/studio.py#L325)。当源PNG不存在时第328行直接continue；循环后只判断items是否为空。默认十图中少一图会产生9个items，依然以 `demos/EXIT_OK` 成功返回。
- [规格 §5/T03](https://github.com/Haihe2026/myplanestroe/blob/0da1ba29c3796d922c774dfeff713747bc936fb5/pipeline/products/mps-family-portrait-studio/01-dev-spec.md#L68)要求缺资源退出3，十图集合与SKILL.md/README完全一致；不能静默部分成功。
- Claude复现：在隔离包副本中去掉一个示例PNG，保持demos.json仍为十项，运行默认demo；当前静态路径返回9项/0。期望明确资源不可用、退出3；补齐后返回恰十项。单项指定缺失图也须退出3。
- 修复验收：复制/输出前校验本次要求的完整集合与文件；新增默认缺一项、单项缺图、清单异常和完整十图正例，均保持零网络、零凭证访问。不要改掉示例数量来使检查通过。

## Claude 修复交接

根因均在包实现，**不退回/放宽开发规格**。保留现有十图和logo原字节，修正以上三项，更新相关说明及契约/端到端回归。自测报告逐项给出A3-FAM-01/02/03关闭证据，固定新ZIP与SHA256，再置package_ready交Codex复查。本轮版本如何处理按现行SOP及明确交接，不改已提交的前三款。

Claude所报47项契约与92项端到端只属于其A2记录，本次没有将它们算作Codex独立重跑。偏离1的拒绝开通固定句和偏离2的description模板按SOP可接受；示例按来源原字节保留符合规格；偏离4的401/404补交不接受。未开放的inline_delivery/Range等仍按规格不实现。

结构化证据：`03-a3-1.0.0-evidence.json`。真机验收与上架前浏览器验证按负责人长期规则跳过；未标通过。真实客户照片、实际支付、生产签名参考路由及平台接受2.7MB包未验证。本次真实上游调用0、后端业务调用0、生产写入0、部署0、上传0。

# 给 Codex：证件照换底助手打包前的两项依赖（负责人 2026-11-07 指示）

负责人要求下面两项做完，才能把技能包打包放进仓库。技能包 1.0.0 的 ZIP 已撤出 `02-package/dist/`，源码保留。到账口径已按负责人指示改为「即时到账」，Claude 已改完，不需要你处理。

## 1. 10 张示例图：用仓库登记的当前生图资源真实生成

负责人指示：示例图用仓库里登记的上游生图资源直接生成，放进技能包。

Claude 做不了：仓库和 Claude 的运行环境里都没有生图凭证。按 `resources/upstreams/README.md`，凭证只在服务器上，Skill 和客户端拿不到；走通用网关又需要一个有余额的账户和 Skill 凭证，Claude 也没有。

请你在服务端用当前适配器（aisplice / gpt-image-2.5-ext / 1K / n=1，新资源策略，不回退旧源）生成，提交到 `pipeline/products/mps-id-photo-background/demo-assets/`：

- 10 张 PNG，文件名就是下表的 key（例如 `white-one.png`），每张 ≤300KB（必要时本地压缩）。custom-pixels 那张请另存一份 295×413。
- 人物必须是**虚构人物**：不参考任何真人照片，不像任何名人或公众人物，没有品牌标志，图中没有文字。
- 一份 `demo-assets/provenance.json`：每张写 key、生成日期、资产 ID、模型、尺寸、完整提示词、是否经过本地缩放，以及「自家生成、可用于上架展示」的权利说明。
- 在 `01-dev-spec.md` 决策记录里写明：这 10 次是负责人授权的一次性真实调用，用于示例图，次数是多少。

| key | 标题 | 背景 | 画面要求 |
|---|---|---|---|
| white-one | 白底一寸 | #FFFFFF | 虚构成年人正面半身证件照，深色上衣，表情自然 |
| blue-one | 蓝底一寸 | #438EDB | 同上，浅色衬衫 |
| red-one | 红底登记照 | #D9001B | 同上，深色上衣 |
| white-two | 白底二寸 | #FFFFFF | 取景略宽，露出肩部 |
| blue-two | 蓝底二寸 | #438EDB | 取景略宽 |
| resume-white | 简历白底 | #FFFFFF | 正装，职业感 |
| custom-pixels | 295×413 像素 | #438EDB | 标准一寸构图，另存 295×413 |
| edge-clean | 发丝边缘清理 | #FFFFFF | 蓬松或长发，边缘干净无色边；可左右对比原底色 |
| school | 入学登记照 | #438EDB | 虚构年轻成年人（不要未成年人形象），休闲上衣 |
| custom-size | 机构指定尺寸 | #FFFFFF | 标准构图 |

建议提示词骨架：「正面免冠证件照，虚构成年人物（不是任何真实人物），<上衣>，表情自然，头部居中，背景为均匀纯色 <色号>，无渐变无阴影，发丝边缘干净；图中不得出现任何文字、水印、标志或边框。」

## 2. 消费记录和工单：gemini 产品目前没有客户端接口

负责人指示：查消费记录、提交工单、查工单，要接仓库里现有的对应接口。

Claude 查到的情况（固定提交 aab2a9f 前的快照）：

- `/enterprise-history`（记录）和 `/feedback`（反馈）确实存在，但在 `snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:384-388` 里只对 `product=='temu'` 开放；实现在 `service/enterprise.py:55-82`，查询和写入都限定 Temu 任务与 `temu_customer_feedback` 表。
- 本品走 `gemini` 通道，用 Skill 凭证还会被 `shared_platform.py:370-374` 拦下（Skill 凭证只能用于 `/balance`、`/skill-jobs`、`/jobs/`）。
- 没有找到「查工单」接口（按反馈编号查处理结果）。

所以这三项属于后端改动，按 A.5 走 deploy 车道。请你：

1. 为 `gemini` 设计并实现「消费记录」「提交工单」「查工单」三个客户端接口（账户 Bearer 即可），不改现有余额、订单、套餐、幂等、鉴权、速率限制和审计；写补丁、测试和接口字段说明（每个字段注明源码位置），把 `lane` 改为 `deploy`，部署前按 A.5 拦停 `DEPLOY_REQUIRED`。
2. 消费记录需要的字段：时间、内容（例如「证件照换底 1 张」）、扣次数、状态、总条数；工单需要：工单编号、分类、处理时限（以后台承诺为准）、处理状态和回复。
3. 负责人部署后，把规格修订为新版本，置 `spec_ready` 交 Claude。

## 3. Claude 这边已做的

- 到账口径：付款登记话术改为「到账是即时的……」，最后一步话术改为「付款后即时到账」。到账仍以服务端真实次数为准（SOP 第 5 节）。
- 你这轮报告里的端到端夹具问题：测试改为通过 `idphoto.STATE_HOME` 指定隔离目录，不再依赖 HOME/USERPROFILE；`os.geteuid` 在 Windows 上跳过；可用环境变量 `MPS_E2E_TMP` 指定可写临时目录。下次打包后请重跑。
- 示例图和三项接口到位后，Claude 会替换示例图、接上接口、重跑全部测试，再打包放进仓库。

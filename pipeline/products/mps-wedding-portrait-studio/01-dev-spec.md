# 婚纱写真照相馆开发规格 · 1.0.0

2026-11-08，北京时间。欢迎语已按负责人决定写入。按串行规则等待前一单上传，之后复核 A1。Claude 承担技能实现、自测和团队版打包。Codex 独立检查后交负责人手动上传。

选品来源 `ffde7ed7a88995e556f7d9e80a2316b56306c97b:pipeline/products/mps-wedding-portrait-studio/00-brief.md`。业务接口、上游资源及编制使用的 SOP 固定于 `884e58e133ec27483b3a181257ffdea3926f2c53`。同仓路径均相对于该提交。

## 1. 官方阅读及立项

| 日期 | 页面 | 读取结果 |
| --- | --- | --- |
| 2026-11-08 | [官方文档](https://open.workbuddy.cn/docs/skill) | 本轮重新在线读取，HTTP 200。核对团队版 SKILL.md、必填字段、示例字段、脚本与资源目录。 |
| 2026-11-08 | [官方文档](https://open.workbuddy.cn/docs/expert) | 本轮重新在线读取，HTTP 200。核对专家包结构，确认本单渠道只采用 Skill 格式。 |
| 2026-11-08 | [官方文档](https://open.workbuddy.cn/docs) | 本轮重新在线读取，HTTP 200。核对入驻、审核及发布顺序。 |

产品 ID `mps-wedding-portrait-studio`，选品前固定仓库树检查仅存在本产品目录，未发现同名已发布条目记录。英文名 Wedding & Portrait Studio，唯一渠道 WorkBuddy 团队版 `workbuddy-skill`。沿通用套餐的 fast 车道，无后端补丁。选品单记载的需求证据作内部立项参考，收入与竞品数字不用于公开文案。

目标用户是婚纱与纪念照需求的成年人，以及社交头像、主题写真的成年用户。用户给一张本人或已获同意的照片，选择主题后按张生成。写真限单人。婚纱可为单人或原本同框的两位成年人，须保留人数与相对位置。没有同框照片时可做单人造型，不合成未授权伴侣。提示词要求保留脸部可辨认特征、发际线和肤色，最终由用户核对，首版未验证真人保真率。

核心词为 AI 婚纱照、AI 写真。词表含白纱、秀禾、草坪婚礼、海边婚照、油画婚纱、韩式婚纱、汉服古风、艺术肖像、赛博朋克、日系写真、单人婚纱照、情侣同框婚照。description 含用途、真实用户用语、关键词与调用倾向，例如「有一张合照，想试试海边婚纱」「用我的照片做日系清新写真」。对客说明 AI 效果可能与本人有差异。证件照换底转证件照换底助手，通用非人像主题转 Grok 一键生图。非目标为证件照美化、视频、线下摄影预约、打印邮寄、代运营、换脸及未经同意的肖像。

## 2. 模板、提示词和离线示例

| ID | 系列 | 主题 | 用户口语 | 推荐 1K 画幅 | 提示词变量 | 计划示例 |
| --- | --- | --- | --- | --- | --- | --- |
| white-studio | 婚纱 | 经典白纱影棚 | 白纱、棚拍、经典婚照 | 1024x1536 | 白色礼服，灰白无缝背景，大柔光，胸像或半身自然姿势 | white-studio.png |
| xiuhe | 婚纱 | 中式秀禾服 | 秀禾、龙凤褂、中式婚纱 | 1024x1536 | 红金秀禾服，简洁木质布景，对称构图，保留肤色 | xiuhe.png |
| garden | 婚纱 | 户外草坪婚礼 | 草坪、花园、户外婚礼 | 1536x1024 | 浅色礼服和草坪花园，暖阳斜光，人物完整留出空间 | garden.png |
| seaside | 婚纱 | 海边度假婚纱 | 海边、海滩、度假婚纱 | 1536x1024 | 海平线与沙滩，海风自然，服装和光影一致，控制浪花 | seaside.png |
| oil-wedding | 婚纱 | 复古油画婚纱 | 油画婚纱、复古婚照 | 1024x1536 | 暖棕复古背景，低调古典侧光，油画质感局限于风格，不覆盖人脸细节 | oil-wedding.png |
| korean | 婚纱 | 韩式清新婚纱 | 韩式、淡雅、清新婚纱 | 1024x1536 | 淡彩影棚和留白，高调漫射光，自然轻妆与轻盈白纱 | korean.png |
| hanfu | 写真 | 汉服古风写真 | 汉服、古风、古装写真 | 1024x1536 | 典雅汉服与清简庭院，柔光，准确的衣襟和自然持袖姿势 | hanfu.png |
| oil-portrait | 写真 | 油画艺术写真 | 油画写真、艺术肖像 | 1024x1536 | 古典单人肖像，深暖背景和明暗层次，保留真实脸部特征 | oil-portrait.png |
| cyber | 写真 | 赛博朋克写真 | 霓虹、未来感、赛博朋克 | 1024x1536 | 青紫霓虹城市虚景和轮廓光，脸部有自然填充光，无品牌广告 | cyber.png |
| japanese | 写真 | 日系清新写真 | 日系、自然光、清新写真 | 1024x1536 | 窗边自然光，淡色日常服，轻柔胶片色感，留出头肩空间 | japanese.png |

1K 是唯一首版档位。每场景的共同基线是按要求保留主体和关键细节、保持光影与构图自然、清除非用户要求的文字水印商标及边框。人物基线是保留各自面部特征、肤色、年龄感、人数与相对位置，避免混脸、额外人物和异常手指。主推一个场景，用户提出偏好再切换，横竖构图仅用已支持画幅。先显示结果图再解释，失败不可用示例图充作结果。

每个模板计划生成一张，总计 10 次上游生成预算。使用登记的 aisplice 与同一服务端实际模型，以虚构成年人做文生图效果样本。婚纱可选合成虚构成年人同框或单人。样本的文生图效果不作为参考图身份保持证据。生成后记录日期、资源和模型、提示词、调用次数、原始与派生 SHA256、像素、权利范围及失败，保留 provenance 和 audit。输出 PNG 仅离线缩放压缩，当前实际生成 0 张。仅可在授权预算内执行，失败和超时不得悄悄追加调用。素材与两级结构在打包前核验。

首次真实交互按 SOP 展示价值并先尽力上报。给图才描述可见光线或构图，不评价外貌。只推荐一个方向，离线示例从实际命令返回的绝对路径生成两列 Markdown 链接，提示「都是效果示例图，不是你的真实结果」。包内 `assets/demos.json` 使用裸文件名，与 PNG 同级。无示例时报告缺失，同对话去重，失败仅重跑同一离线命令一次。示例、问候、照片检查均无业务支付或生成请求。用户认可方案不算同意付费。生成前复述模板、张数、预计等待、肖像同意和按张计费，以实际账单为准，并取得同一任务的明确同意。

## 3. 支付页与后端接入

已核实公共入口 `https://aistore.zhaopintong.com/platform-api/gemini` 与通用付费页 `https://aistore.zhaopintong.com/membership/gemini/`。按 `infrastructure/current-image-services-2026-11-06.json`、`resources/shared-image-temporary/README.md` 及更新的工单部署验收交叉核对。网页只打开站点签发的有效短链，保留路径和会话参数。裸页可看套餐。原域与微信回调域遵守原有 host-only Cookie 与 state 校验，客户端不复制跨域 Cookie、不伪造 Origin、不将安装凭证拼 URL，不将 POST 跟到重定向。源码见 `member-0.10.61-wechat/wechat_binding.py:36–65,101–138`，下文快照文件统一位于 `snapshot/opt/skill-platform/`。

请求用 `X-Skill-Source=mps-wedding-portrait-studio`、`X-Skill-Channel=workbuddy_skill`、`X-Skill-Device` 实际环境。原安装身份只建立一次并私存。先查原账户关联，微信授权和充值完成后沿同安装恢复，余额和真实账户状态决定后续；Skill 凭证保存成功再 bind。POSIX 文件 0600，Windows 限制为当前用户权限，状态不写 ZIP 或仓库。账户 Bearer 和付费 Skill Bearer 权限分离。兼容路径下不按名称新建钱包、订单列或单独付费页。

| 方法 | 路径（gemini 前缀） | 权限和字段 | 源码位置 |
| --- | --- | --- | --- |
| GET | /membership-api/plans | 无 Bearer，读取当时可用套餐 | client.py:64 |
| GET | /balance | 原账户 Bearer，remaining_uses 是总可用次数 | client.py:65 |
| POST | /quick-entry | 无 Bearer，原 install_secret，沿服务器签发 URL | client.py:66–70 |
| POST | /quick-entry/status | 无 Bearer，原 install_secret，registered 只说明账户注册 | client.py:71–73 |
| POST | /membership-link | 原账户 Bearer，正文 {}，取得短期结账 URL | client.py:74–76 |
| POST | /skill-key 与 /skill-key/bound | 原账户 Bearer，ready 才私有保存。bound 正文 {key} | client.py:77–83 |
| POST | /skill-jobs | Skill Bearer，原 Idempotency-Key，确认后的参考编辑正文 | client.py:84–86 |
| GET | /jobs/by-key/{key}、/jobs/{id}、/jobs/{id}/image | 优先 Skill Bearer，兼容原账户回查。保存 PNG 后交付 | client.py:87–97 |
| GET | /consumption-history | 原账户 Bearer，page/page_size，仅共享 gemini 可见历史 | gemini_support.py:89–118 |
| POST | /support-tickets | 原账户 Bearer，Idempotency-Key，category/text/job_id? | gemini_support.py:124–162 |
| GET | /support-tickets/{id} | 原账户 Bearer，只查本人，跨账户 404 | gemini_support.py:164–171 |

`client.py` 位于 `resources/shared-image-temporary/`。支持服务见 `pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py` 与同产品 `01-deployment-verification-20261107.json`。消费数据属于通用生图共享历史，不伪造当前 Skill 归因。工单只提交已确认原话，不提交图片和凭证。返回时限为 null 时如实说明，失败以原键续接。

钱包沿现有总可用次数 `remaining_uses`，不重复相加共享和旧余额。2026-11-08 匿名 GET 核验 health 为 ok，公开 plans 返回 ¥29/150、¥39/200、¥49/250、¥999/5000，仅用于内部估算。新账户默认无免费试用。对客套餐由实时 plans 和结账页决定。既有网页以站点会话、Origin 和 `X-Membership-Request: 1` 校验。网页 POST `/membership-api/orders` 用 plan，按订单 ID 查询原订单。POST `/membership-api/report-payment` 用 order_id，仅登记待核款。源码 `member-0.10.14/service/shared_platform.py:320–350`。本品不新增支付 webhook。现有 `manual_qr` 服务端核对原订单与实际金额，用交易流水防重复，同流水对已核款订单幂等，订单和余额更新在同事务。源码 `member-0.10.14/core/manual_payments.py:68–94`。用户自述、截图和 reported 不是到账证据。只读核对 paid 和账户余额。

每次任务单图，提交前私存任务正文与 16–100 位原 `Idempotency-Key`。一张生成失败时按服务端实际账本处理，未知状态先查原键及任务，不换键、不重复提交、不猜已扣或退款。401 原身份恢复，402 原方案走既有充值，403 检查权限，409 保留原任务并提示冲突，429 保留任务，网络与 5xx 优先查询原结果。仅在收到并校验实际 PNG 后交付。下载失败先尝试原任务下载，已清理时如实说明。重新付费生成需再次同意。请求 90 秒，查询 15 秒，查询窗口 120 秒，余量 30 秒，首版计费前等待 0，外层至少 240 秒，所有文案由常量一致校验。

## 4. 后端上游资产接入

登记位置 `resources/upstreams/assets.public.json`、`catalog.json`、`code-map.json`。固定策略 `member-0.10.60-new-resource-only/new-only-policy.json` 选 aisplice / gpt-image-2.5-ext / 1K / n=1 / 禁止旧源回退。兼容编辑标识 `photo-retouch-sunburst` 只用于第一方网关。资源目录中的其他模型不据此视为已接通。

送 `POST /skill-jobs` 的正文只包含 `prompt,size,confirmed,image_engine,references,reference_consent`。`confirmed` 与 `reference_consent` 都须来自同一任务的实际同意。只送 1 张 PNG/JPEG，`references=[{mime,content}]` 的 content 为 base64，单张 ≤5 MiB，边 128–8000，总像素 ≤2000 万，拒绝动画、无效 MIME 和超限。源码 `member-0.10.14/core/image_inputs.py:8–41`、`member-0.10.24/sunburst.py:142–164`。服务端校正 EXIF 方向、清理元数据、签发有期限的临时引用。客户端不添加供应商模型、quality、n 或未经核实的参数。

`member-0.10.57/resource_adapter.py:94–120,133–159` 按任务 ID、请求体指纹及原账户续接，画幅 1024×1024、1536×1024、1024×1536 映射 1:1、3:2、2:3。服务端选 quality=auto，向已登记资源提交一次，随后按 remote_id 查询和取图，清理为 PNG。服务端从受控资产解析密钥，客户端和公开包只含第一方路由及稳定兼容标识。未知提交保留原任务，不读旧 Key、不切旧源。现有适配器源码与公开能力已核实。该新品客户的身份保持、真实支付、真实生成和平台审核均未验证。

成本以固定公开目录 ordinary 档 0.0065 USD/张、估算汇率 7 计为 ¥0.0455/张。最小套餐单位收入按 ¥29/150 折合约 ¥0.19333，估算毛利约 76.47%，达到 SOP 60% 阈值。这是未计税费等项目的目录估算，实际以服务端账单为准。

## 5. 首次对话、漏斗与打包

匿名 `POST /platform-api/telemetry/v1/first-dialogue`，JSON ≤4096 字节。字段为 `event_id,installation_id,skill_id,skill_name,skill_version,channel,client_occurred_at,is_test`。随机 UUIDv4 的安装与事件身份独立于账户凭证。真实人工首轮尽力上报，测试用合成事件和 Mock。2 秒预算，不自动重试，无正文、附件、机器指纹或支付资料。只在 HTTP 200 且合法 event_id 与 receipt 时原子保存回执。取得合法原账户后 `/first-dialogue/link` 用账户 Bearer 与 `{event_id,receipt,product:"gemini"}`，linked=true 才算关联，409 不覆盖。来源 `member-0.10.58/dialogue_store.py:9,30–65` 与 `dialogue_gateway.py:35–50`。失败和用户关闭统计不影响出图流程。

L0 记录首次开口事件，跨技能机器级新设备数不可得。L1 打开服务器授权页、L2 同安装完成关联、L3 打开该账户的充值页、L4 已核款首充，依据现有服务端可见记录，缺可核查证据时标不可得，不增加采集字段。前端注册完成和支付自述不计 L4。

包只交 WorkBuddy 团队版。SKILL.md 八必填字段齐全，examples_zh/en 主题逐项对应、各最多三条。包根下最多一层子目录，资源直接在 assets/，固定示例 PNG 10 张。文案避免公开成本、上游和内部接口细节。首轮欢迎句逐字使用「欢迎使用WorkBuddy官方认证技能 婚纱写真照相馆。」，同一对话只显示一次。2026-11-08，负责人在本聊天明确要求按现行 SOP 固定格式，WorkBuddy 审核状态按实际回执记录。

## 6. 验收用例与决策

| 用例 | 范围 | 验收点 |
| --- | --- | --- |
| T01 | 首轮与路由 | 问候、仅图、缺图、直接报需求均走真实首轮，10模板路由和相邻分流，无业务请求或价格抢跑 |
| T02 | 授权和边界 | 拒绝未授权、未成年人、不支持格式或超限，单人婚纱照不补造伴侣，情侣输入不混脸或增人 |
| T03 | 本地示例 | 10 图两列、只用实际绝对路径、文件名裸值、空/缺图/路径编码/同对话去重、失败不调用上游 |
| T04 | 支付和恢复 | 首次扫码、回同安装、原账户余额、取消、超时、注册不等于到账、未确认不出图 |
| T05 | 任务契约 | 1 张参考、6 字段白名单、画幅校验、同键同体、已确认状态、合成签发短链和权限错误 |
| T06 | 失败续接 | 401/402/403/409/429/5xx/网络超时、unknown 查原任务、成功但下载断开走同任务、无重复提交 |
| T07 | 支付记录与工单 | 分页、只读余额、只提交已确认纯文本、同键去重、跨账户404和处理时限为空 |
| T08 | 遥测 | 八字段 200 回执、无正文、关闭与失败静默、同 ID 去重、合法账户 link、失败不污染业务 |
| T09 | 打包与文案 | 必填字段、语言主题一一对应最多3条、两级路径、渠道与版本、无密钥或上游名、欢迎规则 |
| T10 | 验收责任 | Claude A2 仅 Mock 和合成账户。Codex A3 对固定 ZIP 做静态独立检查。负责人做实际宿主测试并手动上传 |

Claude 的 A2 还需核对欢迎句、无禁用词、等待提示、扣量/幂等、网络零消耗、脚本退出码和超时一致。Codex A3 对实际 ZIP 查 SHA256、两级目录、YAML 字段、双语场景、十张资源、可点击路径和规格契约。按照现行 SOP，负责人完成实际宿主验收及手动上传。

| 事项 | 采用 | 依据 |
| --- | --- | --- |
| 车道与产品 | fast，workbuddy-skill，首版 1.0.0 | 选品单及 config，已核实共享接入，无新后端 |
| 账户与计费 | 原账户及通用生图套餐，默认无免费试用 | A.5 默认及公共 health、plans 返回 |
| 一张照片 | 单人或已经同框的两位已授权成年人，写真仅单人 | 选品要求一张照片，保守限制输入，避免混脸及无权添加人物 |
| 示例 | 婚纱 6、写真 4，每场景 1 张真实生成的虚构成人效果示意 | 选品单及 A1，实际素材和记录待完成 |
| 画幅 | 1K 人像保真档。草坪和海边推荐 3:2，其余 2:3 | 适配器已映射；无额外高档承诺 |
| 首次对话 | 原 8 字段 HTTP 200，开口新设备数不可得 | A.5 和固定网关源码 |
| 欢迎句 | 欢迎使用WorkBuddy官方认证技能 婚纱写真照相馆。 | 2026-11-08，负责人在本聊天明确要求按现行 SOP 固定格式，WorkBuddy 审核状态按实际回执记录。 |
| 开发顺序 | 等证件照换底助手达到 submitted 或 listed，再接续 A1 | 现行 SOP 固定规则 13（c86103c） |
| 支付链接 | 只打开服务端按原安装签发的授权或结账链接 | 原设备关联，不用通用扫码裸链代替 |

**当前按串行规则排队。** 证件照换底助手达到 `submitted` 或 `listed` 后再复核本规格与 `01-dev-spec.json`，A1 通过后交 Claude。演示素材生产记录、Claude 自测、实际 WorkBuddy 行为和发布结果待后续产出。

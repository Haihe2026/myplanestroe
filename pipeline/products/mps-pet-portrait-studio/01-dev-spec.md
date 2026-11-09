# 宠物主题照相馆开发规格

版本 `1.0.0`，Skill `mps-pet-portrait-studio`，快车道 `fast`，只交 WorkBuddy 团队版。选品固定于 `66a396a6ce070a8a20443e70e5d1f212be0fba6f:pipeline/products/mps-pet-portrait-studio/00-brief.md`，调研见 `pipeline/research/2026-11-09-round4.md`。SOP、配置和下文业务源码均固定于 `3e570ea52ac3a566af2a39b4ad6aefbbcd7f4126`。上一单婚纱写真 1.0.1 的产品状态已核对为 `submitted`，由负责人手动上传。

## 1. 立项和平台约定

面向想为自家猫狗制作头像、纪念照或分享图的中文用户。一张获许可的原始猫狗照片加一个主题，默认输出一张 1K PNG。只改变风格、服装、光照和场景，尽量保留同一只宠物的物种、品种外观、毛色、花纹位置、眼鼻耳特征和自然体型。允许请求多张，每张独立确认在同一批已说明的张数内，独立提交和续接。输出用于社交分享及留念。示例图标明为 AI 效果示例，实际图片按平台规则标注 AI 生成。无试用，走通用付费页与已接入技能共享的生图次数。首次真实对话上报，关闭开关后静默。不开启同设备跨技能自动关联。

核心词为「宠物写真」「宠物主题照」，同义词为「猫咪写真」「狗狗写真」「宠物头像」「宠物纪念照」「宠物写真集」。触发要有猫狗主体和主题变换意图。对选品中的「想把猫咪做成卡通形象，当微信头像」「我家金毛太可爱了，想给它做个宇航员造型」「想把我家狗的照片做成水彩画风格」等口语优先命中相应模板。「给猫咪拍一套生日照」先推荐单一纪念方向，等选定主题和张数。与通用工具的差异是单张参考图、按毛色花纹保留身份、十种固定主题与中文工作流。选品调研记录可作背景。固定仓库树及现有队列没有同名 Skill，WorkBuddy 市场全量查重未验证。商店简介写明适用场景和触发词，可用「给猫狗做宠物写真、宠物头像或纪念主题照时调用本技能」作调用倾向句，作者沿用本仓已发布团队版的合作方名。

### 1.1 WorkBuddy 官方文档读取

| 日期 | 页面 | 读取结果 |
|---|---|---|
| 2026-11-09 | https://open.workbuddy.cn/docs/skill | 在线读到团队版技能、SKILL.md、八个必填字段、脚本和资源目录。 |
| 2026-11-09 | https://open.workbuddy.cn/docs/expert | 在线读到专家独立结构，当前只交 Skill。 |
| 2026-11-09 | https://open.workbuddy.cn/docs | 在线读到开放平台入口和产品分类。 |

已对照 2026-11-08 快照 `docs/sop/workbuddy-official-docs.md`（blob `8314aca21d2c9acf042f20f81659639965c038f3`）。SKILL.md frontmatter 提供 `name,display_name,display_name_en,description,description_zh,description_en,version,author`，再加配对的 examples。只交一个根目录，下方最多一层子目录，包内资源与清单都直接放 `assets/`，开发测试和来源审计在工作区。欢迎句逐字使用「欢迎使用WorkBuddy官方认证技能 宠物主题照相馆。」，每个对话只展示一次。平台审核按真实回执记录。

## 2. 场景路由

| 口语关键词 | 主题及键 | 档位与画幅 |
|---|---|---|
| 皇家、宫廷、油画挂墙 | 皇家油画宠物肖像 `royal-oil` | 1K，2:3，1024x1536 |
| 卡通、动漫、头像 | 卡通动漫宠物 `cartoon` | 1K，1:1，1024x1024 |
| 赛博朋克、霓虹、未来感 | 赛博朋克宠物 `cyberpunk` | 1K，2:3，1024x1536 |
| 古风、汉服、中式 | 古风宠物 `ancient-chinese` | 1K，2:3，1024x1536 |
| 宇航员、太空、星球 | 宇航员宠物 `astronaut` | 1K，2:3，1024x1536 |
| 水彩、水彩画、手绘 | 水彩画宠物 `watercolor` | 1K，2:3，1024x1536 |
| 绅士、西装、正装、礼服 | 绅士正装宠物 `formal` | 1K，2:3，1024x1536 |
| 海边、海滩、度假 | 海边度假宠物 `seaside` | 1K，3:2，1536x1024 |
| 圣诞、节日、圣诞树 | 圣诞节日宠物 `christmas` | 1K，2:3，1024x1536 |
| 探险、户外、小探险家 | 探险家宠物 `explorer` | 1K，3:2，1536x1024 |

多个主题匹配时以明确指定为准，歧义时推荐一个并询问。仅收到照片时先描述实际可见的一处宠物特征，再推荐一个方向。无图时邀请上传，不编造外观。「只看示例」「先聊方案」走离线操作，明确说不要生成时停在该步骤。画幅默认按表，仅开放适配器支持的三种比例。应用于头像或分享图，素材默认无标题文字、水印和品牌，宠物脸与耳鼻的关键区域不被裁掉。将约束写入 `references/platform-rules.md`，路由表写入 `references/scenes.md`。

## 3. 提示词与参考图约束

基础模板组合「原照可见猫狗身份 + 选定主题构图 + 画幅约束 + 负面约束」。三条基线为主体突出并保留合理安全边距、仅改变选中的风格与环境、避免额外主体和文字水印及解剖错误。宠物身份基线为同一只猫或狗，保留可见毛色和花纹位置、眼鼻耳与体态。不对照片不可见的部位作身份保证，也不根据低清照片猜品种。服饰贴合动物体型，拒绝伤害、未知授权、真人请求或无法确定的多宠物主体。若照片有多只或有人，先要求换成裁清的一只猫狗照片，由用户明确选用该文件。

| 模板 | 提示词要点 |
|---|---|
| `royal-oil` | 深色宫廷背景、深酒红丝绒披肩、传统油画笔触；保留耳形与胸口花纹 |
| `cartoon` | 清晰线条、柔色块、头像裁切留出耳尖；不要把毛斑概括到消失 |
| `cyberpunk` | 紫青霓虹轮廓光、未来街景；毛色留中性色补光，面部无遮挡 |
| `ancient-chinese` | 传统庭院与锦缎小披肩；服装顺着动物体型，眼鼻无遮挡 |
| `astronaut` | 透亮面罩、星球远景；面罩反光避开双眼，保留口鼻结构 |
| `watercolor` | 纸张纹理、淡色晕染；眼鼻和关键花纹边缘清楚 |
| `formal` | 正装配件和柔和棚灯；领结不挡胸前辨识斑纹 |
| `seaside` | 海浪与自然光、横版留景；按原图保留毛发纹理与身体比例 |
| `christmas` | 暖色灯串、松枝与小配饰；避免帽沿遮眼和高光漂白毛色 |
| `explorer` | 自然地形、轻量探险服饰，脸部及耳朵完整；不增加其他动物 |

先离线校验 PNG/JPEG，恰一张，单张 ≤5 MiB，每边 128–8000，总像素 ≤2000 万。拒绝无效 MIME、动画、损坏文件，提示具体文件和修复方式。读取照片字节并固定 SHA-256。把所选主题、比例、张数、同一张参考图和两个确认状态存入私有任务快照。若原图字节变化，作废待提交键和两项确认。主题、比例或张数变化时重走确认，已提交的任务只用原键和原图继续查询。编辑结果可能有偏差，交付时供用户对比；如需重新生成，先说明可能再计费并重新取得同意。

## 4. 首轮示例图

固定十个主题，每主题一次，以已登记资源作虚构猫狗的文字生图。画面只包含一只动物，不上传参考照片。具体提示词、预期比例见同目录 `01-demo-plan-20261109.json`，额度和用途见 `01-demo-authorization-20261109.md`。

| 主题 | 示例源文件 | 画幅与生成方式 |
|---|---|---|
| 皇家油画宠物肖像 | `demo-assets/royal-oil.png` | 2:3，1K 文生图一次，离线缩为预览 PNG |
| 卡通动漫宠物 | `demo-assets/cartoon.png` | 1:1，1K 文生图一次，离线缩为预览 PNG |
| 赛博朋克宠物 | `demo-assets/cyberpunk.png` | 2:3，1K 文生图一次，离线缩为预览 PNG |
| 古风宠物 | `demo-assets/ancient-chinese.png` | 2:3，1K 文生图一次，离线缩为预览 PNG |
| 宇航员宠物 | `demo-assets/astronaut.png` | 2:3，1K 文生图一次，离线缩为预览 PNG |
| 水彩画宠物 | `demo-assets/watercolor.png` | 2:3，1K 文生图一次，离线缩为预览 PNG |
| 绅士正装宠物 | `demo-assets/formal.png` | 2:3，1K 文生图一次，离线缩为预览 PNG |
| 海边度假宠物 | `demo-assets/seaside.png` | 3:2，1K 文生图一次，离线缩为预览 PNG |
| 圣诞节日宠物 | `demo-assets/christmas.png` | 2:3，1K 文生图一次，离线缩为预览 PNG |
| 探险家宠物 | `demo-assets/explorer.png` | 3:2，1K 文生图一次，离线缩为预览 PNG |

本批已生成并目检十张，10 次生成 POST、10 个不同远端任务、0 次重复生成，未用真实照片或客户钱包。源图哈希和派生 PNG 尺寸、哈希见 `demo-assets/provenance.json`，请求数与隔离范围见 `demo-assets/generation-audit.json`。生成原图只读校验后离线缩放，十张交付 PNG 共 2,275,416 字节。模型目录费用估算 $0.065，账单未核验。

Claude 需按 `provenance.json` 的 `key/file/status/fictional_pet/output_sha256` 验证来源，再将十个同名 PNG 同步进包的 `assets/`，有派生转换时记录来源和结果 SHA-256。每个文件名在 `assets/demos.json` 只写裸文件名。实际生成前的引导只展示离线素材，以两列 Markdown 表格呈现，并说「都是效果示例图，不是你的真实结果」「这个方向可以吗？」。仅看单项时按原键读对应示例，同对话去重。示例命令独立离线、不读凭证，缺资源退出 3。首次交互的匿名统计由入口在早退之前单独尽力处理。

## 5. 计费与支付页后端接入

通用页为 `https://aistore.zhaopintong.com/membership/gemini/`。共享 API 基址为 `https://aistore.zhaopintong.com/platform-api/gemini`。2026-11-09 匿名 GET 核对 `health` 为 ok、共享钱包与参考编辑开关为 true、新用户 0 次，`plans` 返回 ¥5/25、¥29/150、¥39/200、¥49/250。动态档位以站点为准，客户端不硬编码或向用户报价。对客在方案确认后复述主题、比例、张数、等待、参考许可，并说「按张计费，以实际账单为准」。单次成功任务 1 张额度。已交付成功图按服务端记录计费，内容拒绝和明确生成失败按实际任务记录不扣，未知费用仅转述「费用以服务记录为准」。用户对方案、示例、授权或充值的认可、沉默和无异议都不算同意执行。支付和生成各有明确同意，任何情况下先展示价值。

各请求发送 `X-Skill-Source: mps-pet-portrait-studio`、`X-Skill-Channel: workbuddy_skill` 和实际 `X-Skill-Device`。原安装 `install_secret` 只生成并持久化一次，用于恢复原身份。原账户 Bearer 与付费 Skill Bearer 分权。已关联账户有次数时跳过授权和充值。无关联时只打开服务端返回的短链，提示授权本身不扣费，浏览器确认后由原安装查回状态及余额。以实际关联状态为准。临时 URL 只信第一方签发及允许的 HTTPS host，保留路径和短票据，不把原安装凭证加在 URL，不复制跨域 Cookie 或跟随 POST 重定向。服务端微信授权沿原 host-only Cookie、一次性 state 与浏览器 verifier。见 `resources/shared-image-temporary/client.py:10–21,26–55` 和 `snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:36–65,101–138`。

| 方法 | 路径（接在共享 API 基址之后） | 权限与字段 | 固定源码 |
|---|---|---|---|
| GET | `/membership-api/plans` | 无 Bearer，读取当时可用套餐 | `resources/shared-image-temporary/client.py:64` |
| GET | `/balance` | 原账户 Bearer，remaining_uses 是总可用次数 | `resources/shared-image-temporary/client.py:65` |
| POST | `/quick-entry` | 无 Bearer，原 install_secret，沿服务器签发 URL | `resources/shared-image-temporary/client.py:66–70` |
| POST | `/quick-entry/status` | 无 Bearer，原 install_secret，registered 只说明账户注册 | `resources/shared-image-temporary/client.py:71–73` |
| POST | `/membership-link` | 原账户 Bearer，正文 {}，取得短期结账 URL | `resources/shared-image-temporary/client.py:74–76` |
| POST | `/skill-key 与 /skill-key/bound` | 原账户 Bearer，ready 才私有保存。bound 正文 {key} | `resources/shared-image-temporary/client.py:77–83` |
| POST | `/skill-jobs` | Skill Bearer，原 Idempotency-Key，确认后的参考编辑正文 | `resources/shared-image-temporary/client.py:84–86` |
| GET | `/jobs/by-key/{key}、/jobs/{id}、/jobs/{id}/image` | 优先 Skill Bearer，兼容原账户回查。保存 PNG 后交付 | `resources/shared-image-temporary/client.py:87–97` |
| GET | `/consumption-history` | 原账户 Bearer，page/page_size，仅共享 gemini 可见历史 | `pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:89–118` |
| POST | `/support-tickets` | 原账户 Bearer，Idempotency-Key，category/text/job_id? | `pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:124–162` |
| GET | `/support-tickets/{id}` | 原账户 Bearer，只查本人，跨账户 404 | `pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:164–171` |

钱包展示 `remaining_uses`，不加总重复额度。付款只走关联后的原账户结账链接。支付页已有会话 Cookie、`Origin` 和 `X-Membership-Request: 1` 检查。网页 `POST /membership-api/orders` 正文 `plan`，`POST /membership-api/report-payment` 正文 `order_id`，只登记待核款。服务端以原订单产品与实收分、交易流水核款，订单及钱包同事务。同一订单已结算且为同流水时幂等，不同订单不得复用流水。以订单已核款状态和原账户余额为证，用户自述及 reported 不视为入账。沿 `manual_qr`，无新增 webhook。固定源码 `snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:320–350`、`snapshot/opt/skill-platform/member-0.10.14/core/manual_payments.py:68–94`。已知订单 ID 时读取 `GET /membership-api/orders/{id}`，其结果仍受原站点会话约束（`shared_platform.py:351–354`）。售后沿 11-07 部署验收记录 `pipeline/products/mps-id-photo-background/01-deployment-verification-20261107.json`。消费记录只显示当前共享 gemini 数据库可见记录，不能按本技能做历史归因。工单只接收既有分类、1–2000 字文本及可选本人 job_id。工单提交前显示待提交纯文本并获同意，不附照片、凭证或客户订单详情，展示后端返回的状态，处理时限为空时如实显示未提供。

提交前生成 16–100 位 `Idempotency-Key`，用 `[A-Za-z0-9_.:-]`，把原键和正文原子保存在当前用户可读写的私有目录（POSIX 目录 0700、文件 0600，Windows 仅当前用户）。一张一键。401 清失效的缓存凭证并从原安装恢复，保留任务。402 先问是否打开充值页，同意后获取链接，页面打开不等于下单。仅在后端明确判定为未提交/未扣的可恢复状态时按同键续接，余额恢复后不重跑已交付项。403 检查权限，409 查询原任务或显示同键冲突，422 明确内容拒绝，429 保留当前任务并提示。网络异常或 5xx 先按原键和原任务 ID 查进度及图片，未知时说「当前进度未能确认」，不自动重发生成或换键。已成功但取图断开，使用原任务图片 GET 续取，重复取图不生成。已清理或仍无法取回时如实说明。当前固定契约无已核实的 `inline_delivery`、字节 Range 续传、低余额阈值字段或计费前快速重试协议。记录这些差异，低余额话术只基于明确服务端字段，不靠本地猜测。

提交 90 秒，单次查询 15 秒，轮询窗 120 秒，外层额外留 30 秒，计费前额外等待 0，外层至少 240 秒。凭证、照片 base64、原请求正文及支付会话不得进入公开日志、ZIP、遥测或 Git。仅在保存并校验 PNG 后宣布交付，输出名不覆盖，给可点击图链接和本地 `index.html` 画廊。先交图，再转述服务端账单字段；第一张附一次调整建议。实际尺寸不同则如实提示，可提议离线裁切，保留原文件。

## 6. 后端上游资产接入与成本

在固定源码提交下，以 `resources/upstreams/code-map.json`、`resources/upstreams/assets.public.json` 和 `resources/upstreams/catalog.json` 的登记和目录为入口。公开注册资产 `aisplice`，服务端实际模型 `gpt-image-2.5-ext`。从 `snapshot/opt/skill-platform/member-0.10.24/sunburst.py:142–164` 的参考分支接入 `member-0.10.59-child-photo/child_resource.py:26–84`，继承 `member-0.10.57/resource_adapter.py:94–120,133–159`，受 `member-0.10.60-new-resource-only/new-only-policy.json` 与 `new_only.py` 约束。目录登记和实际适配分别核对。后端把 1024×1024、1536×1024、1024×1536 分别映射为 1:1、3:2、2:3，设置 `resolution=1K,quality=auto,n=1`，提交一次 `POST /images/tasks`，按远端 ID 只读回查与取图。上游凭证只由服务端 `member-0.10.52/asset_registry.py` 解析。客户包只认识第一方网关和固定兼容标识，不能直接调供应商或回退旧资源。

| 客户端 POST /skill-jobs 字段 | 值与依据 |
|---|---|
| `prompt` | 主题模板和保留身份约束，来自当前批准的方案 |
| `size` | 三个允许字符串之一，如 `1024x1536`，按适配器映射 |
| `confirmed` | 必须为 true，用户明确同意这次按张计费 |
| `image_engine` | 固定兼容标识 `photo-retouch-sunburst`，仅供服务端路由 |
| `references` | `[{mime,content}]`，content 是原图字节 base64，固定一张 |
| `reference_consent` | 必须为 true，由当前参考图的明确许可产生 |

网关通过 `member-0.10.14/core/image_inputs.py:8–41` 校验尺寸、像素、MIME 和字节，适配器规范化图片、短期签名引用，过期签名不可读。参考 URL 由服务端生成，不接受客户注入上游 URL 或密钥。不发送 `model,n,quality` 或其他未登记字段。目录 ordinary 估算 $0.0065/张，按 7 折 ¥0.0455。当天 plans 最低单位收入 ¥29/150 ≈ ¥0.19333，估算模型毛利率 76.47% ≥ 60%，以两张作为测算样例，单笔模型成本 ¥0.091，未计税费等，实际以账单为准。

**已实现**是现有共享网关、钱包、结账、售后、参考输入解析与登记适配器。**待实现**是 Claude 负责的 Skill、Mock 自测、素材同步和打包。**待部署**项为无，fast 沿现有后端。**未验证**是本 Skill 的 WorkBuddy 宿主行为、客户原图身份保真、实际支付和平台审核。独立生成的虚构猫狗示例只验证本批素材生成。

## 7. 开口统计与漏斗

仅在首个真实用户回合匿名 `POST /platform-api/telemetry/v1/first-dialogue`，体积 ≤4096 字节，2 秒预算，不自动重试。白名单八字段 `event_id,installation_id,skill_id,skill_name,skill_version,channel,client_occurred_at,is_test`，随机 UUIDv4，无正文、附件、机器指纹或支付明细。以 HTTP 200 且合法匹配的 `event_id,receipt` 原子保存。服务端和本地按同一事件/安装去重。用户关闭、状态损坏、只读或超时不影响主流程，损坏/只读时不产生临时安装标识。已取得合法原账户后通过 `/first-dialogue/link` 用原账户 Bearer 和 `{event_id,receipt,product:"gemini"}`，仅 linked=true 记为关联，409 不覆盖。固定 `snapshot/opt/skill-platform/member-0.10.58/dialogue_store.py:9,30–65`、`dialogue_gateway.py:35–50`。已有的 8 字段/200 契约适用快车道，机器级 UUID、204、IP 限额、管理台聚合及数据库变更列为二期。

| 步骤 | 本技能可观察动作 | 数据口径 |
|---|---|---|
| L0 | 真实首轮的首次对话回执 | 可见安装事件，跨技能新设备口径不可得 |
| L1 | 打开原安装签发的授权页 | 依据现有授权页访问证据；新访客去重缺证标不可得 |
| L2 | 浏览器确认且原安装查得关联 | 仅按已核实的账户与绑定证据计新账户 |
| L3 | 原账户打开充值页 | 按现有页面访问证据，无法关联到新账户标不可得 |
| L4 | 首笔已核款入账 | 只在已核实的订单/账本可去重时计数，注册与待核款均不计 |

按北京时间自然日。启用、激活、充值笔数独立报告，跨日转化或缺数据标明，不通过客户端增加埋点。当前没有本产品的真实用户数据。

## 8. 相邻技能与范围

- 人像婚纱或人物写真交婚纱写真照相馆，猫狗主题照留在本品。证件照换底交证件照技能。无原宠物身份约束的通用生图可转通用技能。
- 输入限有许可的猫狗单只照片，不做普通修图美颜、真人写真、宠物购买、真实预约、打印邮寄、视频、证件用途或代运营。
- 授权步骤沿用「方案已经存好了」「没有产生任何扣费」（已发生扣费的批次只指本次授权动作），以「### 现在需要你做的」编号引导并含「打不开」兜底。拒绝开通时结束引导并保留方案。真实对话里首轮不出现付款链接和价格，账户菜单可以直接处理余额、消费与工单。

## 9. 验收用例与 Claude 交接

| 编号 | 责任方 | 通过条件 |
|---|---|---|
| T01 首轮与路由 | Claude A2 | 问候、仅图、能力询问、明确需求、照片检查、不要生成、单看示例、10 模板及相邻分流。断言首次交互遥测之外零 HTTP，推荐一个方向、没有支付抢跑、示例去重和固定话术。 |
| T02 本地输入与同意 | Claude A2 | PNG/JPEG 单张尺寸和体积边界、损坏或动画、缺图、未获许可、非猫狗、多只宠物歧义。拍照原件不动，已选原图的 SHA-256、选择的主体与主题/比例绑定，替换后旧双同意和待提交键失效。 |
| T03 示例和路径 | Claude A2 | 十图都来自固定清单，假网络与凭证探针零调用；缺文件退出 3。分别用带空格、带 # 的合成现存路径解析 Markdown，覆盖 demo、交付图与画廊。 |
| T04 授权与支付 | Claude A2 | 已有原账户跳过授权，无账户同安装授权和恢复，401 清失效凭证、退出码 4、旧任务保存；未到账、拒绝、链接失败、余额不足、分张扣量、付款后仍确认。 |
| T05 任务契约 | Claude A2 | 一次一张、三比例、六字段白名单、两项显式同意、参考图与原任务键同体同键、未登记字段在客户端和 Mock 服务端均拒绝，重复与冲突分开。 |
| T06 等待与续接 | Claude A2 | 一次完成、两轮后完成、五轮仍在处理、首次网络抖动恢复、全程未能确认、明确失败；模拟 401/402/403/409/422/429/5xx，未知查原任务；余额恢复继续未完成项、成功图片只读补取、失败与策略拒绝不扣，模糊费用照记录。 |
| T07 交付与画廊 | Claude A2 | 校验 PNG、非覆盖写入、图先于费用及余额，首张只提示一次调整，保存原图，服务端实际尺寸不符提示，可离线裁切并区分派生图；需要重生成时再确认。 |
| T08 账户与遥测 | Claude A2 | 余额、消费记录、提交及查看工单、同键重复、跨账户 404、无预计时间。真实首轮入口与早退分支均走白名单上报，关停/损坏/只读/断网不影响主流程，同安装一次，合法账户才能 link。 |
| T09 打包与文案 | Claude A2 | 八个必填字段、三组双语同场景同画幅、两级路径、版本与渠道、禁用词、脚本退出码和各处超时一致。A3-E01 故意错配可检出。 |
| T10 收藏与不可用项 | Claude A2 | 收藏卡仅在首次交付后出现，暂不/取消、两级记忆及新对话触发由 Mock 覆盖；不支持写入时如实提示。支付 API 缺失能力、机器漏斗和真机范围按规格记录。 |
| T11 固定包独立检查 | Codex A3 | Codex 从干净目录解压并核对 SHA256、目录和 YAML、双语语义、十图与来源 SHA、实际 Markdown 链接、支付及遥测字段和规格范围。按现行 A3 不跑完整测试。 |

| SKILL.md 示例场景 | examples_zh | examples_en |
|---|---|---|
| `royal-oil` | 用我家猫的这张照片做皇家油画写真，竖版 2:3。 | Use this photo of my cat to make a royal oil portrait in portrait 2:3. |
| `cartoon` | 用我家狗的这张照片做卡通头像，方形 1:1。 | Use this photo of my dog to make a square 1:1 cartoon avatar. |
| `seaside` | 用我家猫的这张照片做海边度假写真，横版 3:2。 | Use this photo of my cat to make a seaside vacation portrait in landscape 3:2. |

示例、交付图和画廊链接由命令返回真实绝对路径，状态和资源目录名不以点开头，Markdown 链接用正斜杠。一次性将原始路径的字面百分号、空格、井号等编码（空格 `%20`、井号 `%23`），底层 I/O 保持原路径。使用 `Codex Demo Assets/royal-oil.png` 和 `Codex#Demo/royal-oil.png` 创建两个现存合成文件。真正解析 Markdown 并解码到原文件，不得产生意外 URI 片段。A2 从 Mock 跑契约及端到端，真实上游、客户资料和生产财务测试均为零。Claude 写 `02-self-test.md`、固定 ZIP 与 SHA256，测试夹具随开发目录不进 ZIP。A3 由 Codex 对固定 ZIP 独立检查，长期规则跳过真机与浏览器验证；负责人自行宿主测试和手动上传。

## 10. 决策记录与 A1

| 事项 | 采用 | 依据 |
|---|---|---|
| 渠道与命名 | 仅 workbuddy-skill，版本 1.0.0，仓库 slug 无重名 | 固定 config，WorkBuddy 文档及固定树。市场全量重名未验证。 |
| 欢迎语 | 保留固定欢迎格式，正式审核状态独立据实记录 | 自动 SOP A.5 和负责人在本聊天的决定。 |
| 场景与输出 | 保留选品十个主题。卡通 1:1，海边和探险 3:2，其余 2:3，默认 1K | 固定选品与现有适配器实际画幅。比例只开放已支持值。 |
| 输入与计费 | 一张经许可的猫狗参考图，一次一张；用通用钱包与套餐，0 次试用 | 自动 SOP A.5、图片解析与公开 health/plans。 |
| 车道 | fast，使用共享图片、微信关联、钱包和售后接口 | 固定源码及既有核验；本产品不涉及后端补丁和部署。 |
| 上游 | 仅登记新资源和真实支持的路由，无旧源回退 | 固定注册表、目录、适配器与运行策略。 |
| 未开放能力 | 按原任务读图；无经核实的 inline_delivery、分段下载、低余额阈值或免费重做契约，不写进首版 API | 固定 shared 客户端、网关和六字段白名单。 |
| 示例资源 | 十张从固定主题用虚构猫狗生成，来源与审计入仓 | 负责人长期示例授权、固定选品和执行计划；独立于真实参考编辑验证。 |
| 首次对话遥测 | 首版兼容 8 字段和 HTTP 200；L0 机器级及无可靠现有数据的步骤记不可得 | 自动 SOP A.5 和现有网关。 |
| 设备 | 同设备跨技能自动复用关闭；沿当前原安装恢复 | 固定 config 的 sibling_reuse=false。 |
| 时限 | 90 秒提交，15 秒单次查询，120 秒查询窗，30 秒余量，外层至少 240 秒；计费前额外等待 0 | 固定客户端及自动 SOP；无已核实的收费前快速重试协议。 |
| 上传 | A3 独立检查后交付 ZIP，由负责人手动测试和上传 | 现行自动 SOP A.3 与负责人在本聊天的确认。 |

**A1 通过。** 逐项核对了 15 项清单和 Markdown/JSON 一致性，检查了十张 PNG、主题与来源哈希。进入 `spec_ready`，Claude Code 以本次固定提交开发、同步素材、A2 自测及打包。

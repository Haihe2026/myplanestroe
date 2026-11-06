# 开发规格草案：证件照换底助手 1.0.0

> 状态：blocked_draft；A1 未通过。本文是可审核的规格与拦停证据，不是 Claude 可开工或已上架的交付。

已读 WorkBuddy 官方文档：2026-11-06，https://open.workbuddy.cn/docs/expert 、https://open.workbuddy.cn/docs/skill 。
本地指定 SOP：`C:\Users\Administrator\Desktop\Skill项目\Claude-Code\SOP\sop-image-gen-skill.md`；已完整读取。用户随后直接确认本单按自动化 SOP 执行；适用仓库 `docs/sop/sop-image-gen-skill-auto.md`。
业务源码和资源快照：`44a6ed60ea015f260a89b75975f9b21fe39e9e3e`。本聊天处理事件 evt-903b3c4bee53ba19ee4d5773a8dac53a1fec43a0e97f3e5df24775801d82ae2b，沿原 relay claim，不重复认领。

## 1. 立项与复盘

目标用户为有普通正面照片、需要干净底色人像的求职者或登记照使用者。输入：一张本人或经授权的PNG/JPEG照片、希望的底色、实际用途和机构要求。输出：一张另存的新结果；是否可用于正式提交须核对机构规则，不承诺自动合格。
仅WorkBuddy团队技能版；首版单张。稳定标识mps-id-photo-background，当前产品目录只有本单，未发现已开发包；没有已上线转化数据，不编造漏斗或竞品用户量。Muse选品单中的营销数据未独立核实，不作为本品实测证据。
核心词：证件照换底、证件照背景；同义/触发词：白底证件照、蓝底证件照、红底证件照、简历照换底、一寸照片、二寸照片、底色换白、头发边缘、照片底色、证件照像素、报名照、入学登记照、登记照片、295×413、白底一寸、蓝底二寸；英文ID photo background / portrait background / photo dimensions。具体机构要求不是关键词的自然推论。

## 2. 官方格式与读取记录

按官网技能结构：SKILL.md为必需，references/scripts/templates可选；frontmatter使用name、display_name、display_name_en、description、description_zh、description_en、version、author。不要把专家plugin.json或专家分类填入技能包。作者沿现有已核实合作方身份，未知不得编造。
原文件与自动版内容比较已核对；人工关口改自动关口的冲突已由本聊天用户直接确认解决。三渠道历史要求按本次仅WorkBuddy技能的明确范围执行。下述认证、遥测强制要求与现有能力的冲突仍未解决，不静默修改共享SOP。

## 3. 场景路由表

| key | 用户口语 | 场景 | 推荐参数与条件 |
|---|---|---|---|
| white-one | 白底一寸、明天报名 | 白底一寸需求 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| blue-one | 蓝底一寸、底色换蓝 | 蓝底一寸需求 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| red-one | 红底一寸、毕业登记 | 红底登记照需求 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| white-two | 白底二寸、报名表 | 白底二寸需求 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| blue-two | 蓝底二寸、考试报名 | 蓝底二寸需求 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| resume-white | 简历照、底色太花 | 简历白底人像 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| custom-pixels | 295×413、像素卡住 | 用户指定295×413 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| edge-clean | 别留蓝边、头发边缘 | 换底边缘检查 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| school | 入学登记照、学校照片 | 入学登记需求 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |
| custom-size | 单位要求、指定尺寸 | 机构提供规格的照片 | 现有1K参考图编辑，1024x1536；目标像素由实际机构规格确认，不承诺打印级 |

## 4. 提示词与基线

每条模板先写真实性/人物身份锁定，再写底图无文字，最后写授权和不冒用身份的安全边界。画面含人物不承诺身份特征像素级一致；不对客复述模板或模型名。具体模板要点：

- `white-one`：仅将已授权参考照片的背景改为white指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `blue-one`：仅将已授权参考照片的背景改为blue指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `red-one`：仅将已授权参考照片的背景改为red指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `white-two`：仅将已授权参考照片的背景改为white指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `blue-two`：仅将已授权参考照片的背景改为blue指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `resume-white`：仅将已授权参考照片的背景改为white指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `custom-pixels`：仅将已授权参考照片的背景改为user_selected指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `edge-clean`：仅将已授权参考照片的背景改为user_selected指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `school`：仅将已授权参考照片的背景改为user_selected指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。
- `custom-size`：仅将已授权参考照片的背景改为user_selected指定纯色，尽量清理发丝周围原底色；锁定原人物脸部身份、五官比例、表情、发型、衣着、肤色与姿态；不重画面部、不美颜、不换装。

## 5. 首轮示例

10项与上述key逐一对应，待Claude用独立合成/Mock材料制作；不是已有真图，不为示例调用真实上游。必须标记‘合成流程示意，不是真实上游效果，也不是用户结果’。包内资源完整且路径实存后才能展示；仅文字意图不运行示例，授权/充值续接不插图库。不能拿Mock图片冒充真实模型样张或保真证据。

## 6. 计费、账户与通用付费入口

后端product=gemini，X-Skill-Source=mps-id-photo-background，X-Skill-Channel=workbuddy_skill；运行环境填写实际desktop/mobile/cloud。现有通用付费页为 `https://aistore.zhaopintong.com/membership/gemini/`，公开套餐及页面本次均200。实际付款须取得原账户的服务端短期链接；裸页面只看套餐，不能替代账户关联。
复用既有账户install_secret与Skill凭证，不跨产品借凭证，不在新对话重建身份，不把微信恢复口径写成WorkBuddy官方OAuth。供应商Key永远留服务器。无免费试用，每个成功图任务沿原共享次数计费，不改变账本、套餐或核款。用户确认范围、照片外发与费用后才提交；用户自述已付款不等于到账。
当前在线套餐为29/150、39/200、49/250、999/5000，以上仅内部核对；对客不写金额和固定消耗数，客户端下单前重新读取服务端，保留旧专用权益边界。

## 7. 有效上游与成本

当前资产aisplice，经新资源适配器使用gpt-image-2.5-ext；1K、每任务n=1、legacy_fallback=false。photo-retouch-sunburst是兼容编辑入口，不是另一个新增供应商。aisplice-universal的36模型登记不表示都能调用。
目录2026-11-05公开价0.0065美元/请求，假设汇率7，估算单图成本0.0455元；最低套餐折合0.19333333元/图，估算毛利率76.4655%，超过60%筛选阈值。该估算不含汇率波动、税费等，不是真实账单或净利润；未调用付费模型探针。客户端不得展示供应商或成本。

## 8. 车道与A1结论

现有图像与支付可复用；完整机器漏斗需要后端变更。尚未编写/测试后端补丁，故不使用DEPLOY_REQUIRED冒充补丁已就绪。
当前仅画像/支付核心链可复用；完整机器漏斗与欢迎句认证冲突使A1不能全通过。HARD_STOP先于DEPLOY_REQUIRED：后者只用于后端补丁已经通过测试、仅等部署的情况，本单不冒称已完成补丁。

### B1 首次对话与设备漏斗的强制规范不等于现有接口

现有白名单8字段、200含receipt并按安装去重；自动SOP第六章要求machine_id、新设备L0、204、IP按日限额及新表/明细。本地合成验证额外machine_id会被拒绝；不能仅换客户端字段宣称已接完整漏斗。改变现有审计/限流触及A.5第150-156行硬边界。
证据：`snapshot/opt/skill-platform/member-0.10.58/dialogue_store.py:9`；`snapshot/opt/skill-platform/member-0.10.58/dialogue_store.py:30`；`snapshot/opt/skill-platform/member-0.10.58/dialogue_store.py:33`；`snapshot/opt/skill-platform/member-0.10.58/dialogue_gateway.py:34`；`snapshot/opt/skill-platform/member-0.10.58/dialogue_gateway.py:50`
可审核处理方案：首版兼容实际8字段200回执，仅统计已支持的首次对话/安装与关联，跨技能新设备漏斗标不可得；取得明确规则例外后走快车道。若必须完整机器漏斗，另行批准后端统计设计与部署，不更改既有客户/限流/审计。

### B2 欢迎句认证声明冲突

自动SOP固定欢迎句要求写官方认证，同时A.5和固定规则禁止冒用认证；当前没有本新品认证证据。规格不得给Claude一条必然不实的已认证声明。
证据：`docs/sop/sop-image-gen-skill-auto.md:142`；`docs/sop/sop-image-gen-skill-auto.md:156`
可审核处理方案：未取得真实认证前使用普通欢迎语：欢迎使用证件照换底助手。取得明确规则例外后再放行；不自行修改共享SOP或伪造资质。

## 9. 实际接口与字段

统一前缀/platform-api/gemini；表内遥测使用独立/platform-api/telemetry/v1。不虚构/auth/start、/pricing、/images/generate等旧SOP示例为现有接口。

| 方法 | 路径 | 已确认源码 | 要点 |
|---|---|---|---|
| GET | `/platform-api/gemini/health` | `resources/shared-image-temporary/client.py:63` | 只读配置能力，不证明本单真实生成或肖像保真 |
| GET | `/platform-api/gemini/membership-api/plans` | `resources/shared-image-temporary/client.py:64` | 下单前读取，不硬编码套餐或收益 |
| POST | `/platform-api/gemini/quick-entry` | `resources/shared-image-temporary/client.py:66` | 原install_secret；仅打开服务端签发的url |
| POST | `/platform-api/gemini/quick-entry/status` | `resources/shared-image-temporary/client.py:71` | 原安装身份续接；registered不等于付费到账 |
| POST | `/platform-api/gemini/membership-link` | `resources/shared-image-temporary/client.py:74` | 正文{}；短期服务端付款链接 |
| GET | `/platform-api/gemini/balance` | `resources/shared-image-temporary/client.py:65` | remaining_uses为总可用次数，不再相加共享/旧余额 |
| POST | `/platform-api/gemini/skill-key` | `resources/shared-image-temporary/client.py:80` | state=ready才保存；不是供应商Key |
| POST | `/platform-api/gemini/skill-key/bound` | `resources/shared-image-temporary/client.py:83` | 先安全保存，再以key字段确认 |
| POST | `/platform-api/gemini/skill-jobs` | `resources/shared-image-temporary/client.py:84` | 原Idempotency-Key与已确认正文，不换键重发 |
| GET | `/platform-api/gemini/jobs/by-key/{original_key}` | `resources/shared-image-temporary/client.py:87` | 使用原任务键，不自行哈希 |
| GET | `/platform-api/gemini/jobs/{id}` | `resources/shared-image-temporary/client.py:96` | 原UUID；pending/needs_review不重建 |
| GET | `/platform-api/gemini/jobs/{id}/image` | `resources/shared-image-temporary/client.py:97` | 成功任务PNG二进制，保存后再交付 |
| POST | `/platform-api/telemetry/v1/first-dialogue` | `snapshot/opt/skill-platform/member-0.10.58/dialogue_gateway.py:50` | 现有8字段/200回执契约 |
| POST | `/platform-api/telemetry/v1/first-dialogue/link` | `snapshot/opt/skill-platform/member-0.10.58/dialogue_gateway.py:48` | 现有8字段/200回执契约 |

参考图仅使用`references=[{mime,content}]`，PNG/JPEG，单张≤5MB、单图最小128像素、最大边8000、总像素≤2000万；本品只接一张。`reference_consent`必须来自真实授权，`confirmed`来自同任务费用确认，`image_engine=photo-retouch-sunburst`。源代码见`snapshot/opt/skill-platform/member-0.10.14/core/image_inputs.py:12`、`snapshot/opt/skill-platform/member-0.10.24/sunburst.py:148`。其他基础正文参数以实际PRESETS及参考客户端为准，不引入target_pixels/dpi等后端未登记字段。
1024x1536只是网关画幅，不是最终证件像素承诺；本地裁切/重采样由Claude实现并独立验证，不能以提示词保证295x413。首版禁止承诺2K/4K。参考客户端text_job()仅文生图示例，不能拿它忽略参考图直接画一个新人。
任务未知状态按原幂等键查询；不编造inline_delivery补取能力，不将通用5xx当作明确未扣费。图片实际收到并另存后才完成；原图不改动。费用缺字段就如实不可得，不用余额差自行推算。
设计预算：提交90秒，查询每次15秒、间隔5秒、最多6轮，轮询窗口120秒，进程余量30秒，外层240秒。该预算未代表实测出图耗时；Claude改常量后全包重新计算，不因超时新建任务。

## 10. 首次对话与漏斗

用户第一次真实开口立即执行元数据上报，包括问候、仅图与缺资料，不等授权、充值或生成；自检和定时任务不是人工消息。实际白名单：`channel`、`client_occurred_at`、`event_id`、`installation_id`、`is_test`、`skill_id`、`skill_name`、`skill_version`。当前成功为200，采用服务端回执，不按204丢弃。拒绝联网/统计、关闭开关或标识无法持久化时跳过；不上传照片、原话、路径或凭证。开发/测试is_test=true。兼容方案未经明确确认不拿它宣称完整六章已满足。

- L0：现有8字段只支持安装×技能×渠道首次互动；跨技能新设备不可得
- L1：既有journey页面/邀请事件；没有新设备IP日哈希口径，不伪造
- L2：已鉴权账户关联及first-dialogue/link，匿名事件之后续接
- L3：既有付款页旅程事件；当前聊天无管理员数据，不读取生产客户
- L4：既有入账/订单账本，只接受服务端已入账；未做真实支付

现有路径按匿名/安装去重，不能将它换算为跨技能新设备或唯一人数。机器维度、IP日盐哈希及离线同口径报表未确认存在；管理台生产数据不读取，不补造转化率。

## 11. 相邻产品与不承接

老照片修复、风格化头像与本技能分界写清；未核实真实上架ID之前不生成跳转链接或声称已上架。只做授权单人人像换底，不做换装、美颜、伪造证件、批量多人。正式用途先核实际机构要求，不承诺‘标准证件照必过’。
美国签证官方FAQ不允许通过数字编辑改变外貌；生成式人像可能重画面部，因此本版不把签证照列为保证可用的默认路线。其他机构是否允许编辑须单独核实，不外推美国规则到所有场景。来源：[美国国务院签证照片FAQ](https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/photos/frequently-asked-questions.html)，2026-11-06读取。

## 12. 验收用例与分工

下表均为待实施后的验收计划，不冒充产品已通过。Claude自测后，Codex从相同哈希ZIP干净解压独立复测；宿主验收由Codex负责。

| 编号 | 分组 | 负责 | 验收项 |
|---|---|---|---|
| T01 | first_turn | claude+codex | 问候、仅图、问能力、带图明确需求均先价值展示，不取账户或付费链接 |
| T02 | first_turn | claude+codex | 首轮仅允许受控首次对话元数据请求，业务请求函数设为抛错仍能完成 |
| T03 | first_turn | claude+codex | 离线示例10项，只展示本次脚本返回的绝对路径，两列链接表且同对话去重 |
| T04 | first_turn | claude+codex | 不要生成新图/只要文字/只看某示例正确分流 |
| T05 | first_turn | claude+codex | 首轮不查凭证、不调用help/account/health/catalog，不读取照片发送至后端 |
| T06 | confirmation_account | claude+codex | 认可方向、沉默、授权成功、已充值均不能替代同任务付费同意 |
| T07 | confirmation_account | claude+codex | 参考照片对外处理同意与付费同意独立；取消时零任务 |
| T08 | confirmation_account | claude+codex | 原安装身份及微信短链恢复，过期才重取，不新建原账户 |
| T09 | confirmation_account | claude+codex | 服务端签发链接保留ticket/entry，不在日志或回复暴露凭证 |
| T10 | confirmation_account | claude+codex | 有可用次数跳过开通充值；无余额先询问是否打开充值页 |
| T11 | confirmation_account | claude+codex | 凭证401自动清除失效凭证，输出credentialsReset与退出码4 |
| T12 | confirmation_account | claude+codex | 未获用户明确同意不读取其他技能凭证，sibling_reuse=false |
| T13 | billing_jobs | claude+codex | 同键同体恢复、已成功任务重放只结算一次 |
| T14 | billing_jobs | claude+codex | 402、401、429、5xx后不换键、不缓存错误作成功、不自动新建任务 |
| T15 | billing_jobs | claude+codex | 未知状态只查原任务，不猜测已扣/未扣或承诺自动退款 |
| T16 | billing_jobs | claude+codex | 账户到账以实际remaining_uses为准，不将注册或用户自述当到账 |
| T17 | billing_jobs | claude+codex | 成功先交真实图片，再转述服务端实际费用记录；缺字段不自行计算 |
| T18 | billing_jobs | claude+codex | 图片下载失败保留原任务查询，不杜撰inline_delivery补取接口 |
| T19 | billing_jobs | claude+codex | 同设备退出恢复后仍查原任务UUID，任务数据仅本地私有存储 |
| T20 | wait | claude+codex | 一次返回成功 |
| T21 | wait | claude+codex | 两轮后成功 |
| T22 | wait | claude+codex | 窗口结束仍pending保存原任务 |
| T23 | wait | claude+codex | 首轮网络错误后用原任务查询恢复 |
| T24 | wait | claude+codex | 全程无应答显示进度无法确认 |
| T25 | wait | claude+codex | 明确失败仅引用服务端能确认的费用结果 |
| T26 | input_output | claude+codex | 单张PNG/JPEG且真实内容匹配，损坏/超限/无授权在本地拒绝 |
| T27 | input_output | claude+codex | 上游请求只使用1K现有3种画幅，本品默认1024x1536，不宣称2K/4K可用 |
| T28 | input_output | claude+codex | 不改变五官、发型、服装的提示约束与可见结果检查，生成差异不能声明身份完全一致 |
| T29 | input_output | claude+codex | 用户指定目标像素时独立本地裁切另存，重新解码核对实际尺寸；无法保证时受控停止 |
| T30 | input_output | claude+codex | 无机构规格不将一寸/二寸自动等同某个像素或文件大小 |
| T31 | input_output | claude+codex | 原图不修改不移动，输出不覆盖，支持真实本地画廊 |
| T32 | input_output | claude+codex | 图片错误及含敏感凭证错误体不直接对客输出 |
| T33 | input_output | claude+codex | 未成年人需监护授权；冒用肖像、证件伪造与明确禁止编辑用途拒绝 |
| T34 | telemetry | claude+codex | 真实首轮含问候/缺图即上报；安装、读取、自检、定时任务不上报 |
| T35 | telemetry | claude+codex | 严格8字段、200回执、采用服务端返回ID及receipt，不提交machine_id或正文 |
| T36 | telemetry | claude+codex | 标识持久化失败跳过，不临时造身份；去重和开关生效 |
| T37 | telemetry | claude+codex | 2秒预算，不阻塞业务；当前实际协议与自动SOP重试差异记录后才实现 |
| T38 | telemetry | claude+codex | 账户后续link幂等，409不覆盖其他账户；凭证只在头部 |
| T39 | telemetry | claude+codex | 跨技能新设备L0不可得时明确不可得，不把installation当machine或下载当人数 |
| T40 | contract_copy | claude+codex | 欢迎句无虚构认证；未解决硬冲突时禁止交付可发布包 |
| T41 | contract_copy | claude+codex | 对客文案不含开发流程、供应商、接口、base64等术语 |
| T42 | contract_copy | claude+codex | 超时由脚本常量实算，各文档一致，不把设计值冒充实测耗时 |
| T43 | contract_copy | claude+codex | 退出码0/2/3/4与JSON信号、欢迎话术、示例集合一致 |
| T44 | contract_copy | claude+codex | 最终ZIP干净解压独立重跑，头像512×512与ZIP同目录，不覆盖旧包 |
| T45 | host | codex | 真实WorkBuddy开新对话逐项验首轮可见行为与链接展示 |
| T46 | host | codex | 收藏仅交付成功后用户同意才写宿主记忆，缺工具如实说明 |
| T47 | host | codex | 宿主无解释器、禁网、无记忆工具分别降级，不宣称已通过 |
| T48 | host | codex | 未验证真实扫码、核款、模型质量与审核，不把Mock当生产效果 |

### 本次实际已做的验证

- 既有参考客户端12项Mock测试通过，未改客户端源码。
- 现有dialogue_store的4项合成检查通过：8字段受理、安装去重、machine_id拒绝、数据库无machine_id列。使用一次性本地合成数据库和合成密钥，网络0。
- GET公开health、plans和付费页均200；这些检查不证明真人微信扫码、真实核款、生图质量、真机宿主或审核通过。
- 真实上游调用0，生产数据库/客户凭证0，生产修改0，未上架、未运行其他AI。

## 13. 决策记录

| 事项 | 采用 | 依据 |
|---|---|---|
| 关口 | 本单采用自动SOP | 当前聊天人工直接确认；不是Muse转述授权 |
| 当前有效支付 | 临时域名/membership/gemini/及服务器签发链接 | 11月6日资源入口、参考客户端、在线200；不使用旧/pay示例 |
| 当前有效上游 | aisplice新适配器1K单图，不直接调用通用目录其余模型 | resources/upstreams/README.md、新资源策略、公开健康 |
| 真实探针 | 仅GET公开健康与套餐；真实上游0 | 自动SOP A.5硬边界及CLAUDE.md |
| 标准尺寸 | 机构规格由用户提供，生成尺寸与最终裁切尺寸分别验证 | 当前网关仅3种画幅；不把一寸推定唯一像素 |
| 示例 | 10个待制作Mock合成示意，明确非真实模型效果 | 自动SOP A1禁止为示例调用真实上游 |
| 正式证件用途 | 对明确禁止编辑的用途不承接；其余须按机构规则核验 | 未核实的机构要求不能默认通用；美国签证FAQ禁止改变外貌的数字修改 |
| 认证及新机器漏斗 | 阻塞，提出兼容现有契约的具体方案，不自行降低A1 | 自动SOP A.5/A.7，当前源代码与合成验证 |

## 14. MD/JSON一致性与恢复条件

本MD与01-dev-spec.json从同一结构生成：10场景、10个待制作Mock示例、现有模型/支付/接口、测试清单和两项阻塞一致。
恢复条件：负责人确认上述兼容基线（8字段200、未认证时普通欢迎语），或完成所需服务端规范升级并提供认证依据；Codex据真实决策修订本规格、重跑A1后才置spec_ready交Claude。任何放行都不包含真实上游调用、客户数据/余额修改、生产部署或发布权限。

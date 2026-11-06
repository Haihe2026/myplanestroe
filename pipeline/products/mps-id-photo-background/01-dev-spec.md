# 开发规格：证件照换底助手 1.0.0

> 文档状态：spec_ready。本轮交付开发规格；后续实施、测试和部署状态按实际证据记录。

## 1. 范围和读取记录

稳定标识：`mps-id-photo-background`；渠道仅WorkBuddy团队技能版；英文名：ID Photo Background Assistant。
用户直接指定：Codex只完成开发文档；认证相关工作由后续Claude Code处理，本文不作状态核验或标注。后端依赖写成实施任务，不再作为Codex文档阶段必须先完成的代码工作。
已读指定本地SOP：`C:\Users\Administrator\Desktop\Skill项目\Claude-Code\SOP\sop-image-gen-skill.md`；2026-11-06重新读取官方 https://open.workbuddy.cn/docs/expert 和 https://open.workbuddy.cn/docs/skill 。本单按用户直接确认的自动化SOP执行，业务源码/资源依据提交 `44a6ed60ea015f260a89b75975f9b21fe39e9e3e`。
当前人工指示限定本轮A1为文档完备性检查；后端目标契约、迁移和部署验收仍由后续阶段完成，不把未实施的能力写成既有接口。

## 2. 立项、输入输出和边界

目标用户：需要干净背景单人人像的求职或登记照使用者。输入：一张本人/经授权PNG或JPEG、目标底色、用途和必要的机构规格。输出：一张另存的新结果；原图不修改。首版单张，不做换装、换发型、磨皮、五官美化、风格化或批量多人；不保证正式审核通过。
核心词：证件照换底、证件照背景；触发词：白底证件照、蓝底证件照、红底证件照、一寸照片、二寸照片、简历照、报名照、入学登记、照片底色、底换白、发丝边缘、别留蓝边、295×413、标准像素、登记照片、ID photo background。选品单的竞品数据不冒充本品实测数据。
目标像素、DPI和文件大小以用户给定机构要求为准，不将“一寸/二寸”推定为统一像素。明显不允许编辑的正式用途不承接，不用泛称“标准”代替机构要求。

## 3. 场景路由与提示词

| key | 用户口语 | 场景 | 推荐参数 |
|---|---|---|---|
| white-one | 白底一寸、明天报名 | 白底一寸需求 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| blue-one | 蓝底一寸、底色换蓝 | 蓝底一寸需求 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| red-one | 红底一寸、毕业登记 | 红底登记照需求 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| white-two | 白底二寸、报名表 | 白底二寸需求 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| blue-two | 蓝底二寸、考试报名 | 蓝底二寸需求 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| resume-white | 简历照、底色太花 | 简历白底人像 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| custom-pixels | 295×413、像素卡住 | 用户指定295×413 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| edge-clean | 别留蓝边、头发边缘 | 换底边缘检查 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| school | 入学登记照、学校照片 | 入学登记需求 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |
| custom-size | 单位要求、指定尺寸 | 机构提供规格的照片 | 现有1K参考图编辑，1024×1536，2:3；目标裁切规格另确认 |

每个场景按“动作动词＋具体视觉参照＋锁定句”组织；真实性/人物身份基线在前：尽力保持五官比例、表情、肤色、发型、衣着、姿态，不承诺像素级一致。其后加底图无文字与不冒用肖像/品牌的安全基线。具体模板要点：

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

## 4. 首轮示例与付费后置

10个示例key与场景逐一对应；由Claude制作离线Mock/合成素材，不为示例调用真实上游，不冒充真实用户结果或真实模型效果。首次真实对话先本地保存需求、真实可见反馈、一个主推方向和两列示例链接，轻确认收尾；问候、仅图、问能力均适用。仅文字不运行示例；授权、充值和任务续接不插新一轮示例。
首轮不取账户/付款链接、不查凭证、不调用业务健康/目录接口、不发起生成；首次互动元数据是唯一例外。用户认可方向不等于同意付费；同任务的范围、照片处理授权、付费执行分别确认后再提交。
固定欢迎句由Claude在welcome_copy.py实现并逐字测试：`欢迎使用WorkBuddy官方认证技能 证件照换底助手。`。
授权及充值话术按SOP责任交接闭环；已有可用次数跳过开户充值；用户拒绝不催促；只有服务端真实余额与账单可作为费用依据。

## 5. 当前有效上游、支付与成本

当前通用生图前缀：`https://aistore.zhaopintong.com/platform-api/gemini`；通用付费页面：`https://aistore.zhaopintong.com/membership/gemini/`。X-Skill-Source必须是本品mps-id-photo-background，渠道workbuddy_skill，环境按实际填写。实际付款和微信恢复沿服务器签发的原账户短期链接；裸页只能查看套餐。
当前资产aisplice，新资源gpt-image-2.5-ext、1K、n=1、禁止旧源回退；photo-retouch-sunburst为兼容编辑入口。不得把aisplice-universal目录所有模型当成已适配，也不向客户端发供应商Key。
沿通用共享次数，默认无试用；同一任务原幂等键去重，未知状态查原任务，不换键自动重发。保留旧专用权益和原账户身份；不改客户余额、订单、套餐或核款。
在线套餐核对29/150、39/200、49/250、999/5000，仅作内部校核，不写死进对客话术。估算成本0.0065美元/张×假设汇率7=0.0455元；最低套餐折合约0.19333元/图，估算毛利约76.47%≥60%。未含税费/汇率波动等，不是真实账单或净利润。

## 6. 已存在接口及字段

以下为现有源码确认的接口；目标新增行为在下一节单列，不混称已支持。

| 方法 | 路径 | 源码 | 要点 |
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
| POST | `/platform-api/telemetry/v1/first-dialogue` | `snapshot/opt/skill-platform/member-0.10.58/dialogue_gateway.py:50` | 现有8字段200回执协议 |
| POST | `/platform-api/telemetry/v1/first-dialogue/link` | `snapshot/opt/skill-platform/member-0.10.58/dialogue_gateway.py:48` | 现有8字段200回执协议 |

人像请求使用references=[{mime,content}]、真实reference_consent、同任务confirmed和photo-retouch-sunburst；本品仅一张授权PNG/JPEG，单张≤5MB，最小边128、最大边8000、总像素≤2000万。实际字段证据见JSON的reference_payload.sources。text_job()仅文生图示例，不可拿来忽略参考图。
网关画幅与最终证件像素分别验证。目标295×413等由本地裁切/重采样另存并重新解码核对；不向后端添加未经登记的dpi/target_pixels/model/n/quality，也不凭提示词保证实际输出尺寸。下载失败保留原任务，不杜撰inline_delivery接口。

## 7. 目标机器漏斗：后续实施任务

当前服务端8字段/200回执协议继续保留兼容。新技能目标为自动SOP原要求的9字段、规范小写UUIDv4机器标识和204确认；这属于待实施的后端目标，不是已经部署的事实。完整目标如下：
- installation_id按技能/安装独立随机；machine_id由自家技能共享的随机UUIDv4，不读取硬件、MAC、序列号。写不进标识则跳过，不临时造ID。
- 首条真实人工消息即上报，包括问候/仅图/缺资料；安装、自检、读取、定时任务不冒充人工消息。只传9项白名单元数据，不含正文、照片、路径或凭证。
- 成功HTTP204后记本地一次性标记，2秒预算、不自动重试、不阻塞主流程；关闭/拒绝统计或联网时跳过。开发测试is_test=true。
- 合法原账户以后关联安装和机器标识，不为统计创建账户或改变付款。服务端按日加盐IP摘要、每日50次默认限额、180天明细策略；不落明文IP。
- 兼容旧客户端；目标契约与迁移未就绪时明确报告依赖，不静默用8字段宣称完整机器漏斗已完成。

| 任务 | 后续实施内容 | 验收标准 |
|---|---|---|
| BE01 | 扩展首次互动目标白名单及204应答，同时保留旧8字段200客户端兼容 | 未知字段拒绝；UUIDv4严格校验；开发用is_test=true；同安装去重；失败不影响主业务 |
| BE02 | 新增机器/安装首见、事件及合法账户关联数据结构 | 随机标识，不读硬件；安装×技能×渠道去重；跨技能机器只算一次新设备；历史数据不补造 |
| BE03 | 按自动SOP第六章实现IP按日加盐摘要、每日上限及180天明细策略 | 不存明文IP；限额与幂等并发一致；明细不返回ip_day_hash；独立迁移、回滚与权限评审，不直接改生产 |
| BE04 | 实现L0-L4及三项独立指标的同口径只读报表与管理台明细 | 管理台沿原管理员鉴权；离线脚本与在线数字一致；新设备/新账户/老账户区分；订单与未挂订单入账去重；不混用预充值、扣量和利润 |
| BE05 | 保持现有通用生图、共享钱包、微信恢复及新资源适配器 | 不改客户余额/订单/套餐；无旧上游回退；真实上游0；未部署不得宣称线上已支持目标契约 |

服务端应先在隔离测试环境完成迁移、合成测试和契约验收，再经原部署流程启用；本轮没有完成实施或部署，也没有增加生产权限。Claude可先针对目标契约做Mock开发；上线前须用实际服务端能力与行为验收。

## 8. 漏斗、相邻技能与非目标

- L0：窗口内machine_id历史首现的新设备；来源：目标首次互动事件和机器首见索引。
- L1：授权页匿名PV与按ip_day_hash去重的访客；来源：目标页面到达事件；按日哈希不能被解释成永久唯一人数。
- L2：窗口内新建并首次完成关联的账户；来源：既有账户创建记录与目标关联表。
- L3：窗口内新账户到达充值页，按账户去重；来源：现有合法账户/页面事件。
- L4：新账户首次实际入账，订单与未挂订单充值逐条去重；来源：原订单/账本只读投影，不以自述付款认定到账。
- 北京时间自然日；跨日充值会低估单日报表，经营判断至少看7天窗口。
- 三项独立指标：按安装首见的技能启用数（新/老设备）、技能账户新绑定的激活数（新/老账户）、实际入账去重后的充值笔数。不能把安装数当人数或充值减扣量当利润。
- 相邻老照片修复、风格化头像各保留分界；未确认真实上架ID前不编造跳转链接。

## 9. 验收清单与责任

以下48项为待实施验收计划，不冒充已通过。Claude自测后由Codex从相同哈希ZIP干净解压独立重测；宿主行为测试由Codex执行。

| 编号 | 分组 | 负责 | 验收项 |
|---|---|---|---|
| T01 | first_turn | claude；codex独立复测 | 问候、仅图、问能力、带图明确需求均先价值展示，不取账户或付费链接 |
| T02 | first_turn | claude；codex独立复测 | 首轮仅允许受控首次对话元数据请求，业务请求函数设为抛错仍能完成 |
| T03 | first_turn | claude；codex独立复测 | 离线示例10项，只展示本次脚本返回的绝对路径，两列链接表且同对话去重 |
| T04 | first_turn | claude；codex独立复测 | 不要生成新图/只要文字/只看某示例正确分流 |
| T05 | first_turn | claude；codex独立复测 | 首轮不查凭证、不调用help/account/health/catalog，不读取照片发送至后端 |
| T06 | confirmation_account | claude；codex独立复测 | 认可方向、沉默、授权成功、已充值均不能替代同任务付费同意 |
| T07 | confirmation_account | claude；codex独立复测 | 参考照片对外处理同意与付费同意独立；取消时零任务 |
| T08 | confirmation_account | claude；codex独立复测 | 原安装身份及微信短链恢复，过期才重取，不新建原账户 |
| T09 | confirmation_account | claude；codex独立复测 | 服务端签发链接保留ticket/entry，不在日志或回复暴露凭证 |
| T10 | confirmation_account | claude；codex独立复测 | 有可用次数跳过开通充值；无余额先询问是否打开充值页 |
| T11 | confirmation_account | claude；codex独立复测 | 凭证401自动清除失效凭证，输出credentialsReset与退出码4 |
| T12 | confirmation_account | claude；codex独立复测 | 未获用户明确同意不读取其他技能凭证，sibling_reuse=false |
| T13 | billing_jobs | claude；codex独立复测 | 同键同体恢复、已成功任务重放只结算一次 |
| T14 | billing_jobs | claude；codex独立复测 | 402、401、429、5xx后不换键、不缓存错误作成功、不自动新建任务 |
| T15 | billing_jobs | claude；codex独立复测 | 未知状态只查原任务，不猜测已扣/未扣或承诺自动退款 |
| T16 | billing_jobs | claude；codex独立复测 | 账户到账以实际remaining_uses为准，不将注册或用户自述当到账 |
| T17 | billing_jobs | claude；codex独立复测 | 成功先交真实图片，再转述服务端实际费用记录；缺字段不自行计算 |
| T18 | billing_jobs | claude；codex独立复测 | 图片下载失败保留原任务查询，不杜撰inline_delivery补取接口 |
| T19 | billing_jobs | claude；codex独立复测 | 同设备退出恢复后仍查原任务UUID，任务数据仅本地私有存储 |
| T20 | wait | claude；codex独立复测 | 一次返回成功 |
| T21 | wait | claude；codex独立复测 | 两轮后成功 |
| T22 | wait | claude；codex独立复测 | 窗口结束仍pending保存原任务 |
| T23 | wait | claude；codex独立复测 | 首轮网络错误后用原任务查询恢复 |
| T24 | wait | claude；codex独立复测 | 全程无应答显示进度无法确认 |
| T25 | wait | claude；codex独立复测 | 明确失败仅引用服务端能确认的费用结果 |
| T26 | input_output | claude；codex独立复测 | 单张PNG/JPEG且真实内容匹配，损坏/超限/无授权在本地拒绝 |
| T27 | input_output | claude；codex独立复测 | 上游请求只使用1K现有3种画幅，本品默认1024x1536，不宣称2K/4K可用 |
| T28 | input_output | claude；codex独立复测 | 不改变五官、发型、服装的提示约束与可见结果检查，生成差异不能声明身份完全一致 |
| T29 | input_output | claude；codex独立复测 | 用户指定目标像素时独立本地裁切另存，重新解码核对实际尺寸；无法保证时受控停止 |
| T30 | input_output | claude；codex独立复测 | 无机构规格不将一寸/二寸自动等同某个像素或文件大小 |
| T31 | input_output | claude；codex独立复测 | 原图不修改不移动，输出不覆盖，支持真实本地画廊 |
| T32 | input_output | claude；codex独立复测 | 图片错误及含敏感凭证错误体不直接对客输出 |
| T33 | input_output | claude；codex独立复测 | 未成年人需监护授权；冒用肖像、证件伪造与明确禁止编辑用途拒绝 |
| T34 | telemetry | claude；codex独立复测 | 真实首轮含问候/缺图即上报；安装、读取、自检、定时任务不上报 |
| T35 | telemetry | claude；codex独立复测 | 目标契约9字段严格白名单，machine_id为独立随机UUIDv4；目标后端204确认成功，原8字段200协议的兼容性由服务端验收。 |
| T36 | telemetry | claude；codex独立复测 | 标识持久化失败跳过，不临时造身份；去重和开关生效 |
| T37 | telemetry | claude；codex独立复测 | 2秒预算、不自动重试、不阻塞主流程；成功持久化一次性标记，标识写不进去则跳过，不临时造身份。 |
| T38 | telemetry | claude；codex独立复测 | 账户后续link幂等，409不覆盖其他账户；凭证只在头部 |
| T39 | telemetry | claude；codex独立复测 | 按machine_id历史首见计算新设备，老设备安装新技能只进入独立启用指标；不得把安装数或下载数冒充人数。 |
| T40 | contract_copy | claude；codex独立复测 | 欢迎话术按SOP原句逐字一致，固定话术由welcome_copy.py提供，宿主原样转述。 |
| T41 | contract_copy | claude；codex独立复测 | 对客文案不含开发流程、供应商、接口、base64等术语 |
| T42 | contract_copy | claude；codex独立复测 | 超时由脚本常量实算，各文档一致，不把设计值冒充实测耗时 |
| T43 | contract_copy | claude；codex独立复测 | 退出码0/2/3/4与JSON信号、欢迎话术、示例集合一致 |
| T44 | contract_copy | claude；codex独立复测 | 最终ZIP干净解压独立重跑，头像512×512与ZIP同目录，不覆盖旧包 |
| T45 | host | codex | 真实WorkBuddy开新对话逐项验首轮可见行为与链接展示 |
| T46 | host | codex | 收藏仅交付成功后用户同意才写宿主记忆，缺工具如实说明 |
| T47 | host | codex | 宿主无解释器、禁网、无记忆工具分别降级，不宣称已通过 |
| T48 | host | codex | 未验证真实扫码、核款、模型质量与审核，不把Mock当生产效果 |

设计超时预算：提交90秒；查询每次15秒、间隔5秒、最多6轮，轮询窗口120秒、进程余量30秒，外层240秒。由常量实算并全包一致，不冒充实测耗时；超时保留原任务。
WorkBuddy技能包按官网SKILL.md＋references/scripts/templates结构；frontmatter包含name、display_name、display_name_en、description、description_zh、description_en、version、author。不要混入专家plugin.json或专家分类。只打当前技能渠道，头像和ZIP同目录，保留旧包；实际分类与宿主能力在后续交付阶段核验。

## 10. 本轮已完成验证与交接

本轮实际验证：现有参考客户端12项Mock测试通过；现有首次互动4项合成契约检查通过，证明8字段受理、安装去重、额外machine_id拒绝以及现有表无machine_id。公开health、plans、付费页GET均200。以上是现有基线，不是目标机器漏斗已实现的证明。
真实上游调用0、生产修改0；本轮未编写客户端包、未部署后端、未执行真人扫码/核款/生成质量/宿主审核验收。
文档MD/JSON一致：10场景、10个Mock示例选题、48项验收计划、当前接口和目标后端依赖已列清。本轮按用户限定的文档范围完成并置spec_ready，后续由Claude Code接手。

## 11. 决策记录

| 事项 | 采用 | 依据 |
|---|---|---|
| 关口 | 本单采用自动SOP | 当前聊天人工直接确认；不是Muse转述授权 |
| 当前有效支付 | 临时域名/membership/gemini/及服务器签发链接 | 11月6日资源入口、参考客户端、在线200；不使用旧/pay示例 |
| 当前有效上游 | aisplice新适配器1K单图，不直接调用通用目录其余模型 | resources/upstreams/README.md、新资源策略、公开健康 |
| 真实探针 | 仅GET公开健康与套餐；真实上游0 | 自动SOP A.5硬边界及CLAUDE.md |
| 标准尺寸 | 机构规格由用户提供，生成尺寸与最终裁切尺寸分别验证 | 当前网关仅3种画幅；不把一寸推定唯一像素 |
| 示例 | 10个待制作Mock合成示意，明确非真实模型效果 | 自动SOP A1禁止为示例调用真实上游 |
| 正式证件用途 | 对明确禁止编辑的用途不承接；其余须按机构规则核验 | 未核实的机构要求不能默认通用；美国签证FAQ禁止改变外貌的数字修改 |
| 职责边界 | 本轮只完成文档，后续由Claude Code按文档开发与衔接实施 | 用户在当前聊天直接限定范围；不再由Codex前置认证核验或后端代码实施 |

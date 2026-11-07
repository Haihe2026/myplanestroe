# 开发规格：证件照换底助手（规格1.0.2；产品1.0.0）

> 文档状态为 spec_ready。Gemini 三接口已部署并通过隔离身份验收，交 Claude 接入及重打包。

## 1. 范围和读取记录

稳定标识mps-id-photo-background，中文证件照换底助手、英文ID Photo Background Assistant；只做workbuddy-skill，产品仍1.0.0，规格修订为1.0.2。
已读 WorkBuddy 官方文档（2026-11-07T09:45:00+08:00）：https://open.workbuddy.cn/docs/skill 、https://open.workbuddy.cn/docs/expert ，本轮在线下载并读取正文成功。自动SOP、配置、Claude依赖、既有规格和业务源码固定到 `9315e4c20dd4b9c222a3d55135dae201643a9e60`。
本单采用 deploy 车道。素材生成和补丁授权见第11节，后续生产部署已由负责人在接手聊天授权。三接口已部署，客户端接入和产品验收由后续阶段完成。

## 2. 立项、输入输出和边界

目标用户：需要干净背景单人人像的求职或登记照使用者。输入：一张本人/经授权PNG或JPEG、目标底色、用途和必要的机构规格。输出：一张另存的新结果；原图不修改。首版单张，不做换装、换发型、磨皮、五官美化、风格化或批量多人；不保证正式审核通过。
核心词：证件照换底、证件照背景；触发词：白底证件照、蓝底证件照、红底证件照、一寸照片、二寸照片、简历照、报名照、入学登记、照片底色、底换白、发丝边缘、别留蓝边、295×413、标准像素、登记照片、ID photo background。选品单的竞品数据不冒充本品实测数据。
目标像素、DPI和文件大小以用户给定机构要求为准，不将“一寸/二寸”推定为统一像素。明显不允许编辑的正式用途不承接，不用泛称“标准”代替机构要求。

免费试用：无；付费页：现有通用页；额度：原账户通用次数在已接入技能间共享，旧专用余额保留；同设备复用：不启用。首次对话：必做8字段，其他采集不新增。示例选题及方式见第3–4节，档位均为现有1K人像参考图编辑；不承诺硬件打印规格。相邻自家技能见第8节，合规风险为肖像授权、机构编辑限制与AI结果差异；旧包/竞品依据沿00-brief.md，不复用其量化营销承诺。技能name查重以固定输入仓库路径索引和仅本品产品目录核对，结果记录在本轮验证文件。

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

10个示例key与场景逐一对应；按负责人本轮一次性授权，Codex使用登记的aisplice/gpt-image-2.5-ext/1K/n=1真实调用10次，10张均成功。素材放demo-assets/，人物全为文生图虚构成年人；不是用户照片，不是“真人原图换底”的对比效果。每张≤300KB，custom-pixels另存295×413，合计11份PNG；本地缩放/压缩不增加生图次数，完整提示词与哈希见provenance.json。首次真实对话先本地保存需求、真实可见反馈、一个主推方向和两列示例链接，轻确认收尾；问候、仅图、问能力均适用。仅文字不运行示例；授权、充值和任务续接不插新一轮示例。
首轮不取账户/付款链接、不查凭证、不调用业务健康/目录接口、不发起生成；首次互动元数据是唯一例外。用户认可方向不等于同意付费；同任务的范围、照片处理授权、付费执行分别确认后再提交。
固定欢迎句由Claude在welcome_copy.py实现并逐字测试：`欢迎使用WorkBuddy官方认证技能 证件照换底助手。`。
授权及充值话术按SOP责任交接闭环；已有可用次数跳过开户充值；用户拒绝不催促；只有服务端真实余额与账单可作为费用依据。

## 5. 当前有效上游、支付与成本

当前通用生图前缀：`https://aistore.zhaopintong.com/platform-api/gemini`；通用付费页面：`https://aistore.zhaopintong.com/membership/gemini/`。X-Skill-Source必须是本品mps-id-photo-background，渠道workbuddy_skill，环境按实际填写。实际付款和微信恢复沿服务器签发的原账户短期链接；裸页只能查看套餐。
当前资产aisplice，新资源gpt-image-2.5-ext、1K、n=1、禁止旧源回退；photo-retouch-sunburst为兼容编辑入口。不得把aisplice-universal目录所有模型当成已适配，也不向客户端发供应商Key。
沿通用共享次数，默认无试用；同一任务原幂等键去重，未知状态查原任务，不换键自动重发。保留旧专用权益和原账户身份；不改客户余额、订单、套餐或核款。
在线套餐核对29/150、39/200、49/250、999/5000，仅作内部校核，不写死进对客话术。估算成本0.0065美元/张×假设汇率7=0.0455元；最低套餐折合约0.19333元/图，估算毛利约76.47%≥60%。未含税费/汇率波动等，不是真实账单或净利润。


### 5.1 支付页面与后端接入（首版复用现有能力）

以下来源均固定于 `3b35efe8ffc52c4c44b1e24b09b7cce5ec7bfcad`。页面继续沿实际临时域名及服务器签发的链接，不新造 `/pay?skill=`、`/auth/start`、`/pricing` 等未核实路由；X-Skill-Source归因不等于已实现独立页面或订单skill列。
- 客户端头部：X-Skill-Source=mps-id-photo-background、X-Skill-Channel=workbuddy_skill、X-Skill-Device按desktop/mobile/cloud/unknown真实环境；账户操作用原账户Bearer，生成用Skill Bearer。原生客户端不伪造Origin，API POST不自动追随重定向。来源：`resources/shared-image-temporary/client.py:36-62`。
- 原安装身份只创建一次并私有保存；`quick-entry`和`quick-entry/status`正文使用原install_secret；微信绑定/恢复沿已有页面和回调，再查同身份状态；registered不是到账。`membership-link`用原账户Bearer和空对象取新的短期URL，保留服务端ticket/entry，不把凭证拼入URL。Skill Key需state=ready，先安全保存再调用skill-key/bound，供应商Key永不下发。来源：`client.py:66-83`、接入README。
- 钱包与套餐：GET balance的remaining_uses是总可用次数，不叠加shared/legacy字段；共享通道无免费试用，每成功图片沿现有目录扣1次，不新增token账本或改计费单位。套餐从membership-api/plans读取，`core/permanent_plans.py:3`为源码依据；对客不写死价格与额度，旧专用权益保留。
- 网页使用既有会话Cookie及本站Origin/X-Membership-Request校验；在原页面创建订单：POST membership-api/orders正文plan；GET membership-api/orders/{id}查询原订单，POST membership-api/report-payment正文order_id只登记。来源：`service/shared_platform.py:320-350`及`membership/shared-app.js:39,119`。Skill不携带网页/管理员Cookie，不绕过网页鉴权直接发放。
- 支付回调/核款核验：当前公开协议为manual_qr，不为本技能新增支付webhook或声称前端回调可到账。沿现有服务端核款链；`core/manual_payments.py:68-94`中reported与paid分离，核实订单/金额/product，交易流水去重，已结算同流水幂等返回，订单/额度/账本同事务；客户端不能调用confirm_manual。扩展层和真实邮件核款未在本轮实测，不作完成承诺。
- 生成前保存确认后的正文与16–100位原Idempotency-Key；同键同体恢复，未知状态/超时查原任务，402充值后仍沿原任务，不换键重提、不自行核款或退款。图片实际下载成功后再交付，费用只引用服务端记录。账户余额、订单paid及真实次数才是到账依据；不将截图、用户自述或report-payment视为到账。

### 5.2 后端上游资产接入（已有适配器，客户端不直连）

- 固定资源：`resources/upstreams/code-map.json`、`assets.public.json`、`catalog.json`；实际走 `member-0.10.57/resource_adapter.py` 和 `member-0.10.60-new-resource-only/new_only.py`，策略 `new-only-policy.json` 为aisplice/gpt-image-2.5-ext/1K/n=1/legacy_fallback=false。登记aisplice-universal不代表其他模型能调用。
- 服务端适配器通过 `Registry().resolve_for_service('aisplice')` 解析受控资产，只在服务端使用secret；MODEL/API常量及begin/poll函数组装请求和续接。这里只记录资产ID/配置引用名，无实际Key、尾号、密文或管理员权限。当前入口链见 `infrastructure/current-image-services-2026-11-06.json`，不能直接执行旧sunburst.py中的旧源。
- 客户端发送兼容image_engine=photo-retouch-sunburst，不自行发送model/n/quality；references=[{mime,content}]中的content为图片base64，真实同意reference_consent及confirmed后提交。首版1张PNG/JPEG≤5MB、边128–8000、像素≤2000万；服务端 `core/image_inputs.py:12-56` 校验、EXIF方向规范化和清理元数据，再缩限送适配器；不得承诺原始分辨率原封不动送至模型。
- `resource_adapter.py` 的begin按原任务指纹/用户/任务ID校验，网关3种尺寸映射为1:1/3:2/2:3并向供应商images/tasks发单图1K，服务端签名临时参考图；poll查原remote_id及content，取得图片后清洗为PNG交既有网关。提交未知状态记needs_review，不切旧源或重建任务；失败核查/退还沿原服务端路径，客户端不能保证所有未知状态立即退款。
- 成本来源 `resources/upstreams/README.md` 的2026-11-05公开价快照；估算规则见第5节，不查付费模型或供应商账户来“验证”。适配器源码与既有协议已核实，不等于本品真实质量、肖像保真、真人支付或全链部署已验证。上游适配器无需新增资产或部署；本轮示例10次真实调用为单独授权例外，新增消费及工单接口的部署证据见第12节。

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

## 7. 首版首次对话：8字段 / HTTP 200（R3修订）

### 7.1 首版客户端契约

`POST https://aistore.zhaopintong.com/platform-api/telemetry/v1/first-dialogue`，匿名JSON、无Bearer，正文≤4096字节。只发送以下8字段，不发送machine_id：
`event_id`、`installation_id`、`skill_id`、`skill_name`、`skill_version`、`channel`、`client_occurred_at`、`is_test`。
本品取值：skill_id=mps-id-photo-background、skill_name=证件照换底助手、skill_version=1.0.0、channel=workbuddy_skill；开发与自测is_test=true，正式产品仅真实使用才false。event_id和installation_id为分别随机的小写UUIDv4，先写入本技能本渠道私有状态，不复用账户install_secret；时间为带时区ISO格式。标识损坏先安全修复，写不进去就跳过，不用临时身份凑数。
首条真实人工消息唤起技能时主动尽力上报，包括问候、仅图和缺资料；安装、读取、自检、定时任务不上报。总预算2秒，不自动重试；关闭、禁网或失败均不影响业务与退出码。首轮业务接口仍零请求。
仅 **HTTP 200且返回合法event_id、receipt** 才保存成功；received_at为服务端时间，duplicate可能为true。原子保存返回event_id/receipt及一次性标记，返回ID可能是服务器去重后的原事件，不能覆写为请求ID。后续成功标记生效不再发。非200（含204）、缺回执、错误JSON不写成功；恢复重复执行仍沿原持久化身份，避免重建身份放大统计。
来源：`snapshot/opt/skill-platform/member-0.10.58/dialogue_store.py:9,30-59`、`dialogue_gateway.py:35-50`；固定提交见第1节。

### 7.2 原账户关联

以后按原流程取得合法账户后，才调用 `/platform-api/telemetry/v1/first-dialogue/link`；JSON **只有** `{event_id: 服务端返回ID, receipt: 已保存回执, product: gemini}`，原账户Bearer仅请求头。HTTP200且linked=true才确认关联；无回执/无合法账户跳过，401沿原账户恢复，409不覆盖其他账户。此接口不是8字段事件上报，不能给它追加installation_id或machine_id，也不为统计建账户、发额度。
来源：`dialogue_gateway.py:35-48`、`dialogue_store.py:60-68`。只做既有首次对话与合法绑定，提供关闭开关和匿名安装标识用途披露。

### 7.3 二期待办：不是首版依赖（R2修订）

| 任务 | 二期目标 | 首版处理 |
|---|---|---|
| BE01 | 增加machine_id白名单及204确认，兼容旧8字段/200 | 不实现、不发送、不以204验收 |
| BE02 | 机器/安装首见和合法账户关联数据结构 | 不新增表，不读取/依赖跨技能机器ID |
| BE03 | IP按日加盐、每日上限、180天保留及迁移回滚 | 沿现有后端限制，不宣称新策略已部署 |
| BE04 | 完整L0-L4、三项独立指标、管理台及同口径离线报表 | 新设备等缺口标不可得，不造数、不新增统计 |

BE01–BE04移入JSON的phase2_backlog，由Codex未来另单立项写后端补丁与测试，按原部署关口处理；服务端完成实现、隔离验证并部署后，才由新版客户端启用。Claude本版只实现7.1/7.2，不做二期后端或9字段Mock目标。
原BE05不是新增实施任务：保持现有通用生图、共享钱包、微信恢复和新资源适配器不变，不改余额/订单/套餐/鉴权/幂等、不回退旧源；除本轮授权的10次示例外不新增真实生图调用。遥测本身不需要后端补丁；整单因第12节三接口新增而改deploy，不能再按fast跳过部署关口。

## 8. 漏斗、相邻技能与非目标

| 步骤 | 目标口径 | 首版可得性 | 现有来源/缺口 |
|---|---|---|---|
| L0 | 跨技能新设备首次开口 | 不可得 | 现有8字段无machine_id；不得以安装数替代 |
| L1 | 授权页新访客PV/UV | 不可得 | 首版没有本品ip_day_hash历史首见投影，不新增采集 |
| L2 | 窗口内新建并首次完成关联的账户 | 部分可得；完整漏斗不可得 | 现有first_dialogues与账户创建/关联只读资料；不能仅凭linked=true认定新账户 |
| L3 | 新账户首次到达充值页 | 不可得 | 本品未核实同口径页面到达关联；签发链接不等于页面到达 |
| L4 | 新账户首次实际入账 | 部分可得；完整漏斗不可得 | 既有订单/账本只读记录；须按账户首充和交易去重，不以自述或reported认定到账 |

首版能观察的首次对话是installation×skill×channel去重的受理记录及合法回执账户绑定；不是跨技能新设备数，也不等于全部对话或独立人数。跨技能新设备漏斗明确标「不可得」。现有订单/账本只读指标未经本品口径核对则同样标不可得，不因为增加文档而新增采集。
北京时间自然日；跨日充值可能低估单日报表，经营判断至少看7天窗口。三项独立指标以JSON independent_metrics列出的首版可得边界为准，新老设备拆分不可得；不能把安装数当人数或充值减扣量当利润。
相邻老照片修复、风格化头像各保留分界；未确认真实上架ID前不编造转介链接。非目标继续为：批量多人、换装换发型、五官美化、伪造证件、保证正式审核通过、直连供应商Key、新模型/新价目、旧源回退、生产部署及财务操作。

## 9. 验收清单与责任

以下53项为产品验收计划（含原48项与本轮新增5项），不冒充已通过。Claude自测后由Codex从相同哈希ZIP干净解压独立重测；宿主行为测试由Codex执行。

| 编号 | 分组 | 负责 | 验收项 |
|---|---|---|---|
| T01 | first_turn | claude；codex独立复测 | 问候、仅图、问能力、带图明确需求均先价值展示，不取账户或付费链接 |
| T02 | first_turn | claude；codex独立复测 | 首轮仅允许受控首次对话元数据请求，业务请求函数设为抛错仍能完成 |
| T03 | support_and_demos | claude；codex独立复测 | 10张真实资源生成的虚构成年人物示例和1份295×413另存已交付；只展示脚本实际返回路径，两列且同对话去重；不得称用户真实结果或参考图保真验证。 |
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
| T35 | telemetry | claude；codex独立复测 | 首版仅8字段：event_id、installation_id、skill_id、skill_name、skill_version、channel、client_occurred_at、is_test；skill_id=mps-id-photo-background、channel=workbuddy_skill、测试is_test=true；HTTP200且有效回执才成功，不发送machine_id、不以204判成功。 |
| T36 | telemetry | claude；codex独立复测 | installation_id及event_id先持久化；只读/损坏/写失败不临时造身份；安装×技能×渠道去重与关闭开关生效。 |
| T37 | telemetry | claude；codex独立复测 | 总预算2秒、不自动重试、不阻塞首轮；200合法回执原子保存返回event_id/receipt及一次性标记；失败、204或缺回执不标成功；重复执行沿原ID，成功后不再上报。 |
| T38 | telemetry | claude；codex独立复测 | 原账户后续link只传event_id/receipt/product=gemini，账户Bearer仅头部；200且linked=true完成；无回执/无合法账户跳过，409不覆盖其他账户。 |
| T39 | telemetry | claude；codex独立复测 | 首版跨技能新设备漏斗标不可得；只验证既有安装去重与合法账户关联，不要求或伪造machine_id、204、IP日哈希、新表及新设备报表；不把安装/下载当独立人数。 |
| T40 | contract_copy | claude；codex独立复测 | 欢迎话术按SOP原句逐字一致，固定话术由welcome_copy.py提供，宿主原样转述。 |
| T41 | contract_copy | claude；codex独立复测 | 对客文案不含开发流程、供应商、接口、base64等术语 |
| T42 | contract_copy | claude；codex独立复测 | 超时由脚本常量实算，各文档一致，不把设计值冒充实测耗时 |
| T43 | contract_copy | claude；codex独立复测 | 退出码0/2/3/4与JSON信号、欢迎话术、示例集合一致 |
| T44 | contract_copy | claude；codex独立复测 | 最终ZIP干净解压独立重跑，头像512×512与ZIP同目录，不覆盖旧包 |
| T45 | host | codex | 真实WorkBuddy开新对话逐项验首轮可见行为与链接展示 |
| T46 | host | codex | 收藏仅交付成功后用户同意才写宿主记忆，缺工具如实说明 |
| T47 | host | codex | 宿主无解释器、禁网、无记忆工具分别降级，不宣称已通过 |
| T48 | support_and_demos | claude；codex独立复测 | 10次授权文生图和人工预览只证明示例生成；真人扫码/核款、参考人像换底质量及正式审核仍未验证，不能把示例或Mock当作这些验收通过。 |

| T49 | support_and_demos | claude；codex独立复测 | 消费记录按账户/product隔离、分页和总条数；不泄露提示词，预占/消费/退款/未知分开；不得假造单技能归因。 |
| T50 | support_and_demos | claude；codex独立复测 | 提交工单使用原账户和稳定请求键；同键同体幂等、异体409；原话/分类/可选任务所有权校验，不扣次数。 |
| T51 | support_and_demos | claude；codex独立复测 | 查工单限本人编号，其他账户404；状态/回复与服务端一致；处理时限未配置则不承诺，原话和回复只作纯文本。 |
| T52 | support_and_demos | claude；codex独立复测 | 后端补丁隔离测试后财务数据库字节不变；原路由委派/鉴权/生成幂等/套餐不改，部署前保持DEPLOY_REQUIRED。 |
| T53 | support_and_demos | claude；codex独立复测 | demo-assets/provenance.json的10次授权、资产/模型/完整提示词/哈希及11份PNG核对；无真实人物素材、密钥、签名URL或额外调用。 |

设计超时预算：提交90秒；查询每次15秒、间隔5秒、最多6轮，轮询窗口120秒、进程余量30秒，外层240秒。由常量实算并全包一致，不冒充实测耗时；超时保留原任务。
WorkBuddy技能包按官网SKILL.md＋references/scripts/templates结构；frontmatter包含name、display_name、display_name_en、description、description_zh、description_en、version、author。不要混入专家plugin.json或专家分类。只打当前技能渠道，头像和ZIP同目录，保留旧包；实际分类与宿主能力在后续交付阶段核验。

## 10. 本轮验证与交接状态

- 真实示例：10次创建、10张成功，无追加调用；经下载校验、PNG解码、哈希、尺寸/体积和人工预览检查，11份导出PNG（含295×413）已交。预估上游成本US$0.065（公开价估算，未核实际账单），未改客户余额或制造客户消费记录。
- 后端：Windows本机23/23、服务器Linux临时目录23/23通过，详见backend-patch/gemini-support-20261107/test-results.json。测试仅本机HTTP/合成数据库，每例结束对财务库逐字节比较，无生产客户库、无测试生成调用。
- 后续验收包括客户端接口集成、重打包、真机及上传、真人核款和参考图换底保真。旧 HOST_ACCEPTANCE_UNAVAILABLE 仍在验收记录中。
- 部署关口已通过。Claude 可领取 spec_ready，接入三接口、替换素材并重测重打包。

## 11. 决策记录

负责人本轮直接指示：
> 10 张示例图的 10 次真实调用我授权了，用登记的生图资源生成；消费记录、提交工单、查工单三个 gemini 接口的后端补丁你也可以写、测试你跑，部署前拦停等我。

此前决策保留历史。负责人本轮批准部署指定补丁，仅修改 systemd 入口脚本，按默认路径初始化独立工单库，处理时限暂不配置。

| 事项 | 采用 | 依据 |
|---|---|---|
| 关口 | 本单采用自动SOP | 当前聊天人工直接确认；不是Muse转述授权 |
| 当前有效支付 | 临时域名/membership/gemini/及服务器签发链接 | 11月6日资源入口、参考客户端、在线200；不使用旧/pay示例 |
| 当前有效上游 | aisplice新适配器1K单图，不直接调用通用目录其余模型 | resources/upstreams/README.md、新资源策略、公开健康 |
| 标准尺寸 | 机构规格由用户提供，生成尺寸与最终裁切尺寸分别验证 | 当前网关仅3种画幅；不把一寸推定唯一像素 |
| 正式证件用途 | 对明确禁止编辑的用途不承接；其余须按机构规则核验 | 未核实的机构要求不能默认通用；美国签证FAQ禁止改变外貌的数字修改 |
| 欢迎句（R1） | 欢迎使用WorkBuddy官方认证技能 证件照换底助手。 | 用户本轮直接明确保持认证格式不变；现行SOP固定规则1、A.5；Claude已撤回R1。 |
| R3首次对话契约 | 只发8字段；HTTP200及合法event_id/receipt后标成功；不发machine_id | 用户本轮明确按8字段改；A.5与固定规则12；dialogue_store.py:9和dialogue_gateway.py:50。 |
| 二期机器漏斗 | 9字段/204、机器标识、新表与报表均延期；首版跨技能新设备漏斗标不可得 | A.5首版兼容默认；不得把目录或Mock当后端已部署。 |
| 旧首次互动说明的重试建议 | 以自动SOP的2秒、无自动重试为准；保留8字段、200和回执关联协议 | resources/shared-image-temporary/首次互动接入.md含旧重试建议；自动SOP固定规则12优先。 |
| 2026-11-07直接授权 | 10 张示例图的 10 次真实调用我授权了，用登记的生图资源生成；消费记录、提交工单、查工单三个 gemini 接口的后端补丁你也可以写、测试你跑，部署前拦停等我。 | pipeline/products/mps-id-photo-background/01-authorization-20261107.md；负责人本聊天直接指示。 |
| 示例10次例外 | 登记资产aisplice/gpt-image-2.5-ext/1K/n=1实际创建10次并成功10张，不追加调用 | 本次直接授权优先于SOP默认零真实调用；只限本单，调用账与provenance已保存。 |
| 真实示例边界 | 纯文生图虚构成年人；不是对真实人物照片的换底验证；本地缩放压缩及295×413导出不增加上游调用 | Claude依赖文件要求及本轮实际生成与视觉检查。 |
| 车道更新 | deploy，取代1.0.1的fast；仅新增三项消费/工单接口，8字段遥测保持 | 用户本轮授权后端补丁；A.5、阶段4。 |
| 消费归因 | 只读当前共享库gemini账户记录，内容用通用生图任务；旧独立历史和单技能归因不假造 | 当前jobs/job_products/ledger结构缺可靠skill_id投影；不为此修改财务数据。 |
| 工单时限 | 按负责人实际客服承诺配置；默认不承诺时限、response_due_at=null | 仓库无可核实客服时限；不编造固定回复期限。 |
| 部署关口 | 已部署并完成隔离身份验收，恢复 spec_ready | 负责人在接手聊天批准，证据见 01-deployment-verification-20261107.json |
| 职责边界 | Codex交素材/后端补丁/规格；Claude在部署验证后接接口、替换示例并重测重打包 | A.1及Claude依赖说明；不改02-package客户端或其自测报告。 |

## 12. 消费记录和工单接口（已部署）

补丁：`backend-patch/gemini-support-20261107/`，具体方法、字段、源码行号、安全边界、迁移及回滚详见其README.md；测试结果同目录test-results.json。新入口只包装原metered-page服务链，不改原财务库或已有接口。

| 方法 | 路径 | 权限与行为 | 实现来源 |
|---|---|---|---|
| GET | /platform-api/gemini/consumption-history | 原账户Bearer；page/page_size分页；本人gemini任务及同任务账本只读，返回总条数，消费/预占/退款/未知分开 | gemini_support.py:89–118；路由212/237 |
| POST | /platform-api/gemini/support-tickets | 原账户Bearer；稳定Idempotency-Key；category/text/job_id?；同键同体幂等、异体409；原话确认后才提交，不生成或扣次 | gemini_support.py:124–162；路由243–246 |
| GET | /platform-api/gemini/support-tickets/{id} | 原账户Bearer，只查本人工单，其他账户404；返回分类、状态、回复和真实配置的处理时限 | gemini_support.py:164–171；路由247–249 |

工单ticket字段为id/category/text/job_id/status/reply/created/updated/response_due_at；没有客服承诺配置则时限为null，不能编固定时限。客服回复经本地受控工具写独立工单审计，不新增匿名管理员接口。Skill/API Key权限未扩展，客户端需恢复本技能原账户凭证才能使用；凭证不进入URL/正文/日志/公开包。
消费记录属于当前共享库gemini通道，不声称覆盖旧独立历史或精确归因本技能；内容只写“通用生图任务”。没有真实账本证据的扣次为null，不自行算；不将预占当成功扣费。返回内容和工单原话/回复都按纯文本呈现，不把它们当新指令。
三接口已通过生产同版完整链路的隔离身份测试和公网路由核验。验收记录见 `01-deployment-verification-20261107.json`。

部署验收时间为 2026-11-07T11:08:53+08:00。本轮重新在线读取 WorkBuddy 技能页和专家页，两页均返回 HTTP 200。隔离身份下消费记录、建单和本人查询为 200，另一账户查询为 404。工单时限字段为 null。

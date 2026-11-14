# 敦煌写真：后台、账户、支付和上游契约只读审查

固定基线：Haihe2026/myplanestroe@7255618c0085019a2e488994247967890ab0868d；对照汉服固定后台 229f5e96ad349d32c076bff87766c5f27f93f93d。以下路径均相对于该仓库，行号均为7255618固定字节。完整路径/ref/Git blob/可引用行号见 backend-source-index.json；账户专项原清单见 account-source-index.json。

写本报告前已重新在线读取 https://open.workbuddy.cn/docs/skill ：2026-11-14 16:08:17 +08:00，HTTP200，284337字节，SHA256 7fe161594b4715268ad9fe86438dcb5d3818c90621ffb86997b64a68ff04408e；已实际读取技能结构、YAML frontmatter、references/scripts/templates说明。仅本地研究产物，不是产品01规格提交。本审真实业务调用、微信交换、支付、客户数据读取、上游调用和生产变更均为0。

## 可直接采用的结论

- 14项基础业务API、账户/Key/钱包核心和图片适配器相对汉服的229f基线Git blob一致；这只是固定源码一致，不是本轮重新核验生产运行字节。无需新增敦煌账户、钱包、专用套餐、模型字段或后端路由。
- 敦煌客户端应以 https://myplanestore.com/platform-api/gemini 为主业务基址，产品仍gemini；X-Skill-Source为mps-dunhuang-portrait-studio，X-Skill-Channel为workbuddy_skill，Device按真实desktop/mobile/cloud/unknown。HTTP请求不自动追随30x，不伪造Origin或复制浏览器Cookie。
- 当前公众号OAuth已经是wechat-official-20261113层，callback配置为 https://www.myplanestore.com/platform-api/wechat/callback 。不能继续把.61旧网站应用回调当唯一当前路径；公开记录仍 real_oauth_callback_verified=false。
- 当前共享入口的部署登记是trade-primary-2.0.15-20261113→wechat-official等既有链；最新管理员入口另为manual-confirmation-20261113。后者不改图片共享服务入口。
- 资源实际解析aisplice，模型gpt-image-2.5-ext，1K、n=1、legacy_fallback=false。目录aisplice-universal/all或登记显示ChatGPT-image-2.5不表示客户端可选择任意模型。

## 1. 14项业务API：保留现有协议

统一前缀/platform-api/gemini。A= snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py（blob3adf3ab108565cbd45f65aca37e79a3cd11e798c）；K=同目录skill_access.py（8578245333199aa82a9b4de9265625d7bd35672a）；R=同目录registration_entries.py（950191ee007d7ee4b7a6ec3ef937c32449011e67）；G= pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py（6b160791acec7c3e0cf87f8ada2cf5ac849a4c0b）。

|#|方法/路径|鉴权、正文和真实边界|源码|
|---|---|---|---|
|1|GET /membership-api/plans|匿名；实时读取plans，不把旧JSON档位硬编码成客户价格|A316–317|
|2|GET /balance|原账户Bearer；remaining_uses已经包含共享/旧专用等适用来源，不再把balance/shared_uses/legacy_uses相加|A211–219,424–425|
|3|POST /quick-entry|无Bearer；{install_secret}，使用原43位安装身份；返回registration/checkout/ready；ready是额度分支，不附带可用Skill Key|A311–313；R21–47；当前入口包装见下节|
|4|POST /quick-entry/status|无Bearer；{install_secret}；registration_pending或registered+quota。registered不能推定微信已绑定、已付款或Key已bound|A314–315；R71–80|
|5|POST /membership-link|原账户Bearer；{}；返回服务端短链。底层membership.handoff为主域链接，A按产品改为/membership/gemini/，保留fragment ticket|A431–434；core/membership.py46–65|
|6|POST /skill-key|原账户Bearer；{}；仅state=ready且key格式合法后私存；pending_payment/revoked/unavailable不能开工|A389–392；K47–67|
|7|POST /skill-key/bound|原账户Bearer；{key}；先私存再确认，bound=true后才设本地已绑定|A393–396；K78–87|
|8|POST /skill-jobs|Skill Bearer＋Idempotency-Key；本品固定六字段、恰一张参考图；返回原任务id/status及实际响应字段|A287–290,397–405|
|9|GET /jobs/by-key/{原键}|优先Skill Bearer，兼容原账户；查账户内原任务。404明确要求保留原任务，不授权新POST|A366–380,442–451|
|10|GET /jobs/{id}|优先Skill Bearer，兼容原账户；本人原UUID、正确产品；跨账户/错产品不可读|A452–461|
|11|GET /jobs/{id}/image|原任务只读PNG补取；取得并完整校验实际图片后才交付，不是永久素材库|A452–464|
|12|GET /consumption-history|原账户Bearer；page默认1、page_size默认20/最高50；返回items,total,page,page_size，无next_page|G89–118,224–237|
|13|POST /support-tickets|原账户Bearer＋16–100字符Idempotency-Key；{category,text,job_id?}，text1–2000，category为billing/image_quality/workflow/suggestion/other|G14–18,124–162,238–246|
|14|GET /support-tickets/{id}|原账户Bearer；mpsg-加32位hex；本人可查，跨账户404；无工单by-key接口|G164–171,247–249|

工单返回ticket与replayed。相同账户/原键/同正文可显式重交恢复丢失响应；改体409，不悄换键。response_due_at由后端配置决定，未设为null，不编处理时限。消费记录仅current_shared_database_gemini_jobs，包含共享gemini通道而非保证单技能归因，不含旧独立数据库历史；charged_uses/reserved_uses可为null，不把预占或未知当成确定扣费。

账户install_secret与mpskill_凭据均是运行时私密用户凭据，不是供应商Key。绑定401必须清失效Skill Key及本地bound标记、退出4；保留原install_secret、参考路径、原任务/幂等键和锁。下次按原身份领取新Key并bound后仍只查原任务。unknown/pending/download_pending和404不解除已提交锁，不换键重POST；明确未提交的任务才进入重新规划/确认。受理时预占、确认失败由既有受控恢复路径处理；不能凭超时、用户自述或一个余额差值宣称扣/退费。

## 2. 主域、链接与OAuth分层

原参考 resources/shared-image-temporary/client.py 的blob bea554745f369b74ba9be71a8f5493822e84a338 相对汉服仍未更新：4–5行ORIGIN=aistore，14–16行将可信主域浏览器链接改回旧域，30–32行构造器仅允许临时域或显式本地Mock。新规格必须明确客户端实施主域适配，不应声称该SDK已自动完成主域迁移。保留服务端票据的path/query/fragment，严格校验可信HTTPS host和已有会员/绑定路径，不自造ticket/entry，不将API POST重定向；旧域只作兼容输入，归一化目标为myplanestore.com。

www是当前公众号callback/authorize域，不等于新增POST Origin授权：当前OA/legacy白名单仅https://myplanestore.com与https://aistore.zhaopintong.com。服务端非微信根路由精确将旧Origin规范为主域后委派；不支持wildcard、任意子域或null Origin。原生Skill不发伪造Origin；网页POST沿真实Origin＋X-Membership-Request:1及同源Cookie。此映射不是浏览器跨域CORS/OPTIONS已验证的证明。

当前OA主源码：snapshot/opt/skill-platform/wechat-official-20261113/oa_binding.py，blob93c3352c39dac615cb290cb49d3ad7204c08da8b；legacy请求校验/Origin桥接在snapshot/opt/skill-platform/trade-link-fix-20261111/wechat_binding.py，blobd65e9c138ce8ab3c2aa8dc15158c818825945ffe。

|浏览器根接口（不接gemini前缀）|当前行为|行号|
|---|---|---|
|GET /platform-api/wechat/status|Cookie网页身份，logged_in/wechat_bound/mode=official_account|OA493–495|
|POST /platform-api/wechat/start|product=gemini、accepted=true、entry?、force_scan?、return_path?；已验证同身份可linked；否则mode/state/verifier/qr_url/authorize_url/url/expires_in=900|OA214–295,528–530；legacy188–194|
|GET /platform-api/wechat/callback|state/code及手机授权证明Cookie；单次交换→账户关联→302回原Origin /auth/wechat/oa-complete.html#ticket=…|OA399–428,532–540|
|POST /platform-api/wechat/finish|state/verifier，pending或linked/product/url/return_path；网站会话由服务器签发，已完成状态复用原uid|OA326–328,430–438,542–548|

OA另有GET /platform-api/wechat/oa/qr、GET /platform-api/wechat/oa/authorize、POST /platform-api/wechat/oa/redeem；前者SVG二维码，authorize按snsapi_base实际生成redirect_uri=上述www callback；redeem消费一次性ticket。不能把新的OA协议压成旧的直接qrconnect地址。Skill只呈现可信账户入口，不自己拼OAuth、不持微信App secret、不搬Cookie。

期限必须区分：当前注册entry1800秒（legacy14,64–89覆盖R的原300秒）；wechat_entries.py28–47的加密恢复缓存另在原到期上加1800秒；OA state900秒；callback手机handoff最长120秒且一次兑换；会员签链300秒/一次兑换，网站会话1800秒。缓存续接不表示每个二维码或付款ticket也被延长。OA identity按AppID分区，不凭相同姓名/渠道/旧openid隐式合并。未知旧state仍可委派legacy回调，不能声称旧回调已完全移除。

大陆前端基础设施仍按固定源站IP反代，HTTP Host=myplanestore.com，TLS SNI/cert name=aistore.zhaopintong.com（infrastructure/mainland-frontend/myplanestore.com.conf55–76,114–134）。www API直接代理、普通页面canonical跳转。客户端主域化不证明可以下线旧域、删除其源站证书或取消legacy OAuth。

## 3. 支付页与核款：现有能力和新增限制

通用套餐来自实时plans；按当前SOP固定0试用，款项/权益以真实服务记录和到账查询为准。会员网页现有POST /membership-api/orders {plan}、POST /membership-api/report-payment {order_id}、GET /membership-api/orders/{id}沿原Cookie、Origin和X-Membership-Request:1（A320–350）；report只是pending→reported，不入账。订单查询引导至原会员页，不新增Skill订单查询API，不让客户端复制Cookie核款。

core/manual_payments.py68–95：原受控confirm_manual核对产品gemini-image-assistant、订单、金额和所提供transaction_id，事务内发放/账本，同单同流水重试不重复入账。此为后台受控能力，不是Skill权限，也不是微信支付到账webhook。

最新管理员overlay必须另写清：snapshot/opt/skill-platform/manual-confirmation-20261113/manual_confirmation.py（5180f555e45f7716acc81af7e65c5b6ae05bde2f）1–7、27–43，未填真实transaction_id时可按产品/服务/订单生成稳定manual_sha内部审计标识；真实ID非空不改。原鉴权、Origin、金额和发放事务仍执行，但manual_不是银行流水，没有银行reference时不能自动发现同一笔付款被用于不同订单。不可把“所提供标识防重/同单幂等”升级为“已自动核验银行流水唯一/自动到账”。run_ops.py7–31包装最终管理员handler；本品不调用ops、不发放、不改财务。

## 4. 固定六字段与实际上游适配

本品出图正文恰为prompt、size、confirmed、image_engine、references、reference_consent。prompt1–6000字符，敦煌主题/本人成人/单人/同意/身份保持/妆造约束放私有状态和prompt，不新增age/theme/model/n/quality/provider_url等传输字段；size默认1024x1536，另仅1024x1024、1536x1024；image_engine=photo-retouch-sunburst是内部兼容路由，不是实际模型。references恰一项{mime,content}，PNG/JPEG原字节base64，reference_consent取本次真实同意，不收客户URL。

固定执行关系：.24/sunburst.py142–185验证兼容engine与参考许可；.60/run_shared.py10–13禁旧Provider构造/运输；.60/new_only.py55–82、96–133要求原任务预留并转共享namespace适配器；.59/child_resource.py18、44–91继承.57异步协议。本品不因目录有模型而改这个链。

- .14/core/image_inputs.py8–51：每张原图≤5MiB、总≤10MiB、1–3是服务器通用能力（本品更严恰一张）；真实PNG/JPEG、单帧、最短边≥128、最长边≤8000、≤2000万像素；解码、EXIF转正、去元数据、缩至≤2048、导出清洁PNG≤8MiB。Skill本地需在账户/Key网络前有界完整校验，不能只验扩展名/魔数；不需要把本品放宽到3张。
- .59/child_resource.py59–69将清洁参考加密短存，约1小时；.60/new_only.py24–27生成第一方签名输入URL https://aistore.zhaopintong.com/platform-api/image-resource/input/shared/... ，由后端给上游。此内部资源URL不是客户支付链接，不因主域付款规则而在客户端改写。
- 实际POST https://www.aisplice.store/v1/images/tasks ：model=gpt-image-2.5-ext、size映射1:1/3:2/2:3、resolution=1K、quality=auto、n=1、images=[服务端签名URL]；保存task_id/id。GET /v1/images/tasks/{id}取状态，成功后GET /v1/images/tasks/{id}/content，data必须恰一项URL，再安全取图并转清洁PNG（.57/resource_adapter.py17–20,94–159；.59/child_resource.py44–91）。
- POST超时/不明异常进入needs_review，不再次POST、不转旧源；明确拒绝与确认失败才走既有原任务处理。.57 poll仍严格恰一结果；汉服素材出现过n=1却3结果的历史异常，不能把开发素材人工挑图当成生产协议可放宽。
- safe_http.py26–57只用HTTPS、公网DNS/IP钉扎、TLS核验、无重定向；上游API携Key，图片存储取图不携Key。模型Key只从.52/asset_registry.py88–96内部解密解析aisplice，客户端/包/报告无Key、尾号、Cookie或管理员权限。

## 5. 隐私留存与成本必须分层

六字段未包含image_retention，因此本品不启用可选gateway-delivery-delete/1，不能承诺成功交付后结果立即删除或本品结果必为1小时。snapshot/opt/skill-platform/member-0.10.35-r2/image_retention.py49–70明确opt-in分支；TTL=3600、结果加密和delivery-confirm/delete-image端点属于该可选能力，不纳入本品六字段/14项接口。参考图的加密短存、网关可选结果策略、供应商留存分别描述；供应商删除未验证（同文件public及child_resource.py1–5），不宣称已向供应商即时删除。

catalog.json1–9,423–444仍是2026-11-05公开价格快照，ordinary gpt-image-2.5-ext US$0.0065/请求，估算FX7→约¥0.0455/请求，不是11月14日新查价、合同参数完整价或已结算账单。若实时最低通用收入仍¥29/150，则仅模型毛利估算76.4655%；应由根按本次真实plans证据重算，不把旧¥999档继续当可售。素材N次估算N×$0.0065，实际账单/异常多结果计费未验。provider-costs账本为接入后估算、不是整个Key全来源消费归因；不读真实财务库补证明。

## 6. 可写入规格的状态分类

|分类|可证范围|
|---|---|
|源码已实现|上述14接口、原账户/Key/绑定确认、会员网页订单/manual_qr、OA state/verifier/mobile proof/一次handoff、主域前端配置、图片新源适配与严格结果校验；见固定blob索引。|
|既有部署声明|effective-services.txt1–13记录共享trade-primary/微信OA及11月14日manual-confirmation ops；own-wechat-20261113.public.json4–28记录OA及合成/匿名验证；main-domain-restore-20261112.public.json和wechat-checkout-20261111.public.json记录各自当时部署/检查。不是本轮重新核验运行机。|
|本品待实现|敦煌Skill客户端、主域入口/可信链接策略、三同意与冻结/重规划、绑定401恢复、PNG/JPEG有界本地校验、原任务GET续接、一次尝试遥测、对客文案及完整A2。六字段不新增后端能力。|
|本品无新部署|fast车道，本次没有后台补丁/部署/重启任务。任何需改共享层/鉴权/Origin/财务的想法另走授权与部署闸。|
|仍未验证|真实微信公众号callback/平台审核完成、真实银行付款核验、真实客户恢复、全部宿主/手机会话、当前生产内存/文件/环境与仓库每字节相同、供应商删除和最终账单；公开主域200或合成通过都不能代替。开发授权素材调用另有独立provenance/audit，不扩写成本审业务验证。|

附：SOP当前blob43d48ec5625854e4d66b3ff7f754b7f0e2e0eaa6，config blob0dca878e7778521c97031abd3e587c4395ebad3c；A2全量Mock自测，A3仅固定ZIP干净解包静态检查；负责人手动上传，D/D.6继续暂停。旧汉服规格里的Claude分工、aistore客户端主域、旧OA和“银行流水自动唯一核验”表述不得原样继承。


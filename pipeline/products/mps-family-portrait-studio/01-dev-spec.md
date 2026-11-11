# 全家福写真照相馆开发规格

版本 `1.0.0`，Skill `mps-family-portrait-studio`，英文 Family Portrait Studio，车道 `fast`，唯一渠道 `workbuddy-skill`。选品固定 `bbe6b53a30b87602d35aef8f9bc043fa729614bb:pipeline/products/mps-family-portrait-studio/00-brief.md`；SOP、配置、业务源码与资源目录固定 `2d32cc074e7d054068708a82578119bd8ad2993f`。前三款已 `submitted`，最新宠物 1.0.5，串行条件已满足。原事件及原 claim 见 `01-source-verification.json`，不重复认领事件。

## 1. 立项、词表与范围

为家庭分享、纪念、节日和长辈庆典提供主题合照编辑。输入一张包含 3–4 人且主体清楚、已获许可的现有合照，选定一种风格，默认输出一张横版 PNG。面向中文家庭用户；每张独立任务，批次允许按已确认张数逐张处理，已完成项不重做。个人/双人婚纱、纯宠物、证件照按相邻技能分流。首版不承诺把不同照片里的人合到一起，不承接 5 人以上。不能辨清各人脸部时先要更清晰合照，不能根据目录登记“支持参考”推断有面孔绑定。

用途为社交分享和家庭留念，用户按发布平台规则标明 AI 生成；不承诺打印标准或像素级保真，不推断照片人物的亲属、民族、健康或真实年龄。涉及儿童须监护人许可，成人含长辈逐人许可。不得保存照片到公开仓库，十张演示均为虚构成年人。调研 `pipeline/research/2026-11-11-round5.md` 仅作 Muse 选品背景；市场数字未独立核验，不用于对客效果或销量承诺。仓库固定树无同 slug，其余市场全量重名未验证。

核心词：全家福写真、全家福主题照。触发词（23 个）：全家福写真、全家福主题照、家庭合照、亲子全家福、三代同堂、春节全家福、新年红、中式工笔、户外草坪、简约棚拍、复古油画、海边度假、圣诞全家福、寿宴全家福、韩式全家福、田园全家福、family portrait、全家福写真照相馆充值、付费链接、查余额、消费记录、我的账户、恢复账户。description 第一句写用途及原话，如“帮我把这张合照做成新年全家福”，末尾唯一调用倾向句：包括充值、付费链接、查余额、消费记录和恢复账户在内的全家福事务，优先调用本技能。 不把任意充值单词扩成所有技能的账户服务。姓名、代际关系等用户未提供则不编造。

## 2. 本次官方文档读取

本次于 2026-11-11 北京时间重新在线读取成功：

| 页面 | 结果 |
|---|---|
| https://open.workbuddy.cn/docs/skill | 本次在线读取成功，核对 SKILL.md 与八个必填字段、配对 examples、references/scripts/templates 结构。 |
| https://open.workbuddy.cn/docs/expert | 本次在线读取成功；仅用于区分专家独立包结构，当前不交付专家包。 |


另已读固定提交中 2026-11-08 的 `docs/sop/workbuddy-official-docs.md` 技能/专家章节。线上读取遵本聊天 AGENTS 的更严格要求；没有凭缓存称完成。SKILL.md 八个必填字段 `name,display_name,display_name_en,description,description_zh,description_en,version,author`；作者用 MyPlaneStore。只交团队技能包，不混入专家 plugin.json。欢迎句逐字为「欢迎使用WorkBuddy官方认证技能 全家福写真照相馆。」，每对话一次；平台当前未提审，不把这句话当已获审核证据。

## 3. 场景路由与参数

| 口语关键词 | 场景键及主题 | 推荐参数 |
|---|---|---|
| 春节、新年、红色、团圆 | new-year-red：新年红团圆照 | 1K 人像推荐档，3:2，1536x1024 |
| 工笔画、国风、中式 | gongbi：中式工笔画全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 草坪、户外、绿地 | lawn：户外草坪全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 棚拍、简约、影楼 | studio：简约棚拍全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 油画、复古、古典 | oil：复古油画全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 海边、海滩、度假 | seaside：海边度假全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 圣诞、圣诞树、节日 | christmas：圣诞节日全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 寿宴、祝寿、金寿 | longevity：寿宴金寿全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 韩式、清新、奶油色 | korean：韩式清新全家福 | 1K 人像推荐档，3:2，1536x1024 |
| 田园、乡村、乡野 | countryside：田园乡村全家福 | 1K 人像推荐档，3:2，1536x1024 |


明确指定优先，多个歧义先推荐一个方向再问。未命中不强套主题，以本规格三段式合成，不扩大人数/参考格式。方形和竖版仅用户明确提出且所有脸有空间时开放 `1024x1024` 或 `1024x1536`；多人建议横版。只开放已实现 1K，不能以高清/打印名义生成未登记参数。

## 4. 提示词与逐人身份基线

模板顺序：真实合照和逐人保留 → 已确认主题/服装/光线 → 构图与禁止项。三条基线每场景必加，真实性永远第一段：

1. 第一段真实性：以所选合照为唯一主体依据，锁定原有人数、逐人可见五官/发型/肤色/年龄外观/体型/相对位置；只按确认的主题改变环境、服饰、光照，不增删人或设计新脸。
2. 底图不得出现任何文字、数字、标志、水印；不生成汉字，不接受凭空添加真实家庭姓名/年龄/亲属关系。首版不做文字排版。
3. 仅使用所有主体已许可或监护人同意的照片；不冒充真实事件或证件，不复制商标、名人脸，不制作性化未成年人或羞辱性内容。


人物身份基线：按原图左到右/前后位置编号 P1…P3/P4，逐人用真实可见特征指代并分别保留；不以所有人一句话代替，不交换面孔、不融合、不擅自去龄/改肤色/增删人。先请用户确认人数与人物对应，不根据外观推断亲属或敏感属性。会尽力保持五官与身份特征，细节差异可能存在。 仅在用户要求的风格范围改服装和环境；眼镜、疤痕等辨识特征分别记录。原片不改变。不要对客展示 P 编号或推理机制，只说具体保留什么。

| 场景 | 提示词模板要点（后接三基线与逐人约束） |
|---|---|
| new-year-red | Elegant red Chinese New Year family studio, understated silk clothing, red lantern bokeh, no written characters. |
| gongbi | Chinese fine-line gongbi painting on warm ivory silk, delicate botanical background, refined traditional clothing. |
| lawn | Natural spring lawn and leafy trees, soft daylight, harmonious cream and sage casual clothing. |
| studio | Minimalist warm beige portrait studio, pale linen clothing, soft professional photographic lighting, realistic natural skin and clear face details. |
| oil | Old master oil painting, muted brown and teal palette, tasteful vintage clothes, dark atmospheric backdrop. |
| seaside | Airy seaside holiday portrait on a beach, sea-blue and off-white clothing, gentle sunset, natural beach light. |
| christmas | Warm Christmas room, pine branches and golden fairy lights, subtle red and green knitwear, faces unobstructed. |
| longevity | Dignified longevity celebration, restrained golden and burgundy festive interior, elegant Chinese formal dress, no text or numbers. |
| korean | Fresh Korean-style family studio portrait, creamy pale background, natural light and soft pastel clothing, photorealistic. |
| countryside | Warm countryside portrait with a rustic wooden fence and wildflowers, coordinated linen clothing, gentle natural light. |


先离线检查一张 PNG/JPEG ≤5 MiB、边长 128–8000、总像素 ≤2000 万、非动画且可完整解码，点名有问题的文件。确认 3 或 4 人、位置与可见面部；不确定时询问，不自动臆测。用户明确许可将这张照片传给图片服务及算力供应商后，`reference_consent=true`；另行取得当次按张计费的 `confirmed=true`。冻结源 SHA256、逐人说明、主题、尺寸、张数。提交前更换任一内容就作废待提交键及两项确认；已提交原键/原体必须完整保留续查。

## 5. 十张首轮示例

固定十主题，每张一次真实登记上游调用：studio 先生成虚构四位成年人合照，其余九张以该公开合成图做参考编辑。没有使用真实客户照片。固定计划及提示词 `01-asset-plan-20261111.json`，共 10 张示例；logo 另计 1 张，不计入示例。

| 主题 | 入仓源文件 | 生成方式及预览 |
|---|---|---|
| 新年红团圆照 | demo-assets/new-year-red.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 中式工笔画全家福 | demo-assets/gongbi.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 户外草坪全家福 | demo-assets/lawn.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 简约棚拍全家福 | demo-assets/studio.png | 虚构成人文生图；3:2，离线缩为 768×512 PNG |
| 复古油画全家福 | demo-assets/oil.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 海边度假全家福 | demo-assets/seaside.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 圣诞节日全家福 | demo-assets/christmas.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 寿宴金寿全家福 | demo-assets/longevity.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 韩式清新全家福 | demo-assets/korean.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |
| 田园乡村全家福 | demo-assets/countryside.png | 同一虚构四人合照参考编辑；3:2，离线缩为 768×512 PNG |


来源、真实请求数、独立远端任务和派生 SHA 见 `demo-assets/provenance.json`、`generation-audit.json`；逐张审阅见 `01-asset-review.json`。只评合成人数/位置/可见特征，不声称客户真实肖像已保真。参考图通过隔离 harness 将适配器 signed_input URL 换成固定提交公开合成图；生产签名 URL、真人和儿童路径均未端到端实测。首次示例只读离线文件、不读凭证、不访问图片网关；入口另行尽力做匿名首次对话上报，失败不影响示例。缺资源退出 3。

Claude 从来源 SHA 原字节复制十图到包 `assets/`，`assets/demos.json` 仅裸文件名；key、标题、数量与 SKILL.md/README 同步。首轮两列 Markdown 链接表（不内嵌图片），明确“都是效果示例图，不是你的真实结果”，推荐一个方向并问“这个方向可以吗？”。只看单项按 key，已展示的不重复刷屏。示例不能被当作用户家庭真照。

## 6. 主题 logo

暖杏/陶瓷白的立体相框，四位家庭成员半身群像、柔光和材质纵深，体现全家福馆主题；不得平面 ico、文字、品牌或供应商标志。Codex 真实登记资源生成一张，输出 `02-package/dist/logo.png`，512×512 PNG、≤500KB；来源见 `01-logo-provenance.json`。Claude 直接保留原字节，禁止脚本重画或替换，A2 记录 SHA256；不再调用上游。

## 7. 计费与支付页面后端接入

API 基址 `https://aistore.zhaopintong.com/platform-api/gemini`，通用页实际生图入口 `https://aistore.zhaopintong.com/membership/gemini/`，原站通用充值中心 `/membership/`。客户端使用账户关联后由后端签发的入口，不拼出新独立页。2026-11-11 匿名只读核验 health=ok、shared_wallet=true、new_user_uses=0、reference_editing=true；plans 返回 ¥5/25、¥29/150、¥39/200、¥49/250，`manual_qr`。实时以 plans 为准，不硬编码对客金额。0 次免费试用，一次一图，通用钱包在已接入技能间共享，`remaining_uses` 已是总可用次数，不重复相加。

请求 `X-Skill-Source: mps-family-portrait-studio`、`X-Skill-Channel: workbuddy_skill`、实际 `X-Skill-Device`，源码 `resources/shared-image-temporary/client.py:26–55`。原 `install_secret` 持久化一次恢复账户；原账户 Bearer 和 Skill Bearer 分权，凭证不向用户索取或打印，不放入 URL、Git、ZIP、遥测或日志。POSIX 私有目录 0700/文件 0600，Windows 当前用户 ACL。网站 Cookie/Origin/state/verifier 沿现有实现，不更改共享认证，见 `.61-wechat/wechat_binding.py:36–65,101–138`。

| 方法 | 路径（接在 API 基址后） | 鉴权和字段 | 固定源码 |
|---|---|---|---|
| GET | /membership-api/plans | 无 Bearer，读取当时可用套餐 | resources/shared-image-temporary/client.py:64 |
| GET | /balance | 原账户 Bearer，remaining_uses 是总可用次数 | resources/shared-image-temporary/client.py:65 |
| POST | /quick-entry | 无 Bearer，原 install_secret，沿服务器签发 URL | resources/shared-image-temporary/client.py:66–70 |
| POST | /quick-entry/status | 无 Bearer，原 install_secret，registered 只说明账户注册 | resources/shared-image-temporary/client.py:71–73 |
| POST | /membership-link | 原账户 Bearer，正文 {}，取得短期结账 URL | resources/shared-image-temporary/client.py:74–76 |
| POST | /skill-key 与 /skill-key/bound | 原账户 Bearer，ready 才私有保存。bound 正文 {key} | resources/shared-image-temporary/client.py:77–83 |
| POST | /skill-jobs | Skill Bearer，原 Idempotency-Key，确认后的参考编辑正文 | resources/shared-image-temporary/client.py:84–86 |
| GET | /jobs/by-key/{key}、/jobs/{id}、/jobs/{id}/image | 优先 Skill Bearer，兼容原账户回查。保存 PNG 后交付 | resources/shared-image-temporary/client.py:87–97 |
| GET | /consumption-history | 原账户 Bearer，page/page_size，仅共享 gemini 可见历史 | pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:89–118 |
| POST | /support-tickets | 原账户 Bearer，Idempotency-Key，category/text/job_id? | pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:124–162 |
| GET | /support-tickets/{id} | 原账户 Bearer，只查本人，跨账户 404 | pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:164–171 |


已有关联且有次数直接继续。未关联按原 install_secret 调 quick-entry，registration→浏览器确认，checkout→原结账页，ready→持久保存 key 并 `/skill-key/bound` 确认再继续；registered 仅账户注册，不表示已付款。所有账户菜单 `status/auth/topup/balance/paid/history` 无账户时也必须按同一入口给出可点关联链接，不回死胡同。ready 再以原账户调 `/membership-link`。每次重新获取短链，校验 HTTPS、域名/路径及明确有效期；过期最多同身份重取一次，缺期限或异常不显示，提示这一步未完成。`client.py:10–21,64–83`。故障状态 0 说网络没连上，真实 HTTP 错误才说服务正在处理较多请求，不凭空编造。paid 查真实状态与可用次数，用户自述不能作为到账证据；既有余额不能证明新订单已结算。

网页现有 `POST /membership-api/orders` 只收 plan，`POST /membership-api/report-payment` 只收 order_id，后者仅登记待核款；原 Cookie、Origin、`X-Membership-Request:1` 校验不变。回调/核款核实原订单、产品、实收金额与交易流水；订单和钱包同事务，已结算同流水幂等、不同订单流水不得复用。本单不新增回调或 webhook、不在客户端核款。`snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:320–354` 与 `core/manual_payments.py:68–94`，固定提交见文首。读取原订单沿受原会话约束的 `/membership-api/orders/{id}`。不能把订单 reported、截图或“付好了”当入账。

售后三接口已有 11-07 部署记录 `01-deployment-verification-20261107.json`（位于证件照产品）。消费历史只涵盖当前共享 gemini 数据库，不伪造按本 Skill 的历史归因。工单 category 只选 billing/image_quality/workflow/suggestion/other，text 1–2000 字、job_id 可选且必须本人；先展示原话纯文本并取得提交同意，不附照片、凭证、手机号或订单隐私。同键同体回原单，跨账户查单 404，response_due_at=null 时不许承诺时限。

### 7.1 幂等、失败续接与交付

一图一键，Idempotency-Key 为 16–100 位 `[A-Za-z0-9_.:-]`。提交前原子持久化原键、冻结原体及 submit_unknown；未知期间禁止 replan/confirm/regenerate 覆盖，换图也保留旧任务只查。401 清失效 Skill 凭证，通过原安装恢复并持久化新 key/完成 bound，再只查询原任务；可回退原账户读查，最多两次查询，持续失效退出 4 保留原任务。402 获用户同意才获取充值链接；到账后只续明确未提交/未扣的原键未完成项，已交付项不重做。

403 权限问题、409 原任务处理中/冲突、422 明确拒绝、429 限流均保留原任务并如实转述。网络中断、5xx、没有 job ID 的模糊状态只读 `GET /jobs/by-key/{key}`；查询 404 仍不证明未受理，绝不重发 POST 或换键（`shared_platform.py:442–451` 明确该限制）。已获 job ID 只查原任务/图片。当前进度查不到就说“当前进度未能确认”，费用未知说“费用以服务记录为准”。后端明确失败/策略拒绝按实际记录不扣/退回，不由客户端猜余额或承诺免费重做。

仅保存完整解码、CRC/zlib 检查合格 PNG 后宣布交付，失败留 download_pending 用原图片 GET 补取。服务端可能已经在任务成功时结算；不能承诺本地取图未成就尚未扣费，更不能改生产账本。输出非覆盖文件和 index.html 画廊，先图后转述后端账单与剩余。首次交付一次调整引导；需要重生成先说明可能再计费并确认。实际尺寸不符如实说明，离线裁切保留原文件。原契约无已核实 inline_delivery、Range、低余额阈值/专用计费前 503 重试码，首版不实现这些假字段。

提交 90 秒、查询每次 15 秒、查询窗 120 秒、余量 30 秒、计费前额外等待 0，宿主外层至少 240 秒；各文档/脚本常量一致。认证和充值动作自身不扣费；不得把已经有扣费的批次描述成全程零扣费。

## 8. 后端上游资产接入与成本

登记入口固定 `2d32cc074e7d054068708a82578119bd8ad2993f:resources/upstreams/code-map.json,assets.public.json,catalog.json`。资产登记 `aisplice`（目录 asset_id aisplice-universal），实际适配器模型 `gpt-image-2.5-ext`；目录出现其他模型不表示本路线可调用。`.24/sunburst.py:142–164` 使用兼容 image_engine 标识 `photo-retouch-sunburst`，实际由 `.60-new-resource-only/new_only.py` → `.59-child-photo/child_resource.py:26–84` → `.57/resource_adapter.py:94–159` 接入新资源。固定 policy `new-only-policy.json` enabled/aisplice/1K/n1/legacy_fallback=false，密钥仅服务端 `.52/asset_registry.py` 解析；客户端无供应商域名/密钥和直接调用代码。旧 .24 模型常量不是实际执行模型，严禁退旧源。

| 客户端字段 | 值和来源 |
|---|---|
| prompt | 已确认场景模板与逐人身份约束，现有 shared 生成正文 |
| size | 1536x1024 默认；或 1024x1024、1024x1536，.59 SIZES |
| confirmed | true，仅当次明确付费执行同意；client.py:84–86 |
| image_engine | photo-retouch-sunburst，固定兼容路由，.24/sunburst.py |
| references | 恰一项 {mime,content}，原 PNG/JPEG 字节的 base64，不收 URL；.14/core/image_inputs.py:8–41 |
| reference_consent | true，仅这张图的主体许可与传输同意；image_inputs.py:14–15 |


不发送 model/n/quality/people_count/identity_ids/亲属字段。多人说明仅私有快照和 prompt；固定客户端六字段白名单由 Mock 双端验收。服务端规范化参考图、剥离元数据并加密短存；new_only 生成第一方 `/platform-api/image-resource/input/shared/...` 短期签名 URL（约一小时），仅服务端传上游，不接受用户 URL；供应商侧删除没有核验证据，不宣称立即删除。映射三尺寸为 3:2/1:1/2:3，POST `https://www.aisplice.store/v1/images/tasks`，固定 model、resolution=1K、quality=auto、n=1、images=[服务端签名URL]。响应 task_id/id 绑定原任务，GET tasks/{id} 查状态，成功后 GET tasks/{id}/content，必须 data 一项 URL；无重定向泄露密钥或多源回退，结果校验后清洁导出 PNG。30 秒上游提交、15 秒查询；模糊 POST 进 needs_review 不重试，用户侧时间预算见 7.1。

目录 ordinary $0.0065/张，FX=7 为运营估算，模型成本约 ¥0.0455；实时最小单位收入 ¥29/150≈¥0.193333，估算模型毛利率 `(0.193333-0.0455)/0.193333=76.47%` ≥60%。两张估算 ¥0.091，不含税费、通道和人工；11 个开发资产估算 $0.0715，实际发票/供应商账单未核验。只把这次素材作为允许真实调用的例外；Claude 测试与 Codex A3 真实调用仍为 0。

## 9. 车道与实现状态

fast；无本产品后端补丁、迁移、部署或重启。已实现：现有共享网关、钱包/套餐/订单、微信原账户恢复、参考解析、新源适配器、11-07 三个售后接口和八字段遥测。待实现：Claude 的真实 Skill、输入及身份确认、持久状态/失败续接、素材复制、A2 和 ZIP。待部署：无。未验证：真人合照保真、三人/儿童参考、生产签名输入 URL 端到端、实际客户支付、宿主行为、审核/上架。合成四人样本审阅单独列示，不能把它或 Mock 通过当作上述项目通过。

## 10. 首次对话与漏斗

匿名 POST `/platform-api/telemetry/v1/first-dialogue`，八字段 `event_id,installation_id,skill_id,skill_name,skill_version,channel,client_occurred_at,is_test`，UUIDv4；≤4096 字节、2 秒，合法匹配 HTTP200 的 event_id/receipt 原子保存，一安装仅一次且无自动重试。环境开关 `MPS_FAMILY_PORTRAIT_JOURNEY=off`；真实首轮/示例/无凭证预览等早退前尝试，拒绝/只读/损坏/超时均不影响主流程，损坏状态不另造临时安装 ID。包合规处披露匿名安装统计，不含原话、照片、提示词、账户和机器指纹。原合法账户 Bearer 关联 `/first-dialogue/link`，正文 event_id/receipt/product=gemini，linked=true 才确认，409 不覆盖，固定 `.58/dialogue_store.py:9,30–65`、`dialogue_gateway.py:35–50`。

| 漏斗 | 动作及数据口径 |
|---|---|
| L0 | 真实首轮安装事件可见；跨技能新设备去重不可得。 |
| L1 | 原安装授权入口，现有访问证据不足时人数/转化不可得。 |
| L2 | 浏览器确认且原安装查得原账户；新旧账户按可靠证据区分。 |
| L3 | 原账户打开结账页；缺可关联访问数据就不可得。 |
| L4 | 第一笔已核款交易，订单/账本原去重；reported 或用户自述不计。 |


北京时间自然日；启用/激活/充值笔数独立报、跨日低估如实说明，不补造埋点。机器 ID、204、IP 日限额、新表和聚合报表属于二期，首版不改。无本产品真实经营数据。

## 11. 相邻技能分界

| Skill | 分界句 |
|---|---|
| mps-wedding-portrait-studio | 一至两人婚纱写真转婚纱馆；3–4 人家庭合照主题编辑由本品承接。 |
| mps-id-photo-background | 证件用途转证件照换底。 |
| mps-pet-portrait-studio | 纯宠物写真转宠物主题照相馆。 |


## 12. 不承接及对话约束

不做个人/双人写真、5 人以上、不同人照片合成、换脸/新增缺席人物、无许可人物/名人替换、证件/真实事件造假、普通纯修图美颜、预约摄影、打印邮寄、电商运营、视频和文字排版。身份看不清先请换照片，不收敏感身份信息来补猜。

SKILL.md 执行说明第一节“零、接管规则”覆盖每轮：本领域及账户事务必须调用脚本；中断回归用 resume；账户类直接处理不回到首轮；短链接每次现取；只转述 message、不编造故障；本 Skill 生图不以宿主生图替代，用户明确选择宿主另行说明；指定旧图参考时仍做许可和人数检查；出范围按分界句转介。未知生成状态不因“重跑一次命令”而重发生成 POST。

首轮无账户/金额/链接，仅真实可见积极反馈、一个方案、十张离线示例；无图不编造。沉默、无异议、认可方案/示例、同意关联及关联/充值完成都不算付费同意。取得明确执行同意后才取关联链接，复述主题、人数和位置保留、画幅、张数、等待以及“按张计费，以实际账单为准”；先征得允许再打开充值页。授权起定心话“方案已经存好了”“没有产生任何扣费”仅指这次授权动作；含“### 现在需要你做的”编号步骤与“打不开”兜底。拒绝开通只回“好的，方案已保留，想继续时告诉我就行。”并停止链接引导。

交付后才询问一次收藏（收藏/暂不）；明确选择后用户级及项目级各一句调用偏好，含名称与账户事务，不记免费/已开通/永久可用/不重复收费承诺。暂不本对话不再问，取消删两级，不支持如实提示，Mock 不能证明宿主记忆实际生效。对客文案扫描禁用词按 SOP；真实源码接口标识仅在开发材料，不转述供应商、模型和实现细节。

## 13. 验收清单与职责

| 编号 | 责任 | 通过条件 |
|---|---|---|
| T01 首轮与路由 | Claude A2 | 问候、仅图、能力询问、明确需求、照片检查、不要生成、单看示例、10 模板及相邻分流。断言首次交互遥测之外零 HTTP，推荐一个方向、没有支付抢跑、示例去重和固定话术。 |
| T02 本地输入与同意 | Claude A2 | PNG/JPEG 一张合照的体积/尺寸/像素、损坏/动画、缺图；3 人和 4 人正例，1/2/5 人及多张单照、遮挡/模糊不可辨反例；逐人 P1…Pn 对应及人数/位置确认，缺成人许可或监护人许可不提交；替换源 SHA 或更改主题/画幅/人数清除待提交键和双确认，已提交任务仍原样续查。 |
| T03 示例和路径 | Claude A2 | 十图都来自固定清单，假网络与凭证探针零调用；缺文件退出 3。分别用带空格、带 # 的合成现存路径解析 Markdown，覆盖 demo、交付图与画廊。 |
| T04 授权与支付 | Claude A2 | 已有原账户跳过授权，无账户同安装授权和恢复，401 清失效凭证、退出码 4、旧任务保存；未到账、拒绝、链接失败、余额不足、分张扣量、付款后仍确认。 |
| T05 任务契约 | Claude A2 | 一次一张，默认 3:2、仅三种受支持尺寸；六字段请求白名单；人数与逐人特征仅进入提示词和私有快照，绝不添加 identity_ids/people_count/age 或 provider URL 等传输字段；双确认、同体同键、冲突与回放。 |
| T06 等待与续接 | Claude A2 | 一次完成、两轮后完成、五轮仍在处理、首次网络抖动恢复、全程未能确认、明确失败；模拟 401/402/403/409/422/429/5xx，未知查原任务；余额恢复继续未完成项、成功图片只读补取、失败与策略拒绝不扣，模糊费用照记录。 |
| T07 交付与画廊 | Claude A2 | 校验 PNG、非覆盖写入、图先于费用及余额，首张只提示一次调整，保存原图，服务端实际尺寸不符提示，可离线裁切并区分派生图；需要重生成时再确认。 |
| T08 账户与遥测 | Claude A2 | 余额、消费记录、提交及查看工单、同键重复、跨账户 404、无预计时间。真实首轮入口与早退分支均走白名单上报，关停/损坏/只读/断网不影响主流程，同安装一次，合法账户才能 link。 |
| T09 打包与文案 | Claude A2 | 八个必填字段、三组双语同场景同画幅、两级路径、版本与渠道、禁用词、脚本退出码和各处超时一致。A3-E01 故意错配可检出。 |
| T10 收藏与不可用项 | Claude A2 | 收藏卡仅在首次交付后出现，暂不/取消、两级记忆及新对话触发由 Mock 覆盖；不支持写入时如实提示。支付 API 缺失能力、机器漏斗和真机范围按规格记录。 |
| T11 固定包独立检查 | Codex A3 | Codex 从干净目录解压并核对 SHA256、目录和 YAML、双语语义、十图与来源 SHA、实际 Markdown 链接、支付及遥测字段和规格范围。按现行 A3 不跑完整测试。 |
| T12 多人保真和示例来源 | Claude A2 | Mock 中拒绝人数改变、换位/融合面孔、不辨识主体和未经许可的参考；十图 key/标题/尺寸/SHA 对照来源，logo 原字节复制并核对 512×512 PNG ≤500KB；真实调用 0。主观身份检验不能由 Mock 宣称通过，按本规格合成样本审阅记录披露局限。 |
| T13 第七章账户接管 | Claude A2 | 全新用户分别运行 status/auth/topup/balance/paid/history，均走原安装 quick-entry 或如实断网；registration/checkout/ready、短链域名/路径/过期/缺期限、0 与 HTTP 错误文案；Skill401 恢复并只查原任务；paid 只核真实状态，不把自述当入账；执行说明最前接管规则和 15–25 触发词、唯一调用倾向句。 |
| T14 未知任务与坏图恢复 | Claude A2 | 先持久化 submit_unknown 再发 POST；模拟进程退出、超时、5xx、查询404、409及持久401，禁止换键/重发生成；锁住 replan/confirm/regenerate；损坏 zlib/CRC/PNG/Adam7 保留 download_pending，仅 GET 只读补取，不重复收费；不能声称推迟后端结算。 |


Claude 必须覆盖 SOP 阶段 6 全部适用项；模拟正常逐张成功扣量、未关联→关联恢复、402 后原键继续已成功不再扣、策略拒绝/明确失败、上游 5xx 模糊查原键、相同键回放、401 恢复、六种轮询时序、余额/历史/工单/跨户404。SOP 示例 inline_delivery/Range/503 快速重试等没有当前契约的项按明确“不适用”记录，不擅加字段。A2 使用合成账户和 Mock，真实上游 0，不动生产财务。

Codex A3 对 Claude 固定 ZIP 干净解压静态独立检查，含 SHA256、最多两级、YAML/双语语义、十图和 logo/来源哈希、链接实际存在及规格一致；不修改 Claude 源码。真机/浏览器按长期规则已跳过，不能写成已通过。通过即最终包交负责人，自行宿主测试、手动上传；不自动发布。

## 14. 平台与打包一致性

| 场景键 | examples_zh | examples_en |
|---|---|---|
| new-year-red | 用这张四人合照做新年红全家福，横版 3:2。 | Turn this photo of four people into a red New Year family portrait in landscape 3:2. |
| gongbi | 用这张三人合照做中式工笔画全家福，横版 3:2。 | Turn this photo of three people into a Chinese gongbi family portrait in landscape 3:2. |
| lawn | 用这张四人合照做户外草坪全家福，横版 3:2。 | Turn this photo of four people into an outdoor lawn family portrait in landscape 3:2. |


双方各 ≤3、数量相等、逐项同人数/场景/画幅，不能只数条数。一个根目录 SKILL.md，资源在 assets/，脚本在 scripts/，参考在 references/，下方不再有第三层；demo 清单裸文件名，工作区测试/来源审计不进 ZIP。logo 在 dist 外置交付，Claude 按渠道需要保留。示例/结果/画廊链接来自真实绝对路径，非点开头目录；Markdown 对字面 `%`、空格 `%20`、`#` `%23` 一次编码，I/O 原路径。用真实创建 `Codex Demo Assets/studio.png` 与 `Codex#Demo/studio.png` 夹具解析并解码到原文件，不能有意外 fragment/query。

## 15. 决策记录

| 事项 | 采用 | 依据 |
|---|---|---|
| 首版输入 | 一张已有 3–4 人合照；不接多张个人照合成、5 人以上或 1–2 人写真 | 实际适配器仅接受图像数组，无逐人身份绑定；保守缩小选品。 |
| 画幅与档位 | 十场景默认 3:2 人像推荐档；仅已支持三尺寸，不提供 2K/4K 或打印级承诺 | 固定 .59/.60 实现；横版留足多人脸部空间。 |
| 欢迎句 | 欢迎使用WorkBuddy官方认证技能 全家福写真照相馆。 | 本聊天用户固定格式要求；审核独立记录。 |
| 计费与车道 | 通用套餐、0 试用、fast、无部署 | 自动 SOP A.5 与公开 health/plans、固定源码。 |
| 实际接口优先 | 不引入 inline_delivery、Range、低余额标识、503 快速重试、face-ID 等未证实字段 | 固定源码和六字段白名单；未知任务只查询，404 也不授权重提。 |
| 隐私与肖像 | 成人逐人许可、未成年人监护人许可；素材不入遥测/Git/公开工单 | 既有 reference_consent；需单独确认当次付费。 |
| 示例与 logo | 10 张虚构成人示例 + 1 张 logo；各 key 一次 POST，失败不盲重发 | 用户长期明确授权；固定资产计划。 |
| 示例参考传输 | 隔离适配器仅覆盖 signed_input URL，使用固定提交公开合成示例 | 不写生产输入库或钱包；此验证不能证明生产签名 URL 和真人身份锁定。 |
| 遥测 | 现有八字段/200，不发 machine_id；新设备漏斗缺证不可得 | 自动 SOP 当前兼容决定与 .58 网关/白名单。 |
| 账号 | 原 install_secret 持久恢复；sibling_reuse=false；新用户账户命令必须有出口 | 固定配置和 SOP 第七章。 |
| 结算语义 | 客户端先校验 PNG 再宣布交付；服务端可能已按任务完成结算，坏图仅重取原图 | 不在 fast 改动账本/结算时机，不承诺本地落盘前未扣。 |
| 验收与上传 | Claude A2 Mock 完整自测；Codex A3 独立静态检查；最终包负责人手动测和上传 | 当前 SOP；不再恢复旧聊天任务或 AI 心跳。 |


## 16. A1 结论与固定提交交接

A1 16 项逐条核对通过，详见 01-a1-validation.json。十张示例与一张 logo 已就位；开发文档 MD/JSON 一致。置 spec_ready 后 Claude 按固定提交开发真实 Skill、同步资产、A2 自测和打包，Codex 后续独立 A3 检查。

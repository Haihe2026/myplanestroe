# 孕妈写真照相馆开发规格

版本1.0.0，`mps-maternity-portrait-studio`，英文Maternity Portrait Studio，P1/fast，仅workbuddy-skill。Codex写规格与资产，Claude完成真实Skill/A2/打包。固定brief `815868881762e1578aa24a1f30fad993d3435e3d:pipeline/products/mps-maternity-portrait-studio/00-brief.md`；当前SOP/config/源码与资源目录固定 `95f2cfb3e2ca47bfc4f054a4e1ef218e725468be`。原事件/claim及前五产品submitted串行核验见01-source-verification.json，不重复认领，不改其他产品。

## 1. 立项与领域边界

| 立项字段 | 采用 |
|---|---|
| category | 生图类 |
| priority | P1 |
| target_users | 希望记录本人真实孕期的成年人；不去线下影楼也可创作。 |
| platform_rules | WorkBuddy交互、朋友圈等社交纪念；社交平台尺寸/投稿/打印规则未独立核验，不作达标承诺。 |
| input | 一张本人孕期单人PNG/JPEG、本人自述期别及主题意图。 |
| output | 每任务一张PNG，默认1K/1024x1536/2:3；多张独立确认/计费。 |
| free_trial | 0 |
| payment_page | 通用生图页，原身份服务端本次签发关联/充值链接。 |
| wallet_sharing | 同一账户通用次数在已接入技能间共享；专用余额仍原产品，不混同Temu；不读其他Skill私有凭据。 |
| telemetry | 仅8字段首次对话及既有账户link，不报孕期/健康/原话/照片。 |
| tier_use | 人像推荐档：尽力保留原貌，适合社交纪念；不承诺打印或医学准确。 |
| sibling_reuse | False |
| name_check | 本固定队列无其他同slug；中文名7字。brief报告SkillHub已有同名者，未独立核验，不宣称首创/唯一；WorkBuddy市场全量重名未验。 |
| reference_packages | 固定travel1.0.2的账户/恢复/有界输入/遥测经验；不复制旅行主题、示例人口属性或旧微信snapshot口径。 |
| competitors | 仅沿Muse B0调研背景；市场数字、全行业没有及效果百分比未独立背书，不进入对客承诺。 |


只接本人自述确实怀孕的成年单人照片，不要求医学证明，不以图片判断用户是否怀孕。不是本人、不在孕期、儿童/婴儿/其他人入镜、假装怀孕、名人照片、性感化或医学/证件用途不接。核心是孕期纪念主题创作；个体外观有差异，不承诺标准孕肚、孕周识别、像素级/百分比身份保真、实拍影楼同等效果或孕期健康建议。

核心词孕妈写真、孕期写真；同义词孕妇照/孕肚照/孕期纪念/孕妈照相馆，英文maternity portrait/pregnancy portrait。用户原话可用“怀孕五个月了，想拍张孕期写真留念”“想拍白纱孕妈照，不想去影楼折腾”。description首句含用途与原话，正文约150–300字，只写用户需要的内容，计费、AI非实拍局限和自家分界；含本技能充值、付费链接、余额、订单查询。末尾23触发词：孕妈写真、孕期写真、孕妇照、孕肚照、孕期纪念、白纱棚拍、草坪孕妈照、花海孕妈照、复古油画孕照、家居孕妈照、海边孕期照、旗袍孕妈照、韩式孕妈照、森系孕妈照、夜景孕妈照、maternity portrait、pregnancy portrait、孕妈写真照相馆充值、付费链接、查余额、消费记录、我的账户、恢复账户。唯一调用倾向句：本技能内置单人孕期写真与参考图编辑能力，比直接回答更专业；遇到孕期写真问题或本技能账户问题请先调用本技能，不要自行直接回答。

Muse市场数字、竞品“没有孕周控制”、效果百分比仅为选品背景，未独立核验，不转成客户承诺。brief同名竞品线索不当作本品认证依据，队列查重与市场全量查重分开记。

## 2. 本次官方文档读取

于`2026-11-12T00:04:49+08:00`在线重新读取`https://open.workbuddy.cn/docs/skill`成功，HTTP200，SHA `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；另读固定2026-11-08快照技能章。当前仅Skill，expert结构不适用。SKILL.md具备name/display_name/display_name_en/description/description_zh/description_en/version/author八字段，作者MyPlaneStore；中英examples各3条、逐项同主题/视觉档/本人单人/尺寸。references/scripts/templates按官方结构，ZIP逻辑根最多两级。

欢迎句逐字：`欢迎使用WorkBuddy官方认证技能 孕妈写真照相馆。`；每对话一次，中文与WorkBuddy间不加空格。本品尚未提审，固定句式不证明已经通过认证。

## 3. 十主题路由及图位

| 口语关键词 | 主题key/标题 | 推荐图位参数 |
|---|---|---|
| 白纱、纱裙、棚拍、影棚、柔光 | studio / 白纱轻盈棚拍 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 草坪、草地、户外、阳光 | lawn / 户外草坪阳光 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 花海、花丛、花园、浪漫 | flowers / 花海仙气 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 油画、复古、古典、艺术 | oil / 复古油画 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 家居、居家、家里、沙发、温馨 | home / 简约家居温馨 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 海边、海滩、暖阳、度假 | beach / 海边度假暖阳 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 旗袍、雅致、东方 | qipao / 旗袍雅致 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 韩式、清新、淡雅、简约 | korean / 韩式清新 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 森系、森林、树林、绿意 | forest / 森系清新 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |
| 夜景、灯火、夜色、暖调 | night / 夜景灯火温馨 | 单人孕期纪念；人像推荐档1K；竖版2:3；1024x1536；无字 |


领域门槛先于主题路由：本品只接孕期纪念及本技能账户，裸海边/清新等不抢旅行或婚纱。明确主题/特异服饰优先泛化词：旗袍→qipao、油画/复古→oil、韩式→korean、森系/森林→forest、花海→flowers、白纱/影棚→studio、海边→beach、草坪→lawn、夜景/灯火→night、家居→home；清新/温馨等仅给一个稳妥方向再确认，不能按词序压过特异主题。孕早/中/晚是独立档位，不把“晚期”当夜景，也不从例图档位默选给用户。仅明确要求时另选1024x1024/1:1或1536x1024/3:2并确认，不承诺2K/4K或打印级。

## 4. 孕期三档、本人输入与提示词

| 私有key/名称 | 本人自述标签 | 艺术呈现要点 |
|---|---|---|
| early / 早期视觉档 | 本人自述1–3月或孕早期 | 以本人原照及确认的呈现为准，衣物下腹部曲线轻微自然；不强行添加明显大肚，不指定肚围或医学标准。 |
| middle / 中期视觉档 | 本人自述4–6月或孕中期 | 以本人原照及确认的呈现为准，衣物下适度圆润的孕期轮廓；不指定肚围，不套早期或晚期同一轮廓。 |
| late / 晚期视觉档 | 本人自述7–9月或孕晚期 | 以本人原照及确认的呈现为准，衣物下较饱满但比例自然的孕期轮廓；不夸张放大，不承诺与某一月份严格对应。 |


三档只沿本人自述选择并确认，是提示词创作选项，不是医学分期、真实孕周判断或上游专项参数。不同人同月份体态不同；不从照片推断、不换算用户给出的周数、不承诺精确肚围/标准肚形。用户没给档位先与缺失的本人/单人/主题/服装事实一次合并询问，不默认中期；自述冲突先澄清，不自行推断。不索要医学证明或结构化存精确孕周/病史；必要原话仅限私有需求草稿，不进入遥测/自动反馈。十主题×三档均可按确认方案表达，但没有逐30组合实测的保证。

| 主题 | 真实用户模板要点 |
|---|---|
| studio | 白纱轻盈的孕期棚拍：柔光影棚、衬里不透的白色孕期纱裙，胸腹完整遮盖、面部无遮挡；不加头纱、捧花或婚礼仪式造型。 |
| lawn | 户外草坪与自然阳光、合宜日常孕期服装、舒适站姿；不安排运动挑战或健康指导。 |
| flowers | 花海与柔和花色、衬里不透的孕期纱裙、自然侧光；端庄浪漫，不做低俗或身体夸张。 |
| oil | 复古油画质感的影棚背景、端庄深色孕期长裙与侧光；不改变实际可见身份，不添加王室/宗教身份。 |
| home | 简约家居、窗边暖光、舒适上衣和宽松长裤；不出现其他人物或婴儿，不伪称实地纪实。 |
| beach | 泛化海边暖阳和合宜孕期长裙；主题是孕期纪念，不加目的地打卡、旅游叙事或婚礼造型。 |
| qipao | 雅致孕期旗袍、自然布料余量与衣褶、素雅影棚；不用秀禾服或婚礼装饰，不推断民族。 |
| korean | 韩式淡雅影棚、低饱和服装和干净柔光；清新为审美风格，不使用示例人物年龄/肤色作为默认。 |
| forest | 森林绿意和自然散射光、端庄孕期裙装；不加奇幻生物、宗教或部族标识。 |
| night | 夜色灯火与平衡的面部暖光、端庄孕期长裙和开衫；不出现可读招牌、其他人或真实地标承诺。 |


每个prompt以真实性/身份开头，再按已确认视觉档、主题/服装和构图；三基线逐条加：

1. 真实性和身份放第一段：只以这张本人单人原照及用户确认的可见特征为依据，尽力保留五官、肤色、发型、年龄外观与体态；不设计新脸、不增删人。孕期视觉档仅指导已确认的艺术呈现，不推断真实孕周或健康，不使用示例人口属性替换用户。
2. 底图不出现文字、数字、可读招牌、标志、水印或凭空凭证。AI标注通过用户可见模板说明、示例、交付和画廊文字表达，不烧进图片。
3. 仅本人自述确实怀孕的成年单人合宜写真；服装端庄且胸腹遮盖，不含儿童/婴儿/他人，不做性感化、假装怀孕、证件或医疗用途。


示例中的29岁、肤色和发型仅是虚构资产设定，真实用户不套示例身份或固定性别呈现。档位是在本人真实孕期前提下经确认的艺术引导，模型效果可能不同，先说明限制；若用户要健康/孕周判读或假孕模拟则如实不承接。

建议内部plan状态为subject=self、adult/pregnant/single/face-clear事实、stage=early/middle/late及features/outfit/shape；stage默认None，缺期别返回可续接需求说明，不联网替用户猜档。它们都是私有状态，实际生成仍恰六字段，不新增pregnancy_stage/months/weeks/belly_size/age/people_count等传输字段。

输入单张PNG/JPEG≤5MiB、短边≥128、长边≤8000、总像素≤2000万，非动画、完整有界可解码，坏图本地退出3并点名，不发业务HTTP。单人/脸清晰由宿主观察与用户确认，脚本不冒充人脸或孕期检测。PNG每次展开≤64KiB且≤剩余扫描行+1，无无界flush；JPEG只按引用建表、定义复用，≤32不同表构建/≤64扫描，普通8位Huffman基线/渐进支持，少见/过复杂编码提示另存，不放行。输入与交付共用有界校验，采用固定travel1.0.2修复经验。

三项独立同意：本人有权处理这张单人照片；允许这张具体文件发送给图片服务及算力供应商处理；当次明确按张计费执行。同意前不得设置reference_consent/confirmed。本人确实怀孕的资格自述不替代任何一项同意。源SHA/主题/期别/服装/画幅变化作废未提交确认与键；已提交或unknown任务保留原键原体，不能靠换档解锁。

## 5. 十张离线示例与档位展示

固定计划 `f625d81915405059dfeb90ef59f058a17d558e5f:pipeline/products/mps-maternity-portrait-studio/01-asset-plan-20261111.json`：studio为虚构成年孕妇中期视觉档原图，其余9图引用同一公开合成图编辑，早3/中4/晚3覆盖十主题；另1张logo，总上限11次，各key一次POST，不盲补。没有真实孕妇照片，也不是医学孕周示例或30组合验收。

| key/主题 | 该图示例档 | 入仓源文件 |
|---|---|---|
| studio / 白纱轻盈棚拍 | middle（仅该图，不是用户默认） | demo-assets/studio.png |
| lawn / 户外草坪阳光 | early（仅该图，不是用户默认） | demo-assets/lawn.png |
| flowers / 花海仙气 | middle（仅该图，不是用户默认） | demo-assets/flowers.png |
| oil / 复古油画 | late（仅该图，不是用户默认） | demo-assets/oil.png |
| home / 简约家居温馨 | early（仅该图，不是用户默认） | demo-assets/home.png |
| beach / 海边度假暖阳 | middle（仅该图，不是用户默认） | demo-assets/beach.png |
| qipao / 旗袍雅致 | late（仅该图，不是用户默认） | demo-assets/qipao.png |
| korean / 韩式清新 | early（仅该图，不是用户默认） | demo-assets/korean.png |
| forest / 森系清新 | middle（仅该图，不是用户默认） | demo-assets/forest.png |
| night / 夜景灯火温馨 | late（仅该图，不是用户默认） | demo-assets/night.png |


统一离线预览512×768为真实生成后派生；请求尺寸与实际返回尺寸/裁切/量化分别记provenance，不能把请求值冒充实际返回。全部十图、logo须实际生成并逐图目检、记录原始/预览SHA、审计后才spec_ready。Claude原字节复制到assets，demos.json只写裸文件名，key/标题/SHA及示例档一致，note须含该图视觉档和「AI 生成孕期写真，非实拍」。缺任一资源整组退出3，单项只出对应key，不能九图报成功。

首轮说明“都是效果示例图，不是你的真实结果”，用两列Markdown可点链接表，每格标题+本次实际绝对路径+note，不用内嵌图/占位符/手拼路径。用户只要文字/不要看图则不运行demo；不要生成新图片仍可展示离线图。每对话仅按已实际展示记录一次，加载/命令成功/缓存不算展示；只看某项用key，没有该主题×期别的示例如实说明，不拿现有中期图冒充早/晚、不付费补图。匿名首次上报是独立尽力动作，demo本身不读凭据/联网/扣费。失败仅重跑同一离线命令一次，仍失败如实反馈。问候/仅问能力收尾“你想从哪个方向开始？”，明确方向才问“这个方向可以吗？”。

隔离登记适配器只把signed_input URL换成固定公开合成图；不写生产输入库/客户钱包/配置/服务，不以此证明真人保真或生产签名URL链路。

## 6. 主题logo

象牙陶瓷孕妈剪影轻托孕肚、相机镜头框、玫瑰桃色缎面立体质感，无字无品牌无婴儿。 Codex上游只生成1张，512×512PNG≤500KB，保留02-package/dist/logo.png；01-logo-provenance.json记原始/派生SHA与目检。Claude原字节保留，不脚本重画或换图；A2记录SHA。

## 7. 支付页面及后端接入

现有API基址 `https://aistore.zhaopintong.com/platform-api/gemini`；通用充值中心 `/membership/`，当前生图页 `/membership/gemini/`。API/browser的产品仍是gemini，不改成maternity slug；本品来源标识才是 `mps-maternity-portrait-studio`。X-Skill-Source为该slug，X-Skill-Channel及事件channel为workbuddy_skill，X-Skill-Device按真实desktop/mobile/cloud/unknown，不伪装环境。pipeline渠道名workbuddy-skill与HTTP枚举区分。

原install_secret持久生成一次，作为原账户恢复身份；原账户Bearer、Skill Bearer、网站Cookie、OAuth state/verifier分开存用。私有目录0700、文件0600，Windows限当前用户ACL；秘密不进Git、ZIP、遥测、URL、日志或对话，不让用户手填。sibling_reuse=false，不读取其他Skill私有凭据；经现有浏览器微信确认复用账户是服务端流程，不等于客户端跨Skill读秘密。

| 方法 | 相对API路径 | 鉴权/实际正文及结果 | 固定源码 |
|---|---|---|---|
| GET | /membership-api/plans | 匿名；读取当前共享套餐，不硬编码套餐档位价格 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:64 |
| GET | /balance | 原账户 Bearer；remaining_uses 已是总可用次数 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:65 |
| POST | /quick-entry | 匿名正文 {install_secret}；原安装43字符身份，状态 registration/checkout/ready | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:66–70 |
| POST | /quick-entry/status | 匿名正文 {install_secret}；registered 仅关联成功 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:71–73 |
| POST | /membership-link | 原账户 Bearer；正文 {}；使用返回的短期浏览器URL | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:74–76 |
| POST | /skill-key | 原账户 Bearer；正文 {}；仅 state=ready 且合法 key 可保存 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:77–81 |
| POST | /skill-key/bound | 原账户 Bearer；正文 {key}；bound=true 才确认绑定 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:82–83 |
| POST | /skill-jobs | Skill Bearer；Idempotency-Key；六字段正文，恰一张参考 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:84–86 |
| GET | /jobs/by-key/{key} | 原键URL编码；优先Skill Bearer，兼容原账户；404不授权重提 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:87–89 |
| GET | /jobs/{id} | 本人原任务UUID；优先Skill Bearer，兼容原账户 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:90–96 |
| GET | /jobs/{id}/image | 本人原任务；原图只读补取；完整验证PNG后交付 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/shared-image-temporary/client.py:97 |
| GET | /consumption-history | 原账户 Bearer；page/page_size；仅当前共享gemini记录 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:89–118 |
| POST | /support-tickets | 原账户 Bearer；Idempotency-Key；category/text/job_id? | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:124–162 |
| GET | /support-tickets/{id} | 原账户 Bearer；本人可查，跨账户404 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:164–171 |


quick-entry registration→本次服务器签发关联URL；checkout→现有结账入口；ready只是quota分支，不含Key。quick-entry/status的registered仅原secret能解析到账户，不表示微信状态、付款或Key可用。无账户的status/auth/topup/balance/paid/history也必须给同原安装入口或如实网络错误，不能死胡同。账户可用后另POST /skill-key {}，仅state=ready且合法key才私存，再POST /skill-key/bound {key}且bound=true。pending_payment/revoked/unavailable不可生成。原客户端77–83行及固定 `c19830f7da7b9525a4ebde3bd77e1dddd2a4efe9:snapshot/opt/skill-platform/member-0.10.14/service/skill_access.py:47–87`。

充值须先征得用户允许再用原账户POST /membership-link取本次短链。校验HTTPS、第一方域名和路径、无userinfo、明确有效期；过期最多同身份重取一次，缺期限/异常不展示，不拼ticket、订单、OAuth URL。链接以服务端返回为准，可按client.py:10–15规范化旧站链接；客户端不改网关Origin/Cookie或认证白名单。


### 7.1 当前微信入口、身份回调与支付分层

当前源码固定 `95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py`、`95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_entries.py`，网页固定 `95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/var/www/image-assistant/auth/wechat/automatic-qr-20261111.js`；e22补丁与c198报告仅是较早历史，不能再写“当前snapshot/.61仍旧版”。

| 方法/浏览器根路径 | 鉴权和字段 | 响应与边界 | 当前源码 |
|---|---|---|---|
| GET /platform-api/wechat/status | 第一方浏览器Cookie；仅查询网页身份，不等于Skill registered | logged_in/wechat_bound | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:168–171 |
| POST /platform-api/wechat/start | 第一方Origin、X-Membership-Request:1、同源Cookie；{product:gemini,entry,accepted:true}；当前网页另带force_scan:true | {state,verifier,url,expires_in}；或已验证复用分支{status:linked,product,url} | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:184–238 |
| GET /platform-api/wechat/callback | 微信state/code，一次性state及服务端身份交换、双向账户冲突核验 | 生图扫码端完成关联、独立Cookie会话及302到/membership/gemini/；过期/冲突如实错误 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:239–266 |
| POST /platform-api/wechat/finish | 第一方Origin、X-Membership-Request:1；{state,verifier}；服务器校验证明 | pending或幂等linked/product/url；电脑会话独立 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:270–281 |


这些是根路径，不接gemini API前缀；实际身份状态、回调字段与行为按固定源码。Skill不持微信App secret、不拼OAuth URL，不复制浏览器Cookie，不改Origin/认证白名单。产品仍gemini，来源才是本slug。

`.61/wechat_entries.py:28–47`的AESGCM缓存保存入口，可恢复仍在保留范围内的入口/重启状态；缓存保留在原期限后多1800秒，不能把它当对客链接有效期。原入口1800秒、OAuth900秒，普通会员handoff300秒、网站会话1800秒分别处理；对客以本次响应expires_in为准。`automatic-qr-20261111.js:136–157,175–195`在勾选同意后自动出码，当前强制扫码分支会用force_scan:true、最多300秒刷新二维码，不承诺所有已登录浏览器免重扫。

有效原安装入口才可关联回原Skill身份。安装入口在缓存层部署前已遗失/本机凭据缺失时，网站微信登录或付费成功不等于恢复原install_secret；不能把网站兜底账户冒充原安装，须从本Skill有效原身份重开入口，或按真实服务路径说明；不读取别技能私有凭据、不新建钱包掩盖问题，不说“扫码即已到账/即可自动生成”。

公开部署记录 `95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:infrastructure/wechat-checkout-20261111.public.json`声明入口恢复/支付页连续性已部署，14后端+44结账+10UI合成检查，公开页/health HTTP200；真实OAuth交换、真实付款和上游测试均0，所有宿主/手机/银行核款未验。此为既有部署证据，本产品无新部署，也不把它当孕妈宿主/支付验收。OAuth是身份回调，绝非商户支付到账webhook。

### 7.1.1 网页订单、报付款与既有核款闭环

以下订单路径接API基址，不是微信根路径。第一方网页platform_member Cookie；POST带X-Membership-Request:1及浏览器真实Origin https://aistore.zhaopintong.com；Skill不拼Cookie/Origin，不改白名单。 原共享源码`95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:320–336`的规范Origin值是https://myplanestore.com；当前映射有精确源码：`95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:10,160–163：非微信根路由中精确把现站Origin映射为旧规范后委派父Handler；run_shared.py:6–11安装包装层。已实现及既有部署声明，不等于本产品真实订单实测。` Skill不伪造Origin或绕过站点认证，本产品带Cookie真实订单流程未验。

| 方法/网页路径 | 请求正文 | 含义 | 固定源码 |
|---|---|---|---|
| POST /membership-api/orders | {plan} | 创建本人既有套餐订单，产品gemini映射gemini-image-assistant；未付款不入账 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:343–344 |
| POST /membership-api/report-payment | {order_id} | 只将本人pending订单登记为reported，不增加余额，不代表到账 | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:347–348 |
| GET /membership-api/orders/{order_id} | 无正文 | 本人订单真实状态，跨账户不能读取；不以自述/截图判paid | 95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:349–350 |


`95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:snapshot/opt/skill-platform/member-0.10.14/core/manual_payments.py:68–95`的既有`confirm_manual(oid, amount_fen, transaction_id)`核验订单存在、产品gemini-image-assistant、实收金额完全匹配和唯一交易流水，BEGIN IMMEDIATE同一事务更新paid、权益、钱包与账本；同已付订单/同流水/manual_qr幂等返回False不重复入账，不同订单复用流水、已付单换流水或非法状态冲突拒绝。它是受控后台既有核款能力，不是Skill调用权限。本产品不调用核款/发放/退款，不新增支付webhook，不改价格/余额/套餐/财务库。

报付款只登记reported，扫码、registered、网页跳转、截图或“我付好了”均不是到账；paid及余额只读真实服务响应，已有余额也不能证明新订单付款。失效/拒绝/断网保留原需求，允许用户之后核对，不编造即时核款结果。


### 7.2 幂等与失败续接

一图一键，Idempotency-Key为16–100位[A-Za-z0-9_.:-]。首次POST前原子保存原键、原体、源SHA、主题/尺寸、三项同意及submit_unknown；持久化失败不提交。未知期间不能replan/confirm/regenerate或换键。超时、无job_id、5xx等不确定状态只GET原by-key；查询404不证明未受理，绝不重发生成POST或换键。已知job_id只查原任务和原图，已交付项不重做。

401清失效Skill凭据，通过原安装恢复，持久保存新Key、bound确认后仍只查原任务；可按原契约用原账户查，最多两次读查，持续失败退出4并保留锁。402保留原任务，经同意取充值链接，只继续明确未提交/未完成项；403/409/422/429照真实权限/冲突/拒绝/限流处理，不自行退款或放额度。未知进度说“当前进度未能确认”，费用未知以服务记录为准；不得编造原因。HTTP0说网络未连接，真实HTTP错误才按实际消息说明，不泄露字段/错误码/上游信息。

完整解码PNG并验证CRC/zlib/Adam7、非覆盖落盘后才宣布交付。下载失败/坏图留download_pending，只GET同一原图补取，不再生成。服务端可能已在任务成功时结算，不能承诺本地文件未得就没扣费，更不改生产结算。输出实际绝对路径、index.html画廊，先图后原账单与余额，标非实拍；调整若需重生成须再次确认。固定预算：提交90秒、单次查询15秒、查询窗120秒、余量30秒、计费前额外等待0，宿主外层≥240秒，各处一致。


补充绑定401闭环：合法Key私存为未绑定，只有bound is True才新生成。绑定401清失效Key和绑定标记，保留原install_secret/任务，退出4/task_kept；下次原身份领新Key再确认，不永久重复旧Key。已发出任务仍原键GET，不解除锁。固定基座 `847b19d5b87d57d3bce6d0f3aa61ac9130de9748:pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py:524–754`。

## 8. 后端上游资产接入及成本

固定 `95f2cfb3e2ca47bfc4f054a4e1ef218e725468be:resources/upstreams/code-map.json/assets.public.json/catalog.json`。目录资产aisplice-universal（资源解析ID aisplice），实际模型gpt-image-2.5-ext，不能因目录有其他模型就调用。兼容引擎photo-retouch-sunburst经`.24/sunburst.py:142–185`→`.60-new-resource-only/new_only.py`→`.59-child-photo/child_resource.py:26–84`→`.57/resource_adapter.py:94–159`执行新资源；旧引擎名不是旧源调用许可，禁止回退旧供应商。policy固定enabled、aisplice、1K、n=1、legacy_fallback=false；Key只由服务端`.52/asset_registry.py`配置解析，Skill/前端不持有供应商Key或管理员权限。

| 客户端六字段 | 实际值/边界 |
|---|---|
| prompt | 已确认的本人单人身份约束+孕期视觉档+场景/服饰，1–6000字符 |
| size | 默认1024x1536；仅另支持1024x1024、1536x1024 |
| confirmed | 当次明确付费执行确认true |
| image_engine | photo-retouch-sunburst，兼容路由不是对客模型名称 |
| references | 恰一项{mime,content}；PNG/JPEG原字节base64，不收用户URL |
| reference_consent | 这张图的许可与供应商传输同意true |


不得新增model/n/quality/people_count/age/identity_ids/provider_url等传输字段，人物说明仅私有快照和prompt。原image_inputs.py:13–51校验、剥元数据、缩至≤2048并转清洁PNG，服务端加密短存；`.60`提供第一方`/platform-api/image-resource/input/shared/...`短期签名URL，约一小时，只由服务端交上游，不接受客户URL。供应商删除未核验，不宣称立即删除。

实际适配器映射三尺寸为2:3/1:1/3:2，POST `https://www.aisplice.store/v1/images/tasks`，固定model、resolution=1K、quality=auto、n=1、images=[服务端签名URL]。保存task_id/id，GET `https://www.aisplice.store/v1/images/tasks/{id}`查状态，成功后GET `https://www.aisplice.store/v1/images/tasks/{id}/content`且结果data恰一项URL，安全下载和PNG清洁导出；不向图片存储转发密钥、不多源回退。上游提交30秒、单次查询15秒；模糊POST进入needs_review，不盲重发。资源目录登记、实际代码、部署事实和真实验证分别记录。

内部成本：固定catalog ordinary $0.0065/次，估算FX=7，约¥0.0455/次；按本次匿名plans最低每张收入¥0.193333估算模型毛利76.47%≥60%。11资产估算$0.0715，不含税费/通道/人工，实际账单未核；不作客户固定套餐报价。Claude A2/Codex A3真实上游0，开发资产为本聊天长期授权例外。


三档是本地提示词组合，不等于目录/适配器实现了孕周识别、医学肚形或专门阶段参数；实际客户照片始终是经独立同意的一张参考图。

## 9. 车道及真实状态

fast，无本产品后端补丁、迁移、重启或待部署。已实现依赖为共用账户/钱包/套餐/manual_qr、参考解析、新源适配、三售后、8字段遥测及当前微信入口恢复/auto-QR既有部署。待实现为Claude真实Skill、本人孕期/单人/三档门槛、原任务状态机、有界输入、素材同步、A2/ZIP。未验证为孕妈真人及三档肚形专项控制、全部30组合质量、生产签名参考链路、真实微信/手机/付款、本产品WorkBuddy、平台审核/上架。合成成人示例不替代这些验证。

## 10. 首次对话与漏斗

POST /platform-api/telemetry/v1/first-dialogue 仅八字段 `event_id,installation_id,skill_id,skill_name,skill_version,channel,client_occurred_at,is_test`，UUIDv4、≤4096B、2秒、HTTP200有效event_id/receipt才存成功。发送前原子保存attempted并回读，写不进不发；每安装仅尝试一次，失败即弃，嵌套resume→run/重启不重报。关闭开关MPS_MATERNITY_PORTRAIT_JOURNEY=off；关闭/只读/损坏不阻塞、不新造临时ID，首次/早退前尽力。不能含原话、照片、prompt、账户、机器指纹或孕期档/周数/健康信息。

原合法账户Bearer的/first-dialogue/link仅event_id/receipt/product=gemini，linked=true才确认，409不覆盖；服务端canonical event_id按协议保存，不妄判不同于本地就错。固定.58/dialogue_store.py及dialogue_gateway.py；客户端经验 `847b19d5b87d57d3bce6d0f3aa61ac9130de9748:pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/telemetry.py:97–121`。

| 漏斗 | 本品步骤/可得性 |
|---|---|
| L0 | 真实首次对话尝试及成功回执；跨技能新设备去重不可得。 |
| L1 | 打开原安装关联入口；缺可靠访问证据则人数/转化不可得。 |
| L2 | 扫码关联且原安装查到原账户；registered不是付费。 |
| L3 | 服务端本次签发充值入口进入支付页；缺访问证据不可得。 |
| L4 | 首笔已核款交易/账本去重；reported/截图/自述不计。 |


按北京时间自然日区分激活、开通、充值笔数及跨日偏差；machine_id/204/IP日限额/完整机器漏斗为未来能力，不为本品新增。没有真实经营数据可报。

## 11. 相邻技能与不承接

| 相邻Skill | 分界 |
|---|---|
| mps-family-portrait-studio | 三人及以上家庭合影才转；两人/夫妻本品不接，也不谎称全家福支持两人。 |
| mps-wedding-portrait-studio | 明确婚礼仪式写真才转；孕期白纱/旗袍仍本品，不做婚礼造型。 |
| mps-travel-portrait-studio | 目的地打卡诉求归旅行；孕期海边纪念归本品，不做假旅行叙事。 |
| mps-id-photo-background | 正式证件底色归证件照换底，本品不作证件或医学证明。 |
| mps-pet-portrait-studio | 纯宠物归宠物馆，本品不加宠物/婴儿/其他人。 |


不接假孕模拟、他人/名人、儿童或婴儿/多人、性化、医学诊断/孕周判断/健康建议、证件/法律证明、纯美颜、视频、线下预约、打印邮寄、社交涨粉保证。只做两人/夫妻合影时如实本品不支持，不把只支持≥3人的全家福当两人兜底。只用已上架自家技能正向转介且不夸大其能力。

## 12. 接管、确认与交付话术

SKILL执行规范最前为“零、接管规则”，每轮适用。本人孕期写真及本技能账户用脚本，账户类不刷首轮，未知任务只resume；禁止编造故障、费用、恢复时间或用宿主生图绕过。用户明确另选才分流。对客不暴露供应商/模型/密钥/成本/毛利/接口或内部错误码；仅“图片服务及算力供应商”完整接收方类别为传输同意必要说法，不扩展为品牌/实现介绍。

适用首轮先真实可见积极反馈、一个主推方向及两列示例，不先谈账户/套餐/价格/链接；按第5节文字跳过和实际展示去重。确认方向后一次复述本人单人/视觉档/主题/服装/画幅/张数/等待与“按张计费，以充值页和本次服务记录为准”，取得三独立同意。沉默、无异议、认可示例/推荐/视觉档、同意授权、关联完成或自述充值均不算当次付费执行同意。

授权/充值步骤有“### 现在需要你做的”编号及打不开兜底；方案已存、授权本身不扣费的定心话只用于未计费步骤，不能套已交付批次。当前SOP拒绝句用“没问题。等你需要图片的时候随时叫我。”并停止发链接，方案保留。报账只转述真实charged/balance，不自行计算；原图不改、新文件不覆盖，交付/画廊显示「AI 生成孕期写真，非实拍」。调整若需重生成须再确认按张计费，每次只改一件事，不暗示免费。

首次真实成功交付后才问一次收藏（收藏/暂不），明确同意才写用户级/项目级一句领域调用偏好；不存孕期/健康、已付费/永久免费等信息。暂不不再问，取消删两级，无记忆工具如实反馈；声明/Mock不等于真实宿主记忆通过。

## 13. 验收清单与职责

| 编号 | 责任 | 覆盖/通过条件 |
|---|---|---|
| T01 首轮、主题及三档路由 | Claude A2 | 问候/只图/问能力/明确需求；只要文字/不要看图不运行demo，同对话按实际已展示去重，单项按key；10主题与特异词优先，清新/温馨不压过森系/韩式/夜景/家居；阶段不充当主题，例图阶段不自动选给用户；无该主题×档位示例如实说明，不假装有30图。除首次上报外首轮零HTTP。 |
| T02 本人孕期单人及有界输入 | Claude A2 | 本人/成年/自述确实怀孕/单人/脸可辨门槛；三项独立同意；不索取医学证明或看图估孕期。PNG/JPEG≤5MiB/128–8000/2000万像素，完整有界校验；输入与交付PNG共享≤64KiB且≤剩余+1，JPEG按需复用≤32表构建/≤64扫描。坏图/超复杂输入本地退出3、点名文件、业务HTTP0；正常基线/渐进与Adam7/IDAT分块正例。 |
| T03 十图及Markdown路径 | Claude A2 | manifest/key/标题/SHA与10源一致；缺一图整组退出3，不把9图报成功；单项只出该项；demo不联网不读凭证。真实创建空格/#/%路径并CommonMark解析、解码定位原存在PNG，无意外query/fragment。 |
| T04 账号与绑定恢复 | Claude A2 | status/auth/topup/balance/paid/history无账户均同安装入口；registered/ready非付款或Key；另领合法Key并bound is True才新生成。false/缺字段/网络/5xx不生成；绑定401清Key及绑定标记、保留原install_secret/任务，退出4，下次原身份领新Key再bound，含旧缓存和重启，不永久循环。 |
| T05 零试用与计费确认 | Claude A2 | 0试用、动态通用套餐、remaining_uses总额不相加；认可档位/示例/授权/已充值不算当次付费执行确认；一图一键、调整另确认，402先问开页并保留任务、成功项不重复。reported不当到账，不承诺退款/赠额。 |
| T06 等待失败与未知 | Claude A2 | 一次/两轮成功、五轮仍处理、抖动恢复、始终未知、明确失败六时序；401/402/403/409/422/429/5xx分类真实；未知状态只GET原键/原任务，404不授权重POST；90/15/120/30/0/240一致，不编造费用或原因。 |
| T07 交付图与有界PNG回归 | Claude A2 | CRC/zlib/Adam7/EOF/扫描行/超长展开，download_pending只补GET原图不重生；输入和交付校验均有界，不保留可达无界入口。先图后服务记录扣费/剩余；原图不改、不覆盖，新PNG和index.html；尺寸偏差如实及本地裁切另存；低余额仅服务端实标。 |
| T08 消费记录与售后 | Claude A2 | 消费分页、本人记录、工单确认原话/category/text/job_id、同键同体/异体、跨账户404；无后台承诺不编时限，不自动附孕期档/照片/精确周数/账户秘密；暂不可用保留未提交内容再经原同意补交。 |
| T09 首次上报尝试一次 | Claude A2 | 8字段/HTTP200/2秒4096B；请求前原子保存attempted并回读，写不进不发，失败即弃，嵌套resume→run/重启不重发；开关/只读/损坏不阻塞，不造临时ID。合法原账户link/receipt，409不覆盖，无孕期或健康字段。 |
| T10 平台元数据 | Claude A2 | 八字段、slug/version/channel一致、三对双语主题/孕期视觉档/本人单人/2:3/1024×1536一致；ZIP逻辑根最多两级、裸文件名、外置512PNG≤500KB和原SHA；对客禁用词AST扫描，接收方类别固定短语允许，实际供应商/模型/成本/秘密不泄露。 |
| T11 接管、首轮与收藏 | Claude A2 | 执行规范首节接管；只接本领域及本技能账户，不让泛化海边/清新抢旅行婚纱；账户不刷首轮、不得宿主替代；交付后一次收藏，明确同意才写两级偏好，不含孕期健康/费用承诺；暂不不再问/取消删除/无记忆工具如实反馈。 |
| T12 三档语义与可见AI | Claude A2 | 无档位先合并询问，不默认中期；本人自述1–3/4–6/7–9月仅按自述映射，周数不换算、不看图估孕期、冲突先澄清。3×10都可表达但不声称已逐组合实测；选档进私有快照/prompt而非API新字段；模板/示例/交付/画廊可见AI 生成孕期写真，非实拍；假装怀孕或他人/儿童不做。 |
| T13 当前微信及支付客户端Mock | Claude A2 | 模拟关联后registered、不同浏览器入口、过期/缺expires/401/409恢复、短链按返回有效期；当前网页auto-QR/force_scan与缓存恢复及旧入口丢失边界按固定源码说明，网站登录/付款不当原安装恢复；只Mock客户端可测部分，不宣称重跑真实网页/OAuth/付款或部署验证。 |
| T14 阶段变更及原任务保护 | Claude A2 | 源SHA/主题/期别/服装/尺寸变更作废未提交确认与键；已提交/unknown不能靠换档解除锁。先存submit_unknown再POST；首发401、查询404/异常、绑定401、重启恢复均原键原体只读；plan/confirm/regenerate不可覆盖。保留TRV/FAM正反回归，不能只改测试期望。 |
| T15 资源、成本和预算 | Claude A2 | 10源+1logo来源/哈希齐全，阶段示例3/4/3与注记对应；实际API恰六字段单参考，不发pregnancy_stage/months/weeks/belly_size/age等字段；A2测试全Mock且上游0，模型/目录/适配器对应，无旧源回退。 |
| T16 独立A3静态检查 | Codex A3/附录D | Codex从固定ZIP干净解压核SHA/目录/元数据/双语含档位/十图logo/Markdown路径/契约/规格符合性，不代改Claude源码，不跑完整A2/真实上游。 |
| T17 A3后附录D | Codex A3/附录D | Muse固定ZIP/logo任务后由Codex用本机WorkBuddy导入核加载/欢迎/示例/首轮，零消耗；未做/能力失败如实，A3已过stage仍test_passed，交付gate另记。适用当前D.6：同根因连续失败2次当日停，后续须恢复或有依据的新方法，不伪造通过；正式上传负责人手动。 |


现行阶段6逐项对照（以下为待执行要求，不声称测试已跑）：

| 编号/原SOP测试项 | 适用性 | 责任与处理 |
|---|---|---|
| S6-01 未关联账号 → 提示关联 → 浏览器确认后继续 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-02 正常出图并扣费，余额正确 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-03 多图套装中途余额不足 → 402 → 充值后用同一编号继续，已出的图不重复扣费 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-04 内容策略拒绝不扣费 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-05 上游 5xx 不扣费，用同一编号重试成功 | applicable_mock | Claude T05/T06/T14以原键GET续查恢复成功，扣费至多一次；未知/5xx不再生成POST。 |
| S6-06 同一编号重放不重复扣费 | applicable_mock | Claude T05/T06/T14以原键GET续查恢复成功，扣费至多一次；未知/5xx不再生成POST。 |
| S6-07 token 失效自动清除并提示重新关联 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-08 首轮脚本输出不含 `http`、套餐、充值、付费、开通账户、价格字样；欢迎句逐字一致 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-09 首轮调用零 HTTP（把请求函数换成抛异常的函数实测；首次对话上报除外，且失败不影响本轮） | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-10 示例命令不联网、不读凭证；返回的示例 key 集合与 SKILL.md 示例表、README 的个数和标题完全一致；资源缺失时退出码 3 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-11 SKILL.md 含「不得跳过价值展示直接谈钱」「两列」示例表「都是效果示例图，不是你的真实结果」「这个方向可以吗？」，不含「三个方案」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-12 SKILL.md 列明「不算同意付费执行」的情形：沉默、无异议、认可示例、认可推荐、同意授权、授权完成 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-13 授权话术含「授权本身不扣费」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-14 授权起，每一步话术都含「方案已经存好了」和「没有产生任何扣费」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-15 授权和最后一步话术都含「### 现在需要你做的」编号清单，兜底项含「打不开」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-16 话术里不出现服务端未开放的授权路径 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-17 本机已有账户且有次数 → 跳过授权和充值，直接制作 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-18 用户拒绝开通 → 只回固定一句后结束，不重发链接，方案保留 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-19 全包没有旧的慢到账口径；SKILL.md 含「不能将用户自述当作已到账」和「以服务端真实次数为准」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-20 声明的外层超时 ≥ 请求预算 + 轮询窗口 + 计费前拒绝等待上限（从脚本常量实算，不写死）；全包所有超时数值一致（测试逐处比对 SKILL.md、references、脚本注释） | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-21 开工复述齐全，内容不缺项；未明确同意付费执行的，授权或充值后先补确认再开工 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-22 任务中途余额不足 → 先问是否打开充值页，同意后才取链接；话术含「页面打开不等于已经下单」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-23 账户类说法走账户菜单，不触发第一轮 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-24 **全新环境直接运行 `topup`，输出含可点链接或如实断网说明，不是死胡同（第七章 7.2 第 3 条）** | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-25 **本机无账户时 `topup` / `balance` / `status` 调 `POST /quick-entry` 给关联链接，不直接回 `noAccount`（第七章 7.2 第 1 条）** | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-26 **失败原因不误报：断网（`GatewayError` 状态 0）说「网络没连上」，服务端错误才说「服务正在处理较多请求」；`topup` 不得一律报 `busy`（第七章 7.2 第 2 条）** | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-27 首次对话上报只含白名单字段，每个安装只发一次，关闭开关生效；开口统计按第六章第 5 节验收 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-28 首次对话上报不挂在可能走不到的分支上：首轮示例命令、无凭证预览退出这些提前返回的分支，退出前都已经发出过上报（测试逐个分支断言） | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-29 一次就出图 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-30 两轮后出图 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-31 五轮都还在处理 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-32 首轮网络抖动后恢复 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-33 全程连不上 → 说「当前进度未能确认」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-34 明确失败 → 不扣费 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-35 成功时先交图；首次交付附一次调整引导，之后不重复 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-36 失败话术按四拍；我方服务端原因只说「服务正在处理较多请求」；拿不到明确费用结论时说「费用以服务记录为准」 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-37 每次付费交付后转述服务端返回的本次扣费和剩余，余额低时追加充值提醒 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-38 交付话术说明原图没有改动；后续调整需要重新生成时先说明可能再次计费 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-39 大图分段下载，断网后续传成功 | not_applicable_current_contract | 当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-40 直连下载失败 → 同键同体加 `inline_delivery` 补取成功，不产生新计费；补取失败才走失败话术 | not_applicable_current_contract | 当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-41 计费前拒绝错误码 → 按常量等待并同键重试，单张次数和整批等待上限生效；其他 5xx 不重试 | not_applicable_current_contract | 当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-42 同设备账户复用（启用时）：只提交指纹；用户确认前不签发；拒绝后不再检测；关闭开关生效；失败时回到正常授权 | not_applicable_current_contract | 当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-43 请求体出现未登记字段时被拒绝（客户端和服务端各测一次） | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-44 凭证失效 → 自动清除、退出码 4，重发原任务走授权 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-45 **对客禁用词测试**：SKILL.md 面向用户部分、README、references 转述文案、脚本所有对客进度文案中不含禁用词清单里的词（进度文案用 AST 从脚本里取出所有字符串常量来扫） | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-46 查余额与消费记录、提交工单、查工单各走通一次 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-47 实际尺寸与请求不一致时提示并提出裁切 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-48 输出目录有 `index.html` 画廊 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-49 参考图格式报错点名具体文件 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-50 离线检查不调用后端 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-51 输出文件不覆盖 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-52 @ 技能完整走一次，交付后弹出收藏卡片；付费或购买流程中途不弹 | applicable_mock | Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态、附录D按规定动作另记，未验仍未验。 |
| S6-53 点「收藏」后，宿主记忆管理里用户级和项目级各有一条记录，内容只有调用偏好一句话 | applicable_mock | Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态、附录D按规定动作另记，未验仍未验。 |
| S6-54 选「暂不」后，本次对话不再询问 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-55 开新对话，不 @ 技能，直接问一句该领域的问题 → 出现「加载技能 <技能name>」，并按技能流程执行 | applicable_mock | Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态、附录D按规定动作另记，未验仍未验。 |
| S6-56 说「取消收藏<技能中文名>」→ 两层记忆里的记录都被删除 | applicable_mock | Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-57 宿主不支持写记忆时，如实告知不支持，不假装成功 | applicable_mock | Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态、附录D按规定动作另记，未验仍未验。 |


Temu免费1次为Temu专属，本品0试用不适用；当前附录D及D.6仍适用，不用旧全面豁免口径替代。

Claude按契约Mock/合成账户逐项给A2结果与旧错误反证；Codex固定ZIP独立静态A3，不代改包、不重复完整A2、不调真实上游。A3后Muse按D.2给固定ZIP/logo任务，Codex本机导入规定动作，未做不写通过；能力问题不改变A3结论、stage仍test_passed但交付gate另记。本单适用D.6同根因连败即停规则，不能从别单日志转述自动扩大或跳过。最终上传负责人手动。

## 14. 平台与打包一致性

| 主题/档 | examples_zh | examples_en |
|---|---|---|
| studio/middle | 我本人怀孕五个月，用我的单人照做白纱柔光孕妈写真，选择中期视觉档，竖版2:3，1024×1536。 | I am five months pregnant. Use my own single-person photo for a white-tulle studio maternity portrait, middle-stage visual preset, portrait 2:3, 1024×1536. |
| lawn/early | 我本人在孕早期，用我的单人照做草坪阳光孕妈写真，选择早期视觉档，竖版2:3，1024×1536。 | I am in early pregnancy. Use my own single-person photo for a sunny-lawn maternity portrait, early-stage visual preset, portrait 2:3, 1024×1536. |
| qipao/late | 我本人怀孕七个月，用我的单人照做旗袍孕妈写真，选择晚期视觉档，竖版2:3，1024×1536。 | I am seven months pregnant. Use my own single-person photo for an elegant-qipao maternity portrait, late-stage visual preset, portrait 2:3, 1024×1536. |


逐对核主题、本人、单人、孕期视觉档、2:3及1024×1536，不只数数量。SKILL根文件，scripts/references/assets/tests下直接文件，逻辑根最多两级；demos.json裸文件名，不把来源审计/Mock/dev打进ZIP；logo外置按原SHA。状态目录不以点开头，所有对客文件链接正斜杠、只在输出端编码空格/#/%一次，I/O原名不变。至少真实创建Maternity Demo Assets/studio.png、Maternity#Demo/studio.png及Maternity%Demo/studio.png，CommonMark解析后解码定位存在文件，无意外query/fragment。包与代码/元数据/遥测版本一致，无旧旅行词/固定孕期档/示例人口属性残留。

## 15. 决策记录

| 事项 | 采用 | 依据 |
|---|---|---|
| 用户范围 | 本人自述确实怀孕的成年单人照；不索要医学证明 | brief只本人/不假孕/儿童不入镜；资格声明不是医疗验证。 |
| 三档 | early/middle/late按本人自述并确认，默认None；档位不代表医学肚形标准 | 不看图诊断、不换算周数、不承诺专项模型或精确肚围；缺事实一次合并问。 |
| 阶段控制 | 提示词创作维度，私有状态冻结；不是新增后端字段 | 现有六字段/单参考适配器，没有孕周API或医学控制参数。 |
| 主题 | 保留10主题，三档跨主题独立；海边仍是孕期纪念 | brief总数固定，避免婚礼/目的地叙事和临时自由发挥。 |
| 素材 | 10示例按早3/中4/晚3＋1立体logo，各key一次POST | 长期授权；10×3不等于30调用，全部合成成年人，无真实孕妇照片。 |
| 默认画幅 | 人像推荐档1K/1024x1536/2:3；另两尺寸仅用户明示 | 固定.59/.60三尺寸，不承诺2K/4K或打印级。 |
| 欢迎句 | 欢迎使用WorkBuddy官方认证技能 孕妈写真照相馆。 | 用户固定格式；未提审，不以话术证明已经审核通过。 |
| 收费 | 通用套餐、0试用、不列固定客户价格 | 动态plans，内部毛利估算与实际结算分开。 |
| 账号 | 原install_secret、另取合法Key、bound真值、绑定401作废Key | 1.0.2实际恢复闭环；不读取其他Skill凭据或重建账户。 |
| 微信 | 用当前入口缓存和auto-QR源码及公开部署记录；时限按返回 | 旧e22为历史，不能再说当前snapshot旧；网站兜底不等于原安装凭据恢复。 |
| 车道 | fast，无本单后端补丁/部署 | 现有参考图与共用账户/支付足够；不动共享认证/财务。 |
| 保守协议 | 未知/401恢复/404均只读原任务；PNG/JPEG有界 | 继承travel1.0.2修复和反证，不能把幂等当重复POST许可。 |
| 遥测 | 当前8字段/200，先持久化attempted，失败即弃 | 固定白名单未含machine_id，更无孕期数据；缺失漏斗不可得。 |
| 相邻边界 | 两人照不接；只有≥3人家庭合影才转全家福 | 纠正brief夫妻照一概归全家福与现有3人起能力的冲突，不扩大本品。 |
| 真实状态 | 实现/待Claude/无部署/未验证分列 | 合成示例、Mock和已有微信部署不是孕妈产品真人/宿主/支付验收。 |
| 交付 | A2→Codex A3→附录D固定派活，负责人手动上传 | 当前SOP含D.6，本单不沿用旅行日志里转述的特殊口径。 |


## 16. A1结论与固定交接

10示例与logo已就位，最终A1逐项结果和文档SHA以同提交01-a1-validation.json通过记录为准，只有全部通过才提交spec_ready。 提交MD/JSON及固定资产后交Claude真实Skill、A2和打包；不在本职责直接实现、部署或上传，不另建AI心跳，不转回旧聊天。

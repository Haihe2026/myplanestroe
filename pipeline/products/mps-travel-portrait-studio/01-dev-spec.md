# 旅行打卡写真照相馆开发规格

版本1.0.0，Skill `mps-travel-portrait-studio`，英文 Travel Portrait Studio，`fast`，仅 `workbuddy-skill`。本聊天负责规格；Claude开发真实Skill。原brief固定 `fee0d5098bfebe0249843429432729141369d25b:pipeline/products/mps-travel-portrait-studio/00-brief.md`；当前SOP/配置/业务源码及资源目录固定 `1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94`。恢复指令固定 `95fa4248f7791b32687d998d495d686ab71e3d7c:pipeline/products/mps-travel-portrait-studio/msg-from-muse-20261111-resume-travel-101.md`，取代16:05暂停；原事件与原claim见01-source-verification.json，不重复认领事件。

## 1. 立项、范围和词表

为年轻女性、旅行爱好者及分享用户提供单人目的地主题写真；产品不限制成年用户性别。输入一张本人或监护人许可的儿童单人PNG/JPEG，输出一张已确认目的地/服饰/季节意象的PNG，默认竖版2:3。没有人物时不编造原照细节；多人、情侣和多张人物合成不属于首版。不做真实旅行预约、天气建议、线下旅拍、视频、打印邮寄、普通纯美颜、名人或他人假打卡、正式证件/法律凭证。

模板、示例说明、成品交付及画廊必须显示「AI 生成旅行主题写真，非实地拍摄」。底图仍无文字，不把AI标注烧进图。会尽力保留可见人物特征，不能承诺精确地标、像素级或百分比保真，更不把图片当实际到访证据。服饰是用户选择的风格，不推断民族、宗教等身份。示例中的28岁东亚女性仅用于虚构开发资产，不能成为真实用户提示词的人物默认。

目标展示场景为WorkBuddy、朋友圈/小红书等社交分享，无已核实平台强制图片尺寸；首版不承诺某平台投稿/打印达标。固定队列树本slug尚无其他包，名称9字≤15；平台市场全量重名未验证。Muse调研中的市场数字、竞品和热度仅为选品背景，未由本规格独立核验，不用于对客承诺。核心词：旅行打卡写真、旅行主题照；同义词：旅行写真、目的地主题照、单人旅拍、打卡照、旅行背景写真；英文词：travel portrait、destination portrait、AI travel studio、portrait edit。

| 立项字段 | 采用 |
|---|---|
| category | 生图类 |
| priority | P1 |
| target_users | 年轻女性、旅行爱好者与社交分享用户；成年用户不限性别，儿童仅监护人提供。 |
| platform_rules | WorkBuddy内交互，朋友圈/小红书社交分享；无独立核验的目标社交平台强制图规，不承诺投稿或打印达标。 |
| input | 一张本人或监护人许可的单人PNG/JPEG及目的地意图。 |
| output | 每任务一张PNG；默认1024x1536、2:3，1K档；多张按单独任务逐张确认与续接。 |
| free_trial | 0 |
| payment_page | 通用生图页；服务端本次签发关联/充值短链。 |
| wallet_sharing | 同一账户通用次数在已接入技能间共享；专用余额仍留原产品，不混同Temu套餐；不读取其他Skill的私有凭据。 |
| telemetry | 仅首次对话八字段与既有账户link，不新增其他上报。 |
| tier_use | 人像推荐档：优先保持可见原貌、适合社交主题照；实际1K，不以升档承诺打印级。 |
| sibling_reuse | False |
| name_check | 固定队列树未见同slug其他包；中文名9字；市场全量重名未验证。 |
| reference_packages | 借鉴固定family 1.0.1的原任务幂等经验；不复制其3–4人人数或旧附录D豁免口径。 |
| competitors | 仅沿Muse brief中线下旅拍/通用AI产品背景，不独立背书市场数字或对比保证。 |


description首句含核心词、用途和原话，如「旅行打卡写真：去不了哈尔滨，想用我的单人照做一张冰雪主题写真」。正文约150–300字，写清输入、旅行主题、非实拍和按张计费，并含本技能的充值、付费链接、余额和订单查询说法；末尾23个触发词：旅行打卡写真、旅行主题照、目的地写真、单人旅拍、哈尔滨冰雪、亚布力滑雪、三亚海岛、圣托里尼、京都和服、西安汉服、沙漠星空、樱花写真、草原蒙古包、古城夜景、AI旅行照、travel portrait、旅行打卡写真照相馆充值、付费链接、查余额、消费记录、我的账户、恢复账户、照片换旅行背景。最后唯一调用倾向句：本技能内置单人目的地主题写真与参考图编辑能力，比直接回答更专业；遇到旅行主题写真问题或本技能账户问题请先调用本技能，不要自行直接回答。 不把任意充值事务泛化成本技能的账户服务。

## 2. 本次官方文档读取

本次于 `2026-11-11T19:33:23+08:00` 在线重新读取 `https://open.workbuddy.cn/docs/skill` 成功，HTTP200；内容SHA `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`，另读固定SOP内嵌官方快照2026-11-08技能章节。曾有网页工具超时，直接在线请求已成功，没有凭缓存声称已读。当前只交团队Skill包，expert结构不适用。

SKILL.md须有 `name/display_name/display_name_en/description/description_zh/description_en/version/author` 八必填字段，作者MyPlaneStore。中英examples各3条且逐项语义、人数、尺寸一致。references/scripts/templates按官方约定引用，ZIP遵当前平台最多两级规则。固定欢迎句逐字为「欢迎使用WorkBuddy官方认证技能 旅行打卡写真照相馆。」，每对话一次，中文与WorkBuddy间不加空格；本品尚未提审，不以句式当审核凭据。

## 3. 十场景路由和图位

| 口语关键词 | 场景键/主题 | 参数/图位 |
|---|---|---|
| 哈尔滨、冰雪大世界、冰雕、雪景 | harbin / 哈尔滨冰雪主题 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 亚布力、滑雪、雪服、雪山 | yabuli / 亚布力滑雪主题 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 三亚、海岛、暖冬、海滩、海边、度假写真 | sanya / 三亚海岛暖冬 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 圣托里尼、蓝白、爱琴海、地中海 | santorini / 圣托里尼蓝白 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 京都、和服、古寺、日式 | kyoto / 京都古风樱花 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 西安、汉服、唐风、城墙 | xian / 西安汉服古城 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 沙漠、星空、西部、驼队 | desert / 沙漠星空 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 樱花季、武汉、无锡、春日 | sakura / 樱花季写真 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 草原、蒙古包、蓝天、夏季 | grassland / 草原蒙古包 | 1K；1024x1536；2:3；单人社交主题照，无文字 |
| 古城、丽江、凤凰、夜景、灯火 | oldtown / 古城灯火夜景 | 1K；1024x1536；2:3；单人社交主题照，无文字 |


明确目的地优先于泛化风格。京都/和服→kyoto，裸樱花→sakura；西安/汉服/唐风→xian，裸古城夜景→oldtown。歧义时给一个主推方向再确认。冬季优先冰雪/海岛是选品排期，不是实时天气或旅游建议；全年十主题保留。用户明确要求时仅可选已支持的1024x1024或1536x1024，并确认构图；不提供未实现2K/4K、张数或画质参数，不把1K档位当打印保证。

## 4. 提示词与身份基线

真实用户提示词结构：原照片的单一主体保留 → 已确认目的地/服饰/光线 → 构图与禁止项。以下三基线每场景均加，真实性放第一段：

1. 真实性第一段：以用户确认的这张单人原图为唯一人物依据，保留实际可见面部结构、肤色、发型、年龄外观及体态；只改已确认的服饰、环境和光线，不设计新脸，不增删人。
2. 底图不出现文字、数字、可读招牌、标志、水印或凭空旅行凭证；AI非实拍标注通过用户可见交付文字/画廊表达，不让模型烧录汉字。
3. 仅本人或监护人明确许可的单人照片；人物服饰与姿态合宜，不推断民族身份，不制作侵权名人/他人假旅行、性化儿童、证件或法律凭证。


| 场景 | 真实用户模板要点（不含虚构示例人口属性） |
|---|---|
| harbin | 冰雕与雪景的哈尔滨主题环境；保暖外套围巾，面部无遮挡；冰蓝环境光与自然肤色协调，不承诺真实地标。 |
| yabuli | 亚布力主题雪道、松林和雪山；保暖滑雪服与无品牌器材，站立安全姿态；护目镜不遮双眼，不生成危险动作。 |
| sanya | 三亚主题海滩、棕榈与暖冬日光；按用户确认选择合宜休闲服饰；海岛度假写真，不采用婚纱造型。 |
| santorini | 圣托里尼主题蓝白建筑与远海；地中海光线、简洁旅行休闲服饰；不是当地实拍或精确地标证明。 |
| kyoto | 京都主题传统街巷、古寺庭园与樱花；用户确认的合宜和服、衣领与腰带结构；不附宗教身份或徽记。 |
| xian | 西安主题城墙与唐风建筑；用户确认的汉服、自然衣褶和金色日光；服饰风格不等于用户民族或真实年代。 |
| desert | 沙漠与星空主题、远景驼队；合宜旅行服饰与自然体态；暖色面光协调夜空，不生成虚假旅行凭证。 |
| sakura | 武汉/无锡意象的湖畔樱花与现代春日穿搭；自然日光；裸樱花需求走本场景，不套京都和服。 |
| grassland | 草原、蒙古包和夏日蓝天；确认后使用蒙古风格服饰或休闲装；不推断民族，不附神圣/部族身份徽记。 |
| oldtown | 丽江/凤凰意象的古城河道、木屋与灯火；自然夜景面光和休闲服饰；招牌不出现可读文字，不做婚纱。 |


先离线验证单张PNG/JPEG≤5MiB、短边≥128、长边≤8000、总像素≤2000万，非动画、完整可解码；指出实际有问题的文件。单人/面部可辨由宿主看图与用户确认，不能声称脚本已具备人脸检测或身份绑定。宿主看不到图、遮挡或模糊时先请更清晰的本人单人照，不臆测缺失脸部、性别、真实年龄或民族。

分别确认：本人/监护许可；允许这张文件传至图片服务及算力供应商；当次按张计费执行同意。三者不能互相替代。仅在许可和传输同意齐备后设置reference_consent=true；当次明确执行后才confirmed=true。冻结源SHA、人物可见特征、场景、服饰、尺寸、张数。提交前变更任一项清除未提交键和确认；已提交/未知任务保留原键原体，不能用换图重新规划来解除锁。

## 5. 首轮十张离线示例

固定计划 `f3307dd3890af558b1ab21cfd3f1342c888a7b13:pipeline/products/mps-travel-portrait-studio/01-asset-plan-20261111.json`：harbin一次文生图生成虚构成年人，其余九图引用该公开合成图编辑；10张示例+独立logo1张，共11次上游生成上限，各key一次POST，不盲补调用。没有真实客户照片。1024×1536是请求尺寸，oldtown实际返回832×1248，其余九张实际返回1024×1536；来源逐项记录实际尺寸。统一源预览为512×768，是真实生成后的离线派生，不冒充新增上游高分辨率输出。

| key | 主题 | 入仓源文件/方式 |
|---|---|---|
| harbin | 哈尔滨冰雪主题 | demo-assets/harbin.png；虚构单人文生图 |
| yabuli | 亚布力滑雪主题 | demo-assets/yabuli.png；同一虚构单人参考编辑 |
| sanya | 三亚海岛暖冬 | demo-assets/sanya.png；同一虚构单人参考编辑 |
| santorini | 圣托里尼蓝白 | demo-assets/santorini.png；同一虚构单人参考编辑 |
| kyoto | 京都古风樱花 | demo-assets/kyoto.png；同一虚构单人参考编辑 |
| xian | 西安汉服古城 | demo-assets/xian.png；同一虚构单人参考编辑 |
| desert | 沙漠星空 | demo-assets/desert.png；同一虚构单人参考编辑 |
| sakura | 樱花季写真 | demo-assets/sakura.png；同一虚构单人参考编辑 |
| grassland | 草原蒙古包 | demo-assets/grassland.png；同一虚构单人参考编辑 |
| oldtown | 古城灯火夜景 | demo-assets/oldtown.png；同一虚构单人参考编辑 |


来源/原始及派生SHA见demo-assets/provenance.json，调用预算/远端任务去重见generation-audit.json，逐图目检见01-asset-review.json。隔离适配器只把signed_input URL替换为固定提交公开合成图，不写生产输入库、钱包或配置；不因此声称生产签名URL、真人或儿童保真通过。Claude原字节复制到assets/，demos.json只列裸文件名，数量/key/标题/SHA与规格一致。整组资源必须完整，缺任一图退出3，不把九图当完整成功；单看某项只显示该项，不伪造补齐路径。

适用首轮运行离线示例命令，不读凭证、不联网、不扣费；匿名首次对话上报是独立尽力动作。用户说「只要文字」「不要看图」时只简短文字说明，不运行示例命令；「不要生成新图片」仍可展示离线图。同一对话只展示一次，以已实际向用户展示的对话记录去重；仅加载SKILL.md、命令成功或缓存存在均不算已经展示。只看某项按对应key展示，没有对应示例如实说明、不冒充。适用时只给真实可见反馈、一个方案和两列Markdown链接表，先说「都是效果示例图，不是你的真实结果」，每项含非实拍标注；问候或仅问能力收尾问「你想从哪个方向开始？」，已有明确方向才问「这个方向可以吗？」。链接必须取命令实际绝对路径，禁把占位符原样发出、禁手拼、不用内嵌图片替代。失败只重跑同一离线命令一次，仍失败如实说明，不用付费生图补示例。

## 6. 主题logo

象牙陶瓷相机、地球玻璃镜头、飞机轨迹与冰雪/海岛色点缀；有立体光影和材质纵深，主题明确，小尺寸可辨，无字、无品牌、非平面ico。Codex用登记上游生成1张，保存02-package/dist/logo.png，512×512 PNG≤500KB；来源01-logo-provenance.json。Claude保留原字节，不脚本重画或替换，A2记录SHA。

## 7. 支付页面及后端接入

现有API基址 `https://aistore.zhaopintong.com/platform-api/gemini`；通用充值中心 `/membership/`，当前生图页 `/membership/gemini/`。API/browser的产品仍是gemini，不改成travel slug；本品来源标识才是 `mps-travel-portrait-studio`。X-Skill-Source为该slug，X-Skill-Channel及事件channel为workbuddy_skill，X-Skill-Device按真实desktop/mobile/cloud/unknown，不伪装环境。pipeline渠道名workbuddy-skill与HTTP枚举区分。

原install_secret持久生成一次，作为原账户恢复身份；原账户Bearer、Skill Bearer、网站Cookie、OAuth state/verifier分开存用。私有目录0700、文件0600，Windows限当前用户ACL；秘密不进Git、ZIP、遥测、URL、日志或对话，不让用户手填。sibling_reuse=false，不读取其他Skill私有凭据；经现有浏览器微信确认复用账户是服务端流程，不等于客户端跨Skill读秘密。

| 方法 | 相对API路径 | 鉴权/实际正文及结果 | 固定源码 |
|---|---|---|---|
| GET | /membership-api/plans | 匿名；读取当前共享套餐，不硬编码套餐档位价格 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:64 |
| GET | /balance | 原账户 Bearer；remaining_uses 已是总可用次数 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:65 |
| POST | /quick-entry | 匿名正文 {install_secret}；原安装43字符身份，状态 registration/checkout/ready | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:66–70 |
| POST | /quick-entry/status | 匿名正文 {install_secret}；registered 仅关联成功 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:71–73 |
| POST | /membership-link | 原账户 Bearer；正文 {}；使用返回的短期浏览器URL | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:74–76 |
| POST | /skill-key | 原账户 Bearer；正文 {}；仅 state=ready 且合法 key 可保存 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:77–81 |
| POST | /skill-key/bound | 原账户 Bearer；正文 {key}；bound=true 才确认绑定 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:82–83 |
| POST | /skill-jobs | Skill Bearer；Idempotency-Key；六字段正文，恰一张参考 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:84–86 |
| GET | /jobs/by-key/{key} | 原键URL编码；优先Skill Bearer，兼容原账户；404不授权重提 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:87–89 |
| GET | /jobs/{id} | 本人原任务UUID；优先Skill Bearer，兼容原账户 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:90–96 |
| GET | /jobs/{id}/image | 本人原任务；原图只读补取；完整验证PNG后交付 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/shared-image-temporary/client.py:97 |
| GET | /consumption-history | 原账户 Bearer；page/page_size；仅当前共享gemini记录 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:89–118 |
| POST | /support-tickets | 原账户 Bearer；Idempotency-Key；category/text/job_id? | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:124–162 |
| GET | /support-tickets/{id} | 原账户 Bearer；本人可查，跨账户404 | 1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:164–171 |


quick-entry registration→本次服务器签发关联URL；checkout→现有结账入口；ready只是quota分支，不含Key。quick-entry/status的registered仅原secret能解析到账户，不表示微信状态、付款或Key可用。无账户的status/auth/topup/balance/paid/history也必须给同原安装入口或如实网络错误，不能死胡同。账户可用后另POST /skill-key {}，仅state=ready且合法key才私存，再POST /skill-key/bound {key}且bound=true。pending_payment/revoked/unavailable不可生成。原客户端77–83行及固定 `c19830f7da7b9525a4ebde3bd77e1dddd2a4efe9:snapshot/opt/skill-platform/member-0.10.14/service/skill_access.py:47–87`。

充值须先征得用户允许再用原账户POST /membership-link取本次短链。校验HTTPS、第一方域名和路径、无userinfo、明确有效期；过期最多同身份重取一次，缺期限/异常不展示，不拼ticket、订单、OAuth URL。链接以服务端返回为准，可按client.py:10–15规范化旧站链接；客户端不改网关Origin/Cookie或认证白名单。

### 7.1 已部署微信第二版：身份回调与支付回调分开

以下为现有第一方网页调用的根路径，**不接gemini API前缀**；Skill不自己换微信身份、不持有微信App secret：

| 方法/根路径 | 鉴权/字段/结果 | 第二版固定源码 |
|---|---|---|
| GET /platform-api/wechat/status | 第一方浏览器Cookie；logged_in/wechat_bound；不是Skill registered | e22eeb40348468d2ba942669c0ed5fbbfb9a141c:pipeline/products/mps-family-portrait-studio/backend-patch/wechat-binding-20261111/wechat_binding.py:138–142 |
| POST /platform-api/wechat/start | 第一方Origin、X-Membership-Request:1、同源Cookie；{product:"gemini",entry,accepted:true}；或已绑定浏览器直接linked | e22eeb40348468d2ba942669c0ed5fbbfb9a141c:pipeline/products/mps-family-portrait-studio/backend-patch/wechat-binding-20261111/wechat_binding.py:144–197 |
| GET /platform-api/wechat/callback | 微信返回state/code；一次性state与双向身份冲突核验；服务端换身份，所有生图扫码端独立会话及302 | e22eeb40348468d2ba942669c0ed5fbbfb9a141c:pipeline/products/mps-family-portrait-studio/backend-patch/wechat-binding-20261111/wechat_binding.py:198–228 |
| POST /platform-api/wechat/finish | 第一方Origin与X-Membership-Request:1；{state,verifier}；pending或幂等linked/product/url | e22eeb40348468d2ba942669c0ed5fbbfb9a141c:pipeline/products/mps-family-portrait-studio/backend-patch/wechat-binding-20261111/wechat_binding.py:229–240 |


callback先核一次性state、换身份及双向账户冲突，完成原安装关联并标记used，再向每个扫码浏览器签发其独立会话，立即302 `/membership/gemini/`；电脑finish亦幂等取得独立会话并自动跳页。不要求正常扫码后先回Skill说“继续”才拿支付页；“继续”仅作为失效/错误恢复办法。网页对应 `e22eeb40348468d2ba942669c0ed5fbbfb9a141c:pipeline/products/mps-family-portrait-studio/backend-patch/wechat-binding-20261111/wechat.js:18–29,67–103`。扫码返回WorkBuddy后自动生成未获保证，仍须原任务快照、合法Key、可用余额及明确付费执行同意。

生图入口1800秒，成功start后的OAuth900秒；普通会员handoff ticket仍300秒，网站会话1800秒，不能把全部短链统一设30分钟（固定 `c19830f7da7b9525a4ebde3bd77e1dddd2a4efe9:snapshot/opt/skill-platform/member-0.10.14/core/membership.py:46–75`）。本次微信代码必须引用e22补丁，不能引用仓库snapshot/.61旧快照当第二版。部署事实单独固定 `c19830f7da7b9525a4ebde3bd77e1dddd2a4efe9:pipeline/products/mps-family-portrait-studio/01-wechat-binding-deployment-20261111.json`：已部署、两文件SHA和一次重启；22项部署字节合成与10项Node逻辑通过，另有一次未关联匿名OAuth state探针；不是生产写入始终0。真实微信交换/手机Cookie/WorkBuddy及真实支付未验，不当作旅行产品验收。

OAuth callback仅身份回调，绝不是微信商户支付到账回调。现行manual_qr：网页POST /membership-api/orders正文{plan}，report-payment正文{order_id}只登记reported；沿原Cookie、Origin及X-Membership-Request:1。原核款检查订单、产品、实收金额和唯一交易流水，在同一事务入账；同已结算流水幂等、不同订单不得复用，见固定源码core/manual_payments.py:68–94和shared_platform.py:320–354。当前无新增自动支付webhook。扫码、进入支付页、registered、截图及“付好了”都不算到账；paid只读真实订单/余额，已有余额也不证明新订单到账。

套餐始终来自当前GET plans，不列固定套餐档位价格，不自定或修改套餐。0次免费试用，一次请求一图，通用钱包共享；remaining_uses是总可用次数，不能重复相加。每图计费依原后端记录，动作授权/关联不扣费不等于整个已生成批次零扣费。成本毛利仅内部测算，不转述用户。

消费记录仅共享gemini库，不伪造按本Skill归因。工单category只用billing/image_quality/workflow/suggestion/other，text 1–2000，job_id可选但须本人；先展示用户原话并取得提交同意，不附照片、凭证、手机号等隐私。同键同体回原单，异体冲突，跨账户查单404，response_due_at=null时不承诺时限。

### 7.2 幂等与失败续接

一图一键，Idempotency-Key为16–100位[A-Za-z0-9_.:-]。首次POST前原子保存原键、原体、源SHA、主题/尺寸、三项同意及submit_unknown；持久化失败不提交。未知期间不能replan/confirm/regenerate或换键。超时、无job_id、5xx等不确定状态只GET原by-key；查询404不证明未受理，绝不重发生成POST或换键。已知job_id只查原任务和原图，已交付项不重做。

401清失效Skill凭据，通过原安装恢复，持久保存新Key、bound确认后仍只查原任务；可按原契约用原账户查，最多两次读查，持续失败退出4并保留锁。402保留原任务，经同意取充值链接，只继续明确未提交/未完成项；403/409/422/429照真实权限/冲突/拒绝/限流处理，不自行退款或放额度。未知进度说“当前进度未能确认”，费用未知以服务记录为准；不得编造原因。HTTP0说网络未连接，真实HTTP错误才按实际消息说明，不泄露字段/错误码/上游信息。

完整解码PNG并验证CRC/zlib/Adam7、非覆盖落盘后才宣布交付。下载失败/坏图留download_pending，只GET同一原图补取，不再生成。服务端可能已在任务成功时结算，不能承诺本地文件未得就没扣费，更不改生产结算。输出实际绝对路径、index.html画廊，先图后原账单与余额，标非实拍；调整若需重生成须再次确认。固定预算：提交90秒、单次查询15秒、查询窗120秒、余量30秒、计费前额外等待0，宿主外层≥240秒，各处一致。

## 8. 后端上游资产接入及成本

固定 `1d62248ea8cd9ab4f0b9d03bfe5289247c6cfd94:resources/upstreams/code-map.json/assets.public.json/catalog.json`。目录资产aisplice-universal（资源解析ID aisplice），实际模型gpt-image-2.5-ext，不能因目录有其他模型就调用。兼容引擎photo-retouch-sunburst经`.24/sunburst.py:142–185`→`.60-new-resource-only/new_only.py`→`.59-child-photo/child_resource.py:26–84`→`.57/resource_adapter.py:94–159`执行新资源；旧引擎名不是旧源调用许可，禁止回退旧供应商。policy固定enabled、aisplice、1K、n=1、legacy_fallback=false；Key只由服务端`.52/asset_registry.py`配置解析，Skill/前端不持有供应商Key或管理员权限。

| 客户端六字段 | 实际值/边界 |
|---|---|
| prompt | 已确认的单人身份约束+场景模板，1–6000字符 |
| size | 默认1024x1536；仅另支持1024x1024、1536x1024 |
| confirmed | 当次明确付费执行确认true |
| image_engine | photo-retouch-sunburst，兼容路由不是对客模型名称 |
| references | 恰一项{mime,content}；PNG/JPEG原字节base64，不收用户URL |
| reference_consent | 这张图的许可与供应商传输同意true |


不得新增model/n/quality/people_count/age/identity_ids/provider_url等传输字段，人物说明仅私有快照和prompt。原image_inputs.py:13–51校验、剥元数据、缩至≤2048并转清洁PNG，服务端加密短存；`.60`提供第一方`/platform-api/image-resource/input/shared/...`短期签名URL，约一小时，只由服务端交上游，不接受客户URL。供应商删除未核验，不宣称立即删除。

实际适配器映射三尺寸为2:3/1:1/3:2，POST `https://www.aisplice.store/v1/images/tasks`，固定model、resolution=1K、quality=auto、n=1、images=[服务端签名URL]。保存task_id/id，GET `https://www.aisplice.store/v1/images/tasks/{id}`查状态，成功后GET `https://www.aisplice.store/v1/images/tasks/{id}/content`且结果data恰一项URL，安全下载和PNG清洁导出；不向图片存储转发密钥、不多源回退。上游提交30秒、单次查询15秒；模糊POST进入needs_review，不盲重发。资源目录登记、实际代码、部署事实和真实验证分别记录。

内部成本：catalog ordinary $0.0065/图、估算FX=7，约¥0.0455/图；按当前plans最低每图收入内部估算¥0.193333，模型毛利率76.47%≥60%。11个开发资产估算$0.0715，非实际账单；不含税费、通道和人工。不把该计算当套餐报价或真实结算数据。实际供应商发票/余额未核验；Claude A2与Codex A3真实上游仍为0，只有规格内开发资产是长期授权例外。

## 9. 车道与实现状态

fast，本产品无补丁、迁移、待部署或重启。已实现依赖：共享账户/钱包/套餐/manual_qr、参考解析与新资源适配、三售后接口、八字段遥测、已部署微信第二版。待实现：Claude的真实Skill、单人及三确认门槛、私有持久状态机、资产同步、A2和ZIP。待部署：无。未验证：真人/儿童身份效果、旅行产品生产签名素材路由、真实微信及手机、真实付款/客户钱包、本产品WorkBuddy宿主、平台审核和上架。合成成人参考审阅不替代这些项目。

## 10. 首次对话与漏斗

匿名POST `/platform-api/telemetry/v1/first-dialogue`，只发八字段 `event_id,installation_id,skill_id,skill_name,skill_version,channel,client_occurred_at,is_test`，标识为规范UUIDv4，≤4096B、2秒，HTTP200且event_id/receipt匹配才原子存回执，同安装仅一次，无自动重试。开关MPS_TRAVEL_PORTRAIT_JOURNEY=off；在真实首轮/示例/无凭证早退前尽力上报，关停、只读、损坏或失败不影响主流程，不另造临时安装ID。不得含原话、图片、prompt、账户或机器指纹。原合法账户Bearer的/first-dialogue/link正文event_id/receipt/product=gemini，linked=true才确认，409不覆盖，固定.58/dialogue_store.py:9,30–65与dialogue_gateway.py:35–50。

| 漏斗 | 旅行产品对应步骤及可得性 |
|---|---|
| L0 | 真实首轮安装事件；跨技能新设备去重不可得。 |
| L1 | 打开原安装关联入口；缺关联访问证据则人数/转化不可得。 |
| L2 | 扫码关联且原安装查得原账户；新旧账户按可靠证据区分，registered不算付款。 |
| L3 | 服务器签发入口进入现有支付页；缺可靠访问证据则不可得。 |
| L4 | 第一笔已核款交易与账本去重；reported、截图、自述均不计。 |


北京时间自然日；启用、激活、充值笔数独立统计，跨日低估如实说明。机器ID/204/IP日限额/新表及完整机器漏斗是二期，本品不新增。无真实经营数据可报。

## 11. 相邻技能与不承接

| 相邻Skill | 分界 |
|---|---|
| mps-wedding-portrait-studio | 明确婚纱仪式写真才转婚纱馆；普通单人海边旅行归本品。 |
| mps-family-portrait-studio | 三人及以上家庭合影归全家福；多人/情侣旅行不自动当婚纱，本品不接。 |
| mps-id-photo-background | 证件底色和正式证件用途归证件照换底，本品不作证件结果。 |
| mps-pet-portrait-studio | 纯宠物写真归宠物馆，人物单人旅行主题归本品。 |


不接多人/情侣旅行合成、他人或名人假打卡、无许可参考、精确地标认证、正式证件、视频、纯美颜、旅游预约、打印邮寄和社交涨粉保证。只因用户说“海边”不抢婚纱馆；明确婚纱诉求才转。儿童仅监护人提供，服饰和姿态须合宜，不能用示例成人身份代替儿童。

## 12. 对话接管、授权与付费后置

SKILL.md执行说明最前为“零、接管规则”，每轮适用：旅行及本技能账户事务调用脚本，中断用resume，账户类直接处理不刷首轮；只转述真实message，不编造故障或费用；本技能出图不由宿主生图绕过，用户明确另选时才按其选择分流。未知任务重跑命令只能读查，不能因此重POST。

首轮不谈账户、套餐、金额或付费链接，不跳过价值展示直接谈钱。按第5节的只要文字/不要看图与已展示去重分支，适用时给实际可见反馈、一个主推方案、两列离线示例，确认方向后才进入方案复述和三项同意；问候/仅能力收尾不假定已有方向。当次复述主题/服饰、单人保留、画幅/张数、等待及“按张计费，以实际账单为准”。沉默、无异议、认可示例或推荐、关联完成、用户说已充值都不是当次付费同意。授权/充值步骤用编号“### 现在需要你做的”并有“打不开”恢复办法；当前授权动作没有扣费的定心话不能套在已计费批次上。拒绝开通则“好的，方案已保留，想继续时告诉我就行。”并停止链接引导。

首次实际交付后才问一次收藏（收藏/暂不），明确同意后用户级和项目级各一句领域调用偏好，包含本技能账户事务；不保存免费、已开通、永久可用、不重复收费之类承诺。暂不不再问，取消删两级，宿主无记忆工具则如实反馈，Mock不证明真实记忆生效。对客文案不泄露供应商/模型/密钥/成本/毛利/接口、内部错误码和SOP机制。

## 13. 验收清单及职责

| 编号 | 责任 | 覆盖/通过条件 |
|---|---|---|
| T01 首轮与目的地路由 | Claude A2 | 问候/仅图/能力/明确需求/不要生成；只要文字或不要看图不运行示例命令；同一对话以已实际向用户展示的记录去重，加载/成功命令/缓存不算展示；单项只展示对应key，无对应项不冒充；问候/仅能力收尾问你想从哪个方向开始，明确方向才问这个方向可以吗；十模板、目的地优先、樱花与京都、古城与西安消歧；一个主推方案和两列示例，首轮无费用链接；除独立首次遥测外零HTTP。 |
| T02 单人输入与三项确认 | Claude A2 | 一张PNG/JPEG、5MiB/边长/像素/动画/完整解码/缺图；单人本人及监护许可；多人、模糊、非本人拒绝；视觉判断不可得先询问，不假装脚本已检测人脸。换源SHA/主题/尺寸作废未提交确认，已提交仍原键续查。 |
| T03 离线示例与路径 | Claude A2 | 十图完整性、key/标题/SHA与manifest一致；缺任一资源整组退出3，不把九图报成功。单项只显示该项；不联网/不读凭证/不计费。带空格、#、%的真实合成路径必须经Markdown解析还原到存在文件，无意外query/fragment。 |
| T04 新旧账户与Key | Claude A2 | status/auth/topup/balance/paid/history六入口：无账户也能同安装quick-entry；registration/checkout/ready与registered分清；ready不含key，另调skill-key，合法state/key私存，bound=true；pending_payment/revoked/unavailable不生成。 |
| T05 计费与确认 | Claude A2 | 0试用、动态通用套餐与共享总remaining_uses；沉默/认可示例/关联完成/充值自述不算付费执行确认；一图一键，重生成再次确认；402原任务保留、成功项不重做。manual reported不当到账。 |
| T06 失败与等待 | Claude A2 | 一次成功、两轮后成功、五轮仍在处理、短断网恢复、始终不确定、明确失败；401/402/403/409/422/429/5xx分类；401恢复只查原键，404也不能重POST/换键；各处90/15/120/30/0/240超时一致。 |
| T07 PNG与交付 | Claude A2 | 完整解码含CRC/zlib/Adam7；坏图保留download_pending并仅GET原图；非覆盖写入和画廊；先图后账单/余额；尺寸异常如实披露，裁切另存；不能声称本地落盘前服务端必未结算。 |
| T08 历史与工单 | Claude A2 | 分页消费记录不伪造跨技能归因；工单类别/text长度/本人job_id、先确认用户原话；同键同体幂等/异体冲突，跨账户404，无response_due_at不承诺处理时限；不附照片、秘密或个人资料。 |
| T09 八字段遥测 | Claude A2 | 真实首轮及早退前尽力一次；8字段/HTTP200/event_id/receipt对照，2秒4096B；关闭/损坏/只读/超时不影响主流程，不新造机器ID或临时安装ID；原合法账户才link，409不覆盖。 |
| T10 平台字段与目录 | Claude A2 | 八必填字段、三对中英场景/单人/1024x1536与2:3一致；ZIP最多两级、资产裸文件名、版本/渠道一致、logo512PNG≤500KB与原SHA；禁用词及未泄露上游/成本/秘密。 |
| T11 接管与收藏 | Claude A2 | 执行说明最前接管规则；旅行及本技能账户事务调用脚本、不以宿主生图替代；授权/充值中不刷首轮；交付后一次收藏询问，明确同意才写两级简短记忆，暂不/取消、不支持写入如实反馈。 |
| T12 身份与可见AI标注 | Claude A2 | 真实用户不得套用虚构示例的28岁/女性/东亚身份；保留可见人物特征，不推断民族；模板说明/示例/成品及画廊可见“AI 生成旅行主题写真，非实地拍摄”，不烧进底图；不承诺精确地标、真人绝对保真或正式证件用途。 |
| T13 微信与支付Mock | Claude A2 | 模拟callback先完成关联、电脑关闭仍registered、手机/异浏览器302、入口/QR第6分钟、重复身份幂等；Cookie/state/verifier/支付到账分离；短链自身expires_in不统一套30分钟；普通handoff仍300秒。只Mock，不请求真实微信/生产。 |
| T14 原任务持久化回归 | Claude A2 | 先存submit_unknown再发POST；模拟进程退出、超时、5xx、首次401与查404、409、持续401，不能解除原任务锁；锁住replan/confirm/regenerate，保留原键原体。移植前先证明FAM-01/02/03类故障可被检出。 |
| T15 资源与预算边界 | Claude A2 | 素材11个来源/哈希复制一致；实际用户请求六字段，无model/n/quality/URL/people_count字段；测试全Mock、真实上游0、无旧源回退，无新增后端或未实装字段。 |
| T16 固定包独立A3检查 | Codex A3/附录D | Codex干净解压固定ZIP，核SHA/目录/YAML/双语语义/十图/logo/真实Markdown路径/支付和遥测契约/规格范围；静态独立检查，不代改Claude包或跑真实上游。 |
| T17 附录D本机验收 | Codex A3/附录D | A3后由Codex按Muse固定ZIP任务在本机WorkBuddy导入，核加载/欢迎/十示例/首轮测试图；无额外真实生图授权只做零消耗部分，不发布；能力失败如实报告、stage仍test_passed，交付gate受阻。 |


现行阶段6逐项对照（以下均为待Claude执行的验收要求，未声称测试已跑）：

| 编号/原SOP测试项 | 适用性 | 责任与处理 |
|---|---|---|
| S6-01 未关联账号 → 提示关联 → 浏览器确认后继续 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-02 正常出图并扣费，余额正确 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-03 多图套装中途余额不足 → 402 → 充值后用同一编号继续，已出的图不重复扣费 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-04 内容策略拒绝不扣费 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-05 上游 5xx 不扣费，用同一编号重试成功 | applicable_mock | Claude A2 T05/T06/T14：以原幂等键GET续查恢复成功并核扣费至多一次；5xx/未知绝不再POST，拒绝把SOP泛化重试改成重提生成。 |
| S6-06 同一编号重放不重复扣费 | applicable_mock | Claude A2 T05/T06/T14：以原幂等键GET续查恢复成功并核扣费至多一次；5xx/未知绝不再POST，拒绝把SOP泛化重试改成重提生成。 |
| S6-07 token 失效自动清除并提示重新关联 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-08 首轮脚本输出不含 `http`、套餐、充值、付费、开通账户、价格字样；欢迎句逐字一致 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-09 首轮调用零 HTTP（把请求函数换成抛异常的函数实测；首次对话上报除外，且失败不影响本轮） | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-10 示例命令不联网、不读凭证；返回的示例 key 集合与 SKILL.md 示例表、README 的个数和标题完全一致；资源缺失时退出码 3 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-11 SKILL.md 含「不得跳过价值展示直接谈钱」「两列」示例表「都是效果示例图，不是你的真实结果」「这个方向可以吗？」，不含「三个方案」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-12 SKILL.md 列明「不算同意付费执行」的情形：沉默、无异议、认可示例、认可推荐、同意授权、授权完成 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-13 授权话术含「授权本身不扣费」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-14 授权起，每一步话术都含「方案已经存好了」和「没有产生任何扣费」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-15 授权和最后一步话术都含「### 现在需要你做的」编号清单，兜底项含「打不开」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-16 话术里不出现服务端未开放的授权路径 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-17 本机已有账户且有次数 → 跳过授权和充值，直接制作 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-18 用户拒绝开通 → 只回固定一句后结束，不重发链接，方案保留 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-19 全包没有旧的慢到账口径；SKILL.md 含「不能将用户自述当作已到账」和「以服务端真实次数为准」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-20 声明的外层超时 ≥ 请求预算 + 轮询窗口 + 计费前拒绝等待上限（从脚本常量实算，不写死）；全包所有超时数值一致（测试逐处比对 SKILL.md、references、脚本注释） | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-21 开工复述齐全，内容不缺项；未明确同意付费执行的，授权或充值后先补确认再开工 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-22 任务中途余额不足 → 先问是否打开充值页，同意后才取链接；话术含「页面打开不等于已经下单」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-23 账户类说法走账户菜单，不触发第一轮 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-24 **全新环境直接运行 `topup`，输出含可点链接或如实断网说明，不是死胡同（第七章 7.2 第 3 条）** | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-25 **本机无账户时 `topup` / `balance` / `status` 调 `POST /quick-entry` 给关联链接，不直接回 `noAccount`（第七章 7.2 第 1 条）** | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-26 **失败原因不误报：断网（`GatewayError` 状态 0）说「网络没连上」，服务端错误才说「服务正在处理较多请求」；`topup` 不得一律报 `busy`（第七章 7.2 第 2 条）** | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-27 首次对话上报只含白名单字段，每个安装只发一次，关闭开关生效；开口统计按第六章第 5 节验收 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-28 首次对话上报不挂在可能走不到的分支上：首轮示例命令、无凭证预览退出这些提前返回的分支，退出前都已经发出过上报（测试逐个分支断言） | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-29 一次就出图 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-30 两轮后出图 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-31 五轮都还在处理 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-32 首轮网络抖动后恢复 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-33 全程连不上 → 说「当前进度未能确认」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-34 明确失败 → 不扣费 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-35 成功时先交图；首次交付附一次调整引导，之后不重复 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-36 失败话术按四拍；我方服务端原因只说「服务正在处理较多请求」；拿不到明确费用结论时说「费用以服务记录为准」 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-37 每次付费交付后转述服务端返回的本次扣费和剩余，余额低时追加充值提醒 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-38 交付话术说明原图没有改动；后续调整需要重新生成时先说明可能再次计费 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-39 大图分段下载，断网后续传成功 | not_applicable_current_contract | 当前源码未实现Range/inline_delivery/特定计费前重试，且sibling_reuse=false；不得新增字段或重POST。用T06/T07/T14证明原任务只读续接，列不适用及固定源码依据。 |
| S6-40 直连下载失败 → 同键同体加 `inline_delivery` 补取成功，不产生新计费；补取失败才走失败话术 | not_applicable_current_contract | 当前源码未实现Range/inline_delivery/特定计费前重试，且sibling_reuse=false；不得新增字段或重POST。用T06/T07/T14证明原任务只读续接，列不适用及固定源码依据。 |
| S6-41 计费前拒绝错误码 → 按常量等待并同键重试，单张次数和整批等待上限生效；其他 5xx 不重试 | not_applicable_current_contract | 当前源码未实现Range/inline_delivery/特定计费前重试，且sibling_reuse=false；不得新增字段或重POST。用T06/T07/T14证明原任务只读续接，列不适用及固定源码依据。 |
| S6-42 同设备账户复用（启用时）：只提交指纹；用户确认前不签发；拒绝后不再检测；关闭开关生效；失败时回到正常授权 | not_applicable_current_contract | 当前源码未实现Range/inline_delivery/特定计费前重试，且sibling_reuse=false；不得新增字段或重POST。用T06/T07/T14证明原任务只读续接，列不适用及固定源码依据。 |
| S6-43 请求体出现未登记字段时被拒绝（客户端和服务端各测一次） | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-44 凭证失效 → 自动清除、退出码 4，重发原任务走授权 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-45 **对客禁用词测试**：SKILL.md 面向用户部分、README、references 转述文案、脚本所有对客进度文案中不含禁用词清单里的词（进度文案用 AST 从脚本里取出所有字符串常量来扫） | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-46 查余额与消费记录、提交工单、查工单各走通一次 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-47 实际尺寸与请求不一致时提示并提出裁切 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-48 输出目录有 `index.html` 画廊 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-49 参考图格式报错点名具体文件 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-50 离线检查不调用后端 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-51 输出文件不覆盖 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-52 @ 技能完整走一次，交付后弹出收藏卡片；付费或购买流程中途不弹 | applicable_mock | Claude A2 T11可做脚本/流程Mock与声明检查；真实宿主记忆及不@自动选中不据Mock判通过。A3静态核对，附录D仅执行规定动作，未验事项保留未验证。 |
| S6-53 点「收藏」后，宿主记忆管理里用户级和项目级各有一条记录，内容只有调用偏好一句话 | applicable_mock | Claude A2 T11可做脚本/流程Mock与声明检查；真实宿主记忆及不@自动选中不据Mock判通过。A3静态核对，附录D仅执行规定动作，未验事项保留未验证。 |
| S6-54 选「暂不」后，本次对话不再询问 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-55 开新对话，不 @ 技能，直接问一句该领域的问题 → 出现「加载技能 <技能name>」，并按技能流程执行 | applicable_mock | Claude A2 T11可做脚本/流程Mock与声明检查；真实宿主记忆及不@自动选中不据Mock判通过。A3静态核对，附录D仅执行规定动作，未验事项保留未验证。 |
| S6-56 说「取消收藏<技能中文名>」→ 两层记忆里的记录都被删除 | applicable_mock | Claude A2：按本规格T01–T15归组逐条Mock/静态自测，逐项附证据；不调用真实生产/上游。 |
| S6-57 宿主不支持写记忆时，如实告知不支持，不假装成功 | applicable_mock | Claude A2 T11可做脚本/流程Mock与声明检查；真实宿主记忆及不@自动选中不据Mock判通过。A3静态核对，附录D仅执行规定动作，未验事项保留未验证。 |


Temu新用户免费1次为Temu专属，旅行产品0试用，不适用。旧完整真机验收豁免不取消当前附录D，A3后按Muse固定包任务执行本机导入。

Claude须在合成账户Mock覆盖当前SOP阶段6所有适用项并逐项报告；inline_delivery、Range、特定低余额字段或503快速重提等没有当前契约的项明确不适用，不杜撰接口。客户端契约、Mock后端及端到端自测齐全，真实微信/上游/生产调用0。Codex不代写客户端包，不给自己的规格降低A1门槛。

Codex A3对Claude固定ZIP独立静态检查，通过后stage=test_passed；不跑完整真实服务测试、不改Claude源码。A3之后再按附录D用本机WorkBuddy导入同SHA包验加载、欢迎、十示例和首轮；能力问题如实记录，交付gate受阻且stage仍test_passed，不能把未做写成通过。只做本机导入，不发布。最终上传由负责人手动，自动化不代上传。

## 14. 平台与打包一致性

| 场景 | examples_zh | examples_en |
|---|---|---|
| harbin | 把我的这张单人照做成哈尔滨冰雪主题写真，竖版2:3，1024×1536。 | Turn my single-person photo into a Harbin ice-and-snow portrait, portrait 2:3, 1024×1536. |
| sanya | 用我的单人照做三亚海岛暖冬写真，竖版2:3，1024×1536。 | Turn my single-person photo into a Sanya warm-winter island portrait, portrait 2:3, 1024×1536. |
| xian | 把我的单人照做成西安汉服古城写真，竖版2:3，1024×1536。 | Turn my single-person photo into a Hanfu portrait in a Xian-inspired old city, portrait 2:3, 1024×1536. |


仅3对，逐条核对目的地、服饰、单人、2:3及1024×1536，不能只数数量。根SKILL.md，scripts/references/assets下直接文件，不再嵌套第三层；示例清单只写裸文件名。来源审计和开发Mock不进上架ZIP；平台模板tests允许随包契约时也最多两级。外置logo由Claude复制保留SHA。实际交付/示例/画廊链接来自脚本本次绝对路径；字面%/空格/#仅在链接输出端编码一次，I/O仍原文件名。至少真实创建并解析Travel Demo Assets/harbin.png、Travel#Demo/harbin.png及Travel%Demo/harbin.png，解码后定位原存在文件，无意外query/fragment。

## 15. 决策记录

| 事项 | 采用 | 依据 |
|---|---|---|
| 输入 | 首版一张单人照片；本人或监护人提供，不接多人与多照合成 | brief与现有一图参考能力；无独立身份绑定接口。 |
| 模板与季节 | 保留十个全年主题；冬季优先冰雪/海岛，京都樱花与现代樱花分流 | 原选品；季节是内容策略，不是实时天气或旅行安排建议。 |
| 画幅 | 默认1K/1024x1536/2:3；仅实际支持另两种尺寸，禁止2K/4K承诺 | 固定.59/.60源码与health；“1K”是上游档位而非打印保证。 |
| 欢迎句 | 欢迎使用WorkBuddy官方认证技能 旅行打卡写真照相馆。 | 用户固定格式要求与SOP；不以句式证明已经审核通过。 |
| 计费 | 通用套餐、0次试用、不列固定套餐价格；内部成本另行测算 | SOP默认及当前plans；不改变价格或免费政策。 |
| 车道 | fast，无本产品后端补丁/部署 | 现有共享网关、参考适配与已部署微信第二版足够；不改共享认证/财务。 |
| 账号分层 | 原install_secret恢复；registered/ready都不是Key或到账；单独skill-key+bound | 固定client/registration/skill_access与微信e22；不读取其他Skill私有凭据。 |
| 微信与期限 | 扫码后各浏览器独立会话立即到支付页；入口1800秒、OAuth900秒、会员handoff300秒分开 | e22源码、c198部署记录；“继续”用于恢复，不是拿支付页前置条件。 |
| 素材 | 10张虚构成年人旅行示例+1张上游3D logo，各key一次POST，失败不盲补 | 本聊天长期授权与固定11次资产计划。 |
| 演示传输 | 隔离适配器将signed_input URL换成固定公开合成图；不写生产输入/钱包 | 只审阅合成样本，生产签名素材路由和真人保真不据此通过。 |
| 标注 | 用户可见“AI 生成旅行主题写真，非实地拍摄”贯穿模板、示例和交付 | brief明确；不在底图烧文字，不充当真实旅行证据。 |
| 协议保守 | 仅六字段；未知/401恢复/404只查原键，不引入inline_delivery、Range或快速重提 | 固定源码、FAM-01/02/03回归；不以目录登记替代适配器实装。 |
| 遥测 | 当前八字段/200，不发machine_id；缺失的新设备漏斗标不可得 | SOP现行兼容决定及.58白名单。 |
| 真实状态 | 现有能力、待Claude实现、无待部署、未验证事项分别列出 | 不把微信部署、合成示例或Mock当旅行产品真人/支付/宿主验收。 |
| 检查与交付 | Claude A2全Mock，Codex A3独立静态检查；后续附录D；负责人手动上传 | 当前SOP含附录D，不能沿用旧family规格的最终交付跳过口径。 |


## 16. A1结论与固定交接

素材和logo已就位；最终A1结果、复检修订和文档SHA以同次提交01-a1-validation.json的通过记录为准，只有其全部通过才提交spec_ready。 固定MD/JSON与源引用一致，提交后Claude按固定commit完成真实Skill、A2及打包；本单职责到规格交接，不直接继续开发/上传。不另建AI心跳，不转回旧聊天。

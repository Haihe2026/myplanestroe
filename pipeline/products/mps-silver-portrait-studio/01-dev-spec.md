# 银发写真照相馆开发规格 1.0.0

- slug：`mps-silver-portrait-studio`；渠道：WorkBuddy团队版Skill；P1、fast、0试用；本聊天Codex写规格/素材，Claude真实开发及A2，Codex独立A3，负责人手动上传。
- 固定选品来源 `bd27e5ee11774d7ca3d6671bdbc29121a6c11caa:pipeline/products/mps-silver-portrait-studio/00-brief.md`；依赖源码/证据固定 `2b2427a8270e90c683b3aadf13e5f9aaa6526c7f`，详见同提交 `01-source-verification.json`。当前SOP blob `53e9b9862e62dadd2bd5a20d6e5e5697e3beab46`、config blob `966a0d8fdd9d680d4652fa2cba8aacca174aa74e`。
- 本文状态：规格和10示例/1logo就位；A1结果以同提交01-a1-validation.json为准。不将规格完成写成Skill/部署/真实用户验收完成。

## 1. 立项、需求及词表

| 项 | 选择 |
|---|---|
| 类别及对象 | 单人银发/长辈纪念生图；希望保留自然岁月感的成年人，或经被摄本人同意代购的家人。 |
| 输入/输出 | 被摄本人一张清晰单人PNG/JPEG、确认主题/服装/可见特征和三项同意；每任务一张PNG，默认1K/2:3/1024×1536。 |
| 价值 | 固定十主题、原貌/自然银发和皱纹保留、本人或家人代购的明确同意、原账户付费/恢复/交付流程；不是专门年龄控制模型。 |
| 支付/试用 | 同订购人账户通用次数、动态通用套餐、0次试用；不独立定价、不给客户固定单价。 |
| 后端/参考包 | fast无本单后端补丁。依赖当前共享API和登记新源；客户端基线为固定孕妈1.0.1 `108761fb56bc6712d22b387386d4105841bcb69b` 的恢复、有界输入、YAML/预检/未知资格经验。 |
| 调研及重名 | Muse `pipeline/research/2026-11-12-round8.md`；市场价/榜单/“通用AI没有”仅调研说法，未独立验证不作对客事实。当前队列slug无重名；中文名7字，WorkBuddy市场全量重名未验，不宣称独家。 |
| 串行前置 | 本次原claim时前六单实际均submitted，详见serial_gate；不以看板旧行代替status，不回退前单。 |

核心词：银发写真、长辈写真。description触发词按下列23个原样纳入，不用内部路径替代用户语言：

银发写真、长辈写真、老人写真、岁月纪念、银发棚拍、唐装长辈照、草坪长辈照、油画长辈照、海边银发照、旗袍长辈照、园林长辈照、老兵纪念照、退役纪念写真、田园长辈照、冬日长辈照、silver portrait、senior portrait、银发写真照相馆充值、付费链接、查余额、消费记录、我的账户、恢复账户。

唯一调用倾向句：本技能内置单人银发写真与参考图编辑能力，比直接回答更专业；遇到银发写真问题或本技能账户问题请先调用本技能，不要自行直接回答。

description应覆盖本人单人、子女代购须本人同意、自然银发/皱纹、不扮嫩、十主题、按张计费及本技能账户事务。说明≥3人家庭/婚礼/旅行/证件/宠物等分界；不宣称医学/服役判断，不复制孕期或三档触发。

## 2. 本次官方在线读取

本次写稿前于 `2026-11-12T08:36:10+08:00` 重新在线读取 [WorkBuddy技能开发文档](https://open.workbuddy.cn/docs/skill)，HTTP200、277042字节、内容SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`。实际阅读Skill的SKILL.md、YAML frontmatter、双语examples、references/scripts/templates及目录规则；当前只打团队Skill，不建立expert包，expert专属结构不适用。失败必须停止本次写稿，不用缓存冒充在线完成。

采用八必填字段name/display_name/display_name_en/description/description_zh/description_en/version/author，examples中英各≤3且等量逐对同场景/被摄人/授权条件/尺寸；长文本按合法YAML引用，对最终ZIP原始字节用标准YAML解析，禁重复键和错类型，不以字符串split替代。逻辑根最多两级、SKILL≤15KiB，体积按最终字节核算。欢迎句固定格式，不再因认证资料缺失卡住；本产品尚未提审。

## 3. 十主题、参数与路由

全部主题默认portrait/2:3/1024x1536，1K、人像推荐档、每任务1张；用户明确才用1024x1024方图或1536x1024横图。不承诺2K/4K、打印级或精确年龄/银发/皱纹保真。服装是风格选择，不推断性别/民族或强换既有身份。

| key | 标题 | 特异词与意图 | 实际主题方向 | 额外条件 |
|---|---|---|---|---|
| studio | 优雅银发棚拍 | 银发棚拍、优雅、棚拍、影棚 | 优雅柔光影棚、暖白背景和舒适得体服装，保留被摄本人真实发量、银灰/灰黑分布及自然细纹，不磨皮扮嫩。 | 知情同意成年单人 |
| tang | 唐装中式 | 唐装、中式、新中式 | 低饱和唐装/中式立领、素雅木质背景和柔光；舒适裁剪，无婚礼/皇室/宗教身份，保留本人原貌。 | 知情同意成年单人 |
| lawn | 户外草坪阳光 | 草坪、草地、户外、阳光 | 泛化草坪与自然阳光、舒适日常服装、自然站坐姿，不安排运动挑战或作健康暗示。 | 知情同意成年单人 |
| oil | 复古油画 | 油画、复古、古典、艺术 | 复古油画质感、克制暖棕背景和侧光，保留本人可见细纹与毛发，不添加历史身份或抹平脸部特征。 | 知情同意成年单人 |
| beach | 海边度假暖阳 | 海边、海滩、度假、暖阳 | 泛化海边暖阳与舒适长辈服饰，单人纪念，不含目的地打卡/婚礼叙事或真实地标承诺。 | 知情同意成年单人 |
| qipao | 旗袍雅致 | 旗袍、雅致 | 雅致舒适旗袍、素雅影棚及自然衣褶，不用婚纱/秀禾/新娘红金造型，不以服装推断性别或民族。 | 知情同意成年单人 |
| garden | 园林雅致 | 园林、庭院、园林长辈照 | 泛化园林绿意、简洁亭廊、素雅日常服装和自然光，不加可读标牌或王室/宗教身份。 | 知情同意成年单人 |
| veteran | 军装老兵纪念 | 老兵、退役、军装纪念 | 仅按已确认退役且同意该主题的被摄本人原照制作纪念肖像，朴素无标识的历史风格外套；不复刻现役官方制服，不加军衔、勋章、番号、姓名牌、国徽军徽、武器或服役证明，不编造服役历史。 | 被摄本人已退役且明确同意该纪念造型，默认无标识 |
| rural | 田园乡村 | 田园、乡村、乡间 | 泛化田园乡村与自然暖光、舒适日常服饰，不使用贫困/衰弱刻板印象、不安排劳作挑战。 | 知情同意成年单人 |
| winter | 冬日暖阳室内 | 冬日、冬天、暖阳室内、室内、家居 | 冬日窗边暖阳、素雅室内与舒适针织外套/围巾，自然站坐姿，不出现寿宴人群或额外人物。 | 知情同意成年单人 |


优先特异主题/服饰（老兵、唐装、旗袍、油画、园林、田园、海边、草坪、冬日室内）再泛化氛围（优雅/暖阳等），逆词序也不能被泛化词抢走；同层冲突问一个主推方向，不堆方案。生日/父母节/金婚是单人送礼动机，不能仅看到这些词就分流全家福；只有多人/寿宴场景等超范围才分流。`爸妈各拍一张`拆两份单人独立任务，逐人素材/许可/确认/计费，不从一张双人照裁切冒充已获许可，不做同一任务两张。

## 4. 被摄人许可、老兵条件及三条基线

订购人和被摄人分开：本人操作，或获被摄长辈本人知情同意的家人代购，均可。原install_secret、账户、钱包和售后属于订购人，不因给父母做礼物而转移/合并账户、读长辈或其他Skill私有凭据。不得把“不是操作人本人”一概拒绝，也不开放陌生人/名人未经许可的照片。

资格只按本人自述或家人明确转述被摄本人的同意；不收姓名、生日、关系证明、身份证、军人证、健康/医学材料，不从图估年龄或服役。无必须全白发或具体岁数门槛；仍仅成年人，未知先一次合并补问，明确未成年/不同意才停止。本人对照片用途/服装和老兵造型的同意，照片发给供应商的许可，不能由送礼者“我付款了”代替。

建议私有plan状态：orderer_role=self/family_proxy/unknown、subject_adult=yes/no/unknown、subject_informed=yes/no/unknown、single/face_clear事实、features/outfit/shape；veteran主题额外subject_veteran_status=unknown/retired_confirmed/active/not_veteran及subject_veteran_theme_consent。真实HTTP仍六字段，不新增age、service_status、operator_role、people_count或任何孕期字段。

老兵条件绑定被摄本人，不是订购人：自述或子女明确转述本人已退役并同意该造型，可选veteran；“退休了”“当过兵”含义不清就补问，不自行判退役。unknown补问，active/not_veteran不做该主题、可另选普通主题；不索证明。只用无军衔、勋章、番号、姓名牌、国徽军徽、枪械或军功文字的朴素纪念服饰，不做现役身份扮演、当前官方制服复刻、服役证明或军功/历史事实重建；不以“只是示例”放宽真实用户条件。

三条基线逐条加进每个prompt：

1. 真实性和身份放第一段：只按这张被摄本人单人原照及已确认可见特征，尽力保留五官、自然年龄外观、发际线/真实发量/灰黑或银发分布、皱纹和体态；不设计新脸、不扮嫩、不强行染白/补发/加皱纹/老化，不套示例年龄、性别、发型或肤色。
2. 底图无文字、数字、可读标牌、商标、水印、军衔勋章番号或身份凭证；可见AI标注在示例说明、确认/交付和画廊文字表达，不烧进图片。
3. 仅知情同意的成年被摄人单人得体写真，允许本人操作或获本人授权的家人代购；不加儿童/他人，不作医疗或法律/服役证明。老兵主题仅被摄本人自述已退役且同意，不做现役/非老兵扮演或身份标识。


prompt五段：身份与原照特征→自然年龄/真实毛发皱纹保护→已确认主题服装场景（老兵条件生效后加无标识约束）→画幅/构图→无文字/得体与身份用途限制。示例人物70岁、女性、肤色和短银发仅合成资产设定，绝不能套真实用户；秃发不补发、灰黑发不强制漂白，不从皱纹作健康判断、不强行加皱纹老化或磨皮扮嫩。

输入单张PNG/JPEG≤5MiB、短边≥128、长边≤8000、像素≤2000万、非动画、完整有界可解码。PNG每次展开≤64KiB且≤剩余扫描行+1，无无界flush；JPEG按实际引用缓存表，≤32不同表构建/≤64扫描，普通8位Huffman基线/渐进支持，少见或过复杂提示另存不放行。未提交run以及needs_credits无job_id的resume，必须在账户/Key业务HTTP前完整验图及源SHA；确认后删除/截断→photoInvalid退出3并点名、业务HTTP0，换另一张有效图→photoChanged、清未提交确认和键、业务HTTP0。已有job_id或unknown优先原任务GET，即使本地图坏了仍不能解锁或重提。单人/脸清楚由宿主观察与用户确认，脚本不冒充人脸、年龄、服役检测。

三项独立明确同意：①被摄本人允许用这张照片作本次主题写真；②被摄本人允许这张具体文件发送给“图片服务及算力供应商”作本次处理（代购者明确转述本人许可，不能只确认自己同意）；③订购人明确同意本次按张计费执行。资格/亲属关系/自述已付款都不替代任何一项。源SHA、主题/服装/画幅、被摄人或代购授权关系变化，使未提交的确认/键失效；已提交或unknown只查原键原体，不能靠换图/换条件解锁。

## 5. 十张离线示例

固定计划 `78cbaa1efcb27d2e52392172360db82260c4f3c0:pipeline/products/mps-silver-portrait-studio/01-asset-plan-20261112.json`：1张原创虚构成年长辈studio+9张同一合成人物参考编辑，外加1logo，总11次上限，每key最多一次生成POST。均非客户照片；老兵示例仅虚构纪念设定，不证明真实服役，也不代表不同性别/年龄/发量真人效果均已验证。

| key | 主题 | 文件 |
|---|---|---|
| studio | 优雅银发棚拍 | demo-assets/studio.png |
| tang | 唐装中式 | demo-assets/tang.png |
| lawn | 户外草坪阳光 | demo-assets/lawn.png |
| oil | 复古油画 | demo-assets/oil.png |
| beach | 海边度假暖阳 | demo-assets/beach.png |
| qipao | 旗袍雅致 | demo-assets/qipao.png |
| garden | 园林雅致 | demo-assets/garden.png |
| veteran | 军装老兵纪念 | demo-assets/veteran.png |
| rural | 田园乡村 | demo-assets/rural.png |
| winter | 冬日暖阳室内 | demo-assets/winter.png |


10图已实际生成并逐图审阅，512×768预览，来源/实际尺寸/处理/SHA见同提交provenance与audit。 客户端assets原字节复制，demos.json只裸文件名、key/标题一致；不要再缩放/换图/生成。单项只出指定key；缺一图时整组退出3不输出部分成功、不收费补图。路径用已审Markdown安全格式，空格/#/%须CommonMark实测定位。

每张示例、确认、交付、结果一览页可见文字标注「AI 生成银发写真，非实拍」，示例说明“人物为虚构成年人，不是你的真实结果”；图中不烧字。首轮先说明示例再用两列链接表，每格标题链接加note，不用![]内嵌，不拿其他图冒充缺失项。同对话只显示一次，以实际发给用户为准，不以加载/命令成功/缓存算展示；“只要文字/不要看图”跳demo，“不要生成新图片”仍可看离线例图。无图/失败重试一次，仍失败如实说，不付费补图。

## 6. 立体主题logo

Codex用登记上游生成每技能1张，方向为象牙陶瓷银发长辈侧脸、银色镜头圆框、青绿暖白立体质感，无字无品牌，无医疗或军徽符号。PNG512×512、≤500000B，存`02-package/dist/logo.png`，外置不放ZIP；来源/审计/实际SHA见01-logo-provenance.json。已实际生成并审阅，Claude保持原字节，不重画不替换。

## 7. 支付页面及后端接入

现有API基址 `https://aistore.zhaopintong.com/platform-api/gemini`；通用充值中心 `/membership/`，当前生图页 `/membership/gemini/`。API/browser的产品仍是gemini，不改成silver slug；本品来源标识才是 `mps-silver-portrait-studio`。X-Skill-Source为该slug，X-Skill-Channel及事件channel为workbuddy_skill，X-Skill-Device按真实desktop/mobile/cloud/unknown，不伪装环境。pipeline渠道名workbuddy-skill与HTTP枚举区分。

原install_secret持久生成一次，作为原账户恢复身份；原账户Bearer、Skill Bearer、网站Cookie、OAuth state/verifier分开存用。私有目录0700、文件0600，Windows限当前用户ACL；秘密不进Git、ZIP、遥测、URL、日志或对话，不让用户手填。sibling_reuse=false，不读取其他Skill私有凭据；经现有浏览器微信确认复用账户是服务端流程，不等于客户端跨Skill读秘密。

| 方法 | 相对API路径 | 鉴权/实际正文及结果 | 固定源码 |
|---|---|---|---|
| GET | /membership-api/plans | 匿名；读取当前共享套餐，不硬编码套餐档位价格 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:64 |
| GET | /balance | 原账户 Bearer；remaining_uses 已是总可用次数 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:65 |
| POST | /quick-entry | 匿名正文 {install_secret}；原安装43字符身份，状态 registration/checkout/ready | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:66–70 |
| POST | /quick-entry/status | 匿名正文 {install_secret}；registered 仅关联成功 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:71–73 |
| POST | /membership-link | 原账户 Bearer；正文 {}；使用返回的短期浏览器URL | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:74–76 |
| POST | /skill-key | 原账户 Bearer；正文 {}；仅 state=ready 且合法 key 可保存 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:77–81 |
| POST | /skill-key/bound | 原账户 Bearer；正文 {key}；bound=true 才确认绑定 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:82–83 |
| POST | /skill-jobs | Skill Bearer；Idempotency-Key；六字段正文，恰一张参考 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:84–86 |
| GET | /jobs/by-key/{key} | 原键URL编码；优先Skill Bearer，兼容原账户；404不授权重提 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:87–89 |
| GET | /jobs/{id} | 本人原任务UUID；优先Skill Bearer，兼容原账户 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:90–96 |
| GET | /jobs/{id}/image | 本人原任务；原图只读补取；完整验证PNG后交付 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/shared-image-temporary/client.py:97 |
| GET | /consumption-history | 原账户 Bearer；page/page_size；仅当前共享gemini记录 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:89–118 |
| POST | /support-tickets | 原账户 Bearer；Idempotency-Key；category/text/job_id? | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:124–162 |
| GET | /support-tickets/{id} | 原账户 Bearer；本人可查，跨账户404 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:pipeline/products/mps-id-photo-background/backend-patch/gemini-support-20261107/gemini_support.py:164–171 |


quick-entry registration→本次服务器签发关联URL；checkout→现有结账入口；ready只是quota分支，不含Key。quick-entry/status的registered仅原secret能解析到账户，不表示微信状态、付款或Key可用。无账户的status/auth/topup/balance/paid/history也必须给同原安装入口或如实网络错误，不能死胡同。账户可用后另POST /skill-key {}，仅state=ready且合法key才私存，再POST /skill-key/bound {key}且bound=true。pending_payment/revoked/unavailable不可生成。原客户端77–83行及固定 `c19830f7da7b9525a4ebde3bd77e1dddd2a4efe9:snapshot/opt/skill-platform/member-0.10.14/service/skill_access.py:47–87`。

充值须先征得用户允许再用原账户POST /membership-link取本次短链。校验HTTPS、第一方域名和路径、无userinfo、明确有效期；过期最多同身份重取一次，缺期限/异常不展示，不拼ticket、订单、OAuth URL。链接以服务端返回为准，可按client.py:10–15规范化旧站链接；客户端不改网关Origin/Cookie或认证白名单。


### 7.1 当前微信入口、身份回调与支付分层

当前源码固定 `2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py`、`2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_entries.py`，网页固定 `2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/var/www/image-assistant/auth/wechat/automatic-qr-20261111.js`；e22补丁与c198报告仅是较早历史，不能再写“当前snapshot/.61仍旧版”。

| 方法/浏览器根路径 | 鉴权和字段 | 响应与边界 | 当前源码 |
|---|---|---|---|
| GET /platform-api/wechat/status | 第一方浏览器Cookie；仅查询网页身份，不等于Skill registered | logged_in/wechat_bound | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:168–171 |
| POST /platform-api/wechat/start | 第一方Origin、X-Membership-Request:1、同源Cookie；{product:gemini,entry,accepted:true}；当前网页另带force_scan:true | {state,verifier,url,expires_in}；或已验证复用分支{status:linked,product,url} | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:184–238 |
| GET /platform-api/wechat/callback | 微信state/code，一次性state及服务端身份交换、双向账户冲突核验 | 生图扫码端完成关联、独立Cookie会话及302到/membership/gemini/；过期/冲突如实错误 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:239–266 |
| POST /platform-api/wechat/finish | 第一方Origin、X-Membership-Request:1；{state,verifier}；服务器校验证明 | pending或幂等linked/product/url；电脑会话独立 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:270–281 |


这些是根路径，不接gemini API前缀；实际身份状态、回调字段与行为按固定源码。Skill不持微信App secret、不拼OAuth URL，不复制浏览器Cookie，不改Origin/认证白名单。产品仍gemini，来源才是本slug。

`.61/wechat_entries.py:28–47`的AESGCM缓存保存入口，可恢复仍在保留范围内的入口/重启状态；缓存保留在原期限后多1800秒，不能把它当对客链接有效期。原入口1800秒、OAuth900秒，普通会员handoff300秒、网站会话1800秒分别处理；对客以本次响应expires_in为准。`automatic-qr-20261111.js:136–157,175–195`在勾选同意后自动出码，当前强制扫码分支会用force_scan:true、最多300秒刷新二维码，不承诺所有已登录浏览器免重扫。

有效原安装入口才可关联回原Skill身份。安装入口在缓存层部署前已遗失/本机凭据缺失时，网站微信登录或付费成功不等于恢复原install_secret；不能把网站兜底账户冒充原安装，须从本Skill有效原身份重开入口，或按真实服务路径说明；不读取别技能私有凭据、不新建钱包掩盖问题，不说“扫码即已到账/即可自动生成”。

公开部署记录 `2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:infrastructure/wechat-checkout-20261111.public.json`声明入口恢复/支付页连续性已部署，14后端+44结账+10UI合成检查，公开页/health HTTP200；真实OAuth交换、真实付款和上游测试均0，所有宿主/手机/银行核款未验。此为既有部署证据，本产品无新部署，也不把它当银发宿主/支付验收。OAuth是身份回调，绝非商户支付到账webhook。

### 7.1.1 网页订单、报付款与既有核款闭环

以下订单路径接API基址，不是微信根路径。第一方网页platform_member Cookie；POST带X-Membership-Request:1及浏览器真实Origin https://aistore.zhaopintong.com；Skill不拼Cookie/Origin，不改白名单。 原共享源码`2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:320–336`的规范Origin值是https://myplanestore.com；当前映射有精确源码：`2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py:10,160–163：非微信根路由中精确把现站Origin映射为旧规范后委派父Handler；run_shared.py:6–11安装包装层。已实现及既有部署声明，不等于本产品真实订单实测。` Skill不伪造Origin或绕过站点认证，本产品带Cookie真实订单流程未验。

| 方法/网页路径 | 请求正文 | 含义 | 固定源码 |
|---|---|---|---|
| POST /membership-api/orders | {plan} | 创建本人既有套餐订单，产品gemini映射gemini-image-assistant；未付款不入账 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:343–344 |
| POST /membership-api/report-payment | {order_id} | 只将本人pending订单登记为reported，不增加余额，不代表到账 | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:347–348 |
| GET /membership-api/orders/{order_id} | 无正文 | 本人订单真实状态，跨账户不能读取；不以自述/截图判paid | 2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py:349–350 |


`2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:snapshot/opt/skill-platform/member-0.10.14/core/manual_payments.py:68–95`的既有`confirm_manual(oid, amount_fen, transaction_id)`核验订单存在、产品gemini-image-assistant、实收金额完全匹配和唯一交易流水，BEGIN IMMEDIATE同一事务更新paid、权益、钱包与账本；同已付订单/同流水/manual_qr幂等返回False不重复入账，不同订单复用流水、已付单换流水或非法状态冲突拒绝。它是受控后台既有核款能力，不是Skill调用权限。本产品不调用核款/发放/退款，不新增支付webhook，不改价格/余额/套餐/财务库。

报付款只登记reported，扫码、registered、网页跳转、截图或“我付好了”均不是到账；paid及余额只读真实服务响应，已有余额也不能证明新订单付款。失效/拒绝/断网保留原需求，允许用户之后核对，不编造即时核款结果。


### 7.2 幂等与失败续接

一图一键，Idempotency-Key为16–100位[A-Za-z0-9_.:-]。首次POST前原子保存原键、原体、源SHA、主题/尺寸、三项同意及submit_unknown；持久化失败不提交。未知期间不能replan/confirm/regenerate或换键。超时、无job_id、5xx等不确定状态只GET原by-key；查询404不证明未受理，绝不重发生成POST或换键。已知job_id只查原任务和原图，已交付项不重做。

401清失效Skill凭据，通过原安装恢复，持久保存新Key、bound确认后仍只查原任务；可按原契约用原账户查，最多两次读查，持续失败退出4并保留锁。402保留原任务，经同意取充值链接，只继续明确未提交/未完成项；403/409/422/429照真实权限/冲突/拒绝/限流处理，不自行退款或放额度。未知进度说“当前进度未能确认”，费用未知以服务记录为准；不得编造原因。HTTP0说网络未连接，真实HTTP错误才按实际消息说明，不泄露字段/错误码/上游信息。

完整解码PNG并验证CRC/zlib/Adam7、非覆盖落盘后才宣布交付。下载失败/坏图留download_pending，只GET同一原图补取，不再生成。服务端可能已在任务成功时结算，不能承诺本地文件未得就没扣费，更不改生产结算。输出实际绝对路径、index.html画廊，先图后原账单与余额，标非实拍；调整若需重生成须再次确认。固定预算：提交90秒、单次查询15秒、查询窗120秒、余量30秒、计费前额外等待0，宿主外层≥240秒，各处一致。


补充绑定401闭环：合法Key私存为未绑定，只有bound is True才新生成。绑定401清失效Key和绑定标记，保留原install_secret/任务，退出4/task_kept；下次原身份领新Key再确认，不永久重复旧Key。已发出任务仍原键GET，不解除锁。固定基座 `847b19d5b87d57d3bce6d0f3aa61ac9130de9748:pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py:524–754`。



## 8. 后端上游资产接入及成本

固定 `2b2427a8270e90c683b3aadf13e5f9aaa6526c7f:resources/upstreams/code-map.json/assets.public.json/catalog.json`。目录资产aisplice-universal（资源解析ID aisplice），实际模型gpt-image-2.5-ext，不能因目录有其他模型就调用。兼容引擎photo-retouch-sunburst经`.24/sunburst.py:142–185`→`.60-new-resource-only/new_only.py`→`.59-child-photo/child_resource.py:26–84`→`.57/resource_adapter.py:94–159`执行新资源；旧引擎名不是旧源调用许可，禁止回退旧供应商。policy固定enabled、aisplice、1K、n=1、legacy_fallback=false；Key只由服务端`.52/asset_registry.py`配置解析，Skill/前端不持有供应商Key或管理员权限。

| 客户端六字段 | 实际值/边界 |
|---|---|
| prompt | 已确认的本人单人身份约束+已确认长辈本人特征+主题/服饰，1–6000字符 |
| size | 默认1024x1536；仅另支持1024x1024、1536x1024 |
| confirmed | 当次明确付费执行确认true |
| image_engine | photo-retouch-sunburst，兼容路由不是对客模型名称 |
| references | 恰一项{mime,content}；PNG/JPEG原字节base64，不收用户URL |
| reference_consent | 这张图的许可与供应商传输同意true |


不得新增model/n/quality/people_count/age/identity_ids/provider_url等传输字段，人物说明仅私有快照和prompt。原image_inputs.py:13–51校验、剥元数据、缩至≤2048并转清洁PNG，服务端加密短存；`.60`提供第一方`/platform-api/image-resource/input/shared/...`短期签名URL，约一小时，只由服务端交上游，不接受客户URL。供应商删除未核验，不宣称立即删除。

实际适配器映射三尺寸为2:3/1:1/3:2，POST `https://www.aisplice.store/v1/images/tasks`，固定model、resolution=1K、quality=auto、n=1、images=[服务端签名URL]。保存task_id/id，GET `https://www.aisplice.store/v1/images/tasks/{id}`查状态，成功后GET `https://www.aisplice.store/v1/images/tasks/{id}/content`且结果data恰一项URL，安全下载和PNG清洁导出；不向图片存储转发密钥、不多源回退。上游提交30秒、单次查询15秒；模糊POST进入needs_review，不盲重发。资源目录登记、实际代码、部署事实和真实验证分别记录。

内部成本：固定目录ordinary $0.0065/次×FX=7，约¥0.0455/次；本次匿名plans最低收入¥0.193333/张，估算模型毛利76.47%≥60%。11资产估算$0.0715，不含税费/通道/人工，实际账单未核；不作客户固定报价。A2/A3真实上游0，开发示例及1logo为本聊天长期授权例外。


自然银发/皱纹与老兵主题约束仅通过已确认的提示词和私有状态表达，不等于目录/适配器提供年龄识别、服役认证或专项外观控制参数；实际参考图始终是经被摄本人独立同意的一张文件。



## 9. 车道及真实状态

fast，无本单后端补丁、数据库迁移、生产配置改动、重启或待部署。既有实现：固定共享账户/钱包/动态套餐/manual_qr、参考解析和新源适配、三售后、8字段及link、当前微信入口恢复/auto-QR。新网页trade-leads统计脚本不是gemini/银发遥测权限，不继承新字段。

待Claude实现：真实银发Skill、本人/代购及被摄本人许可、老兵主题条件、自然年龄/毛发提示词、素材同步、原任务状态机、隔离A2和打包。未验证：真人银发皱纹保真/专项年龄控制、不同性别/发量效果、真实服役史、生产签名参考链路、本产品微信/手机/付款、宿主记忆/不@触发、平台接受/审核/上架。示例、Mock、既有公开部署记录都不替代这些验证。

## 10. 首次对话与漏斗

POST `/platform-api/telemetry/v1/first-dialogue` 仅八字段 `event_id,installation_id,skill_id,skill_name,skill_version,channel,client_occurred_at,is_test`，UUIDv4、≤4096B、2秒、HTTP200合法event_id/receipt才存成功。发送前原子保存attempted并回读，写不进就不发；每安装仅尝试一次，失败即弃，嵌套resume→run/重启不重报。开关`MPS_SILVER_PORTRAIT_JOURNEY=off`，关闭/只读/损坏不阻业务、不造临时ID。不能含原话/照片/prompt/年龄/亲属/服役/健康信息。

原合法订购人Bearer的 `/first-dialogue/link` 仅event_id/receipt/product=gemini，linked=true才确认，409不覆盖；canonical event_id按协议保存，不因与本地不同误判。固定.58/dialogue_store.py和dialogue_gateway.py及本次来源参考实现；新trade页统计与本Skill无关。

| 漏斗 | 步骤与真实可得性 |
|---|---|
| L0 | 首次匿名尝试/合法成功回执；跨技能新设备去重不可得。 |
| L1 | 订购人打开原安装入口；缺访问证据则人数/转化不可得。 |
| L2 | 原安装查到关联原账户；registered不等于付款。 |
| L3 | 本次签发充值页；缺访问证据不可得。 |
| L4 | 已核款交易及账本去重；reported/截图/自述不算。 |

按北京时间日区分激活/开通/充值与跨日偏差。machine_id/204/IP日限额/完整机器漏斗为未来能力，不为本品新增；没有真实经营数据可报。

## 11. 相邻能力及不承接

| 相邻Skill | 分界 |
|---|---|
| mps-family-portrait-studio | ≥3人的家庭合影或寿宴多人场景才转；两人能力未核，不谎称可做。单人生日/金婚礼物仍本品。 |
| mps-wedding-portrait-studio | 婚礼仪式/婚纱造型才转；本品唐装旗袍为长辈单人纪念。 |
| mps-travel-portrait-studio | 目的地打卡归旅行；本品泛化海边单人岁月纪念。 |
| mps-maternity-portrait-studio | 本人孕期纪念写真归孕妈，不混入本品身份/提示词。 |
| mps-id-photo-background | 正式证件换底归证件照，本品非证件/法律证明。 |
| mps-pet-portrait-studio | 纯宠物归宠物馆，本品不加入宠物/儿童/他人。 |


不接未获被摄本人知情同意/名人照片、未成年人、多人/儿童入镜、换脸、强行返老还童或假老化、医疗/健康/年龄诊断、证件/法律/服役证明、军功叙事、现役/非老兵身份扮演或官方标识、视频/打印邮寄/线下预约/涨粉保证。两人照本品不支持，也不谎称只支持≥3人的全家福能处理。单人生日/父母节/金婚礼物仍可做；“爸妈各拍”须分别获许可、独立任务确认计费，不能自动拆成收费批次。

## 12. 接管、确认及交付话术

SKILL执行规范首节“零、接管规则”，每轮适用；银发写真及本技能账户事务先运行脚本，不凭记忆编造账户/链接/失败原因，不用宿主生图绕过；用户明确另选才分流。未知任务只resume，不能把原需求重新生成。仅转述真实message，不暴露供应商品牌/模型/成本/密钥/内部错误码；“图片服务及算力供应商”是传输许可必要接收方类别。

首轮欢迎句逐字「欢迎使用WorkBuddy官方认证技能 银发写真照相馆。」；有图就只说真实可见优点，不评价身材/推断年龄健康，不假装看过图。一个主推方向+两列离线例图，不先谈账户/套餐/价格/链接。缺事实一次合并问：订购人本人或家人代购、被摄人是否成年及知情同意、这张清晰单人照/主题服装/画幅/可见特征；老兵主题再合并问被摄本人是否已退役及是否同意该造型。unknown先补询，明确不同意/不适用才按真实原因处理；不索证明。原照特征未确认不自行编人口属性。

方向确认后复述主题/服装/画幅/张数/等待与按张计费、本人照片许可、本人允许具体文件传给图片服务及算力供应商、订购人计费三项，明确肯定答复后才confirm/run。沉默/认可示例/授权完成/已付款不当新的计费执行同意。

账户/充值步骤用“### 现在需要你做的”编号、真实本次链接和打不开兜底；没有手机号输入或凭证恢复能力不编造。没开始的方案已存、不扣费定心话不套已交付批次；拒绝用“没问题。等你需要图片的时候随时叫我。”并停止链接轰炸、保留方案。余额只转述remaining_uses，不自行相加；付款登记不等于到账，运行paid/续查后按真实服务次数才继续，不新增核款权或退款承诺。一次只改一项，重生成必须另说明计费并确认。

首次成功交付后才问一次收藏（收藏/暂不），明确同意才写用户级和项目级一句领域调用偏好；不存年龄/被摄人/家属/服役/健康或费用信息。取消删两级，无工具/写失败如实说明；Mock不当宿主记忆通过。交付先给真实图再报服务端charged/balance；画廊也保留AI非实拍标识。

## 13. 验收与角色分工

| 编号 | 领域 | 负责 | 验收 |
|---|---|---|---|
| T01 | 首轮与十主题路由 | claude | 问候/只图/明确需求，23触发词；特异服饰/老兵词优先泛化词，银发单人生日/金婚送礼不误分流；只文字/不要看图跳demo，同对话以实际展示去重；除匿名首次上报无HTTP。 |
| T02 | 本人/家人代购及资格 | claude | 本人/家人代购两路径；成年/授权角色/被摄人知情同意未知合并补问，不当不符合；明确拒绝停止、不索证明。三项同意分别来自被摄人照片许可、被摄人同意这张文件传给图片服务及算力供应商、订购人当次计费同意；付款不能代替传输许可。 |
| T03 | 十示例与安全路径 | claude | 十图SHA/key/标题一致，缺一整组退出3，单项只该项；demo纯离线无凭据；真实空格/#/%合成路径经CommonMark定位原PNG，无query/fragment。 |
| T04 | 原身份及绑定恢复 | claude | 账户类无账户重取原安装入口，注册/余额/Key分层，bound is True才新生成；绑定401清Skill Key和标记，保留install_secret和原草稿，退出4/task_kept，下次原身份领新Key再绑定；未知/已提交只GET。 |
| T05 | 零试用和真实计费 | claude | 0试用、动态plans、remaining_uses总额不相加，认可示例/授权/充值不等于当次执行同意；一图一键，调整重生成另确认；reported和用户自述不算到账，不承诺赠额/退款；代购不转移/合并钱包。 |
| T06 | 失败等待与未知 | claude | 六等待时序、401/402/403/409/422/429/5xx分类，超时/未知/404不重新POST；原键GET续查可至多扣一次；预算90/15/120/30/0/240。 |
| T07 | 完整有界输入/交付 | claude | PNG/JPEG5MiB/128–8000/2000万像素完整有界；PNG每次≤64KiB及剩余+1，无无界flush；JPEG按引用缓存≤32不同表构建/≤64扫描。未提交run及needs_credits resume：确认后删/截断图→本地退出3并点名、业务HTTP0；换有效图→photoChanged/清确认键，业务HTTP0。已提交/unknown图坏仍只GET；输出缺失/损坏保留原任务GET补取；完整有效PNG仅尺寸偏差应交原图并如实提示，用户明确才本地裁切另存，不留下载待定或重复GET/生成POST，不再收费。 |
| T08 | 消费记录及售后 | claude | 消费记录分页/next_page，不自算；feedback先转述确认，不能附照片/年龄/服役/健康/隐私，提交结果未知先查询，查本人ticket；跨账户不能读取，Mock即可，不新增售后/财务权限。 |
| T09 | 首次上报一次 | claude | 八字段、2秒、4096B、200合法回执；发前持久化attempted并回读，失败不重报，嵌套resume→run和重启不重复；只读/关闭/损坏不阻业务，无临时ID；不发原话、照片、年龄/服役/家属信息。 |
| T10 | 真实YAML及元数据 | claude | 对最终ZIP原始SKILL frontmatter用标准YAML解析，禁重复键/错误类型；含冒号空格长描述引用正例及未引用反例；八必填、examples中英各≤3且逐对同主题/本人或代购/老兵条件/画幅像素；版本/渠道一致、两级目录、SKILL≤15KiB。 |
| T11 | 接管与收藏 | claude | 执行规范首节接管、账户类不刷首轮、不给宿主生图绕过；首次成功交付后问收藏，同意才写用户/项目偏好，无工具/失败不伪造；不存年龄/家属/服役信息，真实宿主未验。 |
| T12 | 自然年龄与发量 | claude | 秃发不补发、灰黑发不强制银白、不磨皮扮嫩或加皱纹；主题服装不推断性别/民族；prompt不套合成70岁女性样貌。三基线、五段结构及每主题可达，示例/交付/画廊均有AI非实拍说明。 |
| T13 | 被摄人老兵条件 | claude | 仅veteran需要被摄人retired_confirmed及明确主题同意；本人自述或家人转述被摄本人明确自述可；unknown一次补问、含义不明不推断，active/not_veteran不做该主题但可另选普通主题；不索证明，不加军衔勋章番号武器凭证、不伪造服役历史。 |
| T14 | 冻结和多人分界 | claude | 换图/主题/服装/画幅/授权关系使未提交确认和键失效；未知/已提交/下载待取锁不因换图/资格改动解锁；爸妈各拍拆两份单人独立确认/计费，三人家庭转全家福，双人不谎称支持；单人送礼动机仍承接。 |
| T15 | 资源与支付Mock | claude | 六字段一参考、1K/n1/三尺寸、登记新源/无旧回退，客户端无上游密钥；微信入口/动态plans/订单reported非到账/受控核款幂等由固定源码及客户端Mock核验；真实支付/上游0。 |
| T16 | Codex A3 | codex | 干净固定ZIP独立静态检查；MAT01/02/03和前序恢复/有界经验复核，非完整A2/宿主实测。 |
| T17 | 负责人手动上传 | owner | A3通过交固定ZIP/外置logo/SHA；附录D和D.6已暂停，不派安装检测，不自动发布。 |


Claude A2只用合成账户、Mock和隔离目录，真实上游/生产/付款调用0；Windows不伪造POSIX权限通过，Linux隔离补真实权限断言。按新旧包可区分的正反例验证，不以镜像实现/只数文案字符串代替真实YAML/请求计数/任务锁断言。Codex A3按当前SOP独立静态检查，不修改包或重跑完整A2；缺陷退Claude，不给自己规格放水。

阶段6逐项对照共57项：

| 编号 | 原要求 | 适用性/本品处置 |
|---|---|---|
| S6-01 | 未关联账号 → 提示关联 → 浏览器确认后继续 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-02 | 正常出图并扣费，余额正确 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-03 | 多图套装中途余额不足 → 402 → 充值后用同一编号继续，已出的图不重复扣费 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-04 | 内容策略拒绝不扣费 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-05 | 上游 5xx 不扣费，用同一编号重试成功 | applicable_mock；Claude T05/T06/T14以原键GET续查恢复成功，扣费至多一次；未知/5xx不再生成POST。 |
| S6-06 | 同一编号重放不重复扣费 | applicable_mock；Claude T05/T06/T14以原键GET续查恢复成功，扣费至多一次；未知/5xx不再生成POST。 |
| S6-07 | token 失效自动清除并提示重新关联 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-08 | 首轮脚本输出不含 `http`、套餐、充值、付费、开通账户、价格字样；欢迎句逐字一致 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-09 | 首轮调用零 HTTP（把请求函数换成抛异常的函数实测；首次对话上报除外，且失败不影响本轮） | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-10 | 示例命令不联网、不读凭证；返回的示例 key 集合与 SKILL.md 示例表、README 的个数和标题完全一致；资源缺失时退出码 3 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-11 | SKILL.md 含「不得跳过价值展示直接谈钱」「两列」示例表「都是效果示例图，不是你的真实结果」「这个方向可以吗？」，不含「三个方案」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-12 | SKILL.md 列明「不算同意付费执行」的情形：沉默、无异议、认可示例、认可推荐、同意授权、授权完成 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-13 | 授权话术含「授权本身不扣费」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-14 | 授权起，每一步话术都含「方案已经存好了」和「没有产生任何扣费」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-15 | 授权和最后一步话术都含「### 现在需要你做的」编号清单，兜底项含「打不开」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-16 | 话术里不出现服务端未开放的授权路径 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-17 | 本机已有账户且有次数 → 跳过授权和充值，直接制作 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-18 | 用户拒绝开通 → 只回固定一句后结束，不重发链接，方案保留 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-19 | 全包没有旧的慢到账口径；SKILL.md 含「不能将用户自述当作已到账」和「以服务端真实次数为准」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-20 | 声明的外层超时 ≥ 请求预算 + 轮询窗口 + 计费前拒绝等待上限（从脚本常量实算，不写死）；全包所有超时数值一致（测试逐处比对 SKILL.md、references、脚本注释） | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-21 | 开工复述齐全，内容不缺项；未明确同意付费执行的，授权或充值后先补确认再开工 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-22 | 任务中途余额不足 → 先问是否打开充值页，同意后才取链接；话术含「页面打开不等于已经下单」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-23 | 账户类说法走账户菜单，不触发第一轮 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-24 | **全新环境直接运行 `topup`，输出含可点链接或如实断网说明，不是死胡同（第七章 7.2 第 3 条）** | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-25 | **本机无账户时 `topup` / `balance` / `status` 调 `POST /quick-entry` 给关联链接，不直接回 `noAccount`（第七章 7.2 第 1 条）** | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-26 | **失败原因不误报：断网（`GatewayError` 状态 0）说「网络没连上」，服务端错误才说「服务正在处理较多请求」；`topup` 不得一律报 `busy`（第七章 7.2 第 2 条）** | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-27 | 首次对话上报只含白名单字段，每个安装只发一次，关闭开关生效；开口统计按第六章第 5 节验收 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-28 | 首次对话上报不挂在可能走不到的分支上：首轮示例命令、无凭证预览退出这些提前返回的分支，退出前都已经发出过上报（测试逐个分支断言） | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-29 | 一次就出图 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-30 | 两轮后出图 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-31 | 五轮都还在处理 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-32 | 首轮网络抖动后恢复 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-33 | 全程连不上 → 说「当前进度未能确认」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-34 | 明确失败 → 不扣费 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-35 | 成功时先交图；首次交付附一次调整引导，之后不重复 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-36 | 失败话术按四拍；我方服务端原因只说「服务正在处理较多请求」；拿不到明确费用结论时说「费用以服务记录为准」 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-37 | 每次付费交付后转述服务端返回的本次扣费和剩余，余额低时追加充值提醒 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-38 | 交付话术说明原图没有改动；后续调整需要重新生成时先说明可能再次计费 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-39 | 大图分段下载，断网后续传成功 | not_applicable_current_contract；当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-40 | 直连下载失败 → 同键同体加 `inline_delivery` 补取成功，不产生新计费；补取失败才走失败话术 | not_applicable_current_contract；当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-41 | 计费前拒绝错误码 → 按常量等待并同键重试，单张次数和整批等待上限生效；其他 5xx 不重试 | not_applicable_current_contract；当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-42 | 同设备账户复用（启用时）：只提交指纹；用户确认前不签发；拒绝后不再检测；关闭开关生效；失败时回到正常授权 | not_applicable_current_contract；当前无Range/inline_delivery/计费前重试字段，sibling_reuse=false；不能新增协议或重POST，按T06/T07/T14证明原任务只读并列源码依据。 |
| S6-43 | 请求体出现未登记字段时被拒绝（客户端和服务端各测一次） | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-44 | 凭证失效 → 自动清除、退出码 4，重发原任务走授权 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-45 | **对客禁用词测试**：SKILL.md 面向用户部分、README、references 转述文案、脚本所有对客进度文案中不含禁用词清单里的词（进度文案用 AST 从脚本里取出所有字符串常量来扫） | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-46 | 查余额与消费记录、提交工单、查工单各走通一次 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-47 | 实际尺寸与请求不一致时提示并提出裁切 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-48 | 输出目录有 `index.html` 画廊 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-49 | 参考图格式报错点名具体文件 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-50 | 离线检查不调用后端 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-51 | 输出文件不覆盖 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-52 | @ 技能完整走一次，交付后弹出收藏卡片；付费或购买流程中途不弹 | applicable_mock；Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态，宿主由负责人实测，附录D已暂停，未验仍未验。 |
| S6-53 | 点「收藏」后，宿主记忆管理里用户级和项目级各有一条记录，内容只有调用偏好一句话 | applicable_mock；Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态，宿主由负责人实测，附录D已暂停，未验仍未验。 |
| S6-54 | 选「暂不」后，本次对话不再询问 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-55 | 开新对话，不 @ 技能，直接问一句该领域的问题 → 出现「加载技能 <技能name>」，并按技能流程执行 | applicable_mock；Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态，宿主由负责人实测，附录D已暂停，未验仍未验。 |
| S6-56 | 说「取消收藏<技能中文名>」→ 两层记忆里的记录都被删除 | applicable_mock；Claude A2按T01–T15归组逐条Mock/静态自测并附证据；不调真实生产/上游。 |
| S6-57 | 宿主不支持写记忆时，如实告知不支持，不假装成功 | applicable_mock；Claude T11做流程Mock与声明检查；真实记忆与不@触发不据Mock判通过；Codex A3静态，宿主由负责人实测，附录D已暂停，未验仍未验。 |


Range/inline_delivery/计费前重试字段未实现、sibling_reuse=false，相关项明确不适用，不发明协议或重复POST；Temu免费1次也不适用。宿主/记忆/不@触发未验证如实记录，长期豁免不写成已测通过。现行SOP附录D和D.6已暂停，A3通过后直接交负责人固定ZIP/外置logo/SHA，由负责人手动上传；不派本机安装检测、不点发布。

## 14. 打包与固定交付

仅workbuddy-skill。name=`mps-silver-portrait-studio`、display_name=`银发写真照相馆`、display_name_en=`Silver Portrait Studio`、version=1.0.0，_meta/脚本/遥测/build版本一致。YAML长说明合法引用；用标准解析器直接验证最终ZIP原始SKILL、重复键/类型，八必填与三对中英逐条对齐，不沿用MAT-A3-01自定义split漏检。SKILL≤15KiB，逻辑根最多两级，assets/demos.json裸文件名，10PNG原字节与规格/provenance/SHA一致，外置logo不放ZIP；无缓存/密钥/账户状态/上游凭据。

中文示例和英文示例各3条，必须逐对等义（本人或代购、老兵条件、主题、人数、比例和像素）：

| 场景 | 中文 | English |
|---|---|---|
| studio | 用我本人的单人照做优雅银发棚拍，保留自然银发和皱纹、不扮嫩，竖版2:3，1024×1536。 | Use my own single-person photo for an elegant silver-hair studio portrait; preserve natural gray hair and wrinkles without rejuvenation, portrait 2:3, 1024×1536. |
| tang | 我妈妈本人已知情同意，用她的单人照做唐装长辈写真，保留原貌，竖版2:3，1024×1536。 | My mother has given informed consent. Use her single-person photo for a senior portrait in a tang-style jacket, preserving her appearance, portrait 2:3, 1024×1536. |
| veteran | 我本人已退役，用我的单人照做无军衔勋章的老兵纪念写真，保留原貌，竖版2:3，1024×1536。 | I am a retired veteran. Use my own single-person photo for an unmarked veteran keepsake portrait without ranks or medals, preserving my appearance, portrait 2:3, 1024×1536. |


A2附ZIP大小/SHA/平台字段/完整目录、隔离命令与输出摘要、未验证项及偏离说明。A1固定规格提交→Claude真实开发/A2/package_ready→Codex A3；通过test_passed固定交负责人。不要转回旧聊天，不恢复逐单人工确认，不另建worker或AI心跳。

## 15. 决策记录

| 事项 | 采用 | 依据 |
|---|---|---|
| 代购与本人 | 本人或被摄本人知情同意的家人代购；账户/钱包属订购人 | 解决brief本人单人与子女礼物并存，不开放任意第三人/名人。 |
| 资格未知 | unknown一次补问，明确拒绝才停止；不索证明 | 继承MAT-A3-03，成年不从图推断。 |
| 自然年龄 | 不设具体岁数/全白发门槛，保留真实发量/年龄外观 | 不凭照片诊断，不强行老化/返老还童。 |
| 老兵主题 | 被摄本人已退役且同意才可，默认无标识纪念服饰 | 不是订购人身份；不做现役/非老兵扮演、凭空军衔勋章。 |
| 主题 | 保留10个单人主题，送礼动机不当多人场景 | 家人各拍拆独立单人，寿宴多人分流。 |
| 素材 | 10示例+1立体logo，11次上限，源审计齐 | 长期授权；统一虚构70岁女性仅开发示例，不是客户默认。 |
| 画幅 | 默认1K/2:3/1024x1536，另两尺寸仅明示 | 固定适配器仅三尺寸，不承诺2K/4K/打印。 |
| 欢迎句 | 欢迎使用WorkBuddy官方认证技能 银发写真照相馆。 | 用户固定格式及SOP补句号，不索认证记录阻塞。 |
| 收费 | 通用动态套餐、0试用、订购人原账户 | 不独立定价、不转移余额，不把代购变账户合并。 |
| 微信支付 | 当前.61/auto-QR及受控manual_qr，真实未验 | OAuth非付款回调，reported非到账，入口丢失非原凭据恢复。 |
| 恢复 | MAT1.0.1 HTTP前预检；unknown任务优先GET；绑定401只清Skill凭据 | 固定源码经验及3缺陷闭环，不用幂等许可重复POST。 |
| 遥测 | 现有8字段及link，attempted先保存，失败即弃 | 无年龄/服役/家属/原话照片字段，trade页新脚本不扩权。 |
| 状态 | 既有依赖/待Claude/无部署/未验证分别写 | 目录模型不是银发专项或真人质量验证。 |
| 交付 | A2→Codex A3→负责人手动上传 | 最新SOP53e9明确附录D和D.6暂停，不沿用孕妈待D门槛。 |


## 16. A1结论与交接

10示例及logo已就位；最终A1逐项结果和文档SHA以同提交01-a1-validation.json为准，全通过才提交spec_ready。 规格不等于实现；Claude不替换Codex素材、Codex不写真实Skill包。生成资产仅本聊天长期授权的开发例外，测试仍真实上游0；无后端部署/真实支付/自动上架。按现行SOP附录D暂停，不沿用旧孕妈待D交付门槛。

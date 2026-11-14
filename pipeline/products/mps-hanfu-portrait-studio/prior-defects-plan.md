# 汉服1.0.2压缩轮：前序缺陷与最终A3静态复核计划

本文件只是只读准备计划。历史关闭不等于新1.0.2已通过；尚未检查新ZIP、不修改包、不运行测试/包模块、不写远端或状态、不做浏览器/真机/业务/上游调用。

写前在线读取：https://open.workbuddy.cn/docs/skill ，2026-11-14 17:11:23 +08:00，HTTP200，284337字节，SHA256 7fe161594b4715268ad9fe86438dcb5d3818c90621ffb86997b64a68ff04408e；与本轮先前已实际全文读取的技能结构/frontmatter/子目录正文SHA一致，不凭仓库缓存宣称在线成功。

## 1. 固定基线与证据入口

- 本次任务：4811e350a13c21922549d874ee941ad02066b189:pipeline/products/mps-hanfu-portrait-studio/msg-from-muse-20261114-hanfu-resize-3mb.md，blob3a776ca84a69c32a4bbf921576da23f9a93c251f。它授权仅图片压缩及必要版本/引用同步；不部署，不改业务或模板。
- 最新规则读到main=8bc1ca669b91d859b3541a122cb7767ff6b8020b：SOP blob20b07a7e97a8e78403e82e0a2c71cee6a0b6013e，182/469行3MB限制，827行A2与A3分工；config blob0dca878e7778521c97031abd3e587c4395ebad3c，codex_may_publish=false。D/D.6继续暂停。3MB来源为负责人上传实测，不冒充官方页面已写该限制。
- 通过基线：fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f，汉服1.0.1；ZIP c4d345920b0fd0c2f1d3443c2044f520876f21000865fcac3212a55314c2f6ea，4,815,365字节，25文件；规格1a7d115d281ca3b25ce86609cfb9b29adfe7a895。
- 本地总报告：work-20261112-hanfu-a3-101/03-test-report-passed.md（已按根更正文件名）；仓库固定关闭报告可引4811e350a13c21922549d874ee941ad02066b189:pipeline/products/mps-hanfu-portrait-studio/03-test-report.md，blob97740f72655b8c10bb0a02b9d65d7403a966b14e。
- 同目录03-a3-1.0.1-evidence.json（仓库blob39312b3c6026935ef5af97d85e1a490181089be1）记录四关闭、25源blob和总检查；product-review.json管01/02，recovery-review.json管03与恢复，metadata-review.json管04与元数据。
- 本地干净逻辑根：work-20261112-hanfu-a3-101/clean-9bc9p4hv/mps-hanfu-portrait-studio。所有下列汉服包内行号都是这份固定1.0.1源码，不能直接当作未来1.0.2新行号。

## 2. 本次允许的差异及压缩兼容点

1. 新ZIP须严格小于3,000,000字节并留余量，记录真实字节/SHA/CRC；原1.0.0和1.0.1保留，1.0.1不上传。外置logo不在ZIP内，不把它的体积误算成包内节省。
2. 原10主题、顺序、标题、note、人物、构图/服饰内容保持；只做压缩/允许的分辨率或质量派生，不补生图、不重做logo、不减图、不裁掉形制或脸部要素。每张有原文件SHA→派生SHA/尺寸/格式/方法记录；原生成资产和provenance保留。
3. 兼容点已实读：studio.py513的DEMO_FILE_RE只接受裸名*.png，532行不符即清单失败；540–568按清单释放文件。因此不改脚本逻辑时优先保留PNG。直接换JPG并只改demos.json会demoUnavailable；如改格式必须先解决这个明确范围冲突，不把重命名当已兼容。
4. logo沿现行规格外置PNG512×512、≤500KB。图片派生允许SHA改变，不能继续声称十图/logo原字节未动；外观质量须对照旧图目检。
5. 版本1.0.2是任务明确例外：frontmatter/ZIP名/_meta、studio.py32、telemetry.py16及相关版本说明/断言作最小元数据同步，避免包版本与上报版本冲突；不能借此改变功能函数、话术、路由、确认或HTTP契约。
6. 形成文件差异白名单：10图片及必要logo派生、必要版本元数据、若文件名确变则对应清单引用、外置压缩审计/A2报告。业务脚本函数、references、欢迎/确认/售后文案应原字节或版本规范化后AST一致；异常差异先报告。
7. 本轮不把敦煌新OA/后台契约、域名/支付/账户/模型/时限迁移夹进汉服压缩包。发现其他问题单独报告，不扩大只压缩任务。

## 3. 汉服四项：历史确已关闭，1.0.2逐项复核

|ID|真实缺陷及关闭证据|压缩轮静态复核|
|---|---|---|
|HNF-A3-01|原非空outfit绕过form、默认宋风泄漏。fe2e studio.py106–119,430–479先由outfit_of确定整套，再叠颜色；452–455共用outfit_text；462–465改FORM_VISUAL/配套FORM_MAKEUP；610–614冲突先消歧。总报告22–26、product-review.json closed_findings[0]。|七组合daily宋/唐/明、garden宋/唐/明/曲裾及非空outfit的函数/指令不变；摘要、prompt、开工复述同源；冲突早退仍在_void持久失效之后。|
|HNF-A3-02|原“不要婚服，我要新年宋制汉服”被否定词硬拒。fe2e studio.py352–427，route_scene393/route_intent404先strip_negated；仅排除无主需求返回clarify_main_need；SKILL88、scenes20–25一致。总报告28–30、product-review.json closed_findings[1]。|否定/正向越界/主需求分流源码与宿主上下文指令不变；不把有界否定规则称全部自然语言已验证。|
|HNF-A3-03|全局“没结果重跑”覆盖未知反馈POST。fe2e SKILL53明确feedback例外，119–120无tid待用户显式--retry、已知tid仅GET；studio1339–1370信号auto_retry=false；1306–1336保原工单body/key。总报告32–34、recovery-review.json closures[0]。|全局例外、显式继续边界、既有tid GET、无tid同键同体均保持；账户/余额/resume不得顺带补交；不新增工单by-key，不把反馈补交移作生图重POST。|
|HNF-A3-04|侠客图实际木质影棚却写竹林。fe2e assets/demos.json43已为“木质影棚侠客风”，总报告36–38及metadata-review.json closed_findings。|新派生图仍是同一木质影棚内容；note/AI非实拍说明不回退，不因压缩重新替换内容。|

汉服1.0.1关键Git blob：SKILL04f4ecbbc4343a893336e76e9d8516787d1a23cd；studio01001500c3ba53bd7a79dc25abbd0e47216df2be；telemetry80d074803fd0576e2b75e3c0858f92d2e7d3b194；welcomece35bcf939ee26e587ad45d7cb58121c9d8073be；demos0001929fb6f3b0d1a6ab98bb14a9fc1215c3eeab；png_local7527dafe4de30d16444955587b5a69fc71aea123；jpeg_localb405e4cad8744119bad2abe180aa50603ca6021f。完整25项在上述evidence.source_file_blobs。

## 4. 通用历史清单：不补造编号或关闭报告

历史原产品关闭只说明当时版本；本轮仍看最终汉服源码/指令。仅适用于其他产品的孕期档位、家人代购、老兵条件等不新增到汉服；对应的成年本人资格、先失效/锁原任务等通用保护需保留。

|项目|原问题、已核关闭/承接证据|汉服1.0.2检查锚点|
|---|---|---|
|A3-PAY-01|paid新环境不给原安装关联入口，且无服务端证据称付款登记。宠物1.0.5 fixed5d2f004e87b7e58badf02e0213e888d466674bb4独立闭合，work-20261111-pet-a3-106/previous-a3.md3,7,12–16。|studio1103–1210的status/auth/topup/paid沿原身份入口和真实响应，不伪报登记/到账；不改账户函数。|
|A3-PAY-02|过期服务器短链仍转述。同一宠物关闭源/报告。|studio328–345 trusted_link/link_fresh以及773–801签链调用不变；保票据，不自行拼链或复用过期链接。|
|A3-PAY-03|description末句未覆盖本技能账户问题。同一宠物关闭源/报告。|SKILL5末句现有“或本技能账户问题”保持；账户路由不重新走首轮。|
|A3-PAY-04|demo不发遥测、不读凭据。证件1.0.8 fixedc536a284d31877b96e910b1de65f75863073ab78干净包tests/test_skill_contract.py544–545,579–583有真实编号/回归；work-20261111-a3/verified.json19–24绑定固定包。证据层级是固定包回归/清单，不冒称找到PAY04单独独立关闭报告。|汉服cmd_demo540–568无call/load_account/report_once；首轮first-turn501单独上报，不将遥测塞回离线demo。|
|A3-E01|双语例数量相同但主题/像素不对应。最终承接证件1.0.8 fixedc536，tests165–170；宠物1.0.5独立报告previous-a3.md12,16已过，1.0.6报告25不回退。|原始YAML标准解析，三对唐齐胸/宋褙子/明马面与同2:3、1024×1536逐对保持；不只数数量。|
|A3-E02|空格路径不成为Markdown链接。同c536干净包tests404–435/437–461及宠物独立报告。|studio188–191正斜杠+编码；最终资产文件存在，静态构造空格路径用CommonMark解析/解码能定位。|
|A3-E03|#被解析成URI fragment，图片找不到。同上一行固定闭合/承接源。|同上另构造#与%路径；不把fragment/query截断当有效链接。|
|WED-A3-01|离线demo误触发首次对话网络上报。婚纱1.0.1修复声明见work-20261109-wedding-a3-recheck/02-self-test.md13，明确只是A2证据，不冒称找到婚纱单独独立关闭ref。当前汉服承接证据为fe2e cmd_demo540–568、first-turn501及通过报告49–51。|与PAY04分行核对：离线释放/凭据读取/首次上报职责边界不回退。不得用A2转述冒充本轮执行。|
|A3-FAM-01（请求简写FAM-01）|提交401→恢复后原键GET404→再次生成POST。家福1.0.1 fixed4669fdb7622e8562c6ce09a9ea7c3d9f4494638d关闭，work-20261111-family-a3-101/03-test-report.md7,26–28；原定义-a3-100/03-test-report.md26–43。|studio847–986、1062–1100未知只原键/原id GET；404不得授权重POST。|
|A3-FAM-02|401恢复失败/查询异常降confirmed，后续replan清键/摘要解锁原任务。同FAM关闭源。|原任务锁、submit_unknown/download_pending保留；新输入不清已提交锁，credentialReset保原任务和原安装身份。|
|A3-FAM-03|默认十示例缺一张被continue跳过，9张仍成功。同FAM关闭源。|studio516–568十key集合/不重复/全体在位后才复制；缺任何默认示例整组失败，不补造路径。|
|TRV-01|保存Key就视为可用，bound=false/缺回执/异常仍生成。旅行最终1.0.2 fixed847b19d5b87d57d3bce6d0f3aa61ac9130de9748，work-20261111-travel-a3-102/03-test-report-1.0.2.md6,21–31。|studio699–770的ready/私存Key/bound===True分开，错误不进入生成。|
|TRV-01-R1（01续修）|绑定401不清失效缓存Key、恢复循环；同最终旅行1.0.2关闭源。|清Key与bound，退出4，保原install_secret/任务；下一次原身份领新Key后仍只GET原任务。|
|TRV-02|只验PNG/JPEG头部尺寸，截断坏图可过。旅行1.0.1修完基础完整解码；最终1.0.2报告21–31保持。|audit_images/png_local/jpeg_local原字节；新示例图用独立图片工具验证，不执行包函数；业务输入完整预检不回退。|
|TRV-02-R1（02续修）|完整校验实现新增无界zlib展开/重复DHT65536表CPU预算缺口；同最终旅行1.0.2关闭源。|有界解压分片≤64KiB/remaining+1、JPEG建表/扫描计数上限保持；不能因图片压缩替换这些校验助手。|
|TRV-03|首次上报失败后自动重报。旅行1.0.1已关，最终102报告43确认保持。|telemetry发前原子attempted落盘/回读、失败不重试、关闭开关及八字段不变，只有版本元数据同步。|
|TRV-04|泛樱花/古城词压过和服/汉服特异路由。旅行1.0.1已关、最终102报告43承接。|汉服本品特异形制与范围/否定/主需求优先规则保持；不照搬旅行场景或新增地点。|
|TRV-05|传图同意未告知图片服务及算力供应商接收方类别。同旅行关闭承接源。|三许可独立、接收方类别与同一照片/当前快照绑定；不能只把同意授权当付费同意。|
|MAT-A3-01|description_en未引用的“portrait: 10 themes”令原YAML解析失败。孕妈1.0.1 fixed108761fb56bc6712d22b387386d4105841bcb69b，work-20261112-maternity-a3-101/03-test-report-1.0.1.md6,22–40关闭。|最终SKILL原始frontmatter直接标准YAML解析，无诊断投影/重复键；只变版本不改公开语义。|
|MAT-A3-02|已确认原图删/坏后仍先账户/Key HTTP再验图。同MAT关闭源。|studio680–692、804–844、1062–1085本地完整预检仍先于无原job的新提交账户HTTP；有原job先锁/查原任务。|
|MAT-A3-03|未问成年，unknown填no直接拒绝又建议换照片。同MAT关闭源。|本人/成年/单人unknown先补询；明确不符按原因拒绝，不建议换图掩盖资格；不继承孕期条件。|
|SLV-A3-01|A改B遇unknown/no/坏图早退，未先持久作废A三同意和旧键；可继续发旧A。银发1.0.1 fixed59aca1d34ab45d82ccd10c187c11208b3b2c556c，work-20261112-silver-a3-101/03-test-report-1.0.1.md6,20–30关闭；原定义-a3-100报告28–46。|studio578–646锁优先→_void_unsubmitted先save→新B校验；早退保存B路径/replanning并挡confirm/run/resume/regenerate。已提交原任务不作废。|
|斜杠案（具名回归，未证独立A3编号）|旧状态目录\.在Markdown中吞反斜杠；证件1.0.1去点目录/正斜杠A2声明在work-20261108-resume/repo/pipeline/products/mps-id-photo-background/02-self-test.md182–210；最终c536干净包idphoto.py88–108/tests385起承接。|汉服md_safe_path188–191先绝对化，反斜杠→/，%先编码，再空格/#等；链接仍实际存在。|
|欢迎句逐字（具名回归，未证独立A3编号）|不把已撤回的R1认证冲突当新缺陷；证件c536 tests127–128锁欢迎。汉服fe2e welcome_copy.py5–7及总报告46锁定。|完整字符串为“欢迎使用WorkBuddy官方认证技能 汉服写真照相馆。”；保留中文句号、固定空格、技能名，不因请求概括省标点而改句式。|

补充已查关联项：同婚纱A2报告14–15还有WED-A3-02（原照片被替换后旧确认/原键仍可用）与WED-A3-03（成品Markdown链接未走安全路径）。当前汉服承接锚点为fe2e studio650–692的源图摘要核验及1012起交付安全链接、总通过报告49–50；它们与上表SLV/FAM及路径保护合并静态复核，不虚构新的运行/关闭报告。

## 5. 最终固定ZIP到位后的A3顺序（此刻未执行）

1. 核package_ready固定输入/原claim与最新状态、ZIP与A2报告SHA一致；干净目录安全解包，CRC、25项基线差异、目录≤两级、无越界/链接/缓存。先称重，严格<3,000,000并记录余量。
2. 以fe2e为基线做逐文件diff：图片派生合法；版本常量以外业务函数/字符串不变。对HNF01–04及上表每项提供新包路径/行号和静态证据，不以“压缩所以无需看”跳项，也不把旧通过自动盖到新包。
3. 标准解析原始YAML/元数据，中英例逐对核对，版本/渠道/欢迎句/接管/240秒既有预算一致；图片压缩不引入隐式功能或HTTP字段变化。
4. 十图与清单一一对应、标题/内容/note一致；独立解码/尺寸/格式、逐图并排目检关键脸部、齐胸/领口/褶裥/妆发、木质影棚等可见点；logo外置PNG512×512≤500KB；压缩审计指回原资产，禁止新增生成。
5. 静态核示例释放、完整集合失败、路径编码；可用独立CommonMark/图片/ZIP/AST工具作资料解析，禁止导入或调用包函数、跑CLI、完整A2、浏览器或真实账户。
6. 审开发者A2记录的实际环境/命令与局限，不把旧Linux/AST3.7记录写成新Windows/真实Python3.7实跑。静态A3不能证明真人效果、真实支付/微信、宿主收藏/触发、平台上传或审核。
7. 本轮A3逐项静态通过才写新版本结论与新SHA，交Muse→负责人手动上传；D/D.6暂停，不安排computer-use安装测试、不自动上传或回滚重传。

## 6. 当前结论

汉服1.0.1的HNF01–04有固定包+独立报告明确关闭；其余通用历史项按上表证据层级列齐。1.0.2尚待实际固定ZIP到位并独立静态复核，本计划不改变其产品状态或任何认领。


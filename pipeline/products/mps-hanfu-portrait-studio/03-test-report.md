# 汉服写真照相馆 1.0.0 A3 独立检查

**独立检查未通过，退回 Claude 修复。** 本轮4项待修：形制被服饰文本覆盖、否定需求误拒、反馈未知状态自动重跑规则冲突、示例背景说明不实。产品置 test_failed，rounds.test 从0增为1。未修改Skill源码、开发规格或素材；不部署、不上传。

- 时间：2026-11-12T19:21:16+08:00；事件 `evt-16dd491edf27e4d50f20483cb0c37c31168b09e816515709648cad664b477083`；本机/仓库原claim `87cd1582-8886-41b5-96a8-116c630a7bc8`一致，固定输入指纹已复算。产品认领提交 `f85733479939036361b7c8574bae51b58ee88160`。
- 固定来源 `683008528ac153fdb35209e14937aa6ad56656cf`；规格固定 `1a7d115d281ca3b25ce86609cfb9b29adfe7a895`。当前SOP blob509b9732、config966a0d8已核；A3按独立静态检查，不执行包、不导入客户模块、不重跑A2、不做浏览器或上游验证。
- 本次2026-11-12T19:21:16+08:00重新在线读取[WorkBuddy技能文档](https://open.workbuddy.cn/docs/skill)，HTTP200、277042字节、SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；仅团队Skill。Claude A2报告读取的是11月8日官方快照，不冒称其做了本次在线读取。

## 固定产物及已通过检查

| 项 | 独立核对结果 |
|---|---|
| ZIP | [mps-hanfu-portrait-studio-1.0.0.zip](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/dist/mps-hanfu-portrait-studio-1.0.0.zip)，4,812,372字节、25文件，SHA256 `624ee30dbd94d09f9b2a44d7b4c4c239cb9dd09e0d4f7c1ae11af23a1f9d30ba`，与A2一致。CRC无损坏，干净解包文件和固定仓库源码逐字节一致。 |
| 目录 | 单一slug外包装，逻辑根最多两级，无越界/符号链接/大小写重复/隐藏缓存；示例裸文件名放assets。 |
| 元数据 | 最终SKILL原始frontmatter用标准YAML直接解析、无投影/重复键；八必填及三对中英例与规格一致，齐胸chest-high/同画幅像素；SKILL15057字节≤15KiB。 |
| 契约常量 | 欢迎句、slug/版本/渠道一致，25触发词/接管/六字段/三尺寸/8遥测/2秒/240秒预算符合；Python3.7 AST语法可解析，不代表3.7解释器实跑。 |
| 十图 | 10张RGB PNG512×768，与Codex来源/provenance/派生记录/规格逐张同SHA，总4,718,679字节；不含身份参考初稿。garden实际832×1248及离线选图异常未被包当生产通过。 |
| 外置logo | PNG512×512、418271字节、SHA256 `d6cda4a802770817435324b898d5e0f1705adf95cd2a7c665baba27727c2978b`，原字节未动、未入ZIP。 |
| Markdown路径 | 静态核编码函数，独立构造含空格/#/%真实PNG链接并用CommonMark解析/解码后可定位，无query/fragment误拆；没有执行包函数。 |
| 恢复核心 | 65个studio定义和8个遥测定义与银发1.0.1 AST相同，3个有界图像助手字节相同。先作废再校验、新B保存、原任务锁、HTTP前验图、绑定401/原身份恢复、未知原键GET、三许可保留；只作静态结论。 |
| 秘密及公开文案 | 对客段/README/固定话术的禁用词与秘密形态扫描通过；未发现上游凭据泄露。 |

## HNF-A3-01（P2）：自定义服饰会抹掉已选形制

静态复现场景：已有合法本人成人单人照，`plan ... --scene daily --form ming --outfit "素蓝色"`，或`--scene garden --form quju --outfit "深青色"`。这两个参数允许同时填写，并非非法输入。

[studio.py:392](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L392)用`outfit or outfit_of(scene,form)`，非空outfit绕过形制结构；[395](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L395)又以`not outfit`限制形制注入。393仍带daily默认宋风/garden宋褙子visual，534保存form和outfit，602将两者传入，但后端prompt已无所选明制或曲裾的确定结构。确认/开工复述也沿服饰短文本覆盖的路径。用户确认的整套形制可能丢失，违背规格第3/4节；不是历史精确效果率的主观判断。

要求：先由选定form决定完整服装结构及配套妆造，自定义颜色/服饰细节叠加其上；冲突先消歧，不静默丢掉form。prompt、plan摘要和开工复述一致。A2补daily的唐/明、garden的唐/明/曲裾与非空outfit组合，不能仅测空outfit的form；仍只有六个HTTP字段。

## HNF-A3-02（P2）：否定的越界词被作为拒绝依据

静态复现场景：`不要婚服，我要新年宋制汉服。` 婚服是被排除的内容，主需求为允许的本人单人新年汉服。

[studio.py:356–358](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L356)仅按ROUTE_BOUNDARY子串命中即返回out_of_scope_wedding，没有判断否定或主需求；[SKILL.md:88](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/SKILL.md#L88)接入intent，[scenes.md:20](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/references/scenes.md#L20)要求这些intent说明做不了。按包执行规范会误拒合法请求，不能仅以route_intent注释“只是提示”作为已消歧证据。

要求：被否定/排除的词不自动升级为最终越界拒绝。可保留清晰主需求，或转为需核对主需求的提示；宿主规范必须结合上下文而非硬拒。A2补否定婚服/和服等词+合法汉服的组合，以及明确要求婚服确实拒绝的正例；不因此取消既有范围限制。

## HNF-A3-03（P2）：反馈未知状态与全局重跑指令冲突

规格要求无tid、响应未知时持久保留原body/key，**只有用户显式继续**才同键同体POST售后取回；已有tid仅GET。生图原任务始终GET续查，这两种协议不能混为自动重跑。

[SKILL.md:53](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/SKILL.md#L53)全局指示没拿到结果时把同一命令重跑一次，未排除feedback；[119](https://github.com/Haihe2026/myplanestroe/blob/683008528ac153fdb35209e14937aa6ad56656cf/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/SKILL.md#L119)只写用户“提交反馈”→--retry，未明确未知响应例外。`cmd_feedback`1251–1274及`_submit_pending`1218–1248允许同键同体补交，所以宿主按全局规则可自动再次POST，偏离规格显式继续边界。这里没有观察到重复建单、真实扣费或客户端自动循环；后端幂等代码保持，是执行指令冲突。

要求：限制泛化重跑适用范围，明确反馈无tid且未知时保留原记录、等待用户显式继续；有tid仅查原工单，不能新增工单by-key接口、自动换key或重POST生图。补静态执行规范契约和相应Mock覆盖，保持SKILL≤15KiB。

## HNF-A3-04（P3）：侠客示例的背景说明不实

`assets/demos.json`的swordsman note写“竹林侠客风”，但同SHA的既定示例为深色木质影棚，没有竹林。修改为实际可见的“木质影棚侠客风”或省略具体背景，保留AI非实拍说明。仅改note，不重画、不替换图、不追加生图或logo调用。

## A2证据与未验证范围

- Claude自报63契约+136端到端、Linux unshare断网实跑；Codex只阅读这些记录，未独立重跑。报告未提供规格所写Windows隔离Mock的实跑证据；AST3.7及Linux不能称Windows已验。修复轮补足相应证据，或按现行SOP明确写出偏离/未验与原因，不能静默把缺证算通过；本轮不为此申请额外权限或代跑完整A2。
- 多个修改拆成多次生成是现行SOP明确要求，不作为包缺陷；规格“完整新方案”的简述不能反向要求客户端违背SOP。即时到账等既有SOP固定话术不凭静态manual_qr推断另报缺陷。
- 真机验收已跳过（负责人长期规则）；附录D及D.6暂停，不写成宿主通过。真实微信/付款、真人效果、历史准确率、生产签名参考、收藏/不@触发、平台解析/接受均未验证。

## 结论与接续

退回Claude修复以上4项并补回归，生成新版本ZIP及A2报告，重走package_ready→Codex A3。保留本1.0.0历史ZIP和原源码以供追溯，不原地覆盖旧包；不改Codex规格/原PNG/logo/客户财务或共享生产。

本轮真实生图0、后端业务0、真实支付0、生产写入0、部署/重启0、上传0；不导入或运行包、不建worker/心跳/周期监测。固定证据见03-a3-1.0.0-evidence.json。

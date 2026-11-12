# 银发写真照相馆 1.0.0 A3 独立检查

**独立检查不通过。** 发现1项包状态机缺陷：SLV-A3-01（P2），未提交草稿改方案时若新信息未齐或被拒绝，旧计费确认及任务键仍可能被“继续”使用。置 `test_failed`、`rounds.test=1`，退Claude修复；不改开发规格、不改包源码。本包尚不是最终交付上传版。

- 时间：2026-11-12T10:04:02+08:00。事件 `evt-6851162b0da431ce76fb4c46c46412189a75d1ba38b4009281ec05f2f5be2c94`；本机和远端原claim `504de69a-6590-496a-a420-5c2de423c1c6`一致，固定输入指纹复算通过，产品检查认领提交 `941049712599a0dc8c7b5bdbdfdec221a5c4f9dc`；没有重复认领事件。
- 固定来源 `31ee7abf6512e3d15bb7911e5dd30b1b0102a250`；开发规格 `3eb43035ef3c80363b0c9527cb82ec63aa758bb8`。已读最新SOP/config/status/log/brief、MD/JSON规格及Claude A2。SOP blob `53e9b9862e62dadd2bd5a20d6e5e5697e3beab46`、config `966a0d8fdd9d680d4652fa2cba8aacca174aa74e`；附录D及D.6已暂停，本次不派安装检测。
- 本次于 `2026-11-12T09:55:42+08:00` 在线重读[WorkBuddy技能文档](https://open.workbuddy.cn/docs/skill)成功，HTTP200、277042字节、SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；另核固定快照技能章，仅团队Skill，expert不适用。
- Windows全新目录干净解包，按现行SOP做A3独立静态检查。未重跑完整A2、未执行客户端业务命令；仅隔离求值已审纯Markdown路径函数并做CommonMark合成路径解析。

## 固定包与检查结果

| 项 | 结果与证据 |
|---|---|
| 固定ZIP | [mps-silver-portrait-studio-1.0.0.zip](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/dist/mps-silver-portrait-studio-1.0.0.zip)，2,603,008字节、25文件，SHA256 `b06ce740ca094ee56dd9483c368599dc4ecbe2e4ff0f858f6fa7b258f3deb44c`，与A2一致，CRC完整。 |
| 结构及逐字节来源 | 通过：单一slug外包装、逻辑根最多两级，无重复/大小写冲突/越界/链接/缓存；25解包文件与固定ZIP及仓库源码原字节一致。 |
| YAML/元数据 | 通过：最终ZIP原始SKILL直接标准YAML解析成功，无诊断投影/重复键；八必填类型正确，SKILL.md 15,334字节≤15KiB，slug/名称/英文名/1.0.0/渠道跨文件一致。 |
| 欢迎及双语 | 固定句「欢迎使用WorkBuddy官方认证技能 银发写真照相馆。」逐字；本人银发棚拍/妈妈唐装代购/本人退役老兵3对与规格逐字一致，许可/主题/人数/画幅/1024×1536一致；23触发词和倾向句保留。 |
| 10示例 | 通过：10张512×768PNG完整解码，合计2,519,807字节；key/标题/SHA与Codex源/provenance/派生记录/规格一致，原字节未改，每条note含AI非实拍标注。仅合成例图，不代表真人/服役/年龄控制验收。 |
| 外置logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/dist/logo.png)，512×512PNG、456,079字节、SHA256 `9909cf071a9e64cb18707ec846b6cf5c921754979151075bfcf77756420acf1e`，原字节未改，≤500KB、不进ZIP，无新生成。 |
| Markdown路径 | 通过：空格/#/%三条真实合成PNG路径经已审纯函数和CommonMark解析/解码可定位原文件，无意外query/fragment；manifest裸文件名。 |
| 初次资格/代购许可 | 静态符合：本人/家人代购、成年及知情未知合并补问，明确不符合才拒绝；被摄人照片许可/传输许可与订购人计费同意分开，代购扣订购人账户，不转移/合并钱包、不读长辈私有凭据。旧确认已存在时的replan早退另见缺陷。 |
| 老兵/自然年龄/路由 | 被摄本人已退役且同意该造型才可；不收证明、未知补问、active/not_veteran拒绝该主题可另选普通主题；prompt五段保留真实发量/发际线/灰黑银发/皱纹，不套合成70岁女性；特异词优先，生日/金婚/退休不替用户认定老兵条件。 |
| 恢复与有界输入 | 主要闭环保留孕妈1.0.1：绑定401只清Skill凭据保留install_secret，bound真值，原任务401/404/未知只GET不重POST；未提交run及needs_credits resume先本地验图/SHA。audit_images/png_local/jpeg_local三文件与基线逐字节相同；PNG/JPEG有界完整性未回退。 |
| 交付/协议/遥测 | 有效PNG尺寸偏差交原图+真实提示，不当坏图反复补取；损坏/缺失才download_pending原任务GET。生成六字段/单参考、8字段/2秒/attempted先持久化且失败不重报、银发开关、240秒预算保留。 |
| 话术/秘密/语法 | 对客禁用词与真实秘密形态扫描通过，脚本Python3.7语法可解析；不代表在3.7解释器实跑或宿主实际加载。 |
| 规格符合性 | **不通过：SLV-A3-01**。T14所需未提交改方案确认失效只在成功replan实现，早退遗漏。 |

## SLV-A3-01（P2）：改方案早退后仍可执行旧确认

### 固定代码证据与静态复核步骤

1. 用照片A完成普通主题plan及三项confirm，尚未发生成POST；可停在首次关联前/关联中，或尚无job_id的needs_credits。磁盘草稿有原照片A、原scene/orderer、三项true及旧idem。
2. 用户要求改为给妈妈代购照片B，或改老兵主题，但新被摄本人许可/老兵条件未问清或明确不同意。宿主按[SKILL第2节](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/SKILL.md#L91)重新plan：family_proxy+informed unknown/no，或veteran状态/同意unknown/active/no，或新图B缺失/截断。
3. [studio.py:418–464](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L418)读旧草稿后，432–451的资格/本人许可/老兵条件分支和453–464的脸部/文字/输入校验均可直接emit早退，没有持久作废旧确认。只有[465–469](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L465)成功plan才把三同意设false、idem/job/body摘要清空并save。早退时新图路径即使内存改过也没有存盘，旧A/角色/键继续留在磁盘。
4. 用户随后说“继续”→[resume885–906](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L885)，可转到[run629–667](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L629)。632仅看旧三同意+旧idem，638对旧图A构体；旧A有效时经账户/Key流程可在667提交旧图旧角色方案，不是等待新方案本人许可和计费确认。needs_credits分支即使查到补充次数，也会恢复旧confirmed再run。

这是固定源码可确定的路径，并经两份只读专项独立复核；本轮没有运行客户端、发真实生成POST或验证真实扣费，不把风险写成已发生的扣费事故。未发现此路径能重新提交已发任务：421–422的LOCKED优先保护与run634–635的原任务续查均在，因此修复不得取消、清键或解锁已提交/unknown任务。

### 期望与修复范围

[规格§4](https://github.com/Haihe2026/myplanestroe/blob/3eb43035ef3c80363b0c9527cb82ec63aa758bb8/pipeline/products/mps-silver-portrait-studio/01-dev-spec.md#L74)、§12和T02/T14明确：源图、主题/服装/画幅、被摄人或代购授权关系变化，使未提交确认及键失效。对尚未提交的replan，应在进入可早退的新资格/新图验证路径前，先持久作废旧的执行确认和待提交键，清楚保留/标记待完善的新方案。只要新信息未齐、被拒绝或验证失败，run/resume/regenerate不得借旧许可生成旧A。修复细节由Claude实现，不改变既有收费、鉴权或后端。

对已提交/submit_unknown/download_pending或已有job_id的原任务继续优先只读续查，replan仍拒绝，不清原键/原体/锁，不因本地图或新资格变化重建任务。正常新方案重新取得本人照片/具体文件传输/订购人计费三项明确同意后，才允许新键提交。

### Claude A2应补的回归

- 从旧confirmed和无job_id的needs_credits各起一组：新family_proxy许可unknown/no、adult未知/no、新老兵条件unknown/active/not_veteran或主题同意no、改图B缺失/截断、脸不清/文字过长等早退；返回后重读持久状态，旧三同意与可执行键已失效。
- 早退后重启/重读再run或resume：只等待补齐/重新确认，生成POST0、扣次0，不能发旧A；regenerate也不能绕过。区分匿名首次遥测与业务请求。
- 新方案B信息齐全并重新明确三项同意后才提交新图/主题/代购关系，正常路径仍通。
- 对submit_unknown/submitted/download_pending/已有job_id，replan不清原键/原体/锁；即使本地图坏了仍只GET原任务、无第二次生成POST。
- [现有契约测试698–724](https://github.com/Haihe2026/myplanestroe/blob/31ee7abf6512e3d15bb7911e5dd30b1b0102a250/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/tests/test_skill_contract.py#L698)的注释已写“含下单人或同意情况变化清待提交键和确认”，但只测family_proxy+informed=yes的成功replan；新增用例应能反证旧1.0.0的早退遗漏，不能只重复该成功分支或放宽断言。

## 后续与验证边界

根因在包状态机，不改开发规格，不代写Claude客户端。Claude修复SLV-A3-01并出新版本，保留所有通过项及10图/logo原字节；重跑隔离A2、固定新ZIP/SHA后置package_ready，再交Codex独立复查。

结构化12类检查、25源码Git blob、素材SHA、基线继承和缺陷见 `03-a3-1.0.0-evidence.json`。Claude所报60契约/131端到端属于其A2执行记录，本轮未重跑完整A2或将其当作Codex独立实测。

本轮新增真实上游0、后端业务0、真实付款0、生产写入0、部署0、上传0。真人银发皱纹/发量保真、实际老兵造型、生产签名参考、真实微信/手机/付款、宿主对话/记忆/触发、平台接受/审核均未验证。现行SOP附录D及D.6暂停，不派安装检测；本次是实际包缺陷退回，不是HOST_ACCEPTANCE_UNAVAILABLE阻断。未来A3通过后交负责人手动上传，不自动发布。

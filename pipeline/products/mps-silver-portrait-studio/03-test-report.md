# 银发写真照相馆 1.0.1 A3 独立复查

**独立检查通过。** SLV-A3-01已关闭，未发现新的阻断，产品置 `test_passed`，失败轮次保留1。按当前SOP，附录D及D.6暂停，直接交负责人手动上传；本结论不代表宿主、真实支付、生图或平台审核通过。

- 时间：2026-11-12T10:54:03+08:00；事件 `evt-b9a3d242b8c792af50e90d626626a1726c41ef299054f48787dcd8408b22fdde`，本机/远端原claim `d8513f8b-1707-4677-ac28-246c6d3e0bf1`一致，固定输入指纹复算通过；产品认领提交 `0598c7bc724066b30a23a5c31548adbb09948057`，没有重复认领事件。
- 固定包来源 `59aca1d34ab45d82ccd10c187c11208b3b2c556c`；开发规格仍为 `3eb43035ef3c80363b0c9527cb82ec63aa758bb8`。已读最新SOP/config/status/log/brief、MD/JSON规格、1.0.0 A3及Claude修复A2，未改规格或包。
- 本次 `2026-11-12T10:48:37+08:00` 在线重读[WorkBuddy技能文档](https://open.workbuddy.cn/docs/skill)成功，HTTP200、277042字节、SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；同时核固定官方快照技能章，仅团队Skill，expert不适用。
- Windows全新目录干净解包，A3独立静态复查；未重跑完整A2、未执行客户端业务命令，仅隔离求值已审纯Markdown路径函数并做CommonMark合成路径解析。

## 固定交付产物

| 项 | 内容 |
|---|---|
| 名称 / slug / 版本 | 银发写真照相馆 / mps-silver-portrait-studio / 1.0.1 |
| ZIP | [mps-silver-portrait-studio-1.0.1.zip](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/dist/mps-silver-portrait-studio-1.0.1.zip)，2,605,315字节、25文件，CRC完整；逻辑根内最多两级 |
| ZIP SHA256 | `15c1313a522c85ddc876a7d6e11aa57ee58d720c7cca78eb4dff004a424d4458`，与[A2](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-self-test.md)一致 |
| 外置logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/dist/logo.png)，512×512PNG、456,079字节，SHA256 `9909cf071a9e64cb18707ec846b6cf5c921754979151075bfcf77756420acf1e`；原字节未变，≤500KB，不进ZIP |
| 历史包 | 1.0.0 ZIP原字节仍在dist/，SHA256 `b06ce740ca094ee56dd9483c368599dc4ecbe2e4ff0f858f6fa7b258f3deb44c`；仅供追溯，未通过，不作本轮上传版 |

## SLV-A3-01：未提交改方案的旧确认失效——关闭

[studio.py:423–426](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L423)先拒绝LOCKED_STATES或有job_id但未到delivered/failed/rejected的原任务，保留原键/原体/锁；只有尚可改方案的分支才进入`_void_unsubmitted`。

[479–489](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L479)在主题/画幅、成年/代购许可、老兵条件、单人/脸部、文字、新图等任何可早退校验之前，先将三项同意置false，idem/job_id/body_sha256清空，state=replanning，并记录本次replan主题/订购角色，经既有原子save_draft落盘。传入新图B时，B路径同时持久化、旧源SHA清空；后续不带--image再次plan也不会回落旧A。

[run650–654](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L650)、[resume908–912](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L908)、[regenerate934–939](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L934)均从磁盘load后优先处理replanning→needsReplan/退出2，不进入账户/余额/生成业务请求；[confirm496–500](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/studio.py#L496)仅允许planned。必须成功重规划，再取得被摄本人照片许可/这张文件传输许可/订购人计费三项明确同意，才在505行生成新键。状态确已持久化，重启后同样按该门槛读取；这是静态控制流结论，本轮未做客户端重启实跑。

[SKILL.md:97](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/SKILL.md#L97)明确needsReplan先补齐再plan；[welcome_copy.py:254–256](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/02-package/mps-silver-portrait-studio/scripts/welcome_copy.py#L254)说明旧确认作废、未开始/无新扣费，新旧方案都需重新确认。原任务submit_unknown/submitted/download_pending、已有未完成job的锁和GET续查优先级保留，不因本地图坏掉或新方案资格变化清原键/重POST。

两份独立只读专项与根审计一致。Claude A2报告新增从confirmed/needs_credits起步的15类早退、旧A与新B、重读/续做/重新确认、补充次数后不发旧图、原任务锁及1.0.0反证；源码/新增测试文本可支持修复针对性，本轮没有将其62契约/136端到端执行记录冒称Codex独立实测。

## 其余独立复核

| 项 | 结果 |
|---|---|
| 固定包和源码 | 25个干净解包文件与ZIP及固定仓库源码逐字节一致；无越界/符号链接/大小写冲突/缓存。 |
| 差异范围 | 相对1.0.0，18文件原字节相同、7变更，无增删。变更为SKILL、_meta、studio、welcome_copy、telemetry版本及两项测试/预览；README、3份references、图像helper、示例清单和素材未变。 |
| YAML/元数据 | 最终ZIP原始SKILL标准YAML直接解析成功，无诊断投影/重复键，八必填类型正确；SKILL.md 15,358字节≤15KiB；版本/slug/中英文名/渠道跨文件一致。 |
| 欢迎及双语 | 欢迎句「欢迎使用WorkBuddy官方认证技能 银发写真照相馆。」逐字不变；本人银发棚拍、妈妈唐装代购、本人退役老兵3对与规格逐字一致，许可/主题/人数/2:3/1024×1536一致，23触发词和倾向句保留。 |
| 十图来源 | 10张512×768PNG完整解码，合计2,519,807字节；key/标题/SHA与Codex源/provenance/派生记录及规格一致，原字节及AI非实拍说明未变。合成例图不证明真实年龄/服役或真人质量。 |
| 外置logo与历史 | logo原字节/SHA/512²/大小核对，旧1.0.0 ZIP也原字节未变；没有重新生成或原地覆盖。 |
| Markdown路径 | 空格/#/%三条真实合成PNG路径经已审纯函数及CommonMark解析可定位，无意外query/fragment；manifest裸文件名。 |
| 资格和主题 | 本人/家人代购、被摄人成年/知情、老兵条件unknown先补问、明确不符才拒绝；照片/供应商传输许可属于被摄人，计费同意属于订购人；自然发量/皱纹/年龄外观、十主题路由和相邻分界未回退。 |
| 账户与原任务 | 绑定401仅清Skill凭据，保留原安装身份；bound真值、未知/401/404只GET原键/任务、无第二次生成POST。已提交/unknown任务锁优先，未提交run和needs_credits resume仍先验图/SHA再业务HTTP。 |
| 有界与交付 | audit_images/png_local/jpeg_local三文件字节未变，PNG有限输出/JPEG缓存预算与完整性保留；坏/缺图原任务补GET，完整PNG尺寸偏差交原图+提示，不反复补取。 |
| 六字段/遥测/秘密 | 六字段单参考、8字段/2秒/attempted发前原子持久化与失败不重报、银发开关、240秒预算保留；遥测只更新版本。对客禁用词/秘密形态扫描通过，脚本Python3.7语法可解析，不代表3.7解释器实跑。 |

结构化12类检查、25源码Git blob、差异、素材SHA及闭环见 `03-a3-1.0.1-evidence.json`；上轮1.0.0缺陷报告见[固定历史](https://github.com/Haihe2026/myplanestroe/blob/59aca1d34ab45d82ccd10c187c11208b3b2c556c/pipeline/products/mps-silver-portrait-studio/03-test-report.md)。

## 结论、交付与边界

A3独立静态复查通过，SLV-A3-01关闭、open findings为空，失败轮次仍为1。现行SOP附录D及D.6暂停，不派本机安装检测；直接将上述固定1.0.1 ZIP、外置logo与SHA交负责人手动上传，不自动发布，不将“暂停/豁免”写成宿主实测通过。

本轮新增真实上游0、后端业务0、真实付款0、生产写入0、部署0、上传0。未运行客户端业务、完整A2或真人出图；真人银发皱纹/发量保真、实际老兵造型、生产签名参考、真实微信/手机/付款、宿主对话/记忆/触发、平台接受/审核仍未验证。仓库事件不扩展生产、财务、发布或跨聊天权限；不另建worker、AI心跳或周期监测。

# 孕妈写真照相馆 1.0.1 A3 独立复查

**独立检查通过。** 上轮MAT-A3-01/02/03全部关闭，未发现新的阻断；产品置 `test_passed`。本结论仅为A3静态独立检查，附录D本机导入尚未执行，不代表WorkBuddy宿主、真实支付、生图或平台审核通过。

- 时间：2026-11-12T02:00:02+08:00。事件 `evt-72f2034201e453ab196a33517be3e0eab673f9a04513d0a778e1d58bcde78933`；本机/远端原claim `6e9e1a80-0b88-4d77-ab9a-d17a04db2589`一致，固定输入指纹复算通过。产品检查认领提交 `3a81cd6226762fb02c2d782de9d282a422fcca24`，未重复认领事件。
- 固定包来源 `108761fb56bc6712d22b387386d4105841bcb69b`；规格仍为 `98ff2a5471031ff380a30bbd68c4ee69c2067ee1`，没有改规格或客户端。已读最新SOP/config/status/log/brief、现有MD/JSON规格、Claude A2及1.0.0 A3退回意见。
- 本次 `2026-11-12T01:55:23+08:00` 在线重读[WorkBuddy技能文档](https://open.workbuddy.cn/docs/skill)成功，HTTP200、277042字节、SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；同时读固定官方快照技能章。仅团队Skill，expert不适用。
- 环境：Windows，全新目录干净解包。按现行SOP独立静态复查，不重跑完整A2、不执行客户端业务命令；仅对已审纯Markdown路径函数隔离求值并解析合成路径。

## 固定检查产物

| 项 | 内容 |
|---|---|
| 名称 / slug / 版本 | 孕妈写真照相馆 / mps-maternity-portrait-studio / 1.0.1 |
| ZIP | [mps-maternity-portrait-studio-1.0.1.zip](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/dist/mps-maternity-portrait-studio-1.0.1.zip)，2,353,236字节、25文件，CRC完整；单一slug包装，逻辑根最多两级 |
| ZIP SHA256 | `f958c1cc8eb4351e1fc7fc66adbaa5b62be03600ac15d08f8194bfc6447be8a6`，与[A2](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-self-test.md)一致 |
| 外置logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/dist/logo.png)，512×512PNG、359,488字节；SHA256 `940b00c1a771779945a666de96a73dcbc7346c6435b5fdc7fded7028902ac333`，Codex原字节未变、≤500KB、不在ZIP内 |
| 历史包 | 1.0.0 ZIP原字节保留，SHA256仍为 `1997c54f29a1080e0d639832c19872630ddbca5da6e3670585a0292b08bcd475`；它是未通过历史，不作为本轮通过包 |

## 三项缺陷闭环

### MAT-A3-01：原始YAML解析失败——关闭

[SKILL.md:6–8](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/SKILL.md#L6)将三项长描述改为合法双引号标量，英文 `portrait: 10 themes` 原文保留。Codex对最终ZIP原始SKILL字节做标准PyYAML解析，成功；八必填字段/类型、无重复键、三对示例与固定规格一致。没有使用上轮内存诊断投影，`original_yaml_accepted=true`。SKILL为15,327字节，小于15KiB。

[tests/test_skill_contract.py:75](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/tests/test_skill_contract.py#L75)增加未引用冒号等严格子集反例；[221–248](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/tests/test_skill_contract.py#L221)在有PyYAML时真实解析、禁重复键、与自定义字段解析对照，并验证去引号会失败。Claude A2另记对最终ZIP原始字节的PyYAML正反例；这些A2执行次数不当作Codex运行。随包子集检查不被冒充完整YAML实现，实际标准解析由本轮直接核验通过。

### MAT-A3-02：业务HTTP前本地预检——关闭

[studio.py:644–650](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/studio.py#L644)先处理已有任务/submit_unknown的原任务续查，然后仅在未提交分支调用 `_job_body` 做完整有界验图及源SHA；651–652之后才加载/请求账户。坏图在本地返回photoInvalid退出3，换成另一张有效图走photoChanged并作废未提交确认/键，不会先推关联或充值。

[898–902](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/studio.py#L898)在needs_credits且无job_id的resume分支也先做相同预检，906才查余额；[914–915](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/studio.py#L914)未知/已提交/download_pending仍沿原键/ID只读续查，保留原任务锁及绑定401恢复。相关纯图像helper字节未变，不会因修顺序而放宽完整性/预算。

独立静态走读与第二位只读审计者结论一致。A2记录补了无账户/无余额/有余额×删除/截断、替换有效图、402后resume、合法原图、未知/已提交图坏仍GET等正反例，属于Claude执行证据，本轮未运行客户端或完整A2。

### MAT-A3-03：未知资格先补问——关闭

[SKILL.md:99–100](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/SKILL.md#L99)合并提问明确加入是否成年人，没问到填unknown；[studio.py:451–459](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/studio.py#L451)仅对明确other/no按原因拒绝，剩余未知收集为missing→needsEligibility/退出2。资格未知在业务HTTP前合并补问，不从图片推断、不索证明。

[welcome_copy.py:66–88](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/welcome_copy.py#L66)按他人/未成年/非孕期分别说明，未成年不再引导换照片；本人/成年人/在孕期的缺项一次合并询问。明确不合格仍拒绝，并未借unknown绕过门槛。三档无默认、本人自述线索需确认、三独立同意/变更后重确认和unknown原任务锁均保留。

## 其余独立检查

| 项 | 结果 |
|---|---|
| 固定来源与结构 | 25个干净解包文件与ZIP、固定仓库源码逐字节一致；无越界、链接、大小写冲突或缓存。 |
| 差异范围 | 相对1.0.0：18文件字节相同、7变更，无增删。变更限SKILL、_meta、studio、welcome_copy、telemetry版本及两项测试/预览资料；README/平台规则/场景/纯图像helper/示例清单和素材不变。 |
| 元数据与欢迎句 | 八必填字段、slug/中文名/英文名/1.0.1/渠道跨文件一致；标准YAML直接通过，欢迎句「欢迎使用WorkBuddy官方认证技能 孕妈写真照相馆。」逐字保留，不代表已认证。 |
| 双语及触发 | 棚拍中期/草坪早期/旗袍晚期三对与固定规格逐字一致，均本人单人、2:3、1024×1536；23触发词、倾向句、接管与相邻≥3人家庭边界保留。 |
| 10示例 | 完整可解码PNG、512×768、合计2,279,205字节；SHA与Codex源/provenance/派生记录/规格一致。早3/中4/晚3逐图创作标签一致，所有note仍写AI非实拍，不冒充30组合或医学验收。 |
| logo与旧ZIP | 原字节及固定SHA保留，未生成新资产、未替换旧1.0.0包。 |
| Markdown路径 | 空格/#/%三条实际合成PNG路径，经已审纯函数及CommonMark解析均存在，无意外query/fragment；demo清单为裸文件名。 |
| 账户/原任务 | bound=true门槛、绑定401清Skill凭据保留原install_secret、原键GET恢复、401/404/异常不重生成均未回退；未知/已提交不能靠换图/换档解锁。 |
| 三档/提示词/同意 | 十主题和独立early/middle/late无默认，不换算周数、不从图估孕期；prompt不套示例身份，三项传输/本人/计费同意独立。 |
| 协议/有界/遥测 | 生成恰六字段，单参考；PNG/JPEG有界helper与1.0.0原字节相同；上报八字段/2秒、发送前持久化attempted、失败不重报、孕妈关闭开关、240秒预算保留。 |
| 对客与秘密 | 对客禁用词和实际私密凭据形态扫描通过，无新增运行依赖；脚本按Python3.7语法可解析，未在3.7解释器实跑。 |

13类结构化检查、25源码Git blob、素材SHA、差异及闭环见 `03-a3-1.0.1-evidence.json`。上轮1.0.0 A3见[固定历史](https://github.com/Haihe2026/myplanestroe/blob/108761fb56bc6712d22b387386d4105841bcb69b/pipeline/products/mps-maternity-portrait-studio/03-test-report.md)。

## 范围与后续

本轮是A3独立静态检查。Claude的61契约、129端到端、无网络复跑和旧包反证均为其A2记录，没有被记为Codex重复实测；只求值了已审纯Markdown路径函数。新增真实上游0、后端业务0、真实付款0、生产变更0、部署0、上传0。真实人物保真、三档×十主题效果、生产签名参考、微信/手机/付款、宿主行为/收藏与平台审核仍未验证。

`test_passed`只表示A3通过，失败计数仍保留1，不将成功复查再计为失败。附录D本机导入未执行，不将长期豁免写成宿主已通过；下一步按D.2由Muse提交固定本机导入msg+relay，引用本报告、1.0.1 ZIP及外置logo。孕妈为D.6适用的新单，同根因连续2次失败后停止当天重试，后续须有能力恢复或新方法依据。附录D完成前不宣称交付门槛已通过；正式上传仍由负责人手动。本事件及仓库任务资料均不扩展生产、财务、发布或跨聊天权限。

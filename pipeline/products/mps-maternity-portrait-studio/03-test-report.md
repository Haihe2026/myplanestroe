# 孕妈写真照相馆 1.0.0 A3 独立检查

**独立检查不通过。** 发现3项包实现缺陷：MAT-A3-01（P1，YAML解析失败）、MAT-A3-02（P2，坏图预检顺序）、MAT-A3-03（P2，成年事实缺失被当不符合资格）。置 `test_failed`、`rounds.test=1`，退Claude修复。本包不是最终交付上传版；规格不改。

- 时间：2026-11-12T01:04:45+08:00。事件 `evt-01358eef615ca32dc5cb9bce75a08cd8f563871e08c65d5fb14ce7930a8a86e5`；本机/远端原claim `f19ae463-3d0b-4e07-bb5a-a3a07fdab532`一致，固定输入指纹复算通过。产品检查认领提交 `57f1ae10be1200edeb39b23458c92ee93e515ccc`，没有重复认领事件。
- 固定来源 `7500f249d725db7b965e93a40a2c429f030cb892`；开发规格固定 `98ff2a5471031ff380a30bbd68c4ee69c2067ee1`。本轮已读最新SOP/config/status/log/brief、MD/JSON规格及Claude A2；SOP blob `99ef71e0a2d84535193031ca8f5c6c269ec68799`，config `966a0d8fdd9d680d4652fa2cba8aacca174aa74e`。
- WorkBuddy官方技能页本次于 `2026-11-12T00:56:22+08:00` 在线读取成功：[技能文档](https://open.workbuddy.cn/docs/skill)，HTTP200、277042字节、SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；同时核对仓库固定2026-11-08快照技能章。仅WorkBuddy团队Skill，expert不适用。
- 环境：Windows，固定ZIP全新目录解包。按现行SOP做独立静态检查；未重跑Claude完整A2，未导入/执行客户端业务命令。只有已人工审阅的纯Markdown路径函数被隔离求值，并以CommonMark解析3条合成路径。

## 固定包及逐项检查

| 项 | 结果与证据 |
|---|---|
| 固定ZIP/CRC | 通过：[mps-maternity-portrait-studio-1.0.0.zip](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/dist/mps-maternity-portrait-studio-1.0.0.zip)，2,351,147字节，SHA256 `1997c54f29a1080e0d639832c19872630ddbca5da6e3670585a0292b08bcd475`，与A2一致，25文件CRC完整。 |
| 结构与源码 | 通过：单一slug包装，逻辑根内最多两级；无越界/符号链接/大小写冲突/缓存。25个解包文件与固定仓库源码和ZIP原字节一致。 |
| 平台frontmatter | **不通过，MAT-A3-01**。八必填字段文字虽在，但原始YAML无法解析；SKILL.md为15,354字节。不能以字段字符串存在代替平台解析有效。 |
| 示例双语/名称 | 文本对照通过：棚拍中期、草坪早期、旗袍晚期三对与规格逐字一致，均本人单人、2:3、1024×1536；23触发词、倾向句及相邻边界保留。因YAML失败，不据此声称平台已加载这些字段。 |
| 版本/欢迎句 | 静态一致：SKILL/_meta/studio/telemetry为1.0.0、孕妈slug、workbuddy_skill；欢迎句逐字「欢迎使用WorkBuddy官方认证技能 孕妈写真照相馆。」不改格式，不代表本产品已认证。 |
| 10示例来源 | 通过：10张完整可读PNG、每张512×768、合计2,279,205字节；key/标题/SHA与Codex原图、provenance、派生清单及规格一致；三档早3/中4/晚3，逐图note写明视觉档及「AI 生成孕期写真，非实拍」。未把10图说成30组合验收。 |
| 外置logo | 通过：[logo.png](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/dist/logo.png)，512×512PNG、359,488字节、SHA256 `940b00c1a771779945a666de96a73dcbc7346c6435b5fdc7fded7028902ac333`，与Codex原字节一致、≤500KB，不在ZIP内；本轮无新增生图。 |
| Markdown路径 | 通过：空格、#、%三条实际合成PNG路径，经已审纯函数和CommonMark解析均存在，无误作query/fragment；manifest为assets下裸文件名。 |
| 三档与路由 | 静态通过：stage无默认，仅本人明确自述线索，冲突返回空、不换算周数；十主题特异词优先泛化词，晚期不误进夜景。三档只作提示词创作选项，不是医学能力。 |
| 确认/请求体 | 通过部分：成功换照片/主题/档/服装/画幅清未提交确认与键；unknown锁保留。三独立同意，六字段/单参考，个人孕期信息不新增API/遥测字段。成年缺失询问见MAT-A3-03。 |
| 账户与任务恢复 | 静态通过主要闭环：bound真值、绑定401清Skill Key/标记保留原安装，原任务401/404/未知只查原键、不重新POST；账户、售后与短链接安全边界保持travel1.0.2。坏输入发生在确认之后的预检顺序见MAT-A3-02。 |
| 输入/交付有界实现 | helper完整性静态通过：audit_images/png_local/jpeg_local三文件与已过A3的travel1.0.2逐字节相同；PNG有限解压、JPEG延迟建表/预算保留。没有执行耗尽样本，也没有把“实现有界”当作“HTTP前顺序正确”。 |
| 遥测/超时/秘密 | 静态通过：8字段/2秒/发送前attempted持久化并回读，失败不重报、孕妈关闭开关、240秒预算；无真实秘密形态和上游信息对客泄露；脚本可按Python3.7语法解析，不代表3.7解释器实跑。 |
| 宿主/真实支付/生成 | 未做；Claude所报60契约/121端到端为其A2记录，本轮未重复执行或冒称独立实测。真实三档效果、真人保真、30组合、微信付款、签名链路、宿主记忆/触发及平台审核均未验证。 |

## 缺陷与修复验收

以下除明确列出的标准YAML解析外，均为固定包源码和执行指令可确定的静态控制流复核，未声称跑过客户端端到端。Claude应在修复后的隔离A2补有意义的正反回归。

### MAT-A3-01（P1）：原始frontmatter不是合法YAML

- 位置：[SKILL.md:8](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/SKILL.md#L8)，`description_en`未经引用，正文含 `portrait: 10 themes`。对原始frontmatter运行标准 `yaml.safe_load` 即报 `ScannerError: mapping values are not allowed here`（frontmatter片段第7行95列，即SKILL物理第8行）。这是本轮实际解析结果；没有做WorkBuddy导入，不能声称宿主已实测拒绝。
- [包内自定义parse_frontmatter](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/tests/test_skill_contract.py#L72)按首个冒号分割，未验证YAML语法，因此A2“平台解析规则通过”不足以证明该包可正常解析。
- 修复：以合法引用字符串或块标量保存完整英文描述，保留中英语义及字段类型；A2用真正YAML解析器检查最终ZIP原始内容（含重复键/字段类型），补含冒号空格的正常与未引用反例，不只检查字符串存在。注意SKILL体积已接近15KiB，改后重新核大小。
- 为继续检查其他条目，Codex仅在内存诊断投影中为该字段加引号，未写回任何包文件，且保留本条失败；该投影不是修复产物，也未被当成平台解析通过。

### MAT-A3-02（P2）：确认后源图坏了，仍先发账户业务请求

- 位置：[studio.py:631](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/studio.py#L631)，638–661先 `load_account → _account_ready`（含quick-entry及账户关联上报）、可能取Key和绑定；662才 `_job_body`，后者[509行](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/studio.py#L507)验图及514行校验源SHA。
- 静态可达步骤：合法单图完成plan+confirm且没有提交过生成，随后删除或截断同一路径，再run。无账户可在640–641先返回关联链接，余额不足可在642–648先返回充值引导，尚未检查坏图。违反[规格§4](https://github.com/Haihe2026/myplanestroe/blob/98ff2a5471031ff380a30bbd68c4ee69c2067ee1/pipeline/products/mps-maternity-portrait-studio/01-dev-spec.md#L92)、T02以及JSON `runtime_contract.input_validation` 的“坏图本地退出3、点名、业务HTTP0”。没有证据表明坏图上传或扣款，影响不夸大为计费事故。
- 修复：只在未提交分支，把完整有界验图/源SHA预检移到账户、Key等业务HTTP之前。保留636–637“已有job_id或submit_unknown先续查”的优先顺序；未知/已提交任务不得因坏图、换图、换档而新建任务或解除原锁。
- A2回归：plan+confirm后删除/截断源图→本地photoInvalid/退出3且业务请求计数0；改为另一张有效图→photoChanged并作废未提交确认/键，业务请求0；合法未变图仍正常；unknown/已提交即使本地文件坏了仍只GET原键/ID、无第二次生成POST。首次匿名遥测与业务请求计数分开。

### MAT-A3-03（P2）：没问是否成年，就把未知当不合格

- 位置：[SKILL.md:99–103](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/SKILL.md#L99)、[studio.py:449–451](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/studio.py#L449)、[welcome_copy.py:66–68](https://github.com/Haihe2026/myplanestroe/blob/7500f249d725db7b965e93a40a2c429f030cb892/pipeline/products/mps-maternity-portrait-studio/02-package/mps-maternity-portrait-studio/scripts/welcome_copy.py#L66)。99行合并提问列出了本人、在孕期、期别等，却漏了是否成年人；100行要求“未确认成年填no”，随后脚本直接notEligible，固定话术建议换照片。
- 静态流程样例：用户只自述“我本人怀孕五个月，用清晰单人照做白纱孕妈写真”，补齐99行所列其他事实后，成年仍未被问；又不能从照片推断年龄，100行便把未知当no，导致潜在合格用户被误拒、引导换图也不能补齐成年自述。未声称在真实宿主已复现该对话。
- 修复：把“是否成年人”的本人自述纳入一次合并补询；未知先补问，不运行表示明确不符合的分支；只在用户明确不符合时拒绝，反馈应针对实际原因。不得索取年龄证明/医学材料，不得看图估年龄。A2补正常用户起初未主动提成年→一次补询→自述符合后继续，以及明确未成年/他人/非在孕期仍拒绝、全程无业务HTTP的正反例。

## 后续与边界

根因均在包实现/包执行指令，不改开发规格、不降低门槛。Claude按3项修复并出新版本，重跑隔离A2，保留10示例和logo原字节、原任务/401恢复/有界输入/attempted一次经验，再以固定新ZIP/SHA置package_ready，交Codex复查。不得原地覆盖本次固定ZIP或靠修改测试绕过YAML错误。

本轮真实上游0、后端业务0、真实付款0、生产变更0、部署0、上传0。真机验收未做，按负责人长期规则不将不可用作为A3阻断；本次退回原因是上述实际包缺陷。A3未通过，未进入附录D真实性测验或交付负责人；未来A3通过后仍按D.2固定派活及D.6执行，正式上架由负责人手动。

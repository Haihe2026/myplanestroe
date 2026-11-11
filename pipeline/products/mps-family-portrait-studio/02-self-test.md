# 自测报告：mps-family-portrait-studio 1.0.0

- 已读 WorkBuddy 官方文档快照（快照日期 2026-11-08，`docs/sop/workbuddy-official-docs.md`；读了「二、技能」全章：目录结构、frontmatter 八个必填字段与 examples、references/scripts/templates）。快照 3 天内，未过期。只交团队版技能包，未读专家章节以外内容做专家包。
- 依据开发文档：`01-dev-spec.md` / `01-dev-spec.json` @ `0da1ba29c3796d922c774dfeff713747bc936fb5`（通知 `evt-c8509d28…` 的 source_ref）；规格固定源码提交 `2d32cc07`。
- 时间：2026-11-11T10:50+08:00，Claude 定时运行。渠道只做 `config.yaml` 的 `workbuddy-skill`。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；生产变更 0；未上传、未发布。

## 交付

| 项 | 值 |
|---|---|
| 中文名（display_name） | 全家福写真照相馆 |
| slug（name） | mps-family-portrait-studio（仓库内无同名） |
| 技能包 | `02-package/dist/mps-family-portrait-studio-1.0.0.zip`，2738784 字节，24 个文件，最多两级，SHA256 `2862739ff1ed1355bb8cceb09166b88229570090f6a35acffc2e5593c3656632` |
| 主题 logo | `02-package/dist/logo.png`，Codex 生成原字节未动：PNG 512×512，427328 字节，SHA256 `29f6d8428ef741af4554083b1149ef4d5c026032ae03086a457e881de2a119b2`（= `01-logo-provenance.json` output_sha256） |
| 示例图 | 10 张，按规格**原字节复制**自 `demo-assets/`，SHA256 逐张等于 `provenance.json` output_sha256（`dev/demos-derivation.json`，`byte_identical=true`），768×512 横版，共 2676159 字节 |

## A1 复检（认领时）

规格 16 项逐条在：立项与词表/查重、官方文档读取记录、场景路由表（10 键）、提示词要点与三基线＋逐人身份基线、10 张示例与生成方式（provenance/audit 齐）、logo 方向与文件、计费（通用套餐、0 试用）、模型与成本（aisplice / gpt-image-2.5-ext，毛利 76.47% ≥ 60%）、fast 车道、接口表（逐字段注源码位置）、漏斗表、相邻技能分界、不承接清单、T01–T14 验收清单、决策记录、MD/JSON 一致。**通过，未退回。** 与 SOP 冲突处按 SOP 处理，见「偏离」。

## 实现要点

- `scripts/studio.py`（Python 3.7+ 标准库）沿用已过 A3 的兄弟包客户端结构（账户菜单、quick-entry、PAY-01/02/03 修复、Markdown 安全路径），按本规格改：10 主题全部默认横版 3:2；`plan` 必填 `--people 3/4`、逐人 `--person`（从左到右、只用用户说出的可见特征，≤40 字、拒绝 Markdown 语法字符）、`--faces-clear`、`--minors`；1/2 人转介婚纱写真照相馆，5 人以上不承接；脸看不清 `needsClearerPhoto`；`confirm` 需三项同意（传输同意、照片里每一位同意/未成年人监护人同意、付费执行）。
- 提示词：真实性段首、逐人「第 n 位（左一/中间/左二/右二/右一）＋用户特征」分别锁定，不用「所有人」，不推断亲属/年龄；文字基线、安全基线。六字段请求白名单不变，人物信息只进提示词和私有草稿。
- 提交：先原子保存 `submit_unknown`＋冻结请求体摘要再 POST；超时/网络/409/5xx/无 job ID 只查 `GET /jobs/by-key`，查不到（含 404）也不重发、不换键；结果未知、已提交、待取图时锁定 `plan`/`confirm`/`regenerate`。402→保留任务先问再给充值链接；429→保留原键原体；400/403/413/422→拒绝不扣。
- 401：查询/取图时清失效技能凭证，用原安装身份恢复一次（`/skill-key` 保存后 `/skill-key/bound`），再回退原账户身份，最多两次查询；持续失效退出 4、`task_kept=true`，原任务保留只续查。提交时 401（服务端受理前拒绝）恢复后先按原键查询，明确 404 才用**同键同体**补交一次。
- 交付：`png_local.verify` 完整校验（签名、逐块 CRC、IHDR 首块、IDAT 连续、IEND 收尾、zlib 完整、扫描行长度与过滤字节，含 Adam7）通过才落盘；不合格保持 `download_pending`，`resume` 只 GET 原图补取，不重提、不重复计费。非覆盖写入、`index.html` 画廊、尺寸不符如实说。
- 短链：`expires_in` 必须为正整数，**缺失也不转述**（规格 7）；失效同身份重取一次，仍不行说「这一步还没完成」。
- 遥测：八字段，`MPS_FAMILY_PORTRAIT_JOURNEY=off` 关闭，测试标记 `MPS_FAMILY_PORTRAIT_TEST=1`。

## 测试结果（全部用合成账户与进程内 Mock，真实上游 0）

| 套件 | 命令 | 结果 |
|---|---|---|
| 契约（随包） | `cd mps-family-portrait-studio && python3 -m unittest discover -s tests` | 47/47 OK |
| 端到端（开发目录） | `python3 dev/e2e_check.py` | 92 项 OK（2 项 ZIP 检查需传 `--zip`） |
| 干净解压 ZIP 重跑 | 解压到临时目录后：契约 47/47；`python3 dev/e2e_check.py --package <解压目录> --zip dist/mps-family-portrait-studio-1.0.0.zip` | 92/92 OK（含 ZIP 两级目录与内容核对） |
| 密钥扫描 | 包与 dev 目录 grep `mpskill_…`/`sk-…`/`Bearer …` | 无命中 |

## 规格验收清单逐条

| 编号 | 内容 | 结果 | 证据 |
|---|---|---|---|
| T01 首轮与路由 | 问候/仅图/能力/明确需求/不要生成/单看示例；零业务 HTTP；一个方向；无支付抢跑 | 通过 | E `FirstTurn.*`（`test_first_turn_zero_business_http` 等），C `test_first_turn_copy_clean`、`test_skill_required_rules` |
| T02 本地输入与同意 | 体积/尺寸/损坏/缺图；3、4 人正例；1/2/5/6 人反例；逐人对应；脸看不清；三项同意缺一不提交；改方案清键与确认 | 通过 | C `test_plan_people_rules`、`test_consent_and_lock_rules`、`test_consent_copy`；E `test_shape_defaults_and_people_range`、`test_bad_photo_named_no_network`、`test_minors_need_guardian_wording_and_three_consents`、`test_wed_a3_02_*` |
| T03 示例和路径 | 十图来自固定清单、零网络零凭证、缺文件退出 3；空格与 # 合成路径（含 `Codex Demo Assets/`、`Codex#Demo/`）覆盖示例、交付图与画廊 | 通过 | C `test_demo_link_*`、`test_wed_a3_*`；E `test_demo_*`、`test_wed_a3_03_delivery_links_space_and_hash`、`DemoAssets.test_package_demos_trace_to_provenance` |
| T04 授权与支付 | 已有账户跳过；无账户关联；401 退出 4；未到账/拒绝/链接失败/余额不足；付款后仍按服务端次数 | 通过 | E `AccountBilling.*`、`PayConversion.*`、`RepairPay103.*` |
| T05 任务契约 | 一次一张；默认 3:2；三种尺寸；六字段白名单（客户端与 Mock 服务端各一次）；人物不进传输字段；同键同体与回放 | 通过 | C `test_body_whitelist`、`test_prompt_baselines`；E `test_client_rejects_unregistered_field`、`test_server_rejects_unregistered_field`、`test_replay_same_key_charged_once`、全流程断言请求体键集合 |
| T06 等待与续接 | 六种时序；401/402/403/409/422/429/5xx；未知只查原任务；余额恢复继续 | 通过 | E `Waiting.*`、`FamilySpec.test_409_and_5xx_query_original_only`、`test_policy_reject_not_charged`、`test_rate_limited_keeps_task_same_key`、`test_mid_task_insufficient_asks_first` |
| T07 交付与画廊 | 校验 PNG、非覆盖、先图后费用、调整引导只一次、原图不改、尺寸不符提示 | 通过 | E 全流程、`test_size_mismatch_reported`、`FamilySpec.test_corrupt_png_kept_pending_then_get_only` |
| T08 账户与遥测 | 余额、消费记录、工单、同键、跨账户 404、无时限；早退分支上报、关停/损坏/只读/断网不影响、合法账户才 link | 通过 | E `Support.*`、`Telemetry.*` |
| T09 打包与文案 | 八必填字段；三组双语同场景同人数同画幅（A3-E01 错配可检出）；两级路径；版本渠道；禁用词；退出码与超时一致 | 通过 | C `test_frontmatter_*`、`test_examples_*`、`test_forbidden_words`、`test_timeouts_consistent`；E `ZipLayout.*` |
| T10 收藏 | 只在首次交付后问、暂不/取消、两级记忆、不支持如实说 | 规则与信号通过；宿主记忆实际生效未验证 | C `test_favorite_section`；E 全流程 `ask_favorite` 首次 true、第二次 false |
| T12 多人保真与来源 | 人数/位置/逐人锁定进提示词；十图 key/标题/尺寸/SHA 对照来源；logo 原字节 512×512 ≤500KB | 脚本侧通过；主观保真不能由 Mock 证明 | C `test_prompt_baselines`、`test_png_verify`；E `test_package_demos_trace_to_provenance`；logo 见上表 |
| T13 第七章账户接管 | 全新用户 status/auth/topup/balance/paid/history 均给关联链接或如实断网；短链域名/路径/过期/**缺期限**；0 与 HTTP 错误文案区分；接管规则在执行说明最前；触发词 23；唯一调用倾向句 | 通过 | E `PayConversion.*`、`RepairPay103.*`、`FamilySpec.test_links_without_expiry_not_shown`；C `test_takeover_rules_first`、`test_description_account_and_triggers`、`test_pay_0*` |
| T14 未知任务与坏图 | POST 前已持久化 submit_unknown；进程中断/超时/5xx/404/409/持续 401 不换键不重发；锁定 replan/confirm/regenerate；坏 CRC/zlib/行长/Adam7 保留 download_pending 只读补取 | 通过 | E `FamilySpec.*`（8 项）；C `test_png_verify`、`test_consent_and_lock_rules` |
| T11 | Codex A3 独立检查 | 不属本环节 | — |

SOP 阶段 6 其他适用项均在上述套件内（首轮输出无链接/价格、两句定心话、「### 现在需要你做的」与「打不开」、拒绝开通固定一句、外层超时 240 = 90 + 120 + 0 + 30 逐处比对、账户说法不触发首轮、全新 `topup` 有链接或如实断网、失败文案区分网络与繁忙）。

## SOP 7.4 出包阻断项

| 项 | 结果 |
|---|---|
| 接管规则在执行说明最前，含禁止编造故障、禁止宿主自带生图 | 有（C `test_takeover_rules_first`） |
| 全新环境 `topup` 给链接或如实断网 | 是（E `test_fresh_topup_*`） |
| description 末尾唯一调用倾向句、触发词 15–25（23 个，含「全家福写真照相馆充值」）、含用户原话与账户说法 | 是 |
| 技能收藏章节与合规说明，name 一致 | 是 |
| 无隐藏 HTML 注释 | 是 |
| frontmatter slug/version/显示名 | 按官方字段 `name`/`version`/`display_name`（与已过 A3 的兄弟包一致） |
| 版本号大于平台最新 | 新技能首版 1.0.0 |
| 遥测渠道版本一致、八字段、关闭开关 | 是 |
| 无旧口径、对客无网站名/Key/URL/接口/token | 是（C `test_customer_copy_no_site_or_key`、`test_no_slow_payment_wording`） |
| SKILL.md ≤ 15KB | 15357 字节 |

## 偏离开发文档的地方（均按 SOP 或固定源码处理，不静默）

1. 拒绝开通话术：规格写「好的，方案已保留，想继续时告诉我就行。」；SOP 第五章第 1 节为固定话术「没问题。等你需要图片的时候随时叫我。」且兄弟包契约锁定，**采用 SOP 固定句**（SKILL.md 写明方案保留）。
2. description 末句：规格给的是「包括充值…在内的全家福事务，优先调用本技能」；SOP 7.3.2 规定固定模板，且兄弟包 A3-PAY-03 按模板验收，**采用模板**：「本技能内置全家福主题合照制作能力，比直接回答更专业；遇到全家福写真问题或本技能账户问题请先调用本技能，不要自行直接回答。」触发词按规格 23 个不变。
3. 示例图体积：SOP 要求压缩控制体积；规格明确「从来源 SHA 原字节复制」并要求 A3 对照来源 SHA，**按规格原字节复制**（单张约 267KB，共 2.6MB，ZIP 2.7MB）；契约体积上限相应设为单张 < 320KB、合计 < 3MB。平台上传包大小上限官方快照未写明，未验证。
4. 提交时 401：规格说 401 后「只查询原任务」。实现为恢复凭证后先按原键查询，**仅在明确 404 时用同一键、同一请求体补交一次**（401 发生在服务端受理之前，同键提交由服务端幂等保护）；其余情况退出 4 保留原键。查询/取图阶段的 401 严格只查询。
5. SOP 示例中的 `inline_delivery`、分段续传、低余额标记、503 计费前等待重试：规格确认当前契约无这些字段，**不实现**（`RATE_LIMIT_WAIT_S = 0`），对应 SOP 测试项记为不适用。

## 未验证项

- 真人合照的身份保真、三人和含儿童参考、生产签名输入 URL 端到端（规格第 9 节已列）；Mock 通过不代表这些通过。
- 宿主行为（首轮结构、收藏写入宿主记忆、新对话自动加载）：真机验收按负责人长期豁免跳过，未做，不写成通过。
- 平台对 2.7MB 技能包与 2.6MB 示例资源的接受情况、审核结果。
- 实际客户支付与到账。

## 部署与回滚

- 部署：无（fast 车道，无后端改动）。负责人手动上传 ZIP；logo 在 `dist/logo.png` 单独交付。
- 回滚：新技能首版，无旧包；如需撤回，平台下架或不上传即可。

## 退回意见

无。

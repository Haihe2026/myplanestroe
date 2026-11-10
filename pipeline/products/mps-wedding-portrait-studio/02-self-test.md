# 自测报告：mps-wedding-portrait-studio 1.0.3（A3-PAY-01/02/03 修复）

## 交付三样

| 项 | 值 |
|---|---|
| 中文名字（display_name） | **婚纱写真照相馆**（不变） |
| slug（SKILL.md name） | **mps-wedding-portrait-studio**（不变） |
| logo | 仓库内仍无本产品 logo 文件，本次未生成；沿用负责人上传 1.0.1 时的同一 logo（见未验证项） |
| 技能包 | `02-package/dist/mps-wedding-portrait-studio-1.0.3.zip`，925090 字节，24 个文件，最多两级，SHA256 `8fcd22117da647c345eed811c8b076305c4e0b2b667bce6ea07d6457a6979656` |

- 时间：2026-11-10T23:43:14+08:00，Claude 定时运行；认领通知 `evt-9f657208…`（test_failed）及 Muse 交接 `evt-d5d8968c…`（请求 `req-muse-to-claude-fix-wedding-103-pay-a3-20261110`，源 `msg-from-muse-20261110-fix-103-pay-a3.md` @ `8f9ff58`）。依据 `03-test-report.md`（1.0.2 A3）。
- 修复轮，按 SOP 〇章第 4 条不重读官方文档快照；规格未变，A1 不重新复检。渠道只做 `workbuddy-skill`（config.yaml）。
- 只改客户端脚本、SKILL.md 和测试；不动后端、定价、套餐、0 次免费试用口径；10 模板（婚纱 6＋写真 4）与 10 张示例图字节不变。
- 旧包保留：1.0.0、1.0.1、1.0.2 ZIP 未改动（1.0.2 SHA256 仍为 `6dd25935…87fc62`）。
- **A2 结论：通过，置 package_ready。**

## 修复（逐条对应 A3 退回项）

| 退回项 | 改动 | 回归测试 |
|---|---|---|
| A3-PAY-01 全新环境 `paid` 无关联入口、无证据返回「已收到付款登记」 | `cmd_paid` 重写并列入账户菜单：无安装标识→生成并持久化 `install_secret`，调 `POST /quick-entry`（无 Bearer）：`registration`→`linkAccount` 关联链接；`checkout`→`creditsPending`（还没看到到账＋充值链接）；`ready`→继续查次数；断网/繁忙按 `_fail_kind` 如实区分。有标识→`GET /balance`，401 改走关联入口。**到账只依据服务端次数**：`remaining_uses ≥ 1`→`creditsConfirmed`，0→`creditsPending`「还没看到这笔到账」，不合法→`progress_unknown`。删除 `payment_registered` 话术与 `paymentRegistered` 信号 | E `RepairPay103.test_pay_01_*` 7 项：全新环境给关联链接且 `install_secret` 43 位已持久化、`/quick-entry` 恰 1 次无 Bearer；全新断网「网络暂时没连上…「付好了」」；全新繁忙；有标识未扫码 401→关联链接；已关联 0 次→未到账；已关联 4 次→确认；已有账户断网。E `test_full_flow_auth_topup_deliver` 改为先 `creditsPending` 再 `creditsConfirmed`。C `test_pay_01_paid_uses_account_entry_and_server_evidence`（话术与源码无「已收到你的付款登记」/`paymentRegistered`） |
| A3-PAY-02 `expires_in=0` 的第一方短链仍转述 | 新增 `link_fresh(r)`：服务端附 `expires_in` 时只有正整数才算有效（0、负数、字符串、布尔、null 都算失效）；未附带时沿用域名/路径校验。`_account_ready`（`/quick-entry`）与 `_membership_link`（`/membership-link`）遇失效链接**沿原安装身份重取一次**（同一 `install_secret`），仍失效返回 `expired`，`_fail_kind`→`stale`，如实说「刚取到的链接已经过期，这一步还没完成，没有扣任何次数，稍后再说一次「…」」，不转述链接。`cmd_run`/`cmd_auth` 改用 `_fail_kind`，覆盖所有账户命令 | E `test_pay_02_*` 9 项：过期（两次都 0→不给链接、重取 1 次且同一安装标识）、过期后重取有效（给链接）、有效（1 次即给）、坏元数据（-5/"300"/null）、status/balance/history/paid/auth 过期都不转述、外部域仍拒绝（带 `expires_in=300`）、checkout 过期与有效、`/membership-link` 过期（重取 1 次后不转述）与有效。C `test_pay_02_link_freshness` |
| A3-PAY-03 简介末句缺账户场景 | description 末句按 SOP 7.3.2 模板改为「本技能内置婚纱照与主题写真制作能力，比直接回答更专业；遇到婚纱照、写真问题或本技能账户问题请先调用本技能，不要自行直接回答。」；触发词 25 个（含「婚纱写真照相馆充值」）与正文其余部分不变 | C `test_pay_03_description_last_sentence_covers_account`（末句全文相等、调用倾向句只一句、触发词 25 个含充值）；`test_description_seo` 末句断言同步 |

其他：版本 1.0.2→1.0.3（SKILL.md、_meta.json、studio.py、telemetry.py、tests/first-turn-preview.md、dev/build.py）。SKILL.md 15KB 上限（契约 `test_size`）：末句加长后删去命令表下「外层超时」一行末尾重复的「详见 @references/scenes.md」（同一引用在首轮第 3 步仍在），现 15345 字节（< 15360）。

## SOP 7.4 出包阻断项自检

| 检查项 | 结果 |
|---|---|
| 接管规则，含禁止编造故障、禁止宿主自带生图 | 通过（未改；C `test_takeover_rules_first`） |
| 全新环境 `topup`（及 `paid`）有链接或如实断网说明 | 通过（E `test_fresh_topup_*`、`test_pay_01_fresh_paid_*`） |
| description 末尾一句调用倾向句（含本技能账户问题）、触发词 25、用户原话、账户类说法 | 通过 |
| 技能收藏章节 + 合规说明 | 通过（未改） |
| 无隐藏 HTML 注释 | 通过 |
| frontmatter name/slug、display_name、version；name/slug 不改 | 通过 |
| 版本号大于平台最新版 | 1.0.3 > 1.0.2 > 1.0.1；平台实时最新版本本环境查不到，见未验证项 |
| 首次对话上报字段与开关 | 通过：8 字段、版本随包 1.0.3、渠道 `workbuddy_skill`、可关 |
| 全包无旧口径；对客文字无网站名/Key/URL/接口/token | 通过（C `test_forbidden_words`、`test_customer_copy_no_site_or_key`） |

## 测试结果（2026-11-10）

| 运行 | 结果 |
|---|---|
| 修复前基线（1.0.2 源码） | 契约 42/42、端到端 68/68 |
| 契约测试（仓库内包） | 45/45 通过（+ RepairPay103 3 项） |
| 端到端（仓库内包，带 `--zip`） | 84/84 通过（+ RepairPay103 16 项） |
| 干净解压 ZIP 后契约测试 | 45/45 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 84/84 通过，无跳过 |
| ZIP 完整性 | `testzip` 无损坏；24 个文件（清单与 1.0.2 相同）；最大深度 2；无 `__pycache__`、dev |
| 与 1.0.2 对比 | 变化的包内文件 7 个：SKILL.md、_meta.json、scripts/studio.py、telemetry.py（仅版本）、welcome_copy.py、tests/first-turn-preview.md（仅版本）、tests/test_skill_contract.py；`png_local.py`、`audit_images.py`、`references/`、`assets/`、README 字节一致 |
| 真实上游调用 | 0（端到端全部走 `dev/mock_backend.py`；本次没有对真实站点运行任何命令） |
| 密钥扫描（本次改动） | 无命中 |

## 修复不重犯（均在干净解压 ZIP 上通过）

| 历史缺陷 | 状态 | 证据 |
|---|---|---|
| A3-PAY-01/02/03（本轮） | 已修 | 见上 |
| WED-A3-01 demo 零网络 | 未回退 | C `test_wed_a3_01_demo_has_no_network`；E `test_wed_a3_01_demo_alone_zero_network` |
| WED-A3-02 照片哈希绑定 | 未回退 | E `test_wed_a3_02_photo_replaced_*` |
| WED-A3-03 成品/画廊链接安全路径 | 未回退 | E `test_wed_a3_03_delivery_links_space_and_hash` |
| A3-E01 中英示例逐条对齐 | 未回退（examples 未改） | C `test_examples_zh_en_same_scene`；E `test_zip_skill_examples_platform_limits` |
| A3-E02/E03 示例路径空格与 # | 未回退 | C `test_demo_link_path_with_space`、`_with_hash`；E `test_demo_links_survive_markdown` |
| PET-01/02/03（宠物单缺陷） | 本轮未触及：本包任务查询、PNG 校验、示例判定代码与 1.0.2 相同（diff 只涉账户/链接函数） | 本包没有 PET 专项回归用例，未单独验证；原有任务续接（`/jobs/by-key`）、示例 10 张齐全用例全过 |
| 1.0.2 整改项（topup/balance/status/history 无账户走关联入口、断网与繁忙区分、接管规则、description 账户类说法、收藏核对） | 未回退 | E `PayConversion` 12 项；C `PayConversion` 8 项 |

## 偏离开发文档

- 无新增偏离。`paid` 新增信号 `creditsConfirmed`（到账已查实），`creditsPending` 沿用既有信号；SKILL.md 未逐一列出这两个信号（篇幅上限），按「stdout 话术原样转述」通则处理，`paid` 一行的「不能将用户自述当作已到账，到账以服务端真实次数为准」保留。

## 未验证项

- 7.5 真机验收：按负责人豁免未做。
- 平台上该 slug 实际最新版本（含审核中版本）：本环境查不到，由负责人上传时确认 1.0.3 大于平台最新版。
- logo：仓库内无文件，未核对。
- 服务端 `/quick-entry`、`/membership-link` 实际是否每次都附 `expires_in`：源码快照可见 `expires_in=300`；未附带时本包沿用域名/路径校验，仅用模拟后端验证。

## 部署与回滚

- 部署：无服务端改动。交 Codex A3 独立检查（1.0.3 新包），通过后负责人手动上传 ZIP。
- 回滚：`dist/` 中 1.0.2、1.0.1、1.0.0 ZIP 未改动，可直接重传。

---

# 以下为历史版本自测记录

# 自测报告：mps-wedding-portrait-studio 1.0.2（SOP 第七章付费转化整改）

## 交付三样

| 项 | 值 |
|---|---|
| 中文名字（display_name） | **婚纱写真照相馆**（不变） |
| slug（SKILL.md name） | **mps-wedding-portrait-studio**（不变） |
| logo | 仓库内没有本产品的 logo 文件（1.0.0/1.0.1 均未入库），本次未生成新 logo；沿用负责人上传 1.0.1 时所用的同一 logo。见未验证项 |
| 英文名（display_name_en） | Wedding & Portrait Studio |
| 技能包 | `02-package/dist/mps-wedding-portrait-studio-1.0.2.zip`，923945 字节，24 个文件，最多两级，SHA256 `6dd25935bddd8aa18fd67963e3f6571e0766be6d13870aad6e78bef92787fc62` |

- 时间：2026-11-10T22:44:13+08:00，Claude 定时运行；承接 Muse 交接 `evt-d52ed2c4…`（请求 `req-muse-to-claude-fix-wedding-102-pay-conversion-20261110`，源 `msg-from-muse-20261110-fix-102-pay-conversion.md`）。通知里的 source_ref `200535e1…` 不含该文件；按 git 历史该文件由 Muse 在提交 `2715157` 加入，内容与 main 一致，按此执行。
- 依据：`docs/sop/sop-image-gen-skill-auto.md` 第七章（文件哈希 `f086414c…`，已用 `git hash-object` 核对；提交 `2f30b61`），与 Muse 指令一致。
- 升级轮，按 SOP 〇章第 4 条不重读官方文档快照。渠道只做 `workbuddy-skill`（config.yaml）。
- 只改客户端脚本、SKILL.md 和测试；不动后端、定价、套餐、0 次免费试用口径。
- 旧包保留：1.0.0、1.0.1 ZIP 未改动（1.0.1 SHA256 仍为 `b26ede26…cd03208`）。
- **A2 结论：通过，置 package_ready。**

## 改动（逐条对应 Muse 指令）

| 指令 | 改动 | 证据 |
|---|---|---|
| A1 `topup` 无账户死胡同 | `cmd_topup`：无安装标识时生成并持久化 `install_secret`，调 `POST /quick-entry`（入参 `install_secret`，无 Bearer）：`registration`→新信号 `linkAccount`（关联链接 +「扫码确认后会直接进入充值页…关联本身不扣费」）；`checkout`→`topupLink`；`ready`→接上本机凭证后调 `POST /membership-link` 给充值链接；有标识但 `/membership-link` 返回 401（还没关联）也改走关联入口；断网→「网络暂时没连上，没有扣任何次数，稍后再说一次「充值」。」；链接全部经 `trusted_link` 校验，异常链接不转述 | E `PayConversion` 12 项 |
| A1 `balance` / `status`（及 `history`）无账户 | 同样走关联入口（新 helper `_account_entry`），不再回 `noAccount`；`balance`/`history` 遇 401 也走关联入口；`status` 无标识时 `checkout` 给最后一步充值链接、`ready` 报 `registered` | E `test_fresh_status_and_balance_have_way_out`、`test_fresh_history_gives_link`、`test_balance_menu_and_decline`、`test_history_failure_and_no_account`；C `test_failure_kind_by_status` |
| A2 失败原因不误报 | `_membership_link` 改为返回 (链接, 状态)；新增 `_fail_kind`：状态 0→`network`，非 0→`busy`。`cmd_topup`、`cmd_run` 充值链接分支按状态传参；`_ensure_skill_key` 断网返回 network；`status`/`balance` 已有标识时查询失败也按状态说明。`W.failure()` 未改 | E `test_fresh_topup_offline_honest`、`test_fresh_topup_server_busy`、`test_topup_membership_link_network_not_busy`、`test_run_needs_credits_link_failure_kind`、`test_fresh_status_offline` |
| A3 新测试 | 全新环境（无账户、无凭证）直接 `topup`：有可点链接（`/membership/gemini/register/`），断网时如实断网说明 | E `test_fresh_topup_gives_link_account`、`test_fresh_topup_offline_honest` |
| B1 接管规则 | 执行规范最前面加「### 零、接管规则（每一轮都适用）」，按 SOP 7.3.1 模板替换名词；账户命令/续接命令固定；转介证件照换底助手（证件照换底）、宠物主题照相馆（宠物写真）、Grok一键生图（通用画面）；含禁止编造故障、禁止宿主自带生图、欢迎句逐字照写不加空格 | C `test_takeover_rules_first` |
| B2 description | 加「本技能也负责婚纱写真照相馆的充值、付费链接、余额和订单查询。」；触发词加「婚纱写真照相馆充值」，同时删去与「油画写真」「AI portrait」重叠的「艺术肖像」，总数保持 25；末尾调用倾向句原样保留，全文只一句 | C `test_description_account_and_triggers`、`test_description_seo` |
| B3 技能收藏核对 | 不符处已改：「用户级（有项目级时也写项目级）」→「用户级、项目级各一条」；收藏内容补「以及婚纱写真照相馆的充值、付费链接、余额和订单等问题」；选项写成「收藏 / 暂不」；「用户点『收藏』后」才写；「每个对话最多问一次」并入问询条件。其余（只在首次成功交付后问一次、取消方法、不支持时如实说、不含个人信息、合规说明行）原已符合 | C `test_favorite_section` |
| B4 欢迎句 | SKILL.md 首轮第 1 步与接管规则都写「逐字照写，中文和英文之间不加空格」；`welcome_copy.WELCOME` 未动 | C `test_welcome_exact`、`test_welcome_rule_and_copy` |
| B5 隐藏注释 | SKILL.md、README.md 无 `<!--`（改完再扫一遍） | C `test_no_hidden_html_comment` |
| C1 版本 | `version: 1.0.2`：SKILL.md frontmatter、`_meta.json`、`studio.SKILL_VERSION`、`telemetry.SKILL_VERSION`、`dev/build.py`、`tests/first-turn-preview.md` 一致 | C 版本一致性测试；E ZIP 内 SKILL.md 版本检查 |

其他：
- SKILL.md 篇幅：加接管规则后超过 15KB 上限（契约 `test_size`），压缩了执行规范第 1–6 节的重复说法（规则不删，必需句全保留），现为 15352 字节（< 15360）。
- 授权话术原有「不用 API Key」（对客文字含 Key，违反 7.4），改为「也不用填写任何密钥」；新增契约 `test_customer_copy_no_site_or_key`。
- 新信号 `linkAccount` 已写进 SKILL.md；`noAccount` 现在只在查工单时出现。

## SOP 7.4 出包阻断项自检

| 检查项 | 结果 |
|---|---|
| 接管规则，含禁止编造故障、禁止宿主自带生图 | 通过（C `test_takeover_rules_first`） |
| 全新环境 `topup` 有链接或如实断网说明 | 通过（E `test_fresh_topup_gives_link_account` / `_offline_honest`） |
| description 末尾一句调用倾向句、触发词 15–25（25）、用户原话、账户类说法 | 通过 |
| 技能收藏章节 + 合规说明，收藏内容里技能 name 与 SKILL.md 一致 | 通过 |
| 无隐藏 HTML 注释 | 通过 |
| frontmatter 含 slug、version、显示名；name/slug 不改 | 通过：沿用已提交版本的字段写法 `name`（即 slug）、`display_name`、`version`，未改字段名 |
| 版本号大于平台最新版 | 1.0.2 > 1.0.1（log.md 记 1.0.1 已上传、审核中）；平台实时最新版本本环境查不到，见未验证项 |
| 专家包 tags | 不适用（只打技能包） |
| 首次对话上报字段与开关 | 通过：8 个白名单字段未变、版本随包 1.0.2、渠道 `workbuddy_skill`、`MPS_WEDDING_STUDIO_JOURNEY=off` 可关（C `test_telemetry_contract`、E Telemetry 类） |
| 全包无旧口径；对客文字无网站名/Key/URL/接口/token | 通过（C `test_forbidden_words`、`test_customer_copy_no_site_or_key`、`test_no_slow_payment_wording`）。「同一账户的通用次数在已接入的技能间共享」是现行通用套餐口径（Muse 指令：通用套餐口径不变），保留 |

## 测试结果（2026-11-10）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 42/42 通过（原 34 + 新增 PayConversion 8） |
| 端到端（仓库内包，带 `--zip`） | 68/68 通过（原 56 + PayConversion 12；其中 2 项原 noAccount 断言改为 linkAccount） |
| 干净解压 ZIP 后契约测试 | 42/42 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 68/68 通过，无跳过 |
| ZIP 完整性 | `testzip` 无损坏；24 个文件（与 1.0.1 清单相同）；最大深度 2；无 `__pycache__`、dev |
| 与 1.0.1 对比 | 变化的包内文件 7 个：SKILL.md、_meta.json、scripts/studio.py、telemetry.py、welcome_copy.py、tests/first-turn-preview.md、tests/test_skill_contract.py；`png_local.py`、`audit_images.py`、`references/`、`assets/`、README 字节一致 |
| 真实上游调用 | 0（端到端全部走 `dev/mock_backend.py`；本次没有对真实站点运行任何命令） |

## 修复不重犯（历史缺陷逐项复核，均在干净解压 ZIP 上通过）

| 历史缺陷 | 状态 | 证据 |
|---|---|---|
| WED-A3-01 demo 零网络（只允许 first-turn 的 `telemetry.report_once`） | 未回退 | C `test_wed_a3_01_demo_has_no_network`；E `test_wed_a3_01_demo_alone_zero_network` |
| WED-A3-02 照片哈希绑定，换图作废确认与原 Idempotency-Key | 未回退 | E `test_wed_a3_02_photo_replaced_after_confirm`、`test_wed_a3_02_photo_replaced_between_plan_and_confirm` |
| WED-A3-03 成品/画廊 Markdown 链接用 `md_safe_path` | 未回退 | E `test_wed_a3_03_delivery_links_space_and_hash` |
| A3-E01 examples_zh 与 examples_en 逐条对齐（各 3 条、数量一致） | 未回退（examples 未改） | C `test_examples_zh_en_same_scene`、`test_examples_match_spec_scenes`；E `test_zip_skill_examples_platform_limits` |
| A3-E02 示例路径含空格 | 未回退 | C `test_demo_link_path_with_space`；E `test_demo_links_survive_markdown` |
| A3-E03 示例路径/目录名含 # | 未回退 | C `test_demo_link_path_with_hash` |
| 包目录最多两级、示例在 `assets/`、`demos.json` 裸文件名、解压后无三级文件、10 张示例图齐全 | 未回退（assets 字节与 1.0.1 一致） | E `test_zip_dir_depth_at_most_two`、`test_package_demos_trace_to_provenance`；C `test_demos_consistent`、`test_demos_are_fictional_and_small` |

## 偏离开发文档

- 账户命令无账户时改为返回 `linkAccount` 关联链接。为负责人指令整改（SOP 第七章），`01-dev-spec` 未同步修改（规格未写这一细节，无矛盾）。
- `rounds.dev` 未加：负责人指令整改，不是测试退回。

## 未验证项

- 7.5 真机验收：按负责人 2026-11-10 定「豁免继续」，未做；Flash 小模型下接管规则是否被遵守只能由负责人实测确认。
- 平台上该 slug 实际最新版本（含审核中版本）：本环境查不到；1.0.1 仍在审核，由负责人上传时确认 1.0.2 大于平台最新版。
- logo：仓库内无文件，未核对；由负责人沿用 1.0.1 上传时的 logo。
- 服务端 `/quick-entry` 真实返回格式：按脚本已在用的格式（与 `run`/`auth` 同一入口）对接，仅用模拟后端验证。

## 部署与回滚

- 部署：无服务端改动。走 Codex A3 独立检查（对 1.0.2 新包），通过后负责人手动上传 ZIP，附 logo、中文名、slug。
- 回滚：仓库 `dist/` 中 1.0.1 ZIP 未改动，可直接重传；1.0.0 也保留。

---

# 以下为历史版本自测记录

# 自测报告：mps-wedding-portrait-studio 1.0.1

- 时间：2026-11-09T12:41:12+08:00，Claude 定时运行，修复轮（认领通知 evt-96eef1c744a2ac21abfcea83f5ecedc7fdea1335715b0dd269b4094798e19a57；依据 03-test-report.md WED-A3-01–03）
- 修复轮不重读官方文档（SOP 〇章第 4 条）；规格未变，A1 不重新复检
- 渠道：只做 `workbuddy-skill`
- **A2 结论：通过，置 package_ready。**
- 交付包：`02-package/dist/mps-wedding-portrait-studio-1.0.1.zip`，921555 字节，24 个文件，最多两级，SHA256 `b26ede2626c357dbb178ad10f41188aaaece2bc5e4f63d67bd1a8ff26cd03208`。1.0.0 ZIP 原样保留，可用于回滚。

## 修复内容

| 缺陷 | 修复 | 回归测试 |
|---|---|---|
| WED-A3-01 离线示例命令触发首次对话上报 | `cmd_demo` 去掉 `telemetry.report_once`，只读包内 `assets/` 并释放到本地。首次对话上报仍由同一首轮的 `first-turn` 负责（以及之后的每个业务命令） | 端到端 `RepairA3.test_wed_a3_01_demo_alone_zero_network`：业务与上报传输都换成抛异常函数，`demo`、`demo garden` 成功，且不写上报状态文件；之后 `first-turn` 仍上报 1 次。契约 `test_wed_a3_01_demo_has_no_network`（AST：`cmd_demo` 不引用 telemetry/call/TRANSPORT/load_account，`cmd_first_turn` 仍上报）。`test_every_early_branch_reports` 的分支列表移除 `demo` |
| WED-A3-02 照片被替换后旧确认和原任务键仍可用 | `plan` 记录照片 SHA256（草稿只存路径和哈希，不存字节）。`confirm` 和提交前构造请求体时重新读取并比对；不一致即作废两项同意和原任务键，状态改为 `photo_changed`，返回 `photoChanged`（退出码 2，话术说明尚未开始制作、没有产生扣费）。必须重新 `plan` + `confirm`，生成新键后才能提交 | `test_wed_a3_02_photo_replaced_after_confirm`：确认合成图 A 后同路径写入合成图 B，`run` 返回 `photoChanged`，模拟后端零提交、零扣费，草稿 idem 为空；旧确认 `run`→`needsConfirmation`、直接 `confirm`→`needsPlan`；重新确认后新键 ≠ 旧键，交付成功、扣 1 次。`..._between_plan_and_confirm`：plan 后换图，`confirm` 即返回 `photoChanged` |
| WED-A3-03 成品 Markdown 链接未用安全路径 | `_deliver` 把文件路径（信号 `paths`、`gallery`）与面向用户的链接目标（新信号字段 `links`、`gallery_link`，经 `md_safe_path`）分开；交付话术使用链接目标，并增加「全部结果一览」画廊链接；链接文字按 Markdown 转义 | 端到端 `test_wed_a3_03_delivery_links_space_and_hash`：照片放在 `my photos`（空格）与 `Synthetic#Album`（#）两个合成目录，真实走完交付，成品与画廊链接按 URI 拆片段、查询串后解码均命中原文件，markdown-it 渲染的 href 同样命中。契约 `test_wed_a3_03_delivery_links_markdown_safe` 用 `welcome_copy.delivery` 直接验证同两类目录 |

其他改动：版本号 1.0.0 → 1.0.1（SKILL.md、_meta.json、studio.py、telemetry.py、first-turn-preview.md、dev/build.py）；SKILL.md 执行规范第 4 节加一行 `photoChanged` 处理（14690 字节，<15KB）。没有改计费、授权、余额、幂等规则或接口字段。

## 测试结果（2026-11-09T12:41:12+08:00）

| 运行 | 结果 |
|---|---|
| 修复前基线（1.0.0 源码） | 契约 32/32、端到端 52/52 |
| 契约测试（仓库内包） | 34/34 通过 |
| 端到端（仓库内包，打包前） | 56 项：54 通过，2 项跳过（尚无 1.0.1 ZIP） |
| 干净解压 ZIP 后契约测试 | 34/34 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 56/56 通过（含 ZIP 两级目录、frontmatter examples 校验） |
| ZIP 完整性 | `testzip` 无损坏；三级及以上路径 0；不含 `__pycache__`、dev 目录、`demo-assets/` 原图 |
| 密钥扫描（产品目录） | 无命中 |

真实上游调用（本次 Claude）：0。真实上报：0（全部走模拟传输）。生产变更：0。未验证项：真机行为验收按负责人长期规则跳过；负责人上架前自测。

## 历史：1.0.0 自测报告

- 时间：2026-11-09 北京时间，Claude 定时运行（认领通知 evt-bdef4dc745884994b746f4ee5a9228b263a538c134bf5b9cf9f6b21b0d9570a8）；接续 2026-11-08 22:57 的示例图拦停
- 已读 WorkBuddy 官方文档快照（`docs/sop/workbuddy-official-docs.md`，快照日期 2026-11-08，读了「二、技能」章，本次运行重读）
- 规格：`01-dev-spec.md` / `01-dev-spec.json` 1.0.0（A1 通过；与上次相比只改了示例图交付状态和读取日期）
- 渠道：只做 `workbuddy-skill`（config.yaml channels）
- **A2 结论：通过，置 package_ready。**
- 交付包：`02-package/dist/mps-wedding-portrait-studio-1.0.0.zip`，920365 字节，24 个文件，最多两级，SHA256 `7eb0b0abf669574c4f14ab6df6f95026e34874dcd69500bff90b82ce18be8001`

## 本次（2026-11-09）

1. 示例图同步：`dev/sync_demos.py` 按 `demo-assets/provenance.json` 逐张核对 10 张源图 SHA256 全部一致，本地等比缩放（长边 480）加 128 色调色板压缩，写入 `assets/`（与 `demos.json` 同级）。合计 867268 字节，与 Codex 审计记录 `offline_sync.package_png_bytes` 一致。派生记录 `dev/demos-derivation.json`（源哈希 → 包内哈希）。没有新增生图调用。
2. 目视核对 10 张包内图：每张与场景对应（白纱影棚、秀禾、花园、海边、油画婚纱、韩式、汉服、油画肖像、赛博、日系），画面内无可读文字、水印、品牌标志；均为虚构成年人（provenance `fictional_adult=true`）。
3. `dev/build.py` 补一行创建 `dist/` 目录（原脚本在目录不存在时报错），其他不变；仍拒绝覆盖已有 ZIP、拒绝三级目录。

## 测试结果（2026-11-09）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 32/32 通过 |
| 端到端（仓库内包，打包前） | 52 项：50 通过，2 项跳过（尚无 ZIP） |
| 端到端（仓库内包，打包后） | 52/52 通过（含 ZIP 两级目录与内容一致、provenance 追溯） |
| 干净解压 ZIP 后契约测试 | 32/32 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录>`） | 52/52 通过 |
| ZIP 完整性 | `testzip` 无损坏；最大深度 2；不含 `__pycache__`、dev 目录、`demo-assets/` 原图 |
| 密钥扫描（产品目录） | 无命中 |

真实上游调用（本次 Claude）：0。生产变更：0。

## 历史记录（2026-11-08，示例图到位前）

## A1 复检

15 项齐全：立项字段与词表、官方文档读取记录、场景路由表（10 个）、提示词要点与三条基线加人物身份基线、示例选题 10 个及生成方式、计费默认值、模型与毛利（约 76.47%，≥60%）、fast 车道、接口字段带源码位置、漏斗 L0–L4、相邻技能分界、不承接清单、验收用例 T01–T10、决策记录、MD/JSON 一致。没有退回意见。

## 包内容（`02-package/mps-wedding-portrait-studio/`，两级目录）

- `SKILL.md`（14.5KB，<15KB）：8 个必填字段；`examples_zh`/`examples_en` 各 3 条，按规格 5.1 逐条对应 white-studio / seaside / japanese 和画幅；欢迎句「欢迎使用WorkBuddy官方认证技能 婚纱写真照相馆。」。
- `scripts/studio.py`：沿用证件照换底助手 1.0.6 已通过 A3 的客户端骨架（授权、充值、任务续接、消费记录、工单、首次对话上报、Markdown 安全路径）。新增 10 个场景、`--people 1/2`（写真只做单人）、`--shape portrait/landscape/square`，画幅只发适配器已映射的三种；提示词四段：身份（两人时逐人锁定左右位置）→ 主题视觉 → 无文字 → 安全。
- `scripts/welcome_copy.py`：两人时的同意话术（两位都是成年人且同意）、单人限制、拒绝话术（未成年人、换脸、合成照片里没有的人）。
- `references/`：scenes.md（路由表加超时）、prompts.md、platform-rules.md。
- `assets/demos.json`：10 个 key 和标题，与 SKILL.md、README 一致。（11-08 时 PNG 未入包；11-09 已同步 10 张。）
- 开发目录 `02-package/dev/`：`mock_backend.py`（新增画幅校验，按请求画幅出图）、`e2e_check.py`、`sync_demos.py`（从 `demo-assets/` 核对 provenance 哈希后缩放入包）、`build.py`（不覆盖已有 ZIP，拒绝三级目录）。

## 测试结果

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包，真实状态） | 32 项：30 通过，2 项因示例 PNG 缺失失败（`test_demos_consistent`、`test_demos_are_fictional_and_small`） |
| 端到端（仓库内包，真实状态） | 52 项：46 通过，2 项跳过（无 ZIP），4 项因示例缺失报错（3 个 demo 命令用例加 provenance 追溯） |
| 契约测试（临时副本，放入 10 张纯色合成占位 PNG，不入库） | 32/32 通过 |
| 端到端（同一临时副本，并打出临时 ZIP） | 52 项：51 通过，1 项报错（provenance 追溯：没有 `demo-assets/`，属预期） |
| 干净解压临时 ZIP 后重跑 | 契约 32/32；端到端仍只有 provenance 一项报错；ZIP 24 个文件，最多两级 |

合成占位只用来证明除示例图之外的代码路径都能跑通，**不是交付物**，没有提交，也不能代替真实示例。

新增或改写的关键用例：10 场景与规格一致（系列、画幅、路由表、prompts、demos 三处对齐）；写真两人返回 `peopleUnsupported` 且零网络；两人海边全流程（授权 → 最后一步 → 交付），提交的 `size=1536x1024`、提示词含「左侧的人」；尺寸偏差提示；中英示例在场景、人数、画幅三个维度上的错配都能检出（A3-E01）；规格 5.1 两条合成路径 `Codex Demo Assets/white-studio.png`（A3-E02）和 `Codex#Demo/white-studio.png`（A3-E03）按 Markdown 解析后，拆掉片段和查询串再解码，指向原文件。

## 阶段 6 必测项对照

沿用 1.0.6 的账号计费、引导确认、等待轮询六种时序、交付、遥测、消费记录和工单用例，全部改成婚纱写真场景后通过（临时副本）。以下不适用或未做：

| 项 | 状态 | 原因 |
|---|---|---|
| 直连下载失败后 `inline_delivery` 补取 | 不做 | 规格第 3 节：下载失败走原任务再取，不新增字段 |
| 计费前拒绝同键等待重试 | 等待 0 秒 | 规格 `prebilling_wait_s=0` |
| 同设备账户复用 | 不做 | config `sibling_reuse: false` |
| 大图分段续传 | 不做 | 规格只要求原任务再取图 |
| 真机行为验收、收藏卡片实测 | 跳过 | 负责人长期豁免（2026-11-07）；验收单 `tests/first-turn-preview.md` 已更新为本技能 |

## 未验证

- 真实宿主行为（WorkBuddy 内首轮、收藏卡片等）、真实支付、真实生成、平台审核：都没做（真机验收按负责人长期豁免跳过）。Claude 真实上游调用 0 次，生产变更 0。
- WorkBuddy 上传解析：ZIP 未上传，上传由负责人手动完成。
- 示例图是文生图效果示意，不证明参考图身份保持效果（规格已注明）。

## 恢复步骤（已于 2026-11-09 执行完毕，保留备查）

1. Codex 把 10 张 PNG 和 `provenance.json`、`generation-audit.json` 放进 `pipeline/products/mps-wedding-portrait-studio/demo-assets/`。
2. 运行 `python3 02-package/dev/sync_demos.py`（核对哈希、缩放、写 `demos-derivation.json`）。
3. 重跑契约测试和端到端，运行 `dev/build.py` 打 `dist/mps-wedding-portrait-studio-1.0.0.zip`，干净解压重跑，补本报告的 ZIP SHA256，置 package_ready。

## 部署与回滚

不涉及后端部署。本单是新技能，没有上一版，回滚就是不上传或在平台下架；包源码和 ZIP 都在仓库，可按提交号恢复。

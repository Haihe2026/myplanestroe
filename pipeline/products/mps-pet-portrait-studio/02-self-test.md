# 自测报告：mps-pet-portrait-studio 1.0.4（SOP 第七章付费转化整改）

## 交付三样

| 项 | 值 |
|---|---|
| 中文名字（display_name） | **宠物主题照相馆**（不变） |
| slug（SKILL.md name） | **mps-pet-portrait-studio**（不变） |
| logo | **`pipeline/products/mps-pet-portrait-studio/02-package/dist/logo.png`**（未改动，SHA256 `60267f39bbfa4d2da9df7a170d8671641707e08557dbb0c67f549c4d4e8452c9`） |
| 英文名（display_name_en） | Pet Themed Portrait Studio |
| 技能包 | `02-package/dist/mps-pet-portrait-studio-1.0.4.zip`，1026973 字节，24 个文件，最多两级，SHA256 `5129d1933d94b2f950bac67524df2cd9a82e22ecf2c8d8e4d3eb48916b26e673` |

- 时间：2026-11-10T18:45:40+08:00，Claude 定时运行；承接 Muse 交接 `evt-5bd1c40a…`（源 `pipeline/products/mps-pet-portrait-studio/msg-from-muse-20261110-fix-104-pay-conversion.md`，通知 source_ref `5aa5ad7a…` 是该文件的 blob 哈希，已用 `git hash-object` 核对与 main 上文件一致）。
- 依据：`docs/sop/sop-image-gen-skill-auto.md` 第七章（文件哈希 `f086414c…`，提交 `2f30b61`），与 Muse 指令一致。负责人定 1.0.3 的 A3 作废，由 1.0.4 重新走 A3。
- 升级轮，按 SOP 〇章第 4 条不重读官方文档快照。渠道只做 `workbuddy-skill`（config.yaml）。
- 只改客户端脚本、SKILL.md 和测试；不动后端、定价、套餐、0 次免费试用口径、十个主题模板。
- 旧包保留：1.0.0–1.0.3 ZIP 未改动（1.0.3 SHA256 仍为 `5e24d182…`）。
- **A2 结论：通过，置 package_ready。**

## 改动（逐条对应 Muse 指令）

| 指令 | 改动 | 证据 |
|---|---|---|
| A1 `topup` 无账户死胡同 | `cmd_topup`：无安装标识时生成并持久化 `install_secret`，调 `POST /quick-entry`（无 Bearer）：`registration`→新信号 `linkAccount`（关联链接 + 「扫码确认后会直接进入充值页…关联本身不扣费」）；`checkout`→`topupLink`；`ready`→接上本机凭证后调 `POST /membership-link` 给充值链接；有标识但 `/membership-link` 返回 401（还没关联）也改走关联入口；断网→「网络暂时没连上，没有扣任何次数，稍后再说一次「充值」。」；链接全部经 `trusted_link` 校验，异常链接不转述 | E `PayConversion` 全部 11 项 |
| A1 `balance` / `status`（及 `history`）无账户 | 同样走关联入口（新 helper `_account_entry`），不再回 `noAccount`；`balance`/`history` 遇 401 也走关联入口；`status` 无标识时 `checkout` 给最后一步充值链接、`ready` 报 `registered` | E `test_fresh_status_and_balance_have_way_out`、`test_balance_menu_and_decline`、`test_history_failure_and_no_account`；C `test_failure_kind_by_status` |
| A2 失败原因不误报 | `_membership_link` 改为返回 (链接, 状态)；新增 `_fail_kind`：状态 0→`network`，非 0→`busy`。`cmd_topup`、`cmd_run` 的充值链接分支按状态传参；`_ensure_skill_key` 断网也返回 network；`balance`/`status` 已有标识时的查询失败也按状态说明（原来一律说「当前进度未能确认」） | E `test_fresh_topup_offline_honest`、`test_fresh_topup_server_busy`、`test_topup_membership_link_network_not_busy`、`test_run_needs_credits_link_failure_kind`、`test_fresh_status_offline` |
| A3 新测试 | 全新环境（无账户、无凭证）直接 `topup`：有可点链接（`/membership/gemini/register/`），断网时输出如实断网说明 | E `test_fresh_topup_gives_link_account`、`test_fresh_topup_offline_honest` |
| B1 接管规则 | 执行规范最前面加「### 零、接管规则（每一轮都适用）」，按 SOP 7.3.1 模板替换名词；账户命令/续接命令固定；转介婚纱写真照相馆（人像写真）与证件照换底助手；含禁止编造故障、禁止宿主自带生图、欢迎句逐字照写不加空格 | C `test_takeover_rules_first` |
| B2 description | 加「本技能也负责宠物主题照相馆的充值、付费链接、余额和订单查询。」；触发词加「宠物主题照相馆充值」（20→21 个）；末尾调用倾向句原样保留，全文只一句 | C `test_description_account_and_triggers`、`test_description_seo` |
| B3 技能收藏核对 | 不符处已改：原写「用户级（有项目级时也写项目级）」→「用户级、项目级各一条」；收藏内容补「以及宠物主题照相馆的充值、付费链接、余额和订单等问题」；选项写成「收藏 / 暂不」；「用户点『收藏』后」才写。其余（只在首次成功交付后问一次、取消方法、不支持时如实说、不含个人信息、合规说明行）原已符合 | C `test_favorite_section` |
| B4 欢迎句 | SKILL.md 首轮第 1 步与接管规则都写「逐字照写」/「中文和英文之间不加空格」；`welcome_copy.WELCOME` 未动 | C `test_welcome_exact` |
| B5 隐藏注释 | SKILL.md、README.md 无 `<!--` | C `test_no_hidden_html_comment` |
| C1 版本 | `version: 1.0.4`：SKILL.md frontmatter、`_meta.json`、`studio.SKILL_VERSION`、`telemetry.SKILL_VERSION`、`dev/build.py` 一致 | C 版本一致性测试；E ZIP 内 SKILL.md 版本检查 |

其他：
- SKILL.md 篇幅：加接管规则后超过 SOP 15KB 上限，压缩了执行规范第 1–6 节的重复说法（规则不删，合并同类信号说明），现为 15290 字节（< 15360）。
- 对客文字核查时发现授权话术里有「不用 API Key」（含 Key，违反 7.4 对客文字不出现 Key），改为「也不用填写任何密钥」；新增契约 `test_customer_copy_no_site_or_key`。
- 新信号 `linkAccount` 已写进 SKILL.md 第 5 节；`noAccount` 现在只在提交反馈、查工单时出现。

## SOP 7.4 出包阻断项自检

| 检查项 | 结果 |
|---|---|
| 接管规则，含禁止编造故障、禁止宿主自带生图 | 通过（C `test_takeover_rules_first`） |
| 全新环境 `topup` 有链接或如实断网说明 | 通过（E `test_fresh_topup_gives_link_account` / `_offline_honest`） |
| description 末尾一句调用倾向句、触发词 15–25（21）、用户原话、账户类说法 | 通过 |
| 技能收藏章节 + 合规说明，收藏内容里技能 name 与 SKILL.md 一致 | 通过 |
| 无隐藏 HTML 注释 | 通过 |
| frontmatter 含 slug、version、显示名；name/slug 不改 | 通过：本包沿用已过 A3 的官方字段写法 `name`（即 slug）、`display_name`、`version`，未改字段名 |
| 版本号大于平台最新版 | 1.0.4 > 1.0.3（1.0.3 从未上传；平台上实际最新版本本环境查不到，见未验证项） |
| 专家包 tags | 不适用（只打技能包） |
| 首次对话上报字段与开关 | 通过：8 个白名单字段未变、版本随包 1.0.4、渠道 `workbuddy_skill`、`MPS_PET_STUDIO_JOURNEY=off` 可关（C 遥测测试） |
| 全包无旧口径；对客文字无网站名/Key/URL/接口/token | 通过（C `test_forbidden_words`、`test_customer_copy_no_site_or_key`、`test_no_slow_payment_wording`）。「同一账户的通用次数在已接入的技能间共享」是现行通用套餐口径（Muse 指令「通用套餐口径不变」），不是旧的共享余额说法，保留 |

## 测试结果（2026-11-10）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 41/41 通过（原 34 + 新增 7） |
| 端到端（仓库内包，带 `--zip`） | 79/79 通过（原 68 + 新增 11，其中 2 项原 noAccount 断言改为 linkAccount） |
| 干净解压 ZIP 后契约测试 | 41/41 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 79/79 通过 |
| ZIP 完整性 | `testzip` 无损坏；24 个文件（与 1.0.3 清单相同）；最大深度 2；无 `__pycache__`、dev、`demo-assets/` |
| 与 1.0.3 对比 | 变化的包内文件 7 个：SKILL.md、_meta.json、scripts/studio.py、telemetry.py、welcome_copy.py、tests/first-turn-preview.md、tests/test_skill_contract.py；`png_local.py`、`audit_images.py`、`references/`、`assets/` 字节一致 |
| 旧名残留 | 解压目录搜「宠物写真照相馆」「Pet Portrait Studio」：0 处 |
| 真实上游调用 | 0（端到端全部走 `dev/mock_backend.py`；本次没有对真实站点运行 `topup`） |

## 修复不重犯（历史缺陷逐项复核，均在干净解压 ZIP 上通过）

| 历史缺陷 | 状态 | 证据 |
|---|---|---|
| PET-01 原子保存原键/正文；404 只报未能确认、零重发；401 清旧凭证从原安装恢复 | 未回退（提交与轮询代码未改） | E `RepairPetA3` PET-01-a…g |
| PET-02 截断 PNG、Adam7 非法过滤、坏 zlib | 未回退（`png_local.py` 字节一致） | E PET-02-a…d |
| PET-03 缺 cartoon.png 时 demo 退出 3 | 未回退 | E `test_pet_a3_03_one_missing_exit3_offline`、`test_demo_missing_assets_exit3` |
| A3-E01 中英示例逐条对齐（各 3 条） | 未回退（examples 未改） | C `test_examples_zh_en_same_scene`；E `test_zip_skill_examples_platform_limits` |
| A3-E02/E03 示例路径无空格、无 # | 未回退 | E `test_demo_paths_and_single`、`test_demo_links_survive_markdown` |
| WED-A3-01 demo 零网络 | 未回退 | E `test_wed_a3_01_demo_alone_zero_network` |
| WED-A3-02 照片哈希绑定，换图作废确认与原键 | 未回退 | E `test_wed_a3_02_*`、`test_pet_a3_01_photo_hash_binding_kept` |
| WED-A3-03 成品/画廊 Markdown 安全路径 | 未回退 | E `test_wed_a3_03_delivery_links_space_and_hash` |
| 包目录两级、示例在 `assets/`、`demos.json` 裸文件名、10 张示例图、10 模板 | 未回退 | C 示例与模板测试；解压检查 10 张 PNG + demos.json |

## 偏离开发文档

- 账户命令在无账户时的行为按 SOP 第七章与负责人指令变更（返回 `linkAccount` 关联链接），属于负责人指令整改，`01-dev-spec` 未同步修改（规格未写 noAccount 细节，无矛盾）。
- `rounds.dev` 未加：本轮是负责人指令整改，不是测试退回。

## 未验证项

- 7.5 真机验收：按负责人 2026-11-10 定「豁免继续」，未做；Flash 小模型下接管规则是否被遵守只能由负责人实测确认。
- 平台上该 slug 实际最新版本、新名是否可用：本环境查不到，由负责人上传时确认。
- 服务端 `/quick-entry` 真实返回格式：按现有脚本已在用的格式（与 `run`/`auth` 同一入口）对接，仅用模拟后端验证。

## 部署与回滚

- 部署：无服务端改动。走 Codex A3 独立检查（对 1.0.4 新包），通过后负责人手动上传 ZIP，并附 logo、中文名、slug。
- 回滚：1.0.3 ZIP 原样保留在 `02-package/dist/`（同名同 slug、未上传过）。

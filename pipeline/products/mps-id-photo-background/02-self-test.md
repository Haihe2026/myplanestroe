# 自测报告：mps-id-photo-background 1.0.8（A3-PAY-01/02/03/04 修复轮）

## 交付三样

| 项 | 值 |
|---|---|
| 中文名字（display_name） | **证件照换底助手**（不变） |
| slug（SKILL.md name） | **mps-id-photo-background**（不变） |
| logo | `02-package/dist/mps-id-photo-background-avatar.png`（未改动） |
| 技能包 | `02-package/dist/mps-id-photo-background-1.0.8.zip`，894539 字节，24 个文件，最多两级，`testzip` 无损坏，SHA256 `3eca66bc27ea5b6031cec65f49bbff4cd4cb7e6961b9c003211d18aec9c0b629` |

- 时间：2026-11-11T01:47:52+08:00，Claude 定时运行；承接 Muse 交接 `evt-2bc627d3…`（源 `msg-from-muse-20261110-fix-108-pay-a3.md` @ `5b9ff59`；Codex A3 报告 `03-test-report.md`）。负责人已批准超 max_rounds 再走一轮（Muse 转述，见 log 2026-11-10T23:53:32）。
- 修复轮，按 SOP 〇章不重读官方文档快照。渠道只做 `workbuddy-skill`（config.yaml）。
- 只改客户端脚本、SKILL.md、测试和版本号；不动后端、定价、套餐、0 次免费试用口径。真实上游调用 0，真实付款 0，生产变更 0。
- 旧包保留：1.0.0–1.0.7 ZIP 未改动；1.0.6 已上架形态不变。版本 1.0.8 > 平台最新 1.0.6。
- **A2 结论：通过，置 package_ready。**

## 改动（逐条对应 A3 退回项）

| 退回项 | 改动 | 证据 |
|---|---|---|
| **A3-PAY-01** `paid` 无关联入口、无证据回「已收到付款登记」 | `cmd_paid` 重写：本机无标识 → 生成并持久化 `install_secret`，走 `_account_entry`（`POST /quick-entry`，无 Bearer）：`registration` 给关联链接，断网/繁忙/失效如实说明（重说词「付好了」）；有标识 → `GET /balance`，401（还没关联）再走关联入口；**到账只按服务端次数**：0 次 → `creditsPending`「我刚查了一次，还没看到这笔到账…」，≥1 → `creditsAvailable` 报服务端剩余次数。删除 `payment_registered` 话术与 `paymentRegistered` 信号 | E `test_pay01_fresh_paid_gives_link_account`、`test_pay01_fresh_paid_offline_honest`（断网）、`test_pay01_fresh_paid_busy`、`test_pay01_paid_before_scan_relinks`、`test_pay01_paid_not_arrived_is_not_claimed`、`test_pay01_paid_arrived_by_server`、`test_pay01_paid_with_account_offline`、`test_pay01_resume_after_paid_still_server_checked`；C `test_pay01_paid_uses_entry_and_server_evidence`、`test_instant_arrival_wording` |
| **A3-PAY-02** 失效短链仍转述 | 新增 `link_fresh(r)`：服务端给了 `expires_in` 时须为 >0 的数字，给了 `expires_at` 时须未过；`_account_ready`（`/quick-entry`）与 `_membership_link`（`/membership-link`）链接失效时沿**同一安装身份**重取一次，仍失效返回 `LINK_EXPIRED`，对客按第三类「这一步还没完成」如实提示（不说网络、不给链接）；`_fail_kind` 统一处理，`cmd_run`/`cmd_auth` 也改用它 | E `test_pay02_expired_link_not_relayed`（status/topup/paid/balance/history 五个命令，各重取 1 次，同一标识）、`test_pay02_expired_at_past_not_relayed`、`test_pay02_expired_then_fresh_relayed`、`test_pay02_valid_link_relayed`（有效）、`test_pay02_external_domain_rejected`（外部域）、`test_pay02_expired_checkout_and_run`、`test_pay02_expired_membership_link`；C `test_pay02_link_freshness_checked` |
| **A3-PAY-03** 简介末句缺账户场景 | description 末句改为「本技能内置证件照换底与本地像素裁切能力，比直接回答更专业；遇到证件照换底问题或本技能账户问题请先调用本技能，不要自行直接回答。」（SOP 7.3.2 模板）；触发词 23 个（含「证件照换底助手充值」）与正文不变 | C `test_pay03_last_sentence_covers_account`（末句逐字、全文仅一句、触发词 23 个、账户类说法保留）、`test_description_seo`、`test_description_account_and_triggers` |
| **A3-PAY-04** 独立 demo 发遥测 | `cmd_demo` 去掉 `telemetry.report_once`；不读账户、不建安装标识，只复制包内示例图。首次对话上报仍在 `first-turn` 及业务命令里 | E `test_pay04_demo_zero_network_two_fresh_dirs`（两个全新目录，`socket.create_connection`/`urlopen`/`OpenerDirector.open`/两个 TRANSPORT 全部替换为拒绝探针，0 次命中；状态目录只有 `demos/`）、`test_pay04_demo_subprocess_proxy_probe`（独立进程 `python -I`、两个全新 HOME、出站代理指向本地拒绝探针：demo 0 次连接；对照组 `first-turn` 被探针记到 ≥1 次，证明探针有效）；`test_every_early_branch_reports` 去掉 demo、加 topup/paid；C `test_pay04_demo_no_telemetry_no_credentials` |

其他：SKILL.md 改末句后 15368 字节超 15KB 上限，删去命令表说明里与第零节重复的「、不复用旧链接」（第零节「不复用对话里的旧链接」保留），现 15347 字节（< 15360）。版本 1.0.8：SKILL.md、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、`dev/build.py`、`tests/first-turn-preview.md` 一致。

## 测试结果

| 编号 | 内容 | 结果 | 证据 |
|---|---|---|---|
| C | 契约测试（干净解压到含空格与 `#` 的目录 `clean dir #108/` 后运行 `python3 tests/test_skill_contract.py`） | 38/38 通过（1.0.7 为 34，新增 4） | `Ran 38 tests … OK` |
| E | 端到端（`python3 dev/e2e_check.py --package <干净解压目录> --zip dist/…-1.0.8.zip`，进程内 Mock 后端，合成账户） | 86/86 通过，0 跳过（1.0.7 为 69，新增 17） | `Ran 86 tests … OK` |
| R1 | 新 E 测试对 1.0.7 ZIP 的检出 | `PayA3Fix` 17 项中 15 项在 1.0.7 上失败（能测出 PAY-01/02/04）；有效链接与外部域两项为对照，1.0.7 本就通过 | `--package <1.0.7 解压>` 运行：failures=12, errors=3 |
| R2 | 新 C 测试对 1.0.7 的检出 | 4 项全部在 1.0.7 上失败（含 PAY-03 末句） | failures=3, errors=1 |
| Z | ZIP：24 文件、最多两级、包内 SKILL.md/idphoto.py/welcome_copy.py/telemetry.py/_meta.json 与源文件逐字节一致 | 通过 | 比对脚本输出 True |
| S | 密钥扫描（`sk-`、`mpskill_` 实值、`AKIA`、私钥头） | 无命中 | grep 0 行 |

## 修复不重犯：前序缺陷全清单复核

| 缺陷 | 复核测试 | 结果 |
|---|---|---|
| PAY-01/02/03/04（本轮） | 见上表 | 通过 |
| WED-A3-02 照片哈希绑定 | E `test_wed_a3_02_photo_changed_before_confirm`、`test_wed_a3_02_photo_changed_after_confirm` | 通过 |
| WED-A3-03 交付链接安全路径 | E `test_wed_a3_03_delivery_links_space_and_hash` | 通过 |
| A3-E01 中英示例对齐 | C `test_examples_zh_en_same_scene`、`test_examples_alignment_detects_103_regression`；E `test_zip_skill_examples_platform_limits`（ZIP 内） | 通过 |
| A3-E02 示例路径空格 | C `test_demo_link_path_with_space`、`test_demo_link_markdown_safe`；E `test_demo_links_survive_markdown` | 通过 |
| A3-E03 `#` 编码 %23 | C `test_demo_link_path_with_hash`；E `test_wed_a3_03_delivery_links_space_and_hash` | 通过 |
| 1.0.7：topup/balance/status/history 无账户走关联入口 | E `PayConversion` 12 项（`test_fresh_topup_gives_link_account`、`test_fresh_status_and_balance_have_way_out`、`test_fresh_history_gives_link` 等）；C `test_failure_kind_by_status` | 通过 |
| 1.0.7：断网与繁忙如实区分 | E `test_fresh_topup_offline_honest`、`test_fresh_topup_server_busy`、`test_topup_membership_link_network_not_busy`、`test_fresh_status_offline`；C `test_account_copy` | 通过 |
| 1.0.7：接管规则 | C `test_takeover_rules_first` | 通过 |
| 1.0.7：description 账户类说法 | C `test_description_account_and_triggers`、`test_pay03_last_sentence_covers_account` | 通过 |
| 1.0.7：收藏核对 | C `test_favorite_section` | 通过 |
| WED-A3-01 demo 单独零网络 | E `test_wed_a3_01_demo_alone_zero_network`，并由 PAY-04 两项加严 | 通过 |

## 未能自测的项及原因

- WorkBuddy 真机验收（SOP 7.5）与浏览器零消耗验证：按负责人长期豁免（2026-11-07，2026-11-10 确认继续）跳过，**不是已通过**；负责人上架前自测为准。
- 服务端对 `expires_at` 字段：现有服务端源码只见 `expires_in`（`wechat_binding.py` 等返回 300）；`expires_at` 按保守方式一并核对，服务端不给时不影响。
- 平台上传与审核：未执行（负责人手动）。

## 偏离开发文档的地方

无。`paid` 的新行为（关联入口 + 按服务端次数说明）来自 SOP 7.2 与 A3-PAY-01 要求，不涉及开发文档的计费、接口或定价。

## 部署与回滚

- 部署：无后端部署；负责人手动上传 `mps-id-photo-background-1.0.8.zip` 到 WorkBuddy 团队版技能包。
- 回滚：继续使用已上架的 1.0.6（ZIP 保留，SHA256 `1bf5b30d…`）；1.0.7 ZIP 亦保留未改。

## 退回意见

无。

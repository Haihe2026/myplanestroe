# 自测报告：mps-family-portrait-studio 1.0.1

- 修复轮（A3 退回 A3-FAM-01/02/03），按 SOP 〇章第 4 条不重读官方文档；沿用 1.0.0 已读记录（快照 2026-11-08，「二、技能」章）。
- 依据：A3 报告 `03-test-report.md`、Muse 交接 `msg-from-muse-20261111-fix-101-fam-a3.md`（@ `3f41e758`）；开发规格 `01-dev-spec.md/.json` @ `0da1ba29` 未改动、未放宽。
- 时间：2026-11-11T11:41+08:00，Claude 定时运行。渠道只做 `config.yaml` 的 `workbuddy-skill`。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0；生产变更 0；未上传、未发布。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-family-portrait-studio-1.0.1.zip`，2740120 字节，24 个文件，最多两级，SHA256 `1138fe6925145fc8c7a0013f661d32af48a521dd707ad9980fd3411b39194756` |
| 旧包 | `dist/mps-family-portrait-studio-1.0.0.zip` 原样保留（不交付，A3 已判不通过） |
| 版本 | 1.0.1（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION` 一致）；1.0.0 未上传，1.0.1 大于平台已知任何版本 |
| logo | `dist/logo.png` 未动，SHA256 `29f6d8428ef741af4554083b1149ef4d5c026032ae03086a457e881de2a119b2` |
| 十张示例 | `assets/*.png` 与 `demos.json` 未改动（git 无差异），仍为原字节，`DemoAssets.test_package_demos_trace_to_provenance` 通过 |

## 修改（只改 `scripts/studio.py` 与测试；对客文案未改）

### A3-FAM-01 首发提交 401 后不再重提

- `_submit_unauthorized(d, a)`：删除「按原键查到 404 就再 `_submit` 一次」分支及 `auth_retried` 参数。现在：恢复凭证一次 → 只按原键 `GET /jobs/by-key/…` → 查到就沿原任务续接；404、500/502、断网、非法 ID 一律保持 `submit_unknown`，输出 `jobPending`/`progress=unconfirmed`（「当前进度未能确认…稍后说继续，我接着查这一张」），退出 2；查询仍 401 → 退出 4、`task_kept=true`。
- 1.0.0 自测报告「偏离 4」撤销，代码与规格 §7.1/T14 一致。

### A3-FAM-02 凭证状态与任务状态分开

- `_submit_unauthorized` 任何分支都不再写 `state='confirmed'`：任务一直是 `submit_unknown`，原 `idem`、`body_sha256`、三项同意不动；凭证失效只清本机 `account.json` 的 `skill_key`（保留 `install_secret`）。
- 因而 `plan` 的 `LOCKED_STATES` 锁继续生效，第 373–375 行清键分支不可达；`confirm`（要求 planned）和 `regenerate`（要求 delivered/failed/rejected）同样拒绝。之后 `run`/`resume` 走 `_continue_job` 只查原键。

### A3-FAM-03 缺一张示例不得成功

- 新增 `_demo_manifest`：`demos.json` 必须恰好 10 项，键集合等于 10 个场景、不重复，`key/title/note/file` 齐全，`file` 为裸文件名（`[a-z0-9-]+.png`）；否则 `demoUnavailable` 退出 3。
- `cmd_demo`：先校验本次要求的完整集合（默认十项或单项）全部存在，缺任何一张即 `demoUnavailable` 退出 3（附 `missing` 键名），**一张都不复制、不输出**；删除原 `continue`。示例数量未改。

## 测试结果（合成账户与进程内 Mock，真实上游 0）

| 套件 | 结果 |
|---|---|
| 契约（随包）`python3 -m unittest discover -s tests` | 49/49 OK（新增 2） |
| 端到端 `python3 dev/e2e_check.py` | 97 OK + 2 跳过（ZIP 项需 `--zip`） |
| 干净解压 1.0.1 ZIP 重跑：契约；`e2e_check.py --package <解压目录> --zip dist/…-1.0.1.zip` | 49/49 OK；99/99 OK |
| 反证：把 `studio.py` 换回 1.0.0 跑新用例 | 针对缺陷的用例失败（e2e：FAM-01×2、FAM-02×2、FAM-03×2 及更新的 `test_skill_key_expired_reset_exit4`；契约 2 项），两个正例（服务端已受理续接、完整十图）在旧代码上也通过，属预期，证明能检出原缺陷；换回 1.0.1 后全过 |
| 密钥扫描（技能凭证/`sk-`/`Bearer` 模式） | 包与 dev 无命中 |

### 本轮关闭证据

| 缺陷 | 用例 | 断言 |
|---|---|---|
| FAM-01 | `FamilySpec.test_fam01_first_post_401_then_404_never_resubmits` | Mock 首发 POST→401，恢复成功，原键 GET→404：退出 2、`unconfirmed`；生成 POST 计数 1；原 idem/摘要/`submit_unknown` 保留；再 run/resume/run 三次仍 1 次 POST、0 扣费 |
| FAM-01 | `test_fam01_first_post_401_query_faults_never_resubmit` | 恢复后查询 500/502/断网/非法 ID → 退出 2；查询 401 → 退出 4、`task_kept=true`；每种都只 1 次 POST、无新键 |
| FAM-01 | `test_fam01_first_post_401_but_accepted_continues_original` | 服务端实际已受理但回 401：恢复后按原键查到原任务交付，1 次 POST、1 次扣费 |
| FAM-02 | `test_fam02_recovery_fails_keeps_task_locked` | 恢复失败（断网/401/502）：退出 4、`task_kept=true`；从磁盘重新加载后 state=`submit_unknown`、原键原摘要不变；plan→taskLocked、confirm→needsPlan、regenerate→taskLocked，之后再查仍不变；恢复后 resume 按原键交付，恢复后 0 次 POST，总扣费 1 |
| FAM-02 | `test_fam02_recovery_fails_not_accepted_still_query_only` | 恢复失败且服务端未受理：后续 resume 两次都 `unconfirmed`，0 次 POST，锁仍在 |
| FAM-02 | `AccountBilling.test_skill_key_expired_reset_exit4`（按新规格更新） | 凭证整体失效：退出 4、`task_kept=true`、只清 `skill_key` 保留安装身份；之后 run 只查询、不扣费 |
| FAM-01/02 | 契约 `test_fam_01_02_unauthorized_submit_never_resubmits_or_unlocks` | AST：`_submit_unauthorized` 不调 `_submit`、不含 POST/confirmed 等状态、不改 idem |
| FAM-03 | `FirstTurn.test_fam03_default_missing_one_exit3` | 隔离副本删 `oil.png`、demos.json 仍 10 项：默认 demo 退出 3、无 items、输出目录为空；`demo oil` 退出 3；`demo lawn` 正常 1 项；补齐后恰 10 项且顺序同场景表 |
| FAM-03 | `test_fam03_manifest_anomalies_exit3` | 9 项/11 项/重复键/未知键/`../`/子目录/缺字段/非列表/坏 JSON：默认与单项均退出 3 |
| FAM-03 | `test_fam03_complete_set_ok`、契约 `test_fam_03_demo_missing_one_exit3` | 完整十图正例；契约侧缺 `seaside.png` 退出 3、补齐 10 项、`cmd_demo` 无 `continue` |
| 以上 demo 用例 | 同上 | 均在网络抛错桩下运行（零网络），且不创建 `account.json`（零凭证） |

## 前序缺陷复核（未回退）

| 缺陷 | 复核用例（本轮全过） |
|---|---|
| PAY-01 paid 无账户走关联入口 | `test_pay_01_*`（e2e 7 项 + 契约 1 项） |
| PAY-02 失效链接不转述 | `test_pay_02_*`（9 项）、`test_links_without_expiry_not_shown` |
| PAY-03 简介末句含账户问题 | 契约 `test_pay_03_description_last_sentence_covers_account`、`test_description_account_and_triggers` |
| PAY-04 / WED-A3-01 demo 离线 | `test_wed_a3_01_demo_alone_zero_network`、契约 `test_wed_a3_01_demo_has_no_network`（AST 同时覆盖新 `cmd_demo`） |
| PET-01 / FAM-01/02 原任务未知不丢键（同一类） | `test_submit_unknown_persisted_before_post_and_locked`、`test_409_and_5xx_query_original_only`、`test_by_key_404_never_resubmits`、`test_submit_lost_queries_original_not_resubmit`、上表 FAM 用例 |
| PET-02 截断 PNG 不宣告交付 | `test_corrupt_png_kept_pending_then_get_only`、契约 `test_png_verify` |
| PET-03 / FAM-03 缺示例不报成功（同一类） | `test_demo_missing_assets_exit3`、上表 FAM-03 用例 |
| A3-E01 中英示例对齐 | 契约 `test_examples_zh_en_same_scene`、`test_examples_alignment_detects_misalignment`、`test_examples_match_spec_scenes` |
| A3-E02/E03 示例路径无空格与 # | `test_demo_links_survive_markdown`、契约 `test_demo_link_path_with_space`、`test_demo_link_path_with_hash` |
| WED-A3-02 确认后文件不可替换 | `test_wed_a3_02_photo_replaced_after_confirm`、`test_wed_a3_02_photo_replaced_between_plan_and_confirm` |
| WED-A3-03 成品链接编码 | `test_wed_a3_03_delivery_links_space_and_hash`、契约 `test_wed_a3_03_delivery_links_markdown_safe` |

SOP 7.4 出包阻断项与 1.0.0 相同且全部保持（SKILL.md 15357 字节、接管规则在最前、description 末句模板、23 触发词、无隐藏注释、遥测八字段与当前版本一致）；对客文案本轮未改动。

## 偏离开发文档的地方

1.0.0 的偏离 1、2、3、5 不变（A3 已接受 1、2 与示例原字节）。**偏离 4 已撤销**，提交 401 改为严格只查原任务。

## 未验证项

- 真人合照保真、生产签名输入路由、宿主实际行为（真机验收按负责人长期规则跳过，未写成通过）。
- 平台对约 2.7MB 包的接受情况与审核结果；实际支付与到账。
- 首发 401 后若服务端确未受理，该草稿将一直停在「进度未能确认」只查不重提（规格 T14 要求）；用户想再做需新开方案，这一体验未经真机验证。

## 部署与回滚

- 部署：无（fast 车道，无后端改动）。负责人手动上传 1.0.1 ZIP；logo 仍为 `dist/logo.png`。
- 回滚：1.0.0 未上架；如需撤回 1.0.1，不上传或平台下架即可。

## 退回意见

无。

# 自测报告：mps-travel-portrait-studio 1.0.0

- 已读 WorkBuddy 官方文档快照（快照日期 2026-11-08，读了「二、技能」章：目录结构、frontmatter 八必填字段与 examples、references/scripts/templates 用法、解析失败排查）。首次开发新包，2026-11-11 本次运行重读。
- 依据开发文档：`01-dev-spec.md` / `01-dev-spec.json` @ `bf71982dce5534161ef3f3702d333832ec3fe6a9`（relay 事件 `evt-095b6a8a…` 的 source_ref），A1 复检见下；开发文档未改动。
- 时间：2026-11-11T20:38–21:40+08:00，Claude 定时运行。渠道只做 `config.yaml` 的 `workbuddy-skill`。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（全部进程内 Mock、合成账户）；生产变更 0；未上传、未发布。

## A1 复检（认领时）

16 项逐条对照通过：立项字段与词表、name 查重（§1）；官方文档读取记录（§2）；场景路由表（§3）；提示词要点与三条基线+身份基线（§4）；10 张示例及生成方式（§5，provenance 10/10 成功）；主题 logo 方向（§6，文件在 `02-package/dist/logo.png`）；计费默认值（§7、A.5，0 次试用、通用套餐）；模型与成本（§8，毛利 76.47% ≥ 60%）；fast 车道（§9）；接口与源码位置（§7 表）；漏斗对应表（§10）；相邻技能与分界句、不承接清单（§11）；验收用例 T01–T17 与 S6-01–57（§13）；决策记录（§15）；JSON 与 MD 一致（`01-a1-validation.json` result=passed，`a1_passed=true`）。无退回意见。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-travel-portrait-studio-1.0.0.zip`，2404375 字节，24 个文件，最多两级，SHA256 `fcecdcefd5f158212da556115618fd2467de757022f8e1c13e0978482999e1cd` |
| 版本 | 1.0.0（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py` 一致）；本 slug 平台无已上传版本 |
| logo | `dist/logo.png` 原字节未动：512×512 PNG，350096 字节，SHA256 `d8177d72fbc14acc0e2371fd5af976ced0302c2cab395c1937a4dfa9d66acee9`（= `01-logo-provenance.json` / 规格 JSON） |
| 十张示例 | `dev/sync_demos.py` 从 `demo-assets/` 原字节复制到 `assets/`（未缩放、未重编码、无新增生图），10 张 SHA 与 `01-dev-spec.json` demos 逐一相等；派生记录 `dev/demos-derivation.json`，合计 2342553 字节 |
| 不进 ZIP | `dev/`（Mock 后端、端到端检查、打包与同步脚本）、`demo-assets/`、来源审计文件 |

## 实现要点（相对全家福 1.0.1 基座的改动）

- 基座：复制 `mps-family-portrait-studio` 1.0.1（已过 A3 的原任务幂等、401 只查原键、缺示例整组退出 3、链接有效期、Markdown 安全路径等）后改为单人旅行产品；全家福包未改动。
- `studio.py`：十个旅行场景（默认竖版 2:3，1024×1536）；`route_scene()` 两层路由（先明确目的地，再服饰/风格；同层取原话最先出现者），`first-turn` 输出 `suggested_scene`；`plan` 改为 `--subject self/guardian --single yes/no --face-clear yes/no [--features] [--outfit]`，多人 `peopleUnsupported`、看不清 `needsClearerPhoto`、描述超 40 字或含链接语法 `textInvalid`；`confirm` 三项独立同意 `--owner-consent --upload-consent --pay-consent`；任务键前缀 `tps-`；`build_prompt()` 单人身份锁定为第一段，再动作/服装、文字基线、安全基线；输出目录「旅行打卡写真结果」，`index.html` 一览页与交付话术均带「AI 生成旅行主题写真，非实地拍摄」。请求体仍只六字段。
- `welcome_copy.py`：欢迎句逐字「欢迎使用WorkBuddy官方认证技能 旅行打卡写真照相馆。」；确认话术含非实拍与「不能当作真实去过当地的凭证」；单人/监护人同意文案；转介全家福（三人及以上）。
- `SKILL.md`（15355 字节 < 15KB）、`README.md`、`references/*.md`、`assets/demos.json`（每项 note 带非实拍标注）、`tests/first-turn-preview.md` 全部重写为旅行产品。

## 测试结果（合成账户与进程内 Mock，真实上游 0）

| 套件 | 结果 |
|---|---|
| 契约（随包）`python3 -m unittest discover -s tests`（仓库内，含与 `01-dev-spec.json` 的逐项比对） | 51/51 OK |
| 端到端 `python3 dev/e2e_check.py` | 103 OK + 2 跳过（ZIP 项需 `--zip`） |
| 干净解压 1.0.0 ZIP：契约；`e2e_check.py --package <解压目录> --zip dist/…-1.0.0.zip` | 51/51 OK（规格 JSON 比对在解压包内跳过）；105/105 OK |
| 反证（T14 要求「移植前先证明 FAM-01/02/03 类故障可被检出」）：把全家福 1.0.0 的 `_submit_unauthorized` 与 `cmd_demo` 拼回本包副本再跑 e2e | 7 项失败/报错：FAM-01×2（含旧代码 404 后走重提分支）、FAM-02×2、FAM-03×2、`test_skill_key_expired_reset_exit4`；换回本包代码全过 |
| 密钥/上游扫描（技能凭证、`sk-`、`Bearer`、上游域名与模型名） | 包与 dev 无命中 |
| Python | 3.13（脚本按 3.7+ 标准库编写） |

## 规格验收项对照（T01–T15 归 Claude A2）

| 编号 | 结果 | 证据（用例） |
|---|---|---|
| T01 首轮与路由 | 通过 | e2e `FirstTurn.test_first_turn_zero_business_http`（问候/仅图/能力/明确需求，唯一网络动作是首次上报 1 次）、`test_close_question`、`test_demo_paths_and_single`（单项只出该项、未知 key 退出 3）；`TravelSpec.test_t01_suggested_scene_in_first_turn`；契约 `test_route_precedence`（京都/樱花、西安/古城消歧，十主题可达）、`test_first_turn_copy_clean`。「只要文字/不要看图」「以已实际展示的记录去重」是宿主行为，写入 SKILL.md 第 1 节，脚本侧无法验证 |
| T02 单人输入与三项确认 | 通过 | 契约 `test_plan_people_rules`、`test_consent_and_lock_rules`、`test_consent_copy`；e2e `Confirmation.*`、`test_guardian_wording_and_three_consents`、`test_bad_photo_named_no_network`、`RepairA3.test_wed_a3_02_*`（换图后作废确认与未提交键） |
| T03 离线示例与路径 | 通过 | 契约 `test_demos_consistent`、`test_fam_03_demo_missing_one_exit3`、`test_demo_link_path_with_space/hash`（含规格三条合成路径 `Travel Demo Assets/`、`Travel#Demo/`、`Travel%Demo/`，真实建文件、Markdown 解析、无 query/fragment、定位原文件）、`test_wed_a3_01_demo_has_no_network`；e2e `test_demo_links_survive_markdown`、`test_fam03_*`、`DemoAssets.test_package_demos_trace_to_provenance` |
| T04 新旧账户与 Key | 通过 | e2e `PayConversion.*`（六入口无账户均给关联入口或如实断网/繁忙）、`RepairPay103.*`、`test_existing_account_skips_auth_and_topup` |
| T05 计费与确认 | 通过 | e2e `test_full_flow_auth_topup_deliver`、`test_mid_task_insufficient_asks_first`、`test_replay_same_key_charged_once`、`TravelSpec.test_t13_reported_payment_not_credited`；契约 `test_skill_required_rules`（不算同意付费执行的情形） |
| T06 失败与等待 | 通过 | e2e `Waiting.*`（一次/两轮/五轮仍处理/抖动恢复/始终不可达/明确失败）、`OriginalTaskSpec.*`（401/404/409/5xx 只查原键）；契约 `test_timeouts_consistent`（90/15/120/30/0/240 逐处比对） |
| T07 PNG 与交付 | 通过 | 契约 `test_png_verify`（CRC/zlib/Adam7）；e2e `test_corrupt_png_kept_pending_then_get_only`、`test_download_fail_keeps_task`、`test_size_mismatch_reported`、`test_wed_a3_03_delivery_links_space_and_hash`（含 `Travel%Demo`） |
| T08 历史与工单 | 通过 | e2e `Support.*`（10 项） |
| T09 八字段遥测 | 通过 | e2e `Telemetry.*`（7 项，含每个早退分支前已上报、关闭开关 `MPS_TRAVEL_PORTRAIT_JOURNEY=off`、409 不覆盖）；契约 `test_telemetry_contract` |
| T10 平台字段与目录 | 通过 | 契约 `test_frontmatter_*`、`test_examples_*`（三对与规格逐字一致、中英同场景/单人/2:3/1024×1536，错配可检出）、`test_package_dir_depth_at_most_two`；e2e `ZipLayout.*`；logo SHA 见上 |
| T11 接管与收藏 | 通过（声明检查） | 契约 `PayConversion.test_takeover_rules_first`、`test_favorite_section`、`test_no_hidden_html_comment`。真实宿主记忆写入与不 @ 自动选中未验证 |
| T12 身份与可见 AI 标注 | 通过 | 契约 `test_prompt_baselines`（单人锁定、不含 28/东亚/女性）、`test_disclosure_everywhere`；e2e `test_full_flow_auth_topup_deliver`（交付话术与 `index.html` 含标注、提示词无示例人物属性）、`TravelSpec.test_t12_demo_items_all_disclosed` |
| T13 微信与支付 Mock | 通过（客户端侧） | e2e `TravelSpec.test_t13_link_expiry_comes_from_server_not_fixed`（1800/900/300 秒均按服务端有效期转述，脚本无 30 分钟硬编码）、`test_t13_callback_links_account_while_client_closed`（模拟回调完成关联、客户端零请求、重复回调幂等、之后 `status` 为已关联）、`test_t13_reported_payment_not_credited`；`test_pay_02_*`（缺期限/过期不转述）。Cookie/state/verifier、302 跳转与第 6 分钟二维码属服务端网页逻辑，本包不持有也不实现 |
| T14 原任务持久化 | 通过 | e2e `OriginalTaskSpec.test_submit_unknown_persisted_before_post_and_locked`、`test_fam01_*`、`test_fam02_*`、`test_poll_401_recovers_once_then_persistent_keeps_task`；契约 `test_fam_01_02_unauthorized_submit_never_resubmits_or_unlocks`；反证见上 |
| T15 资源与预算边界 | 通过 | e2e `TravelSpec.test_t15_request_body_has_only_six_fields`、`test_client_rejects_unregistered_field`、`test_server_rejects_unregistered_field`；契约 `test_body_whitelist`；示例 10 张 SHA 与规格一致，logo SHA 一致 |
| T16/T17 | 不属 Claude | Codex A3 与附录 D |

阶段 6 S6-01–S6-57：适用项均落在上表用例（S6-08/09 首轮零 HTTP，S6-10 示例 key/标题一致、缺失退出 3，S6-24/25/26 新环境 topup/无账户入口/断网不报繁忙，S6-43 未登记字段客户端与服务端各一次，S6-45 禁用词含 AST 取脚本字符串，S6-47/48/49/51 尺寸提示、画廊、点名文件、不覆盖）。S6-39/40/41/42 按规格判不适用（无 Range/inline_delivery/计费前重试契约，sibling_reuse=false），代码未新增相关字段，契约 `test_body_whitelist` 断言无 `inline_delivery`。S6-52/53/55/57 只做声明检查，真实宿主行为未验证。

## 偏离开发文档的地方

1. `first-turn` 额外输出 `suggested_scene`（规格 §3 路由与 T01 消歧的脚本化实现，供宿主参考；只在本地计算，零网络）。不改变对客话术。
2. 服装默认值写在脚本场景表里（规格 §4 各场景要点原文的服装部分）；用户另行确认的服装经 `--outfit` 传入，同样冻结在方案里，改动需重新 `plan` + 确认。
3. 「只要文字/不要看图」「同一对话只展示一次（以实际展示为准）」「收藏」等宿主侧行为只写入 SKILL.md 执行规范，脚本无法感知对话历史，未做脚本断言。
4. 沿用全家福基座的 `X-Skill-Device`：只按操作系统区分 desktop/unknown，不判断 mobile/cloud（无可靠依据时报 unknown，规格「不伪装环境」）。

## 未验证项

- 真人/儿童保真、生产签名输入路由、本产品在 WorkBuddy 宿主的实际行为（加载、欢迎、示例、收藏、不 @ 自动选中），A3 后由附录 D 本机导入另测。
- 真实微信扫码与手机/异浏览器跳转、真实付款与到账、客户钱包；平台审核与上架。
- 约 2.4MB 包的平台接受情况。

## 部署与回滚

- 部署：无（fast 车道，无后端改动、无迁移、无重启）。负责人手动上传 1.0.0 ZIP；logo 为 `dist/logo.png`。
- 回滚：1.0.0 为首版，未上架；不上传或平台下架即可，无数据迁移。

## 退回意见

无。

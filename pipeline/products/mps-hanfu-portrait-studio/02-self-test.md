# 自测报告：mps-hanfu-portrait-studio 1.0.0

已读 WorkBuddy 官方文档快照（docs/sop/workbuddy-official-docs.md，快照日期 2026-11-08；读了「一、开放平台概述」「二、技能」全部：目录结构、8 个必填 frontmatter、examples_zh/examples_en、references/scripts/templates）。本单只打 `config.yaml` channels 中的 `workbuddy-skill`，未读专家章节、未打专家包。

- 首次开发（`rounds.dev` 0 → 1）。时间：2026-11-12T18:51:48+08:00，Claude 定时运行（无人值守）。
- 依据：开发文档固定提交 `1a7d115d281ca3b25ce86609cfb9b29adfe7a895`（`01-dev-spec.md` / `01-dev-spec.json` / `01-a1-validation.json`）；产品通知 `evt-8025373d…`（source_ref 同上）。开发文档、选品单、logo、demo-assets 均未改。
- **A1 复检：通过。** 16 项齐（立项与词表、官方读取记录、场景路由表、十主题动作/视觉参照/锁定与四基线、10 张示例与审计、立体 logo、计费默认值、模型与成本毛利 76.47% ≥ 60%、fast 车道、14 接口带源码位置、漏斗对应表、相邻技能分界、不承接清单、T01–T17 与阶段 6 逐项对照 57 项、决策记录、MD/JSON 一致）；串行前置：银发 1.0.1 已 submitted（规格决策记录）。无退回意见。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；真实支付 0；生产变更 0；未上传、未发布。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-hanfu-portrait-studio-1.0.0.zip`，4812372 字节，25 个文件，逻辑根最多两级，SHA256 `624ee30dbd94d09f9b2a44d7b4c4c239cb9dd09e0d4f7c1ae11af23a1f9d30ba` |
| 版本 | 1.0.0（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py`、first-turn-preview 一致） |
| logo | `02-package/dist/logo.png` Codex 原文件未动，SHA256 `d6cda4a802770817435324b898d5e0f1705adf95cd2a7c665baba27727c2978b`，418271 字节（外置，不进 ZIP） |
| 十张示例 | `dev/sync_demos.py` 按 `demo-assets/provenance.json` 逐张核对后原字节复制到 `assets/`（SHA 与规格第 5 节表一致，派生记录 `dev/demos-derivation.json`）；身份参考 `01-reference-seed.png` 未入包 |
| SKILL.md | 15057 字节（≤ 15360）；frontmatter 8 必填字段与 examples 中英各 3 条逐字取自规格 JSON `frontmatter`；欢迎句「欢迎使用WorkBuddy官方认证技能 汉服写真照相馆。」 |

## 实现要点（对应规格）

- 基座：继承银发 1.0.1（`59aca1d…`）的 `studio.py` 状态机（账户/原安装身份、绑定 401、原任务锁、SLV-A3-01 先作废再校验、PNG/JPEG 有界完整解码、8 字段遥测、售后），去掉银发的家人代购、老兵条件与年龄外观业务。
- 只为本人：`plan` 改为 `--self yes/no/unknown --adult yes/no/unknown`；未知一次合并补问（`needsEligibility`），明确不是本人/未成年 `notEligible`；不开放代购（`--orderer` 不再接受）。三项独立同意不变（本人照片许可 / 发送给图片服务及算力供应商 / 按张计费）。
- 十主题：`SCENES` 的视觉参照与妆发逐字取自规格 JSON `scenes[].direction / hair_makeup`；`build_prompt` 七段：真实性基线（第一段）→ 人物身份基线 → 动作+视觉参照+妆发（整套同一形制）→ 构图 → 文字基线 → 安全基线 → 锁定句；艺术主题（魏晋/日常/流仙/侠客/园林）注明不按考古精确复原。
- 形制整套切换：`--form song/tang/ming`（日常、园林）与 `quju`（仅园林），其他组合 `formInvalid`；默认 daily=宋风上襦两片裙、garden=宋褙子套系（规格决策记录）。
- 路由：具体形制词 → 风格词 → 泛朝代词 → 环境词；`first-turn` 另返回 `intent` 提示（婚服/旗袍和服军装/儿童/多人越界、闺蜜各拍 `separate_self_tasks`、地名 `clarify_destination`、跨朝代 `form_conflict`、`needs_form_choice`、`accessory_with_profile`）；规格第 1 节 16 条用户原话逐条测试。
- 相邻技能：均未核实「已上架且入口可用」，包内不点名转介，越界需求如实说明（规格第 11 节）。
- 开工复述含本人这张照片、主题与服饰妆造、画幅与像素、1 张、AI 非实拍、细节差异、发送给图片服务及算力供应商、「按张计费，以实际账单为准」。

## 自测结果

| 命令 | 结果 |
|---|---|
| `cd mps-hanfu-portrait-studio && python3 -m unittest discover -s tests`（仓库内，含规格 JSON 对照） | Ran 63, OK |
| `python3 dev/e2e_check.py --zip dist/mps-hanfu-portrait-studio-1.0.0.zip`（仓库源码） | Ran 136, OK |
| 干净解压 1.0.0 ZIP（testzip 无损坏、最深 2 级、25 文件）后 `unshare -rn python3 -I -m unittest discover -s tests` | OK（63） |
| `unshare -rn python3 -I dev/e2e_check.py --package <解压目录> --zip dist/…-1.0.0.zip` | Ran 136, OK，0 跳过（含 ZipLayout、FrontmatterYaml：PyYAML 6.0.3 解析 ZIP 原始 SKILL.md，拒重复键、未引用冒号空格反例） |
| scripts/、tests/ 按 `ast.parse(feature_version=(3,7))` | 通过（运行环境 Python 3.13，未在 3.7 解释器实跑） |
| 包与 dev 目录密钥形态扫描（mpskill_/sk-/Bearer/私钥/供应商域名与模型名） | 无（仅测试里的反向断言字符串） |

## 阶段 6 逐项（规格第 13 节 S6-01…S6-57）

| 编号 | 覆盖用例（e2e 类.用例 / 契约用例） | 结果 |
|---|---|---|
| S6-01 关联→浏览器确认→继续 | AccountBilling.full_flow_auth_topup_deliver；HanfuSpec.t13_callback_links_account_while_client_closed | 通过（Mock） |
| S6-02 正常出图扣费余额正确 | AccountBilling.full_flow_auth_topup_deliver（扣 1，剩余取服务端） | 通过 |
| S6-03 第二张 402 → 充值同编号续接、第一张不重扣 | AccountBilling.mid_task_insufficient_asks_first；RepairSlv101.needs_credits_topped_up_still_not_old_photo | 通过 |
| S6-04 策略拒绝不扣费 | AccountBilling.policy_reject_not_charged | 通过 |
| S6-05 5xx 不扣费，原键查询恢复 | AccountBilling.5xx_not_retried；OriginalTaskSpec.409_and_5xx_query_original_only | 通过 |
| S6-06 同编号重放不重扣 | AccountBilling.replay_same_key_charged_once | 通过 |
| S6-07 凭证失效清除并重关联 | AccountBilling.skill_key_expired_reset_exit4；InheritedRepairTrv101.trv01_r1_* | 通过 |
| S6-08 首轮无 http/套餐/充值/价格，欢迎句逐字 | 契约 first_turn_copy_clean、welcome_exact；FirstTurn.close_question | 通过 |
| S6-09 首轮零业务 HTTP | FirstTurn.first_turn_zero_business_http | 通过 |
| S6-10 示例离线、key 与 SKILL/README 一致、缺图退 3 | FirstTurn.demo_*、fam03_*；契约 demos_consistent、fam_03_demo_missing_one_exit3 | 通过 |
| S6-11 SKILL 必含语句、不含「三个方案」 | 契约 skill_required_rules | 通过 |
| S6-12 不算同意付费的情形 | 契约 skill_required_rules、consent_copy | 通过 |
| S6-13 授权本身不扣费 | 契约 handoff_copy | 通过 |
| S6-14 两句定心话 | 契约 handoff_copy | 通过 |
| S6-15「### 现在需要你做的」+「打不开」 | 契约 handoff_copy | 通过 |
| S6-16 无未开放授权路径 | 契约 handoff_copy、customer_copy_no_site_or_key；AccountBilling.untrusted_link_rejected | 通过 |
| S6-17 已有账户有次数直做 | AccountBilling.existing_account_skips_auth_and_topup | 通过 |
| S6-18 拒绝开通固定一句 | AccountBilling.balance_menu_and_decline | 通过 |
| S6-19 无慢到账口径；自述不算到账 | 契约 no_slow_payment_wording、instant_arrival_wording；RepairPay103.pay_01_* | 通过 |
| S6-20 外层超时 240 = 90+120+0+30，全包一致 | 契约 timeouts_consistent | 通过 |
| S6-21 开工复述齐全；未同意先补确认 | 契约 consent_copy（start_recap 十项）；Confirmation.no_consent_no_task | 通过 |
| S6-22 中途余额不足先问 | AccountBilling.mid_task_insufficient_asks_first | 通过 |
| S6-23 账户说法走菜单 | AccountBilling.balance_menu_and_decline；契约 takeover_rules_first | 通过 |
| S6-24 全新环境 topup 有路 | PayConversion.fresh_topup_* | 通过 |
| S6-25 无账户 topup/balance/status 调 quick-entry | PayConversion.fresh_status_and_balance_have_way_out、fresh_history_gives_link | 通过 |
| S6-26 断网 ≠ 服务忙 | PayConversion.topup_membership_link_network_not_busy、fresh_topup_offline_honest、run_needs_credits_link_failure_kind | 通过 |
| S6-27 上报白名单 8 字段、一次、开关 | Telemetry.fields_once_and_flag、off_switch；契约 telemetry_contract | 通过 |
| S6-28 提前返回分支已上报 | Telemetry.every_early_branch_reports | 通过 |
| S6-29…S6-34 六种等待时序 | Waiting.once / two_rounds / still_pending_after_window / glitch_then_recover / never_reachable / explicit_failure | 通过 |
| S6-35 先交图、首次调整引导一次 | AccountBilling.full_flow_auth_topup_deliver | 通过 |
| S6-36 失败四拍、服务忙口径、费用以服务记录为准 | 契约 failure_copy；Waiting.never_reachable、explicit_failure | 通过 |
| S6-37 转述本次扣费与剩余、低余额提醒 | AccountBilling.full_flow_auth_topup_deliver | 通过 |
| S6-38 原图未改、重新生成先说明计费 | AccountBilling.full_flow_auth_topup_deliver | 通过 |
| S6-39 / S6-40 / S6-41 / S6-42 | 规格判定 not_applicable_current_contract（无 Range / inline_delivery / 计费前重试字段，sibling_reuse=false）；以 OriginalTaskSpec.corrupt_png_kept_pending_then_get_only、Waiting.download_fail_keeps_task、契约 body_whitelist（无 inline_delivery）证明只读原任务、不重 POST | 不适用（按规格） |
| S6-43 未登记字段被拒（客户端/服务端） | AccountBilling.client_rejects_unregistered_field、server_rejects_unregistered_field；HanfuSpec.t15_request_body_has_only_six_fields | 通过 |
| S6-44 凭证失效退出 4 | AccountBilling.skill_key_expired_reset_exit4 | 通过 |
| S6-45 对客禁用词（AST 取进度文案） | 契约 forbidden_words、customer_copy_no_site_or_key | 通过 |
| S6-46 余额/消费记录/工单 | Support.* 10 项 | 通过 |
| S6-47 尺寸偏差提示裁切 | Waiting.size_mismatch_reported | 通过 |
| S6-48 index.html 画廊 | AccountBilling.full_flow_auth_topup_deliver | 通过 |
| S6-49 参考图格式点名文件 | Confirmation.bad_photo_named_no_network | 通过 |
| S6-50 离线检查不调后端 | FirstTurn.demo_paths_and_single；契约 png_verify | 通过 |
| S6-51 输出不覆盖 | AccountBilling.full_flow_auth_topup_deliver（`_unique`）；RepairA3.wed_a3_03_* | 通过 |
| S6-52…S6-57 技能收藏 | 契约 favorite_section（只在首次交付成功后、收藏/暂不、两层写入一句偏好、取消、不假装成功） | 声明检查通过；真实宿主记忆与不 @ 触发未验 |

规格 T 组补充：T01/T13 `route_precedence`、`route_intent_boundaries`、HanfuSpec.t01/t13；T02/T14 `plan_people_rules`、`consent_and_lock_rules`、`slv_a3_01_*`（契约 2 项 + e2e RepairSlv101 5 项，早退变体含本人/成年 unknown/no、形制非法、坏图/截断图（路径含空格与 #）、脸不清、文字超长、多人、主题无效）；T03 Markdown 安全路径（空格/#）；T07 TRV-02 有界解码；T10 `frontmatter_*`、`examples_*`（中英逐条同主题，齐胸 chest-high）；T12 `prompt_baselines`、`scenes_match_spec`、HanfuSpec.t12_*。

## 偏离与决策

- **示例图体积**：规格要求按原 SHA 原字节复制，10 张共 4718679 字节（单张 434–646KB），ZIP 4.8MB，比此前各包（≤2.7MB）大；官方快照未写包大小上限。契约里的体积上限相应调为单张 < 700KB、合计 < 5MB（银发包是单张 < 320KB、合计 < 3MB）。若平台拒收体积，需按规格修订后压缩重出，不在本包自行压缩。
- `intent` 信号与 `--form` 参数是规格第 1、3 节路由与「整套切换」的实现细化，不改计费、账户或请求体字段。
- 开发文档无需退回。

## 未验证项

- 真实 WorkBuddy 宿主导入/解析与对话行为（首轮、intent 处理、收藏、不 @ 触发），frontmatter 平台解析结论仅来自 PyYAML 与标准库检查；包体积是否被平台接受。
- 真人出图效果、形制与妆造准确率、不同性别和输入质量效果；真实付款、微信关联、核款（真实上游与支付调用 0）。

## 部署与回滚

- fast 车道，无后端改动，无部署。上传由负责人手动；本流水线不上传。
- 回滚：本 slug 无已上传版本，回滚即不上传 1.0.0；ZIP 与源码保留在仓库。

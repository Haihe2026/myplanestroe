# 独立测试报告 · mps-id-photo-background 1.0.2

- 复测时间 2026-11-07T23:50:36+08:00。通知 `evt-4eff53b0559ef840930c2eb42e625f036af7728b893298b88d81fa0bb2b1ec8e`。固定输入 `6590d26ec08a6df8cf5b6774c6c1a87e6e126ff4:pipeline/products/mps-id-photo-background/status.json`。
- 认领前远端 `main` 为 `b857f3084cc7502fc88e12950318bc22f83a2e8c`，指定产品仍为 `package_ready`，状态 Git blob `ddb5c9835f1bb4e2cdd2336bd94a4184cfe64d70` 与固定输入一致。看板认领提交 `bad94a8e5ae684c399e7d7aca41c2ee302ddc7c2`。
- 已阅读 WorkBuddy 官方文档，核对技能结构、必填 frontmatter 和平台提交流程。[技能](https://open.workbuddy.cn/docs/skill) · [专家](https://open.workbuddy.cn/docs/expert) · [开放平台概述](https://open.workbuddy.cn/docs/what-is-open-platform)
- [1.0.1 独立测试报告](https://github.com/Haihe2026/myplanestroe/blob/b857f3084cc7502fc88e12950318bc22f83a2e8c/pipeline/products/mps-id-photo-background/03-test-report.md)

## 独立复跑

- [WorkBuddy 团队版 1.0.2 ZIP](02-package/dist/mps-id-photo-background-1.0.2.zip) 为 887236 字节，Git blob `53dbf1ffb65be1cd43797a69efeb7a07d4cf9cd2`。SHA256 `4ac1a7d5c266c35d7d76f0b3dc55cbc9c20cca56e2752ab48ac51f14f56673dc` 与 [自测报告](02-self-test.md) 一致。
- 用 `git archive` 从固定提交提取 ZIP、模拟后端脚本及示例溯源夹具。每个套件在 WSL 的独立 POSIX 临时目录中重新解压，Python 3.12.3，以非 root 身份运行。权限探针确认文件模式 0600，目录模式 0500 拒绝写入。
- 解压前验证 CRC、唯一包根和 24 个无重复文件路径，未发现符号链接或路径穿越。1.0.2 最深为两级目录，10 张 PNG 均直接位于 `assets/`。以 1.0.1 ZIP 为反例运行同一层级测试，预期失败，检出 `assets/demos/` 下 10 个超深文件。
- 测试仅用合成账户和进程内模拟后端。Python 审计钩子拦截套接字和子进程调用，触发 0 次。真实付费生图、真实遥测、核款、生产变更和上传均为 0 次。
- 模拟端到端夹具出现未关闭文件的 `ResourceWarning`。全部断言通过，无跳过。保留原测试与包源码。

| 项目 | 入口 | 结果 |
|---|---|---|
| 契约 | `unittest` 从干净解压的 `tests/` 发现测试 | 22/22 |
| 模拟端到端 | `dev/e2e_check.py --package <干净解压的技能目录> --zip <1.0.2 ZIP> -v` | 52/52 |
| 旧版反例 | `dev/e2e_check.py --package <同一技能目录> --zip <1.0.1 ZIP> -v ZipLayout` | 预期失败，检出 10 个超深路径 |

## WorkBuddy 验收与上传

| 项目 | 结果 |
|---|---|
| 真机行为验收 | **blocked**。接收端缺少已验证的电脑操作适配器。真机验收已跳过（负责人长期规则，2026-11-07），无真机结果或截图。 |
| 上架前 `/pricing` 零消耗浏览器验证 | **blocked**。接收端缺少已验证的电脑操作适配器。按同一长期规则跳过，无浏览器验证结果。 |
| WorkBuddy 团队版上传 | **blocked**。接收端缺少已验证的上传适配器，待负责人手动上传。平台解析、审核和发布均未验证。 |

按 SOP 的长期规则，1.0.2 通过 A3 的契约与模拟端到端关口，看板推进到 `test_passed`。本次接收结果仍记录真机验收与上传能力阻断。历史 1.0.1 已被平台拒收。

## 逐项脚本结果

### 契约（全部通过）

- `Contract.test_body_whitelist`
- `Contract.test_demo_link_markdown_safe`
- `Contract.test_demos_are_fictional_and_small`
- `Contract.test_demos_consistent`
- `Contract.test_description_seo`
- `Contract.test_exit_codes_and_signals`
- `Contract.test_failure_copy`
- `Contract.test_first_turn_copy_clean`
- `Contract.test_forbidden_words`
- `Contract.test_frontmatter_official_fields`
- `Contract.test_handoff_copy`
- `Contract.test_instant_arrival_wording`
- `Contract.test_no_secrets_in_package`
- `Contract.test_no_slow_payment_wording`
- `Contract.test_package_dir_depth_at_most_two`
- `Contract.test_size`
- `Contract.test_skill_required_rules`
- `Contract.test_support_commands_contract`
- `Contract.test_support_copy`
- `Contract.test_telemetry_contract`
- `Contract.test_timeouts_consistent`
- `Contract.test_welcome_exact`

### 模拟端到端（全部通过）

- `AccountBilling.test_5xx_not_retried`
- `AccountBilling.test_balance_menu_and_decline`
- `AccountBilling.test_client_rejects_unregistered_field`
- `AccountBilling.test_existing_account_skips_auth_and_topup`
- `AccountBilling.test_full_flow_auth_topup_deliver`
- `AccountBilling.test_mid_task_insufficient_asks_first`
- `AccountBilling.test_policy_reject_not_charged`
- `AccountBilling.test_rate_limited_keeps_task_same_key`
- `AccountBilling.test_replay_same_key_charged_once`
- `AccountBilling.test_server_rejects_unregistered_field`
- `AccountBilling.test_skill_key_expired_reset_exit4`
- `AccountBilling.test_submit_lost_queries_original_not_resubmit`
- `AccountBilling.test_untrusted_link_rejected`
- `Confirmation.test_bad_photo_named_no_network`
- `Confirmation.test_no_consent_no_task`
- `Confirmation.test_plan_copy`
- `Confirmation.test_target_must_be_given_not_inferred`
- `DemoAssets.test_package_demos_trace_to_provenance`
- `FirstTurn.test_close_question`
- `FirstTurn.test_demo_links_survive_markdown`
- `FirstTurn.test_demo_missing_assets_exit3`
- `FirstTurn.test_demo_paths_and_single`
- `FirstTurn.test_first_turn_zero_business_http`
- `LocalImage.test_crop_resize_exact`
- `LocalImage.test_target_too_large`
- `Support.test_balance_shows_recent_records`
- `Support.test_feedback_busy_and_no_account_saved`
- `Support.test_feedback_creates_ticket_without_charge`
- `Support.test_feedback_local_validation_no_network`
- `Support.test_feedback_lost_response_same_key_single_ticket`
- `Support.test_history_failure_and_no_account`
- `Support.test_history_paging_and_states`
- `Support.test_skill_key_not_accepted_and_accounts_isolated`
- `Support.test_ticket_lookup_failure`
- `Support.test_ticket_status_reply_and_isolation`
- `Telemetry.test_audit_not_reported`
- `Telemetry.test_corrupt_identity_repaired_and_readonly_skipped`
- `Telemetry.test_every_early_branch_reports`
- `Telemetry.test_failure_does_not_block_and_no_retry_loop`
- `Telemetry.test_fields_once_and_flag`
- `Telemetry.test_link_409_not_overwritten`
- `Telemetry.test_off_switch`
- `Telemetry.test_transport_exception_swallowed`
- `Waiting.test_download_fail_keeps_task`
- `Waiting.test_explicit_failure`
- `Waiting.test_glitch_then_recover`
- `Waiting.test_never_reachable`
- `Waiting.test_once`
- `Waiting.test_size_mismatch_reported`
- `Waiting.test_still_pending_after_window`
- `Waiting.test_two_rounds`
- `ZipLayout.test_zip_dir_depth_at_most_two`

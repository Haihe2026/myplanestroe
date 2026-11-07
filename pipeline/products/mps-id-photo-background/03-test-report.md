# 独立测试报告 · mps-id-photo-background 1.0.1

- 2026-11-07（北京时间）已读 WorkBuddy 开放平台官方文档，核对 ZIP 结构、必填 frontmatter 和发布步骤。[技能](https://open.workbuddy.cn/docs/skill) · [专家](https://open.workbuddy.cn/docs/expert) · [开放平台概述](https://open.workbuddy.cn/docs/what-is-open-platform)
- 通知 `evt-b577ee81de30178acb36ed5da43b90fec00baa55bd4a9a9f9378cb2854edee21`。固定输入 `03185cb7311ccf3f6fc0e70d978f3029f47c7f7c:pipeline/products/mps-id-photo-background/status.json`。认领前远端状态为 `package_ready`，状态 blob `6ca963c08de2ba68eb7589198aebbd6d1daa0c33` 与固定输入一致。看板认领提交 `728f24fef31590fc3b923fb55ee7b24085f8c2cf`。
- 1.0.1 前次独立复测及真机阻断见 [认领前的独立测试报告](https://github.com/Haihe2026/myplanestroe/blob/c22d6740a0a98a729c96c96a4b0c2ed6525f52de/pipeline/products/mps-id-photo-background/03-test-report.md)。本轮按产品目录的 [1.0.1 书面豁免](01-host-acceptance-waiver-1.0.1-20261107.md) 重新独立测试。

## 干净 ZIP 与独立复跑

- [WorkBuddy 团队版 1.0.1 ZIP](02-package/dist/mps-id-photo-background-1.0.1.zip)，887098 字节，24 个文件。Git blob `8c5051339587fd2718bb4c1d6220e7fbaa8f8fc1` 与认领提交一致，SHA256 `80e4ec1379bb686ccfe37269bdc36221bc0a2258949ab6b6f1f1acdd3f071009` 与自测报告一致。唯一根目录、路径、重复项、符号链接及 CRC 检查通过。
- 从固定提交通过 `git archive` 取 ZIP、开发脚本及演示溯源夹具。Ubuntu WSL、非 root、Python 3.12.3，两个套件分别干净解压。实测文件模式 0600，目录模式 0500 时写入被拒绝。
- 使用合成账户及进程内模拟后端。审计钩子拦截网络和子进程调用，触发 0 次。真实付费生图、核款、生产变更、真实遥测、上传均为 0 次。
- 模拟端到端脚本有夹具文件未关闭的 `ResourceWarning`，全部断言通过。示例链接回归通过，包含 Windows 路径模拟及示例溯源。1.0.1 授权链接沿用包内实现。

| 项目 | 入口 | 结果 |
|---|---|---|
| 契约 | `unittest` 从干净解压的 `tests/` 发现测试 | 21/21，通过 |
| 模拟端到端 | `dev/e2e_check.py --package <干净解压的技能目录> -v` | 51/51，通过 |

## WorkBuddy 验收与上传

| 项目 | 结果 |
|---|---|
| 真机行为验收 | 真机验收已豁免。接收端无已验证的电脑操作适配器，场景 1–24 均未执行，无截图或真实宿主结果。 |
| 上架前 `/pricing` 零消耗浏览器验证 | 在本版书面豁免范围内，未执行。 |
| WorkBuddy 团队版上传 | blocked。接收端无已验证的上传适配器。由负责人按 SOP 手动上传，当前无审核或发布结果。 |

## 结论

1.0.1 按书面豁免范围通过 A3，产品停在 `test_passed`。待负责人手动上传本报告所列的 1.0.1 ZIP。

## 逐项脚本结果

契约（全部通过）

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
- `Contract.test_size`
- `Contract.test_skill_required_rules`
- `Contract.test_support_commands_contract`
- `Contract.test_support_copy`
- `Contract.test_telemetry_contract`
- `Contract.test_timeouts_consistent`
- `Contract.test_welcome_exact`

模拟端到端（全部通过）

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

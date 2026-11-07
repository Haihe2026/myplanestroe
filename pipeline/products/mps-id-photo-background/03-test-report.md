# 独立测试报告 · mps-id-photo-background 1.0.1

- 2026-11-07（北京时间）在线阅读 WorkBuddy 官方文档，核对目录、必填 frontmatter 和发布流程。[技能](https://open.workbuddy.cn/docs/skill) · [专家](https://open.workbuddy.cn/docs/expert) · [开放平台概述](https://open.workbuddy.cn/docs/what-is-open-platform)
- 通知 `evt-c4b02048268ca974c8b16ace350fe547d99e06ec35f8eb6af7653cfc76588a2b`。固定输入 `383e5f6678490df2513b05fe4a127d69f5bd7c9f:pipeline/products/mps-id-photo-background/status.json`。认领前远端 `main` 的 `package_ready` 状态 blob 与固定输入相同（`828cf9aa2329fc4c1bb5c5adb59daa525cd9954f`）。看板认领提交 `e9e9d95e1c86f0571b3a2fce5b6f087a033fe040`。
- 1.0.0 的独立测试和单次真机豁免保存在 `a66055797b590236fa206c2213aeaabd2c9544f3:pipeline/products/mps-id-photo-background/03-test-report.md`。本次是 1.0.1 修复轮，现有豁免记录对应上一轮复位及验收，按原 A3 关口记录。

## 干净 ZIP 与独立复跑

- `02-package/dist/mps-id-photo-background-1.0.1.zip`，887098 字节，24 个文件，Git blob `8c5051339587fd2718bb4c1d6220e7fbaa8f8fc1`。SHA256 `80e4ec1379bb686ccfe37269bdc36221bc0a2258949ab6b6f1f1acdd3f071009`，与自测报告一致。唯一根目录、路径、重复项、符号链接和 CRC 检查通过。
- Ubuntu WSL，非 root，Python 3.12.3。两套测试分别干净解压。验证文件模式 0600、目录模式 0500 下写入被拒绝。通过 `git archive` 从固定提交取原始 ZIP、开发脚本和演示溯源夹具。
- 使用合成账户、进程内模拟后端。测试进程审计钩子拒绝网络、DNS 和外部进程调用，两套均记录 0 次拦截。真实付费生图、生产变更、核款、真实遥测与上传均为 0 次。
- 端到端脚本产生未关闭夹具文件的 `ResourceWarning`，全部断言通过。示例路径转义回归通过，覆盖 Windows 路径规则模拟、点开头的上级目录与示例溯源。真实 WorkBuddy 点击效果待验收。

| 项目 | 测试入口 | 结果 |
|---|---|---|
| 契约 | `unittest` 从干净解压的 `tests/` 发现测试 | 21/21，通过，退出 0 |
| 模拟端到端 | `dev/e2e_check.py --package <干净解压的技能目录> -v` | 51/51，通过，退出 0 |

## WorkBuddy 验收与上传

| 项目 | 结果与证据 |
|---|---|
| 包内 `tests/first-turn-preview.md` 场景 1–24 | 全部待验收。接收端缺少已验证的电脑操作适配器，无真实宿主运行及截图。 |
| 上架前 `/pricing` 零消耗浏览器验证 | 待验证。接收端缺少已验证的电脑操作适配器，无浏览器验证证据。 |
| WorkBuddy 团队版上传 | blocked。接收端缺少已验证的上传适配器，SOP 由负责人在 A3 通过后手动上传。无审核或发布记录。 |

## 结论

离线测试通过，A3 拦停为 `HOST_ACCEPTANCE_UNAVAILABLE`。测试轮次保持 0，发布版本为空。1.0.0 ZIP 保留。1.0.1 授权链接沿用原实现，通用微信扫码地址改动待上游确认。

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

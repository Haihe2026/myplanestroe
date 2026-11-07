# 给 Codex：本单真机验收已豁免，从 package_ready 复测走完流程

负责人 LI 已书面豁免本单（证件照换底助手 mps-id-photo-background）的真机行为验收，豁免记录：`01-host-acceptance-waiver-20261107.md`。

规则已同步：
- SOP 新增「负责人豁免」一节（提交 15ef467）：豁免只对本单有效，不改全局配置；A3 只验契约与端到端；test_passed 后停在 test_passed 等负责人手动上传。
- Codex consumer 指令已加豁免例外（提交 6ccb66c）。

本单状态已复位回 `package_ready`（status.json 提交 444c914，blocked 已清空）。请按 SOP 处理：

1. 认领 `package_ready`，对 ZIP 1.0.0（sha256 f187e418…）做 A3 独立复测：契约 20 项 + 端到端 50 项，跳过真机验收与上架前零消耗浏览器验证。
2. 端到端在可验证 POSIX 文件权限的隔离环境（WSL/Linux）重跑；Windows 下 `AccountBilling.test_skill_key_expired_reset_exit4` 的 POSIX 断言失败是环境不匹配，不得改测试凑通过。上一轮唯一失败项即此项，须按原命令重跑验证。
3. `03-test-report.md` 注明「真机验收已豁免」，不得写成已通过。真实上游调用 0，生产变更 0。
4. 通过后置 `test_passed`，按 A4 备好上架文案与核对（`04-listing.md`），即停在 `test_passed` 等负责人手动上传，不拦停、不冒充上架。

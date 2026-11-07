# Claude 确认：最新 SOP 长期规则（2026-11-07T21:41:13+08:00）

回应 Muse 通知 evt-94426b4b（req-muse-to-claude-sop-latest-20261107）与 evt-ec37f062（req-muse-to-claude-upload-manual-20261107）。

已读 docs/sop/sop-image-gen-skill-auto.md 的阶段 7、A.5（上架授权、永远拦停第 2 条例外）、「负责人手动层」、「负责人豁免」，确认按以下口径执行：

1. 上传一律负责人手动：流水线到 test_passed 即交付最终包，打包时不假设 Codex 会上传；test_passed 后不等上传，下一单按流水线状态接手。
2. 负责人手动层所列事项（选品、定价与试用次数、部署、真实付费生图授权、共享后端改动授权、网页读取放行、登录/扫码、核款发放、上传与审核结果）自动化不代做。
3. 技能内示例图由 Codex 按规格数量用上游资源生成并记 provenance/audit；Claude 无生图凭证，不生成示例图；开发与自测真实上游调用仍为 0。

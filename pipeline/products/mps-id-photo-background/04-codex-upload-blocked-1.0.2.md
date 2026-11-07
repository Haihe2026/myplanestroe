# WorkBuddy 团队版 1.0.2 交付记录

- 产品 `mps-id-photo-background`，通知 `evt-e9e10aa26d173e6da53b2633cfc417c2b3b0b1fb8fb59a67f25c769eae5c4d26`。
- 固定输入 `c30ff6336a08aecd8c15550cfbef85c0f4b77422:pipeline/products/mps-id-photo-background/status.json`。核对远端 `main` 提交 `d1e068c8450831743eb4364e05ecb3af79bb337d`，产品仍为 `test_passed`，包版本为 1.0.2，状态文件 Git blob `14038315628fdcdec7c6fac902fb9b4b037c78b2` 与固定输入一致。
- 交付包为 [mps-id-photo-background-1.0.2.zip](https://github.com/Haihe2026/myplanestroe/blob/c30ff6336a08aecd8c15550cfbef85c0f4b77422/pipeline/products/mps-id-photo-background/02-package/dist/mps-id-photo-background-1.0.2.zip)。本次重新计算 ZIP 的 SHA-256 为 `4ac1a7d5c266c35d7d76f0b3dc55cbc9c20cca56e2752ab48ac51f14f56673dc`，与[独立测试报告](03-test-report.md)一致。报告记录契约 22/22、隔离 POSIX 模拟端到端 52/52。本次交付核对沿用该复测结果。历史包保存在同一 dist 目录。
- 真机操作能力为 `blocked`，接收端缺少已验证的电脑操作适配器。按 SOP 的长期规则，真机行为验收和上架前零消耗浏览器验证均跳过。
- 上传能力为 `blocked`，接收端缺少已验证的上传适配器。按 SOP，负责人直接手动上传 ZIP，上传后由 Muse 或负责人记录 `submitted`。平台解析、审核、发布和上线后数据均待实际验证。
- 本次只提交产品交付证据。按阶段 7 的手动上传规则，产品保留 `test_passed`。真实付费生图、生产变更、核款和上传均为 0 次。

已读 [WorkBuddy 技能开发文档](https://open.workbuddy.cn/docs/skill)、[专家开发文档](https://open.workbuddy.cn/docs/expert)及[开放平台概述](https://open.workbuddy.cn/docs/what-is-open-platform)。

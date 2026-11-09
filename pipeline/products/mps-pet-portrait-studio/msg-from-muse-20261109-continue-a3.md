# 给 Codex：宠物写真照相馆 1.0.0 继续做 A3 独立检查

skill_id: mps-pet-portrait-studio
时间：2026-11-09 CST

包已就绪：2026-11-09 17:44 Claude 置 package_ready，1.0.0，契约 34/34、端到端 56/56 全过，十张示例图哈希核对后同步入包。
包位置：pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.0.zip
SHA256：660889b11d3f03bf35d05b5006a18c9325e7d84f4d56e09b45a962c20f189ade

A3 检查事件 evt-96973e42bb4cd8feaf265b6d3195d408dd41cd4337a0d18f457797fb6257262a 已于 2026-11-09 17:46 被认领，但至今（19:01）无检查结果，已停滞 75 分钟。负责人（LI）要求直接继续检查。

按 SOP 做静态检查（不跑完整测试、不调上游、不做浏览器验证）：
- ZIP 完整性：SHA256 与记录一致，解压无损坏
- 包目录结构：最多两级，无三级及以上嵌套；示例图在 assets/ 下，demos.json 只写裸文件名
- Frontmatter：含 name、description、version；examples_zh ≤ 3、examples_en ≤ 3、两者数量一致；每条 examples_zh[i] 与 examples_en[i] 必须表达同一场景
- 契约：SKILL.md 与开发文档一致；欢迎句格式正确；对客文案无禁用词、无上游信息泄露
- 示例图：数量与规格一致（10 张），文件存在，路径 Markdown 安全；路径不得含空格和 #（或已 URL 编码）
- 规格符合性：实现的功能与开发文档一致，不多做、不漏做
- 重点复核：demo 独立执行零网络；同路径换图后旧确认与原键作废（照片哈希绑定）；成品与画廊链接用安全路径且能命中原文件

检查结果写 03-test-report.md（写明“独立检查通过/不通过”，列逐项检查结果）。
检查合格 → stage 置 test_passed，即为最终版，交付负责人手动上传。
检查不合格 → stage 置 test_failed，03-test-report.md 逐条写缺陷，退回 Claude 修复。

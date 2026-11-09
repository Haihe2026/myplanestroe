# 给 Codex：婚纱写真照相馆 1.0.0 继续做 A3 独立检查

skill_id: mps-wedding-portrait-studio
时间：2026-11-09 CST

包已就绪：2026-11-09 08:39 Claude 置 package_ready，1.0.0，契约 32/32、端到端 52/52 全过。
包位置：pipeline/products/mps-wedding-portrait-studio/02-package/dist/mps-wedding-portrait-studio-1.0.0.zip
SHA256：7eb0b0abf669574c4f14ab6df6f95026e34874dcd69500bff90b82ce18be8001

A3 检查事件 evt-41f79d4724a29727b1e6ef8374403f52adef026e3c69403756c0b0bbe40ce527 已于 2026-11-09 08:41 被认领，但至今无检查结果。负责人（LI）要求直接继续检查。

按 SOP 做静态检查（不跑完整测试、不调上游、不做浏览器验证）：
- ZIP 完整性：SHA256 与记录一致，解压无损坏
- 包目录结构：最多两级，无三级及以上嵌套；示例图在 assets/ 下，demos.json 只写裸文件名
- Frontmatter：含 name、description、version；examples_zh ≤ 3、examples_en ≤ 3、两者数量一致；每条 examples_zh[i] 与 examples_en[i] 必须表达同一场景
- 契约：SKILL.md 与开发文档一致；欢迎句格式正确；对客文案无禁用词、无上游信息泄露
- 示例图：数量与规格一致（10 张），文件存在，路径 Markdown 安全；路径不得含空格和 #（或已 URL 编码）
- 规格符合性：实现的功能与开发文档一致，不多做、不漏做

检查结果写 03-test-report.md（写明“独立检查通过/不通过”，列逐项检查结果）。
检查合格 → stage 置 test_passed，即为最终版，交付负责人手动上传。
检查不合格 → stage 置 test_failed，03-test-report.md 逐条写缺陷，退回 Claude 修复。

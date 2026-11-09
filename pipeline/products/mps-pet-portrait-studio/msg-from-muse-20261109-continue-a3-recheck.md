# 给 Codex：宠物写真照相馆 1.0.1 继续做 A3 复查

skill_id: mps-pet-portrait-studio
时间：2026-11-09 CST

修复版已就绪：2026-11-09 19:44 Claude 置 package_ready，1.0.1，修了 A3-PET-01/02/03 三项，新增 7 项回归，契约 34/34、端到端 63/63 全过，前两单历史缺陷逐项复核未回退。
包位置：pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.1.zip
SHA256：26c3ad64f64a22e3515854e17e1c1a0f9893b67db8a36cbe77b064417b6597e0

A3 复查事件 evt-73f7628e5276c829865333fefe7097385d745f2f402eb2feff8dc498a8d6c92f 已于 2026-11-09 19:46 被认领，但至今（21:02）无检查结果，已停滞 76 分钟。负责人（LI）要求直接继续复查。

按 SOP 做静态检查（不跑完整测试、不调上游、不做浏览器验证），只查 1.0.1 这个新包：
- ZIP 完整性：SHA256 与记录一致，解压无损坏
- 包目录结构：最多两级，无三级及以上嵌套；示例图在 assets/ 下，demos.json 只写裸文件名
- Frontmatter：含 name、description、version；examples_zh ≤ 3、examples_en ≤ 3、两者数量一致；每条 examples_zh[i] 与 examples_en[i] 必须表达同一场景
- 契约：SKILL.md 与开发文档一致；欢迎句格式正确；对客文案无禁用词、无上游信息泄露
- 示例图：数量与规格一致（10 张），文件存在，路径 Markdown 安全；路径不得含空格和 #（或已 URL 编码）
- 规格符合性：实现的功能与开发文档一致，不多做、不漏做
- 重点复核三项修复是否到位（见 03-test-report.md 旧版 A3-PET-01–03 的期望）：
  - PET-01：提交前是否原子保存原键、固定正文及可续接状态；409 或重规划是否不再丢原键、不再静默覆盖
  - PET-02：截断/不可解码的 PNG 是否不再写入输出与画廊、不再宣告交付
  - PET-03：缺一张示例时是否报告资源缺失并退出 3
- 同时复核前两单历史缺陷未回退：示例中英文义对齐、示例图路径无空格无 #、demo 零网络、照片哈希绑定（换图作废确认与原键）、Markdown 链接用安全路径

检查结果写 03-test-report.md（写明“独立检查通过/不通过”，列逐项检查结果，注明是 1.0.1 复查）。
检查合格 → stage 置 test_passed，即为最终版，交付负责人手动上传。
检查不合格 → stage 置 test_failed，03-test-report.md 逐条写缺陷，退回 Claude 修复。

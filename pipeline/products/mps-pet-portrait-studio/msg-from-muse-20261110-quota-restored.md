# 给 Codex：宠物主题照相馆 1.0.3 继续做 A3 复查（额度已恢复）

skill_id: mps-pet-portrait-studio
时间：2026-11-10 CST

负责人（LI）已于 2026-11-10 16:33 前完成 Codex 额度充值，额度已恢复。请继续做 1.0.3 的 A3 复查。

背景：1.0.3 是改名重打包，2026-11-10 07:43 Claude 置 package_ready。改名原因：1.0.2 的 display_name「宠物写真照相馆」在平台已被占用，上传被拒；LI 选定新名「宠物主题照相馆」，slug mps-pet-portrait-studio 不变，功能零改动，另附 logo。
包位置：pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.3.zip
SHA256：5e24d1827a7ce30bf4a1eeaa96a7211749bd352f3d06bcbd8de83b9171b776bf
logo：02-package/dist/logo.png（PNG 512×512 RGBA）
A2：契约 34/34、端到端 68/68 全过。

A3 复查事件 evt-9d9d965700c24ab894394e67ead4f81c05108cc013e8ff584e13ea92129641f4 已于 2026-11-10 07:44:59 被认领，但至今（16:33）无检查结果——原因是 Codex 额度用完，跑不起来，不是包的问题。额度现已恢复，请直接继续复查。

按 SOP 做静态检查（不跑完整测试、不调上游、不做浏览器验证），只查 1.0.3 这个新包：
- ZIP 完整性：SHA256 与记录一致，解压无损坏
- 包目录结构：最多两级，无三级及以上嵌套；示例图在 assets/ 下，demos.json 只写裸文件名
- Frontmatter：含 name、description、version；examples_zh ≤ 3、examples_en ≤ 3、两者数量一致；每条 examples_zh[i] 与 examples_en[i] 必须表达同一场景
- 改名一致性：display_name、欢迎句、README、description、规格里的名字一律是新名「宠物主题照相馆」（英文 Pet Themed Portrait Studio），旧名「宠物写真照相馆」不得残留；slug 仍为 mps-pet-portrait-studio
- 契约：SKILL.md 与开发文档一致；欢迎句格式正确；对客文案无禁用词、无上游信息泄露
- 示例图：数量与规格一致（10 张），文件存在，路径 Markdown 安全；路径不得含空格和 #（或已 URL 编码）；logo 文件存在
- 规格符合性：实现的功能与开发文档一致，不多做、不漏做；功能与 1.0.2 零改动
- 复核 PET-01/02/03 修复未回退（见 03-test-report.md 旧版 1.0.2 复查报告）：原键查回 404 只报进度未能确认、零重发；401 清旧凭证、从原安装身份恢复；隔行 PNG 非法过滤字节被拒绝、坏压缩流转补取；缺一张示例报失败退出 3
- 同时复核前两单历史缺陷未回退：示例中英文义对齐、示例图路径无空格无 #、demo 零网络、照片哈希绑定（换图作废确认与原键）、Markdown 链接用安全路径

检查结果写 03-test-report.md（写明“独立检查通过/不通过”，列逐项检查结果，注明是 1.0.3 复查）。
检查合格 → stage 置 test_passed，即为最终版，交付负责人手动上传。
检查不合格 → stage 置 test_failed，03-test-report.md 逐条写缺陷，退回 Claude 修复。

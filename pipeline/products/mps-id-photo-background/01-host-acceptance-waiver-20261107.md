# 真机验收豁免记录 · 证件照换底助手（mps-id-photo-background）

- 豁免人：负责人 LI（2026-11-07 在主聊亲口指示：跳过真机验收，让流程先走完，今天务必把最终上架版技能包做出来）
- 豁免时间：2026-11-07 20:35（北京时间）
- 豁免范围：仅本单的真机行为验收与随附的上架前零消耗浏览器验证。A3 只验契约与端到端。
- 不豁免：部署、钱、生产类闸门；不改全局配置 `allow_listing_without_host_acceptance`（仍为 false）；不改测试断言（Windows 下 POSIX 断言失败不得改测试凑通过，端到端须在可验证 POSIX 文件权限的隔离环境重跑）。
- 流程：本单复位回 package_ready → Codex 复测 → test_passed（03-test-report.md 注明「真机验收已豁免」）→ 到 test_passed 即停，等负责人手动上传；负责人上传后置 submitted。
- 依据：SOP「负责人豁免」一节（提交 15ef467）与 Codex consumer 豁免指令（提交 6ccb66c）。
- 风险：本单上架版包未经真实宿主验证即上架，首轮真实对话行为（技能加载、首轮顺序、定价页）未经真机核实。

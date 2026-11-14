# 给 Codex：第十二轮选品单，请写规格

新方向第一单：房产经纪人房源图——房源图精修助手（mps-fangyuan-photo-enhancer，P1/fast）。选品单在 pipeline/products/mps-fangyuan-photo-enhancer/00-brief.md，调研在 pipeline/research/2026-11-14-work-position-image-gen.md。

请按 SOP 写 01-dev-spec.md 及配套。首次新包先读仓库官方文档快照（docs/sop/workbuddy-official-docs.md）。

锁死项：欢迎句「欢迎使用WorkBuddy官方认证技能 房源图精修助手。」；付费走 MyPlaneStore 通用套餐 https://myplanestore.com/membership/，0 次免费试用；主题 logo 由上游生成存 02-package/dist/logo.png（PNG 512×512、≤500KB），记 provenance/audit；成品包 ≤3MB；边界：绝不改动房屋结构（不改墙体、窗户、地板、天花板、固定装置，不替换窗外实景，不改户型），每张虚拟布置图必须标注“虚拟布置”并保留原图对照，不编造面积/朝向/配套/房价，不做施工落地承诺。

前序缺陷复核清单（修复不重犯，逐项复核未回退）：账户付费转化 A3-PAY-01/02/03/04；中英示例语义对齐 A3-E01；示例图路径空格/# A3-E02/A3-E03；demo 离线 WED-A3-01；FAM-01/02/03；TRV-01–05；MAT-A3-01/02/03；SLV-A3-01（改方案早退未作废旧同意与旧任务键）；HNF-A3-01–04；DH-A3-01/02/03；示例链接正斜杠；欢迎句逐字一致。

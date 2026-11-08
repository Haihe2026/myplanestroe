# 自测报告：mps-wedding-portrait-studio 1.0.0

- 时间：2026-11-08 北京时间，Claude（负责人交互会话续接 19:28 的认领）
- 已读 WorkBuddy 官方文档快照（`docs/sop/workbuddy-official-docs.md`，快照日期 2026-11-08，读了「二、技能」章）；19:28 另有线上三页读取记录 `02-claude-docs-read-20261108.md`
- 规格：`01-dev-spec.md` / `01-dev-spec.json` 1.0.0（A1 通过）
- 渠道：只做 `workbuddy-skill`（config.yaml channels）
- **A2 结论：未通过，不置 package_ready。** 代码、话术和测试都已完成；唯一缺口是 10 张示例图（规格 `demo_generation.required_before_final_package=true`，实际 0 张）。Codex 本次运行禁止真实付费生图，已记录阻断（`01-codex-demo-dependency-blocked-evt-026aab1d….md`）。按 A.3 拦停，等负责人处理。

## A1 复检

15 项齐全：立项字段与词表、官方文档读取记录、场景路由表（10 个）、提示词要点与三条基线加人物身份基线、示例选题 10 个及生成方式、计费默认值、模型与毛利（约 76.47%，≥60%）、fast 车道、接口字段带源码位置、漏斗 L0–L4、相邻技能分界、不承接清单、验收用例 T01–T10、决策记录、MD/JSON 一致。没有退回意见。

## 包内容（`02-package/mps-wedding-portrait-studio/`，两级目录）

- `SKILL.md`（14.5KB，<15KB）：8 个必填字段；`examples_zh`/`examples_en` 各 3 条，按规格 5.1 逐条对应 white-studio / seaside / japanese 和画幅；欢迎句「欢迎使用WorkBuddy官方认证技能 婚纱写真照相馆。」。
- `scripts/studio.py`：沿用证件照换底助手 1.0.6 已通过 A3 的客户端骨架（授权、充值、任务续接、消费记录、工单、首次对话上报、Markdown 安全路径）。新增 10 个场景、`--people 1/2`（写真只做单人）、`--shape portrait/landscape/square`，画幅只发适配器已映射的三种；提示词四段：身份（两人时逐人锁定左右位置）→ 主题视觉 → 无文字 → 安全。
- `scripts/welcome_copy.py`：两人时的同意话术（两位都是成年人且同意）、单人限制、拒绝话术（未成年人、换脸、合成照片里没有的人）。
- `references/`：scenes.md（路由表加超时）、prompts.md、platform-rules.md。
- `assets/demos.json`：10 个 key 和标题，与 SKILL.md、README 一致。**PNG 未入包**（见下）。
- 开发目录 `02-package/dev/`：`mock_backend.py`（新增画幅校验，按请求画幅出图）、`e2e_check.py`、`sync_demos.py`（从 `demo-assets/` 核对 provenance 哈希后缩放入包）、`build.py`（不覆盖已有 ZIP，拒绝三级目录）。

## 测试结果

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包，真实状态） | 32 项：30 通过，2 项因示例 PNG 缺失失败（`test_demos_consistent`、`test_demos_are_fictional_and_small`） |
| 端到端（仓库内包，真实状态） | 52 项：46 通过，2 项跳过（无 ZIP），4 项因示例缺失报错（3 个 demo 命令用例加 provenance 追溯） |
| 契约测试（临时副本，放入 10 张纯色合成占位 PNG，不入库） | 32/32 通过 |
| 端到端（同一临时副本，并打出临时 ZIP） | 52 项：51 通过，1 项报错（provenance 追溯：没有 `demo-assets/`，属预期） |
| 干净解压临时 ZIP 后重跑 | 契约 32/32；端到端仍只有 provenance 一项报错；ZIP 24 个文件，最多两级 |

合成占位只用来证明除示例图之外的代码路径都能跑通，**不是交付物**，没有提交，也不能代替真实示例。

新增或改写的关键用例：10 场景与规格一致（系列、画幅、路由表、prompts、demos 三处对齐）；写真两人返回 `peopleUnsupported` 且零网络；两人海边全流程（授权 → 最后一步 → 交付），提交的 `size=1536x1024`、提示词含「左侧的人」；尺寸偏差提示；中英示例在场景、人数、画幅三个维度上的错配都能检出（A3-E01）；规格 5.1 两条合成路径 `Codex Demo Assets/white-studio.png`（A3-E02）和 `Codex#Demo/white-studio.png`（A3-E03）按 Markdown 解析后，拆掉片段和查询串再解码，指向原文件。

## 阶段 6 必测项对照

沿用 1.0.6 的账号计费、引导确认、等待轮询六种时序、交付、遥测、消费记录和工单用例，全部改成婚纱写真场景后通过（临时副本）。以下不适用或未做：

| 项 | 状态 | 原因 |
|---|---|---|
| 直连下载失败后 `inline_delivery` 补取 | 不做 | 规格第 3 节：下载失败走原任务再取，不新增字段 |
| 计费前拒绝同键等待重试 | 等待 0 秒 | 规格 `prebilling_wait_s=0` |
| 同设备账户复用 | 不做 | config `sibling_reuse: false` |
| 大图分段续传 | 不做 | 规格只要求原任务再取图 |
| 真机行为验收、收藏卡片实测 | 跳过 | 负责人长期豁免（2026-11-07）；验收单 `tests/first-turn-preview.md` 已更新为本技能 |

## 未验证

- 10 张示例图（规格要求的最终包前置条件）：0 张。
- 真实宿主行为、真实支付、真实生成、平台审核：都没做。真实上游调用 0 次，生产变更 0。
- WorkBuddy 上传解析：没有 ZIP，未上传。

## 恢复步骤（示例图到位后，Claude 约 10 分钟）

1. Codex 把 10 张 PNG 和 `provenance.json`、`generation-audit.json` 放进 `pipeline/products/mps-wedding-portrait-studio/demo-assets/`。
2. 运行 `python3 02-package/dev/sync_demos.py`（核对哈希、缩放、写 `demos-derivation.json`）。
3. 重跑契约测试和端到端，运行 `dev/build.py` 打 `dist/mps-wedding-portrait-studio-1.0.0.zip`，干净解压重跑，补本报告的 ZIP SHA256，置 package_ready。

## 部署与回滚

不涉及后端部署。本单是新技能，没有上一版，回滚就是不上传。

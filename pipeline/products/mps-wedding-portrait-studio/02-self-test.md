# 自测报告：mps-wedding-portrait-studio 1.0.0

- 时间：2026-11-09 北京时间，Claude 定时运行（认领通知 evt-bdef4dc745884994b746f4ee5a9228b263a538c134bf5b9cf9f6b21b0d9570a8）；接续 2026-11-08 22:57 的示例图拦停
- 已读 WorkBuddy 官方文档快照（`docs/sop/workbuddy-official-docs.md`，快照日期 2026-11-08，读了「二、技能」章，本次运行重读）
- 规格：`01-dev-spec.md` / `01-dev-spec.json` 1.0.0（A1 通过；与上次相比只改了示例图交付状态和读取日期）
- 渠道：只做 `workbuddy-skill`（config.yaml channels）
- **A2 结论：通过，置 package_ready。**
- 交付包：`02-package/dist/mps-wedding-portrait-studio-1.0.0.zip`，920365 字节，24 个文件，最多两级，SHA256 `7eb0b0abf669574c4f14ab6df6f95026e34874dcd69500bff90b82ce18be8001`

## 本次（2026-11-09）

1. 示例图同步：`dev/sync_demos.py` 按 `demo-assets/provenance.json` 逐张核对 10 张源图 SHA256 全部一致，本地等比缩放（长边 480）加 128 色调色板压缩，写入 `assets/`（与 `demos.json` 同级）。合计 867268 字节，与 Codex 审计记录 `offline_sync.package_png_bytes` 一致。派生记录 `dev/demos-derivation.json`（源哈希 → 包内哈希）。没有新增生图调用。
2. 目视核对 10 张包内图：每张与场景对应（白纱影棚、秀禾、花园、海边、油画婚纱、韩式、汉服、油画肖像、赛博、日系），画面内无可读文字、水印、品牌标志；均为虚构成年人（provenance `fictional_adult=true`）。
3. `dev/build.py` 补一行创建 `dist/` 目录（原脚本在目录不存在时报错），其他不变；仍拒绝覆盖已有 ZIP、拒绝三级目录。

## 测试结果（2026-11-09）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 32/32 通过 |
| 端到端（仓库内包，打包前） | 52 项：50 通过，2 项跳过（尚无 ZIP） |
| 端到端（仓库内包，打包后） | 52/52 通过（含 ZIP 两级目录与内容一致、provenance 追溯） |
| 干净解压 ZIP 后契约测试 | 32/32 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录>`） | 52/52 通过 |
| ZIP 完整性 | `testzip` 无损坏；最大深度 2；不含 `__pycache__`、dev 目录、`demo-assets/` 原图 |
| 密钥扫描（产品目录） | 无命中 |

真实上游调用（本次 Claude）：0。生产变更：0。

## 历史记录（2026-11-08，示例图到位前）

## A1 复检

15 项齐全：立项字段与词表、官方文档读取记录、场景路由表（10 个）、提示词要点与三条基线加人物身份基线、示例选题 10 个及生成方式、计费默认值、模型与毛利（约 76.47%，≥60%）、fast 车道、接口字段带源码位置、漏斗 L0–L4、相邻技能分界、不承接清单、验收用例 T01–T10、决策记录、MD/JSON 一致。没有退回意见。

## 包内容（`02-package/mps-wedding-portrait-studio/`，两级目录）

- `SKILL.md`（14.5KB，<15KB）：8 个必填字段；`examples_zh`/`examples_en` 各 3 条，按规格 5.1 逐条对应 white-studio / seaside / japanese 和画幅；欢迎句「欢迎使用WorkBuddy官方认证技能 婚纱写真照相馆。」。
- `scripts/studio.py`：沿用证件照换底助手 1.0.6 已通过 A3 的客户端骨架（授权、充值、任务续接、消费记录、工单、首次对话上报、Markdown 安全路径）。新增 10 个场景、`--people 1/2`（写真只做单人）、`--shape portrait/landscape/square`，画幅只发适配器已映射的三种；提示词四段：身份（两人时逐人锁定左右位置）→ 主题视觉 → 无文字 → 安全。
- `scripts/welcome_copy.py`：两人时的同意话术（两位都是成年人且同意）、单人限制、拒绝话术（未成年人、换脸、合成照片里没有的人）。
- `references/`：scenes.md（路由表加超时）、prompts.md、platform-rules.md。
- `assets/demos.json`：10 个 key 和标题，与 SKILL.md、README 一致。（11-08 时 PNG 未入包；11-09 已同步 10 张。）
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

- 真实宿主行为（WorkBuddy 内首轮、收藏卡片等）、真实支付、真实生成、平台审核：都没做（真机验收按负责人长期豁免跳过）。Claude 真实上游调用 0 次，生产变更 0。
- WorkBuddy 上传解析：ZIP 未上传，上传由负责人手动完成。
- 示例图是文生图效果示意，不证明参考图身份保持效果（规格已注明）。

## 恢复步骤（已于 2026-11-09 执行完毕，保留备查）

1. Codex 把 10 张 PNG 和 `provenance.json`、`generation-audit.json` 放进 `pipeline/products/mps-wedding-portrait-studio/demo-assets/`。
2. 运行 `python3 02-package/dev/sync_demos.py`（核对哈希、缩放、写 `demos-derivation.json`）。
3. 重跑契约测试和端到端，运行 `dev/build.py` 打 `dist/mps-wedding-portrait-studio-1.0.0.zip`，干净解压重跑，补本报告的 ZIP SHA256，置 package_ready。

## 部署与回滚

不涉及后端部署。本单是新技能，没有上一版，回滚就是不上传或在平台下架；包源码和 ZIP 都在仓库，可按提交号恢复。

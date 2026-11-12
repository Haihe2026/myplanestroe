# 汉服写真照相馆：启动前置条件核对

核对时间：2026-11-12T16:29:27+08:00。此文件是事件处理与流程依赖记录，不是开发规格、A1 产物或产品 blocked 结论。

## 已收到的内容与状态

- 事件 `evt-0bbc3ba158cfcc26ca42441c59501e329198a7afd07c2dd5b046ec81b984a60f` 是 `brief_ready` 状态通知；原固定来源 `f1167ea4653c65950d71f1a8ea1b18d58ba10cef:pipeline/products/mps-hanfu-portrait-studio/status.json`。它要求 Codex 接手本人单人汉服写真 Skill 的规格，brief 列出十个主题。已校验固定输入指纹、当前输入未变、本机与仓库原 claim 一致；不重复认领。
- 同产品原 Muse 请求 `req-muse-to-codex-start-hanfu-20261112`（`kind=handoff`）固定来源 `6bb8b683a96fca24da8602b0dd9c23f5c4dfa074:pipeline/products/mps-hanfu-portrait-studio/msg-from-muse-20261112-start-hanfu-101.md`，对应事件 `evt-5889b13b7dad5abbb81b481821dcc8d7ea84b6a61917124847599691b971e66d`。已核原请求哈希、固定正文及原认领；正文要求阶段 0–4/A1、十张示例和一张 logo，未附 G7 原文。两通知在本次合并处置，只发送一份依赖请求，各沿各自原 claim 回执。
- 核对时远端 main 为 `c55cb3fe6ceac8c3463ddc363a642379382758f3`。汉服仍为 `brief_ready`、owner=null、spec/dev/test 轮次均为 0；没有现有 `01-dev-spec.md/json`。本次未认领产品、未写开发规格、未生成素材、未派 Claude 开发。
- 上一包银发写真照相馆仍为 `test_passed`，包版本 `1.0.1`，状态更新时间 `2026-11-12T10:54:03+08:00`，listed=null；未找到该产品 `04-listing` 文件。这证明仓库尚无已上传状态，不能据此断言负责人实际上未上传。

## 现行条款与尚未对齐的依据

当前 SOP blob `53e9b9862e62dadd2bd5a20d6e5e5697e3beab46`，固定读取提交 `c55cb3fe6ceac8c3463ddc363a642379382758f3`，第 323 行原文：

> 13. **串行开发（负责人 2026-11-08 定）**：在前一个包顺利完成上传（stage 到 `submitted` 或 `listed`）之前，不启动下一个包的开发（不写规格、不开发、不打包）。上一单未上传就停住，不并行推进。目的是先跑通一单的完整链路（含负责人手动上传），再开下一单。

第九轮调研记录第 4 行转述“LI 2026-11-12 16:06 令继续下一个，依 G7（交付后未回复即继续下一包，优先于串行规则）”。该页固定 blob `7e8107f018881a8d07e5c7de1718cf8faedb5005`；此处确实存在口径差异，不能把转述当成已核对的原始条款，也不声称 Muse 没有该依据。

已核当前 SOP、CLAUDE.md、relay README、本聊天 AGENTS/HANDOVER、第五至第九轮调研及相关旅行产品日志；未定位到 G7 原文、适用范围及优先级的固定来源。关键词搜索未命中不代表穷尽全部历史。当前按负责人在本聊天“以仓库现行 SOP 为准”的指示，暂不跨过该启动门槛。

## 给 Muse 的具体依赖与恢复方式

请核实并完成其中一条：

1. 若负责人已真实上传银发 `1.0.1`，根据事实补齐其上传证据并更新为 `submitted` 或 `listed`；不要仅为解锁下一单修改状态。
2. 若 G7 确实是当前生效的继续规则，请补齐其可核对的固定原文与适用关系，并将当前 SOP 的冲突口径对齐；本次不要求新的生图、生产、财务或发布授权，也不通过仓库转述扩大这些权限。

完成后，请针对同一 `mps-hanfu-portrait-studio` 新建严格八字段 `kind=retry` 请求，`source_ref` 为实际固定 40 位提交，`source_path` 指向本产品内说明前置条件已满足的资料。原 brief_ready 指纹已处理，单改上一包状态不会保证重派本次通知；必须发新的显式 retry。收到后 Codex 将重新核对最新 SOP/状态与官方文档，满足前置条件即继续，无需负责人逐单重新确认。

本次保持汉服 `brief_ready` 与银发 `test_passed` 原状，不写 `blocked`、不改 BOARD，不覆盖 Claude 产物。依赖请求 ID 为 `req-codex-to-muse-hanfu-serial-prerequisite-20261112`，只通过既有 relay 仓库请求交 Muse，不跨聊天发送。

## 在线读取及权限边界

本次重新在线读取 `https://open.workbuddy.cn/docs/skill`：2026-11-12T16:29:27+08:00，HTTP 200，实际读取 277042 字节，SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`。当前仅完成启动前置核对，未据此宣称已完成任何开发文档或 A1。

真实上游调用 0；后端业务调用 0；生产写入/部署/重启 0；真实支付、客户财务修改、平台上传 0；未新增 worker、心跳、自检或周期监测。

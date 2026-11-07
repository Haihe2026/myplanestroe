# Codex 对最新 SOP 的核对记录 · 2026-11-07

已核对 Muse 请求 `req-muse-to-codex-sop-latest-20261107` 与事件 `evt-5bfd7b3d7fb6de3349de4820cc73e7cd5e9728146cf39a703c76dab2764cadfc`。固定来源为 `7346b64c3f6a4d260e40fea722eacb5671965f11:pipeline/products/mps-id-photo-background/msg-from-muse-20261107-sop-latest.md`，并比对同一提交及当前 main 的 SOP 阶段 7、A.5 和「负责人手动层」。

1. 仓库现行 SOP 要求流水线到 `test_passed` 时交付最终 ZIP，由负责人手动上传，上传后再记录 `submitted`。配置仍保留 `codex_may_publish: true`，SOP 明确该字段的自动上架口径已停用。本聊天此前收到过由 Codex 负责上传的直接指示，本次只记录仓库分工与该指示的差异，未执行上传或提交审核。
2. SOP 把选品、定价与试用、部署和共享后端授权、网页读取放行、登录扫码、核款发放及上传与审核反馈列为负责人事项。本通知只确认规则，不构成新增执行授权。
3. SOP 记录了技能演示资产的例外，按规格数量生成并保留 provenance 和 audit。A3 独立测试的真实上游调用为 0。本次确认未调用任何上游资源。

证件照换底助手当前为 Claude 的 1.0.1 修复轮，仓库状态为 `blocked`（`OFFICIAL_DOCS_UNREADABLE`）。现有包版本为 1.0.0，`listed` 为空。本次仅提交本确认记录和事件回执。

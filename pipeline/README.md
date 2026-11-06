# 生图类 Skill 自动流水线

Muse 选品 → Codex 写开发文档 → Claude Code 开发 → Codex 测试与上架 → Codex 回收数据。

三个 AI 开工前必须先读 `docs/sop/sop-image-gen-skill-auto.md`（尤其第 A 章），并按其中的目录约定、状态机和自动关口执行。

- `config.yaml`：负责人维护的流水线配置，AI 只读。
- `BOARD.md`：所有单子的当前状态。
- `BLOCKED.md`：被拦停、等负责人处理的单子。
- `sop-proposals.md`：AI 提出的 SOP 改进建议，只追加。
- `products/<skill-id>/`：每个单子的交接文件。新选品由 Muse 新建目录，放入 `00-brief.md` 和 `status.json`（`stage` 为 `brief_ready`）。

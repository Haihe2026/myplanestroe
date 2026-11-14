# 生图类 Skill 自动流水线

Muse 选品 → Codex 写开发文档 → Muse 审规格 → Codex 开发并自检 → Muse 交付负责人验证上传。

两个 AI 开工前必须先读 `docs/sop/sop-image-gen-skill-auto.md`（尤其第 A 章），并按其中的目录约定、状态机和自动关口执行。

- `config.yaml`：负责人维护的流水线配置，AI 只读。
- `BOARD.md`：所有单子的当前状态。
- `BLOCKED.md`：被拦停、等负责人处理的单子。
- `sop-proposals.md`：AI 提出的 SOP 改进建议，只追加。
- `products/<skill-id>/`：每个单子的交接文件。新选品由 Muse 新建目录，放入 `00-brief.md` 和 `status.json`（`stage` 为 `brief_ready`）。

## 共用通知接入（2026-11-06）

本机共用轮询层已启用；各AI独立流程仍按原闭环看板执行。共享层仅检测状态、写通知和维护认领回执，不代做任何角色业务。各角色自己的消费者接入方法见 [relay/README.md](relay/README.md)。通知已创建不等于AI已启动；is_test=true的交通探针不要当作产品任务。

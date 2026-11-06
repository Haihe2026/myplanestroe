# 给 Codex：权限已修好，现在重新认领并写开发文档

## 背景

- 审批权限问题已修好：审批策略改成按需自动复核 + workspace-write 沙箱，28 项测试通过，本地写、GitHub 提交、回读验证均成功（提交 d1914be）。
- LI 已确认：现在重新认领，写开发文档。

## 第一步：认领前先核对，防重复认领

1. 读最新 `pipeline/products/mps-id-photo-background/status.json`（核对时仍是 brief_ready、owner=null、claimed_at=null）。
2. 原认领（事件 evt-9f4295b1，2026-11-06 14:28 认领）已过 6 小时超时、已释放。确认无其他有效认领后，再认领。

## 第二步：认领产品状态

把 status.json 改为 owner=codex、stage=spec_in_progress、claimed_at 写当前时间，提交。

## 第三步：写开发文档

按 SOP A.1 写 `01-dev-spec.md` + `01-dev-spec.json`：

- 先逐项核后端是否真正支持：付费页、账户路由、计费、首次对话统计、模型真实可调用探针。
- 能复用的走快车道；需要后端配置或部署的单独拦停（lane=deploy，按 SOP 写 blocked 并说明原因）。

## 第四步：交接

写完把 status.json 改为 spec_ready，交给 Claude 开发。

## 只做这一步

不跳步开发、不上架。拦停按 SOP 写 blocked 并说明原因。

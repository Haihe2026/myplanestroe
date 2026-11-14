# Muse 问 Codex：请确认重构后的两角色自动化 SOP 流程

平台级问题，非汉服产品任务。本次只回答、不改包、不改产品状态、不部署、不派开发活；真实上游调用 0 次。

## 背景

负责人 2026-11-13 23:50 亲口定：Claude 永久退出自动化 SOP 开发项目，流程改为两角色。只改流程，自动化 SOP 的标准和严格执行的内容不变。

新流程（已写入 SOP 正文）：
- Muse 出主题（选品单）→ Codex 自己写开发文档 → Muse 检查开发文档（审规格）→ 没问题 Codex 开发并自检（独立检查改为自检，检查项与通过标准不变，Muse 交付前按交付检查复核）→ Codex 交 Muse 转负责人验证和上传。

已落地的改动（均已核验落盘）：
- SOP 正文 `docs/sop/sop-image-gen-skill-auto.md`（提交 8f2f30e）
- 接力路由 `pipeline/relay/transport/relay.py`（提交 2ab8146）：brief_ready→codex 写规格，spec_ready→muse 审规格，test_failed→codex 修复，package_ready→codex 自检，test_passed→muse 交付，listed→codex 回收数据
- `pipeline/relay/registrations/claude.json` 已标记退役（提交 3fd69df），config.yaml 定时键 claude_dev 改名 codex_dev（提交 739e1b5）

## 请你确认（书面回复）

请先全文读 SOP 相关章节（角色与职责、阶段流转、自检要求），然后在本产品目录写回复文件 `reply-from-codex-20261114-sop-two-role-confirm.md`，逐条确认：
1. 你理解新的两角色分工：Muse 出主题＋审规格＋交付，Codex 写开发文档＋开发＋自检。
2. 以后接到 brief_ready，你按 SOP 自己写开发文档；接到 package_ready，你按自检检查项与通过标准自己做检查，不跑完整测试、不调上游、不做浏览器验证。
3. 你不会自行修改 SOP；发现问题只往 `sop-proposals.md` 追加建议，由负责人决定。
4. 如有任何不清楚或有歧义的地方，在回复里逐条列出来，不要猜。

## 说明

- 自动化任务仍按负责人 2026-11-12 20:25 的令暂停：这条只是流程确认，不派新产品轮次、不启动新开发。
- 回复经 relay-poll 带回后由 Muse 转报负责人。

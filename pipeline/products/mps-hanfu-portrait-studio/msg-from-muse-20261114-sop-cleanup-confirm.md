# 请彻底确认：清理后的两角色 SOP（最新标准）

负责人 2026-11-14 亲口定：旧的模式都改掉，按新的跑；有 Claude 参与的环节全部删掉，按最后最新的标准执行 SOP。清理已按此令落地，请你彻底确认一遍。

## 已清理并落盘（请逐项核对原文）

- SOP `docs/sop/sop-image-gen-skill-auto.md`（提交 098dc91b，blob 1d85f87）：
  - A3 旧条文统一改为静态检查：豁免段（单单/长期）不再写“只验契约与端到端（重跑）”；阶段 6 结尾分工明确 A2 做脚本测试、A3 只静态核对解压后的 ZIP，不重新执行脚本测试；报告模板 B.4 改为静态检查逐项，不再有“模拟后端”“脚本测试”“真机截图”旧项。
  - 真机行为验收一律标明 Codex 不执行、仅作负责人本人实测参考；阶段 8 宿主更新后由负责人本人实测。
  - `codex_may_publish` 默认值改为 false（自动上架已停用）。
  - “永远拦停”一节不再引用仓库 `CLAUDE.md`（六条规则原文保留在 SOP 里）。
  - SOP 里只剩一句 Claude 相关文字：第 194 行“负责人 2026-11-13 亲口定：Claude 永久退出流水线”——这是负责人退出决定的记录，不是参与环节。
- 配置 `pipeline/config.yaml`（提交 870489bd）：`codex_may_publish` 由 true 改为 false。
- SOP 索引 `docs/sop/README.md`（提交 ed0f545d）：流水线简介改为两角色流程。
- 接力层路由（2026-11-13 已改，无需再动）：brief_ready→codex，spec_ready→muse，test_failed/package_ready→codex，test_passed→muse，listed→codex；角色只剩 muse、codex。

## 请你书面确认（逐条写进回复文件）

1. 现行流程里是否还有 Claude 参与的环节（路由、阶段、配置、SOP 文字）？如有，逐条列出；如没有，明确写“无”。
2. A3 只做静态检查、A2 跑自动化测试，两者是否已无混淆；B.4 模板是否与之一致。
3. `codex_may_publish=false` 与“上传一律负责人手动”是否已理解；是否还有任何地方能推导出自动上架。
4. 两角色新标准是否已完整理解、可按此执行；如有歧义或残留文字，逐条列出。
5. 本地待发队列与历史事件：旧的发给 Claude 的事件是否还会被派发或误认作新任务？请说明核查结果。

## 回复方式

- 回复文件：`pipeline/products/mps-hanfu-portrait-studio/reply-from-codex-20261114-sop-cleanup-confirm.md`，经一条 kind=question 的 relay 请求回 Muse。
- 只确认、不改包、不派开发活、不启动新轮次；自动化仍按 2026-11-12 20:25 暂停令停住。
- 请先回已确认的结果与发现的问题，不等全部材料齐全再回。

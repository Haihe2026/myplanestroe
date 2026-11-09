2026-11-09T16:28:57+08:00 | muse | → brief_ready | 第三包选品单已投：宠物写真照相馆（B.0 第四轮调研 10 → 5 → 选定，见 pipeline/research/2026-11-09-round4.md）。等 Codex 认领写规格。
2026-11-09T16:34:18+08:00 | codex | brief_ready → spec_in_progress | 核对固定选品、原通知认领与串行条件，按 fast 编写规格。
2026-11-09T16:44:32+08:00 | codex | spec_in_progress → spec_ready | A1 15 项通过；开发文档与十张示例图、provenance/audit 入仓，10 次登记资源调用，交 Claude Code 实现与 A2。
2026-11-09T17:38:14+08:00 | claude | spec_ready → dev_in_progress | Claude 定时运行认领 1.0.0 开发（通知 evt-c681f470…）。
2026-11-09T17:44:18+08:00 | claude | dev_in_progress → package_ready | 1.0.0 A2 通过：契约 34/34、端到端 56/56（干净解压 ZIP），十张示例图哈希核对后同步；ZIP SHA256 660889b1…，见 02-self-test.md。
2026-11-09T19:05:03+08:00 | codex | package_ready → test_in_progress | 核对 Muse 接力、A2 固定 ZIP、原回执与当前产品状态，继续 A3 独立检查。
2026-11-09T19:09:37+08:00 | codex | test_in_progress → test_failed | 1.0.0 A3 不通过：未知任务可丢原键、截断 PNG 被交付、示例缺一张仍报成功。详见 03-test-report.md，退回 Claude 修复。
2026-11-09T19:38:47+08:00 | claude | test_failed → dev_in_progress | Claude 定时运行认领 1.0.1 修复（通知 evt-121583ec…，并承接 Muse 交接 evt-cc1cc93b…）。
2026-11-09T19:44:06+08:00 | claude | dev_in_progress → package_ready | 1.0.1 A2 通过：修 A3-PET-01/02/03，新增 7 项回归，前两单历史缺陷逐项复核未回退；契约 34/34、端到端 63/63（干净解压 ZIP），ZIP SHA256 26c3ad64…，见 02-self-test.md。
2026-11-09T21:05:26+08:00 | codex | package_ready → test_in_progress | 核对 Muse 接力、原认领和当前状态，复查 1.0.1 固定 ZIP 及三项 A3 修复。
2026-11-09T21:10:05+08:00 | codex | test_in_progress → test_failed | 1.0.1 A3 复查不通过；PET-03 已关闭；PET-01 原键查回 404/401、PET-02 隔行过滤与坏压缩流需继续修复。
2026-11-09T21:38:30+08:00 | claude | test_failed → dev_in_progress | Claude 定时运行认领 1.0.2 修复（通知 evt-756ae968…），修 A3-PET-01 的 404/401 边界与 A3-PET-02 的隔行过滤/坏压缩流。
2026-11-09T21:42:08+08:00 | claude | dev_in_progress → package_ready | 1.0.2 A2 通过：PET-01 原键查询 404 只报进度未能确认、零重发，401 清旧凭证从原安装恢复；PET-02 隔行逐子图核过滤字节、坏压缩流转为补取；新增 5 项、调整 2 项回归；契约 34/34、端到端 68/68（干净解压 ZIP），ZIP SHA256 67799fb6…，见 02-self-test.md。
2026-11-09T22:52:16+08:00 | codex | package_ready → test_in_progress | 核对 Muse 交接、原回执与当前状态，复查 1.0.2 固定 ZIP 和上一轮两项退回。
2026-11-09T22:56:34+08:00 | codex | test_in_progress → test_passed | 1.0.2 A3 独立复查通过，PET-01/02 修复，PET-03 无回退；固定 ZIP SHA256 67799fb6…，交负责人手动上传。
2026-11-10T07:42:21+08:00 | claude | test_passed → dev_in_progress | Claude 定时运行承接 Muse 交接（evt-06e47b21… 改名「宠物主题照相馆」重打包 1.0.3；evt-8f39df04… 交付附 logo＋中文名＋slug），slug 不变、功能不变。

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
2026-11-10T07:43:54+08:00 | claude | dev_in_progress → package_ready | 1.0.3 A2 通过：改名「宠物主题照相馆」（slug mps-pet-portrait-studio 不变），功能零改动；附 logo 02-package/dist/logo.png；契约 34/34、端到端 68/68（干净解压 ZIP），PET-01/02/03 及前序缺陷未回退；ZIP SHA256 5e24d182…，见 02-self-test.md。交 Codex A3 复查（只查 1.0.3）。
2026-11-10T18:38:39+08:00 | claude | package_ready → dev_in_progress | Claude 定时运行承接 Muse 交接 evt-5bd1c40a…（负责人定：1.0.3 A3 作废，按 SOP 第七章付费转化自检整改出 1.0.4；负责人指令整改，非测试退回，rounds.dev 不加）。
2026-11-10T18:45:40+08:00 | claude | dev_in_progress → package_ready | 1.0.4 A2 通过：按 SOP 第七章整改——topup/balance/status/history 无账户走关联入口给链接、断网与繁忙如实区分、SKILL.md 加接管规则、description 加账户类说法与「宠物主题照相馆充值」、收藏核对修正；契约 41/41、端到端 79/79（干净解压 ZIP），历史缺陷未回退；ZIP SHA256 5129d193…，见 02-self-test.md。交 Codex A3（1.0.3 A3 作废）。
2026-11-10T23:17:07+08:00 | codex | package_ready → test_in_progress | 按负责人指示查看沟通仓库，核对 1.0.4 固定包事件与 Muse 同包提醒，仅执行一次 A3。
2026-11-10T23:20:34+08:00 | codex | test_in_progress → test_failed | 1.0.4 A3 不通过；新用户 paid 无关联入口、失效短链仍输出、简介末句漏账户；退回 Claude 修复。
2026-11-11T00:39:05+08:00 | claude | test_failed → dev_in_progress | Claude 定时运行认领 1.0.5 修复（通知 evt-b639a6f3… test_failed，并承接 Muse 交接 evt-3d20e0ac…），修 A3-PAY-01/02/03；rounds.dev 4（test 3 未超上限）。
2026-11-11T00:41:46+08:00 | claude | dev_in_progress → package_ready | 1.0.5 A2 通过：修 A3-PAY-01（paid 无账户走关联入口、到账只按服务端次数）、PAY-02（expires_in 失效链接不转述，沿原安装重取一次）、PAY-03（简介末句含本技能账户问题）；契约 44/44、端到端 95/95（干净解压 ZIP），历史缺陷未回退；ZIP SHA256 2e5604a8…，见 02-self-test.md。
2026-11-11T07:40:49+08:00 | codex | package_ready → test_in_progress | 接续漏接的 1.0.5 固定包，执行 A3 修复项复查。
2026-11-11T07:44:16+08:00 | codex | test_in_progress → test_passed | 1.0.5 付费转化 A3 复查通过，交负责人手动上传。
2026-11-11T08:21:53+08:00 | muse | test_passed → submitted | 负责人报已手动上传，置 submitted，等平台审核。
2026-11-11T09:38:59+08:00 | claude | submitted → dev_in_progress | Claude 定时运行承接 Muse 交接 evt-af5b3710…（负责人定：只换新主题 logo 重打包 1.0.6；1.0.5 已上传待审不动；负责人指令，非测试退回，rounds.dev 不加）。
2026-11-11T09:39:48+08:00 | claude | dev_in_progress → package_ready | 1.0.6 A2 通过：只换新主题 logo（SHA256 4945dcd1… 核对一致）＋版本号，其余与 1.0.5 逐字节一致；契约 44/44、端到端 95/95（干净解压 ZIP），不回退清单全过；ZIP SHA256 32249738…，见 02-self-test.md。交 Codex A3。

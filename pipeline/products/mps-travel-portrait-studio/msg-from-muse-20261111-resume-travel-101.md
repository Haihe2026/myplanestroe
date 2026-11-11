# 给 Codex：恢复第五个产品旅行打卡写真照相馆——继续写规格

负责人 2026-11-11 18:50 原话：「继续开发第五个。」16:05 的暂停解除，继续写规格。

## 现状核实（Muse 18:50 查仓库实况）

- status.json 已由 Muse 置回 `brief_ready`（blocked 已清，resume_to 即 brief_ready）。
- 暂停前你 16:00:25 已认领写规格、16:03:20 置 `spec_in_progress`；但仓库里没有交付任何规格文件（无 `01-dev-spec.md`/`01-dev-spec.json`、无 `02-package/`），已写的内容如在你本机，继续用，不要从头重写；如未写，从 brief 从头写。
- 暂停指令（msg b6d8e7d）作废，不再执行。

## 继续做的事（只写规格）

- 按原规格指令（msg-from-muse-20261111-spec-travel-101.md，提交 bd1260d）继续：首次开发先读仓库快照 `docs/sop/workbuddy-official-docs.md`；规格阶段一并生成主题 logo 存 `02-package/dist/logo.png` 并记 provenance/audit；欢迎句逐字「欢迎使用WorkBuddy官方认证技能 旅行打卡写真照相馆」。
- 只做规格：不开发、不打包、不上传。规格写完置 `spec_ready` 交 Claude，不要直接往下走。
- 选品单：`pipeline/products/mps-travel-portrait-studio/00-brief.md`（P1、fast 车道、10 模板、首版冬季冰雪＋海岛暖冬为主；模板避开“婚纱”字样与婚纱造型，不做多人家庭合影；须注明“AI 生成旅行主题写真，非实地拍摄”；只处理本人照片）。

## 其他

- 全家福微信扫码服务端补丁已部署完成（18:10，health=ok），与本产品无关，不用管。
- 旅行产品之外的其他单子不用动。

# 给 Codex：全家福写真照相馆 1.0.1 Computer-use 真实性测验（SOP 附录 D 首测）

负责人 2026-11-11 直接下令：SOP 末尾新增附录 D「Computer-use 真实性测验」，A3 通过之后、交付负责人手动上传之前，用 computer-use 在本机实测一次。SOP 已更新：docs/sop/sop-image-gen-skill-auto.md，提交 e8cf0f932d10b9424baa8c3b2c2cade71391b0d4（附录 D，D.1–D.5 全文按该提交执行）。首测就是这一单。

## 测验对象

- 技能：全家福写真照相馆，slug `mps-family-portrait-studio`，版本 1.0.1
- A3 已通过：2026-11-11 11:51:39，test_passed，FAM-01/02/03 关闭
- 固定提交：`4669fdb7622e8562c6ce09a9ea7c3d9f4494638d`
- ZIP：pipeline/products/mps-family-portrait-studio/02-package/dist/mps-family-portrait-studio-1.0.1.zip，2,740,120 字节，SHA256 `1138fe6925145fc8c7a0013f661d32af48a521dd707ad9980fd3411b39194756`（先核对 SHA256 与 `03-test-report.md` 一致再测）
- 外置 logo：pipeline/products/mps-family-portrait-studio/02-package/dist/logo.png，512×512 PNG

## 测验动作（SOP 附录 D.3，本机导入安装测验）

用你的 computer-use 功能操作本机电脑上的 WorkBuddy 软件：

1. 打开本机 WorkBuddy 软件，在技能里上传/导入技能包（本地安装测验）。
2. 核验包能正常加载，无解析报错。
3. 核验欢迎句逐字出现（固定格式「欢迎使用WorkBuddy官方认证技能 全家福写真照相馆」）。
4. 核验示例图正常展示，数量与规格一致（10 张）。
5. 走一遍首轮流程（发一张测试图，按模板走一次，demo 展示正常）。
6. 只做本机导入安装测验，不点发布/提交上架；正式提交上架仍由负责人手动。

## 钱的闸门（SOP 附录 D.4，不改）

- 真实付费生图须负责人直接对你授权才做，我的转述不算。本次测验没有该授权。
- 无授权时只做到加载、欢迎句、示例展示、首轮流程，不自行扣费生图；报告里写明哪几项因未授权未做，不得写成已测。
- 不动生产后端，不改共享后端，不碰真实资金流动。

## 结果回传（SOP 附录 D.5）

- 写报告 `04-computer-use-test-report.md`（产品目录，写清每项通过/未通过/未做及原因，附关键截图位置），记 log.md，经 relay 回 Muse。
- 通过：我核对报告（SHA256、逐项结论）后交付负责人下载上传。
- 不通过：按老流程退回责任方——包逻辑问题退 Claude 出新版（重走 A2＋A3＋本测验）；规格问题退你改规格；测验本身能力问题（computer-use 不可用、软件打不开、登录态过期）记 blocked（原因写实），报负责人，不编造通过。
- 测验期间 stage 保持 `test_passed`，不改 stage。

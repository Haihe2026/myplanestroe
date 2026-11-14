# 给 Codex：敦煌写真照相馆开发 1.0.0（第十轮）

产品：敦煌写真照相馆，slug mps-dunhuang-portrait-studio，P1、fast 车道。
选品单：pipeline/products/mps-dunhuang-portrait-studio/00-brief.md
规格：pipeline/products/mps-dunhuang-portrait-studio/01-dev-spec.md（SHA256 1731efb08a7cbd1cddf98fdb2f096412015d8eb6b5e50bd4d35dfe0bb6092396）＋01-dev-spec.json（SHA256 8b46131f7526839246300bdd217250451730e3726f5cc04de6a41df182d460f9）

## Muse A1 复检：通过

Muse 按 SOP A1 清单 16 项逐项核对固定规格，全部通过，见 pipeline/products/mps-dunhuang-portrait-studio/01-a1-validation.json（提交 1829ca9362311b8a3376469b1ca71e6313753852）。要点：十场景与 brief 十模板一一对应、16 条原话逐条有路由、10 张示例 SHA 逐项与实际文件核对一致、主题 logo 512×512 PNG 480802B、计费走通用套餐页 https://myplanestore.com/membership/、0 次免费试用、模型成本 $0.0065/张毛利 76.47%、14 业务 API＋7 OA 路径带源码位置、57 项阶段 6＋21 项敦煌专项验收用例、对客文案无上游信息。Codex 的 A1 自检三项发现 DH-A1-01/02/03 均已闭环。

## 任务

按规格开发 1.0.0（阶段 5–6），出 02-package/，跑 A2 自测，交 Codex 自检 A3；A3 通过后交 Muse 交付负责人手动上传。

## 要点

- 一句话：上传一张本人单人照 → 敦煌主题写真（飞天服饰专项控制：飘带、璎珞、发髻、飞天妆，壁画配色＋沙漠场景，人脸保持，飞天不画成汉服），人脸保持，古风自然。
- 核心差值：通用 AI 常把飞天画成汉服/古装/和服混搭，敦煌写真要做飞天服饰专项控制＋壁画配色＋沙漠场景。
- 10 个模板（均为单人）：飞天反弹琵琶、敦煌壁画仙女、莫高窟飞天、鸣沙山沙漠飞天、月牙泉夜景飞天、敦煌乐舞飞天、飞天水袖舞、敦煌古装仕女、沙漠驼队飞天、星空沙漠飞天。
- 边界：只做单人敦煌写真（本人）；不做多人合影、不做双人；飞天服饰不混搭汉服/和服；不做婚纱、旗袍、和服、军装；不做其他地点旅拍主题；儿童不入镜；模板须注明“AI 生成敦煌写真，非实拍”；须用本人照片、本人知情同意。
- 欢迎句固定格式：「欢迎使用WorkBuddy官方认证技能 敦煌写真照相馆」。
- 付费：通用套餐 https://myplanestore.com/membership/，0 次免费试用；技能只做用户引导和生图效果。
- 成品包大小上限 3MB（负责人 2026-11-14 定，已写进 SOP）：ZIP ≤3,000,000 B，目标 ≤2,500,000 B；十张示例 JPEG 共 1,333,229B、logo 外置 512×512 PNG 480802B 不塞进 ZIP；只压图片、不减功能、不重生示例。
- 示例图与 logo 已就位（demo-assets/ 10 张＋02-package/dist/logo.png），开发直接用，不重生。
- 附录 D（安装检测环节）已按负责人 2026-11-12 令暂停：A3 通过即直接交付，不再派附录 D 测验；规格里不写附录 D 执行要求。
- 上传一律负责人手动，codex_may_publish=false；不要尝试上传或发布。
- 认领后请置 dev_in_progress；开发中卡住超 60 分钟无结果请先报，不要静默。

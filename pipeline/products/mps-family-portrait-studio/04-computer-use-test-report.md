# 全家福写真照相馆 1.0.1 Computer-use 真实性测验

**结果：blocked（电脑操作能力：窗口截图连续超时）。本机导入、加载及首轮测验未完成，不得标记通过。** A3 独立检查仍为通过；按本任务和附录D.1，产品stage保留 `test_passed`，拦的是新增附录D交付条件，不回滚A3或转回Claude改包。

## 固定输入和原认领

- 记录时间：2026-11-11T13:22:57+08:00，北京时间。
- 事件 `evt-2d70e1e5a970e4390badd6e89b3c8a387f36351b7bc44e9996e3d878b1fa5bcf`，原claim `3851236d-0a5d-49d0-9f92-848a2e9d3018` 已核对本机及远端；未重复认领。
- Muse原请求 `req-muse-to-codex-computer-use-test-family-101-20261111`，固定来源 `500856b1c504c83b8dc40cf919104db58bbecf0c:pipeline/products/mps-family-portrait-studio/msg-from-muse-20261111-computer-use-test-family-101.md`；原请求哈希匹配事件ID，当前资料与固定来源一致。
- 执行依据：`docs/sop/sop-image-gen-skill-auto.md` 新附录D（提交 `e8cf0f932d10b9424baa8c3b2c2cade71391b0d4`；本次读取blob `898e0b189b95ac2f0fb2e690a0d4bd092c2e67d2`）。
- 被测包固定于 `4669fdb7622e8562c6ce09a9ea7c3d9f4494638d`，`02-package/dist/mps-family-portrait-studio-1.0.1.zip`，2,740,120字节；本地文件SHA256重新核验为 `1138fe6925145fc8c7a0013f661d32af48a521dd707ad9980fd3411b39194756`，与已通过的`03-test-report.md`一致。外置logo未改。

## 逐项真实结果

| 项目 | 结果 | 实际证据/未做原因 |
|---|---|---|
| ZIP身份核验 | 通过 | SHA256及字节数与固定包/A3相同。 |
| Computer-use初始化 | 通过 | 按已读取的computer-use技能，使用node_repl直接导入@oai/sky，初始化成功。 |
| 本机WorkBuddy是否在运行 | 部分确认 | sky.list_apps返回正在运行的WorkBuddy，且只有一个候选窗口；按返回对象选择。仅能确认窗口元数据，未见可读界面。没有借此声称包已加载。 |
| 首次界面捕获 | 未通过 | sky.get_window_state(include_screenshot=true,include_text=true)返回 `window capture timed out: timed out waiting on channel`。 |
| 有界恢复重试 | 未通过 | 重新sky.list_windows仍返回唯一WorkBuddy；重新get_window后以截图模式再捕获一次，返回同样错误。未复用旧坐标、元素索引或截图。 |
| 在UI导入/安装ZIP | 未做 | 未取得可观察的窗口状态，没有点击、输入或盲上传。 |
| 包在宿主加载、无解析错误 | 未验证 | 尚未导入，不能拿A3静态检查替代宿主结果。 |
| 欢迎句逐字显示 | 未做 | 未进入可观察测试对话，不能声称出现欢迎句。 |
| 十张示例显示 | 未做 | 无宿主展示证据；A3已核验文件本身，不等于宿主显示通过。 |
| 发测试图/首轮流程 | 未做 | 未发送图片或提示词。没有使用真实客户照片。 |
| 付费生成 | 未做 | 本次请求无真实付费测试授权，且未到该环节；本轮真实上游调用0。 |
| 发布/正式提交 | 未做 | 按SOP由负责人手动；本次没有发布动作。 |

## 截图与失败证据

**关键截图位置：无。** 两次窗口捕获都没有返回截图，不伪造截图文件，也不使用其他应用/既有图片替代WorkBuddy实测证据。去除无关应用清单、其他窗口标题和本机个人路径后的工具记录见 `04-computer-use-evidence-20261111.json`。

根因目前只能确认到“WorkBuddy窗口捕获超时”。电脑接口可初始化、能枚举目标窗口，所以不笼统写“computer-use不可用”；没有证据证明登录过期、WorkBuddy不能启动或包有解析问题。

## 停止原因与后续

本次已读取 `computer-use:computer-use` 的SKILL.md及其guidance/api/confirmations。guidance的恢复规则要求状态捕获失败后重新选择窗口并只重试一次，失败则报告准确错误（原文：`retry once; report the exact error if recovery fails`）。已完成该恢复次数，停止界面输入，避免不可观察的操作。

需恢复受支持的WorkBuddy窗口捕获能力后，使用**同一个SHA256包**重跑附录D。当前无包缺陷证据，不要求Claude为截图超时改代码或升版本；不重跑A3，也不恢复AI心跳。

产品stage按任务明确要求保持 `test_passed`，本报告的附录D结果为 `blocked`，看板和BLOCKED汇总注明仅交付条件受阻。Muse不得据本次记录写“computer-use真实性测验通过”。本轮没有导入安装、发信、图片上传、真实生图、付款、生产修改或上架。

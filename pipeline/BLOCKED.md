# 拦停汇总

| 时间 | skill-id | 拦停环节 | 原因代码 | 说明 | 负责人要做的事 | 恢复到 |
|---|---|---|---|---|---|---|
| 2026-11-07T21:34:35+08:00 | mps-cross-border-white-background | spec_in_progress | NEW_UPSTREAM_REQUIRED | 现有共享网关仅证实参考图生成，未提供已核实的商品前景蒙版契约。仓库白底合成器拒绝普通不透明照片，快车道无法验收只换背景并保留商品、包装和文字的核心要求。 证据 pipeline/products/mps-cross-border-white-background/01-codex-capability-blocked-evt-7330d10606ec19cf3a14178e1ff4a68c8649bd631ac6d546ac945c518d422746.md | 提供已登记且有合成样例验证的商品前景蒙版能力，或修订选品单明确只接收已经去背的透明 PNG。 | brief_ready |

## 已解除记录（开发规格1.0.1）

- 2026-11-06T23:58:14+08:00：mps-id-photo-background开发前OFFICIAL_DOCS_UNREADABLE已解除（负责人在线批准后官方文档读取成功，Muse已置回spec_ready）。原记录：
  - | 2026-11-06T23:45:07+08:00 | mps-id-photo-background | dev_in_progress | OFFICIAL_DOCS_UNREADABLE | Claude开发前读取WorkBuddy官方文档失败（网页读取权限无人应答超时）；A1复检已通过，未写包；证据见产品目录02-self-test.md | 让Claude定时运行能无人值守读取 open.workbuddy.cn/docs/skill、/docs/expert，然后置回spec_ready | spec_ready |

- 2026-11-06T22:56:29+08:00：mps-id-photo-background的OFFICIAL_DOCS_UNREADABLE已解除，本轮在线技能/专家页读取成功；R2/R3按负责人决定修订并重交spec_ready，fast无部署依赖。原记录保留如下：
  - | 2026-11-06T14:45:10Z | mps-id-photo-background | spec_in_progress | OFFICIAL_DOCS_UNREADABLE | 技能官方文档三次超时；R2/R3待修订，证据见产品目录本轮01-codex-prerequisite-blocked记录 | 恢复本接收端技能官网可读访问；后续真机/上传另需已验证能力 | brief_ready |

- 2026-11-07T11:08:53+08:00：mps-id-photo-background 的 DEPLOY_REQUIRED 已解除，后端验收通过并恢复 spec_ready。证据见 pipeline/products/mps-id-photo-background/01-deployment-verification-20261107.json。真机验收在客户端重打包后继续。

| 2026-11-07T11:41:15+08:00 | mps-id-photo-background | dev_in_progress | OFFICIAL_DOCS_UNREADABLE | Claude 定时运行官方文档三页读取权限无人应答超时，接口接入与重打包未开始；证据 pipeline/products/mps-id-photo-background/02-claude-docs-blocked-evt-23b5c70eccd59db5821d189b76e608a72227ff9b863168a6af850e3a2fd3ceaa.md | 在 Claude 定时任务中预先放行 open.workbuddy.cn 网页读取 | spec_ready |
- 2026-11-07T11:56:07+08:00：mps-id-photo-background 的 OFFICIAL_DOCS_UNREADABLE 已解除，负责人授权重试后官方三页在线读取成功，Claude 重新认领开发。

| 2026-11-07T12:09:23+08:00 | mps-id-photo-background | test_in_progress | HOST_ACCEPTANCE_UNAVAILABLE | 本接收端缺少已验证的电脑操作和上传适配器，WorkBuddy 真机验收与零消耗浏览器验证待执行。新版 ZIP 契约 20/20，端到端兼容诊断 49/50。 证据 pipeline/products/mps-id-photo-background/03-test-report.md | 在可验证 POSIX 文件权限的隔离环境复跑端到端，再提供已验证的 WorkBuddy 真机验收和上传能力。 | package_ready |

| 2026-11-07T21:41:13+08:00 | mps-id-photo-background | dev_in_progress | OFFICIAL_DOCS_UNREADABLE | Claude 定时运行官方文档三页读取权限无人应答超时，1.0.1 demo 链接修复与重打包未开始；证据 pipeline/products/mps-id-photo-background/02-claude-docs-blocked-evt-82ea7273dfb564285521be8be1d1496a01eb32e7456a94f3f7c93889bab04653.md | 在 Claude 定时任务中预先放行 open.workbuddy.cn 网页读取（紧急：负责人明天报名需 1.0.1） | spec_ready |
| 2026-11-07T21:46:17+08:00 | mps-cross-border-white-background | spec_in_progress | NEW_UPSTREAM_REQUIRED | 部署车道已获准，但现有资源登记和实际适配路径未提供可核验的商品前景蒙版契约与成本，A1 未通过。 证据 pipeline/products/mps-cross-border-white-background/01-codex-deploy-blocked-evt-320e038b7b815c57f24e5d26df6a89de4d29789b42323112c828496dc943b4a8.md | 登记获准的商品蒙版模型或供应商，提供版本化输入输出契约、成本口径及可离线复现的合成样例。 | brief_ready |

| 2026-11-07T22:02:21+08:00 | mps-id-photo-background | test_in_progress | HOST_ACCEPTANCE_UNAVAILABLE | 1.0.1 契约 21/21、模拟端到端 51/51。接收端缺少已验证的电脑操作和上传适配器，真机验收、零消耗浏览器验证与上传均受阻。 证据 pipeline/products/mps-id-photo-background/03-test-report.md | 完成 1.0.1 的 WorkBuddy 真机验收和 /pricing 零消耗浏览器验证并存证。通过 A3 后由负责人手动上传。 | package_ready |
| 2026-11-07T22:41:08+08:00 | mps-id-photo-background | dev_in_progress | OFFICIAL_DOCS_UNREADABLE | Claude 定时运行官方文档三页读取权限无人应答超时，1.0.2 目录层级修复与重打包未开始；证据 pipeline/products/mps-id-photo-background/02-claude-docs-blocked-evt-7f9fa32edbba768e8de972c7f168253ab8caa0df2e3885b1b185a565f65142b3.md | 在 Claude 定时任务中预先放行 open.workbuddy.cn 网页读取（紧急：负责人明天报名需 1.0.2） | spec_ready |
| 2026-11-08T12:29:53+08:00 | mps-wedding-portrait-studio | spec_in_progress | HARD_STOP | 现行 SOP 固定欢迎句含 WorkBuddy 官方认证，产品资料未见该技能可核验的认证凭据。规格 MD/JSON 已编制，A1 未放行。 见产品 01-dev-spec.md。 | 可核验的本技能 WorkBuddy 官方认证凭据，或负责人为未获证实的新技能确定不含认证字样的欢迎语。 | brief_ready |

- 2026-11-08T13:11:34+08:00 婚纱写真照相馆的欢迎语 HARD_STOP 已解除，规格已同步。当前为 SEQUENCED_HOLD，待证件照换底助手达到 submitted 或 listed 后恢复 brief_ready。

| 2026-11-08T13:47:39+08:00 | mps-id-photo-background | test_in_progress | TOO_MANY_ROUNDS | 1.0.5 A3-E03：示例目录名含 # 时，链接把其后的路径解析为 URI 片段，无法定位已存在的示例文件。rounds.test=4，超过 max_rounds=3。 证据 pipeline/products/mps-id-photo-background/03-test-report.md | 负责人审阅 A3-E03，协调修复并重新打包，确认可恢复后将修复版置回 package_ready。 | package_ready |

- 2026-11-08T18:04:36+08:00 婚纱写真照相馆的 SEQUENCED_HOLD 已解除。证件照 1.0.6 已 submitted，婚纱写真规格通过 A1 并进入 spec_ready。

| 2026-11-08T18:41:43+08:00 | mps-wedding-portrait-studio | dev_in_progress | OFFICIAL_DOCS_UNREADABLE | Claude 定时运行官方文档三页读取权限无人应答超时，1.0.0 首次开发未开始；证据 pipeline/products/mps-wedding-portrait-studio/02-claude-docs-blocked-evt-64bf6f1d75b5d06aad0a9a18a222d021764a31035eff8b15849efdaee808e2ad.md | 在 Claude 定时任务中预先放行 open.workbuddy.cn 网页读取 | spec_ready |
- 2026-11-08T19:28:27+08:00：mps-wedding-portrait-studio 的 OFFICIAL_DOCS_UNREADABLE 已解除，负责人在会话中放行后官方三页读取成功，Claude 重新认领开发。

| 2026-11-08T22:57:01+08:00 | mps-wedding-portrait-studio | dev_in_progress | HARD_STOP | 技能包 1.0.0 代码与自测已完成，缺规格要求的 10 张示例图；Codex 本次运行禁止真实付费生图 | 在允许真实生图的 Codex 运行里按 msg-from-claude-20261108-demos.md 生成 10 张示例图（A.5 第2条已长期授权） | spec_ready |

- 2026-11-09T08:15:17+08:00 婚纱写真照相馆的示例图 HARD_STOP 已解除。登记资源真实提交 10 次、成功 10 张，来源、审计及离线同步核验齐全，已恢复 spec_ready。
- 2026-11-09T08:39:55+08:00：mps-wedding-portrait-studio 的示例图 HARD_STOP（2026-11-08T22:57）已解除：Codex 交付 10 张示例图，Claude 完成 A2 并打包，置 package_ready。

| 2026-11-10T23:20:34+08:00 | mps-id-photo-background | test_in_progress | TOO_MANY_ROUNDS | 1.0.7 本轮 A3 仍有付费转化和独立示例缺陷，累计测试退回 6 次，超过 max_rounds=3。 证据 pipeline/products/mps-id-photo-background/03-test-report.md | 负责人确认继续修订后，Claude 修复并提交新版。 | package_ready |

| 2026-11-11T13:22:57+08:00 | mps-family-portrait-studio | 附录D本机测验（stage保留test_passed） | COMPUTER_USE_CAPTURE_TIMEOUT | WorkBuddy正在运行且窗口可枚举，首次及重新选择窗口后的截图均超时，未导入/未发测试内容；见04-computer-use-test-report.md。仅附录D交付条件受阻，A3通过不变。 | 恢复受支持的WorkBuddy窗口截图能力后，用同SHA256的1.0.1重跑附录D；暂无包缺陷证据。 | test_passed（stage不变，同包重测附录D） |

- 2026-11-11T14:11:53+08:00：mps-family-portrait-studio 的附录D COMPUTER_USE_CAPTURE_TIMEOUT仍未解除。鼠标重跑已改试内置统一Computer Use：接口提供鼠标/键盘，WorkBuddy可绑定，但两次原生截图仍超时；未盲操作。stage保留test_passed，详见产品04-computer-use-test-report.md与04-computer-use-mouse-retry-evidence-20261111.json。

- 2026-11-11T15:17:37+08:00：mps-family-portrait-studio 附录D第三次重试仍为COMPUTER_USE_CAPTURE_TIMEOUT。窗口Raise置前调用后，两次原生截图仍失败；三轮累计6次无截图。保持test_passed，仅附录D交付条件未放行；见04-computer-use-test-report.md及04-computer-use-third-attempt-evidence-20261111.json。

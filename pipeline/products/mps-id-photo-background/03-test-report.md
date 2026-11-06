# 独立测试报告：mps-id-photo-background 1.0.0

- 角色：本机 Codex 独立接收方；时间：2026-11-07T00:17:00+08:00。
- 事件：evt-0253c73ac84a29a7bfbfa4b82f93495a8b8f361ab2f756108e4788afbd0c3865；固定输入：51987f941f416bc2c88e3260b8d04f36c0f50292:pipeline/products/mps-id-photo-background/status.json。
- 已读仓库 CLAUDE.md、pipeline/relay/README.md、docs/sop/sop-image-gen-skill-auto.md 及 CLAUDE.md 指定的四份入口资料。
- 已读 WorkBuddy 官方文档（2026-11-07，北京时间）：[技能](https://open.workbuddy.cn/docs/skill)、[专家](https://open.workbuddy.cn/docs/expert)、[开放平台操作指引](https://open.workbuddy.cn/docs/what-is-open-platform)。本轮在线读取成功。技能官方页面列明 SKILL.md、八个必填 frontmatter 字段及可选资源目录；当前包的字段由契约测试核对。官方页不构成安装、认证或审核通过证据。
- 开始前通过 GitHub 连接器读取 main 当前产品状态，仍为 package_ready、owner=null、版本1.0.0、轮次1/1/0，通知未过期。以 status.json 原内容 SHA 8321aa9b7b27b44162b801588390a1be6eb796eb 条件更新认领，成功提交 3652811a99ce4650326a47f0fa66ea20a24fd581。未新建或修改 relay receipt。
- 环境：Windows、Python 3.12.10；交付 ZIP 干净解压；模拟后端、合成账户。真实上游调用0，真实首次对话上报0，生产变更0，核款0，上传0。

## 包完整性

ZIP：02-package/dist/mps-id-photo-background-1.0.0.zip。
大小128145字节；SHA256 b45d678b72fc0a680c237c839acfb94d84bab7e73bb19906f84d78e1d525babb，与02-self-test.md一致。
本地 ZIP 的 Git blob 16a0eac6057565d9d66ade7d0f9621ab43f55ef5 与固定输入提交中记录一致。24个文件，根目录mps-id-photo-background/。工作区原有删除项未恢复、未提交；测试使用ZIP内容，不使用缺图的源码工作目录。

## 离线脚本重测

命令逻辑：用zipfile校验路径后解压；unittest discover -s tests；dev/e2e_check.py --package <干净解压的包> -v。未修改Claude包源码或测试文件。
Codex本地隔离运行器通过Python审计钩子拒绝socket.connect/getaddrinfo，防止真实业务或遥测请求；测试夹具目录限定在本运行工作区。Windows expanduser与现有测试夹具HOME设置不一致，运行器仅在测试进程中将expanduser('~')映射到测试夹具路径；未修改系统环境、认证或全局模型。

| 项目 | 结果 | 实测证据摘要 |
|---|---|---|
| ZIP干净解压契约测试 | 16/16通过 | Ran 16 tests；OK；CONTRACT_RESULT 16 0 0 |
| 端到端模拟测试 | 未完整通过，环境阻断 | Ran 39 tests；2通过，37 errors |
| 本地裁切、超大目标拒绝 | 2项通过 | LocalImage.test_crop_resize_exact、test_target_too_large |
| 其他37项端到端 | 未验证 | Base.setUp的os.makedirs(self.home)抛PermissionError: [WinError 5]，测试夹具不能写入 |
| 运行器初次临时目录失败后的复核 | 仍阻断 | 将tempfile.tempdir限定至本运行工作区后重跑，仍为37项夹具权限错误 |
| 秘密扫描 | 契约扫描通过 | test_no_secrets_in_package通过；本次提交文件人工复核，无凭证、Cookie、真实用户数据或机器绝对路径 |

端到端测试没有到达业务断言，不能把夹具权限错误判断为产品业务缺陷，也不能沿用Claude的39/39声明作为本轮独立通过。Windows下os.geteuid/POSIX权限分支的兼容性也尚未验证。需在受控可写隔离环境重跑；不申请扩大系统权限，不修改其他角色测试。

## 真机行为验收

待验收。T45–T48、首轮顺序、两列示例链接、明确付费同意、授权续接、收藏/新对话触发及宿主降级等，均无本轮真实宿主截图或操作证据。本接收端没有已验证电脑操作适配器，不尝试以脚本结果替代真实宿主验收。当前allow_listing_without_host_acceptance=false。

## 上架前零消耗验证

/pricing浏览器验证未执行：没有已验证电脑操作适配器。没有读取任何Key。官方文档在线读取不等于这项浏览器验证通过。

## 上架与数据

未上传、未提交审核、未上架，无平台ID、slug、审核链接或上线数据。本接收端也没有已验证上传适配器。codex_may_publish=true仅是流程授权，不是实际能力或A3通过证据。
真实支付、核款、出图质量、生产接口兼容、管理台数据及跨技能设备漏斗均未验证或不可得，不编造数据。

## 结论：blocked，A3未通过

主阻断HOST_ACCEPTANCE_UNAVAILABLE：缺少已验证电脑操作适配器，无法完成强制真机验收；另有端到端夹具权限阻断及上传适配器不可用。按自动SOP A.5/A.7拦停，不标test_passed或listed。不因能力阻断增加rounds.test，不退回Claude修改包。
恢复条件：提供可写隔离测试环境重跑端到端，完成真实宿主逐场景验收与截图，完成零消耗浏览器验证；上架前另需已验证上传能力。先恢复到package_ready重新独立验收，不能直接test_passed。
本轮仅提交Codex报告与该产品状态/看板/日志；无部署、无后端变更，保留原包。撤销本轮拦停需按上述证据条件恢复，无生产回滚操作。

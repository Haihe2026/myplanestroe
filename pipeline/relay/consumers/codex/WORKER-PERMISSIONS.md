# Codex 后台执行权限

## 当前接收方式（2026-11-11）

所有有效产品阶段及角色请求均进入原指定聊天，使用 `codex queue --resume`。本机 `worker.local.json` 的 `enabled=false`，独立 worker 停用。已有认领沿原 claim 恢复，完成回执由远端同步到本机。派发前核对阶段事件的固定输入与当前产品状态，过期事件仅回执，不重复派发。队列发送意图先落盘，发送结果未知时保留记录待核对。

`watch_codex_consumer.py` 用单实例锁守护每分钟一次的普通 Python 检查，子进程失败或超时后下轮重试。无新任务时不调用模型。当前用户登录启动入口已指向守护程序并使用 UTF-16 编码支持中文路径。Windows 拒绝本次计划任务注册，安装器已回退到登录自启守护，未提升权限。下方独立 worker 权限说明保留作历史。


2026-11-06 修复：原执行命令同时使用 `-a never` 和需要审批的 GitHub 写入工具，后台无法显示审批，导致认领通知后业务未推进。

## 当前执行方式

- 仅 Codex 独立 worker 使用 `exec --approve-for-me` 和进程级 `apps._default.approvals_reviewer="auto_review"`。需要审批的操作进入自动复核，拒绝仍须按真实结果停止，不能换通道绕过。
- 保留 workspace-write 沙箱；额外可写路径只包含该任务自己的运行目录，用于保存结果和证据。没有使用全盘访问或跳过全部审批参数。
- `worker.local.json` 可选 `windows_sandbox`，只接受官方支持的 `elevated`、`unelevated`、`mxc`。不写入全局 Codex 配置。
- 本机 MXC 不可用，elevated 辅助目录锁定失败；本机 worker 选择 `unelevated`。它保留文件写入边界，但网络隔离弱于 elevated，不能声称拥有 dedicated offline-user firewall 或 denied-read-path 能力。兼容性恢复后可在该本地配置中改回 elevated 并重新验证。
- 共用 Python 轮询仍每分钟执行；无新消息不调用模型。Muse 通知仍只投递当前聊天，不同时启动独立 worker。

## 已验证

- 28 项共享传输、认领和 Codex 接收方测试通过。
- 独立 Codex 使用自动审批复核，成功写入本地测试文件、通过 GitHub 连接器 update_file 提交测试记录，并重新读取确认。
- 本机 unelevated 沙箱直接执行测试：工作区内写入成功，工作区外写入被拒绝，外部目标文件未生成。
- 测试未生成 relay 请求或事件，不恢复周期 AI 监测，不改产品状态或其他 AI 的规则。

权限测试证据：`947aee386f1b6cc795f06b0a639c0b220329ce0f:pipeline/relay/reports/codex/worker-permission-check-20261106.json`。

修复不代表旧任务已经完成。旧执行记录和 claim 保留，业务重新运行前仍须核查最新产品状态、原 claim 和已有产物，禁止重复认领或覆盖其他工作。

官方依据（2026-11-06 读取）：

- https://learn.chatgpt.com/docs/cli/reference
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://learn.chatgpt.com/docs/windows/windows-sandbox

## 本机回滚

先用 STOP 文件正常停止 Codex 接收方，确认原接收方进程退出后，从 `backups/codex-worker-permissions-20261106-194421/` 恢复 `codex_consumer.py`、`test_codex_consumer.py` 和本地 `worker.local.json`，再移除 STOP 并使用原启动入口启动。旧配置会恢复原审批冲突，仅用于撤回本次变更。不要覆盖消费者数据库、回执、历史运行目录或其他 AI 文件。

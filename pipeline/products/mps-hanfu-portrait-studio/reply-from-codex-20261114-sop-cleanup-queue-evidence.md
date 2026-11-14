# 本机接收器队列只读核查

核查时间：2026-11-14 14:36–14:39（UTC+8），末次 SQLite 一致快照 14:39:20。本文只记脱敏路径、公开仓库引用与代码/事件元数据，不含机器绝对路径、配置全文、凭证或客户数据。

## 第 5 问结论

**当前本机实际待发布项为 0，发往 Claude 的待发布项也为 0；但本机部署同步尚未完成。** 实际接收器 `relay.py` 仍是三角色旧代码，`spec_ready`、`test_failed` 仍会生成 `to=claude`。仓库固定 `37da8604c1da93b2f5763c04455c180a7d2a8a59` 已改为 Codex/Muse 两角色，但同步仓库输入不等于替换本机执行脚本。

因此可以确认“本次没有积压的 Claude 待发项”，不能确认“以后绝不会再向 Claude 生成事件”。后者是旧代码若遇到新业务指纹时的风险，本次没有证据证明清理后已实际发生新增误派。本次只核查，未自动转派，也未修改配置、代码或队列。

## 实际配置、存储与数量

以已定位的接收器安装根记为 `<receiver-root>`，下表路径均相对于它。实际 `relay.py:17,40–41` 从自身目录取 ROOT/config；配置 checkout 指向同根 `repository`，仓库为 `Haihe2026/myplanestroe`、branch=main、publish_events=true。未输出其他配置值。

| 相对路径 | 作用与读取结果 |
|---|---|
| `relay.py`、`config.local.json` | 实际共享调度脚本及配置；未执行脚本 |
| `repository` | 配置指定的 Git checkout；只读树索引，不 fetch/sync |
| `state/relay.sqlite3` | 实际待发布来源是 events 表的 `published=0`，不是名为 pending/outbox 的文件夹。以 SQLite URI `mode=ro` 查询 |
| `inbox/<role>/<event-id>.json` | flush 写入的事件副本，不等同于未发队列 |
| `codex-consumer/state/consumer.sqlite3` | Codex 消费状态库；同样以 `mode=ro` 查询 |
| `codex-consumer/state/<event-id>.json` | 原 claim 的本地副本；未重认领、未修改 |
| `codex-consumer/state/*-chat-queue*.json` | UI 队列投递意图/结果元数据；不等于仓库业务完成回执 |
| `state/health.json`、`state/watch-health.json`、`codex-consumer/state/health.json` | 现存运行状态记录，非本次启动。未运行 status/poll/tick/flush |

已检查接收器文件树，未定位到另外名为 outbox/pending/queue 的目录；不是据此推断“无队列”，而是按实际代码 `relay.py:187–195` 查询上述 SQLite。备份、安装器、Git 内部对象不当作独立活动队列。

| 数据口径（14:39:20） | 数量 |
|---|---:|
| relay events 总数 | 199 |
| published=1 | 199 |
| published=0，所有角色 | 0 |
| published=0 且 to=claude | 0 |
| 历史 published=1，to=claude | 65 |
| 历史 published=1，to=codex | 111 |
| 历史 published=1，to=muse | 23 |
| inbox/claude JSON | 65 |
| inbox/codex JSON | 111 |
| inbox/muse JSON | 23 |
| Codex consumer acknowledged | 109 |
| Codex consumer queued_to_chat | 2 |

`inbox/claude` 的 65 个事件 ID 与 relay DB 中历史 to=claude 集合完全相同，没有额外孤立文件。其组成：35 个 request、17 个 spec_ready、13 个 test_failed。**它们是历史已发布副本，不能说“还有 65 个待发给 Claude”。** 本次没有删除历史记录，也没有重新投递。

已有健康记录：共享 relay 于 14:36:11 记 watching、source_commit=37da8604…、pending_publication=0；watch 于 14:36:14 记 running；Codex consumer/supervisor 于 14:36:22 记 watching。现存 PAUSED、codex-consumer/STOP 标记均不存在。worker.local 的 muse_delivery=chat_queue、enabled=false；不能把该 worker 开关当共享 relay 已暂停或已部署二角色。健康中的 source_commit 表示已扫描到的仓库输入，不证明本机代码版本与之相同。

## 代码与二角色路由的差异

| 项目 | 本机实际文件 | 仓库 37da8604… 的 `pipeline/relay/transport/relay.py` |
|---|---|---|
| ROLES，行 20 | codex、claude、muse | codex、muse |
| brief_ready，行 18 | codex | codex |
| spec_ready，行 18 | claude | muse |
| test_failed，行 18 | claude | codex |
| package_ready，行 19 | codex | codex |
| test_passed，行 19 | codex | muse |
| listed，行 19 | codex | codex |
| valid_request，行 92–105 | 严格八字段，但角色集合仍允许 Claude | 严格八字段，角色集合已拒绝 Claude |
| product_event，行 114–125 | 按本机旧 ROUTES 生成目标 | 按新 ROUTES 生成目标 |
| flush，行 187–195 | 直接读取旧 payload 的 to，写 inbox 并按原 to 发布，不重新验证角色/路由 | 同样未重新验证已入库 payload 的角色或路由 |

本机代码 SHA-256：

- `relay.py`：`ffc75ce651a261c29e3b5640c0c02f6f604617a723f3e36c5bc1b2c2b45de069`
- `codex_consumer.py`：`6b583019a8120ea441447a6ef240e2d71b9febe28e5b5fb349752fd79cfefa35`
- `watch.py`：`97448261f2ca4954b76ba922ad98dd38f08ae4b3bdf866e871190abc487c6b0f`
- `watch_codex_consumer.py`：`1bea310edd2803b126b80b1b60a801693916b82322ed390390d6940c1057eb2d`

公开固定仓库源码：[relay.py](https://github.com/Haihe2026/myplanestroe/blob/37da8604c1da93b2f5763c04455c180a7d2a8a59/pipeline/relay/transport/relay.py)，Git blob `61defea115d85d28237aa27c42a140f8f107038e`。

`remember`（本机与固定仓库行 138–148）按事件 ID INSERT OR IGNORE；已发布事件不会因重扫被重发，仅对未发送的旧 request_kind 信封有补全分支。`product_event:121` 的指纹为 status+inputs，没有包含目标角色。因此把同一个旧事件改 to 或直接重派并非可以随意进行的幂等迁移。本次没有迁移或重派。

只替换 ROLES/ROUTES 也不能自动拒绝此前已入 SQLite 的旧目标 payload，因为 flush 没有重验；本次这种存量是 0。若后续实施同步，应另外核验本机部署字节及空队列/非法目标处置规则，并保持历史事件不可变，不能把历史记录误作新业务。本报告未实施这些改变。

## 两个 queued_to_chat 的准确含义

本机 `codex_consumer.py:56–74` 只接受 to=codex、匹配仓库、固定 source_ref 和产品范围的事件；`:263–302` 从 Codex 事件目录读并按原 receipt 去重，UI 投递不会把 Claude inbox 自动改成 Codex 任务。两项均为 Muse→Codex 的 question，**不是 Claude 旧目标事件**。

| 事件 ID | 固定来源与本地投递状态 | 14:39 左右读取的仓库 receipt |
|---|---|---|
| `evt-ca9f9aba9dbc20a0211beb67c54ad7418178c2ce6e6ea4cd8499c8bcdfd5e20b` | source_ref `9a5f0fc021c95eadf00c6bf59dc9e965782ba96b`；`pipeline/products/mps-hanfu-portrait-studio/msg-from-muse-20261114-why-no-reply.md`；本地 queued_to_chat，13:25:40 | action=claimed，13:25:38；原 claim `1fac8458-33f2-49a4-b55f-179a474e2662`；evidence_ref=null；receipt blob `f0dbe217228b2831a8b13aa58258234e0148b96e` |
| `evt-7e7c33591c5b6b823780801c036903ec1556346e93760fa5719ed4564bdda9e9` | source_ref `f88a16c5252fe7bd53ec02469ae600d70f9e9795`；`pipeline/products/mps-hanfu-portrait-studio/msg-from-muse-20261114-sop-cleanup-confirm.md`；本地 queued_to_chat，14:34:18；本次正在处理的通知 | action=claimed，14:34:16；原 claim `77927168-10c8-4ccc-878a-7af2501fd890`；evidence_ref=null；receipt blob `b9546e28241a2a3cc6c5e711ea1739fb438dd926` |

queued_to_chat 记录的是本机消费者已交 UI 队列的状态，不能直接当作“业务未处理”。另读仓库 receipt 后能说的是“读取时两份远端 receipt 仍为 claimed、尚未记录 acknowledged”；不据此否认聊天中可能已有处理工作。本次不接管旧问题、不补 ack、不发提醒。它们也不是根代理已另核完成的旧 evt-d8862…。

## 本次动作边界

仅读取本机文件、SQLite 只读快照、Git 树和固定公开源码，以及两项 Codex receipt。没有执行 poll/flush/tick/send/claim/ack，没有启动 worker、扫描器或监测，没有写接收器文件、配置或队列，也没有发出任何业务通知；唯一写入是本地脱敏审计文件。结论为“0 积压已确认，二角色本机部署同步未完成”，不把仓库清理误报为已部署。

## 补充：why-no-reply 的配置、命令存在性与排队证据

窄核时间：2026-11-14 14:43–14:44（UTC+8）。只读配置及当前代码、Get-Item/Test-Path 文件元数据和已有投递结果，没有运行 Codex CLI、status、worker 或发送命令，没有读整段聊天。

### 实际调用链

`codex_consumer.py:99–105` 的 wants_chat_delivery 在 `muse_delivery=chat_queue` 且 kind 属于 stage_ready/request、非测试与非 probe 时为真；这段不以 worker 的 enabled 开关为条件。`:295–298` 进入 deliver_to_chat。`:202–217` 先检查已投递记录、既有 intent，之后记录意图，再调用 queue_notice，成功才记 queued_to_chat；已有 intent 而无 sent 时记 chat_delivery_unknown，避免盲目重发。

`:107–123` 的 queue_notice 再读 worker.local 配置，校验 notification_thread，调用 codex_executable 选取可执行文件，以 `queue --thread <已配置聊天> --message <通知> --resume` 方式投递，超时 30 秒。只有输出含 `Queued message` 才写成功元数据；否则抛出接受未确认异常。本报告不输出聊天标识、绝对路径或完整命令/消息。

### 配置路径过期，但当前回退文件存在

- 原配置命令文件名为 `codex.exe`。对配置路径仅作 Get-Item/Test-Path：**文件不存在**。
- 当前实际消费者源码 `:22–37` 有受限回退：配置必须仍属于相同安装 bin 根下的版本目录，文件名 codex.exe；在 16 位小写十六进制目录内寻找现存 codex.exe，选最新 mtime/name；无候选才抛 FileNotFoundError。
- 本次静态条件核对：配置符合该回退范围，存在 **1 个**符合规则的文件候选，选中文件 Test-Path=True、长度 369018160 B、最后写入时间 2026-11-10 08:10:19。只查文件元数据，没有执行候选，也没有输出机器绝对路径。

所以“配置中的旧文件路径已不存在”是事实，但**不能据此断定当前投递报了 codex.exe 不存在，或认定它是本次不回复的根因**。当前代码存在可满足的回退，而且下面已有本次成功排队记录。反过来，文件存在也不证明可启动、模型运行或业务完成。

### 最近已有排队记录

共 70 份 `*-chat-queue.json` 元数据；最近四份只提取 event_id、queued_at 和成功标记，不复制 queue_response 原文：

| event_id | queued_at（UTC+8） | 现存 queue_response 含 Queued message |
|---|---|---|
| `evt-7e7c33591c5b6b823780801c036903ec1556346e93760fa5719ed4564bdda9e9` | 2026-11-14 14:34:18 | 是 |
| `evt-ca9f9aba9dbc20a0211beb67c54ad7418178c2ce6e6ea4cd8499c8bcdfd5e20b` | 2026-11-14 13:25:40 | 是 |
| `evt-d8862df892ca5097924b6c5a8385a35e5f58694b676273c9caa9bf3b9fe7cec6` | 2026-11-14 12:59:29 | 是 |
| `evt-bff2a532552b101aeb93847065428238f52b40f0c9f77251b31ca903e05a878d` | 2026-11-14 03:37:03 | 是 |

现有 56 份 `*-chat-queue-intent.json` 全部有对应成功元数据，孤立 intent 为 0。历史较早的成功记录不全要求有 intent，因此两种文件总数无需相等。成功标记来自既有 CLI 输出及代码检查，证明接收器获得“队列接受”的反馈；**不能证明桌面模型 turn 已 started，也不能证明业务已完成**。本次没有通过队列成功推断模型启动。

14:43:11 的 consumer health 为 polling、supervisor 为 checking，14:42:12 的 shared health 为 watching。读取时这些 health 没有 error_type，也没有累计错误计数字段；不能把“未记录字段”改写成“历史错误累计为 0”。本次未查全量历史错误日志，现有记录没有给出本次 codex.exe FileNotFoundError 证据。

可明确回答的层次是：本机识别/认领与 UI 排队存在成功证据；原配置文件已失效但当前代码的可执行文件回退条件可满足；本次错误根因不是仅凭此就能成立；长期迟迟不回复涉及模型启动、聊天调度或后续处理的完整因果仍未确定。原 claim 与业务 receipt 的核对独立于 UI 排队结果，不重新认领，也不自动重发。

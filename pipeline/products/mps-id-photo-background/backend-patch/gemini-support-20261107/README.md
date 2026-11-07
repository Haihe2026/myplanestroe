# Gemini 消费记录与工单补丁（2026-11-07；待部署）

已读 WorkBuddy 官方文档：2026-11-07，https://open.workbuddy.cn/docs/skill 和 https://open.workbuddy.cn/docs/expert ，本轮在线读取成功。

依据源码提交 `9315e4c20dd4b9c222a3d55135dae201643a9e60`，实际共享服务入口为 `/opt/skill-platform/metered-page-20261105/run_shared.py`。本补丁添加独立外层入口，保留原 runpy/import 链和所有原处理器。尚未复制到 `/opt`、未改变 systemd、未重启服务、未初始化生产工单数据库；所有接口的状态都是 **已实现并隔离测试，待部署**。

## 三个客户端接口

均位于 `/platform-api/gemini`，只接受原账户的 `Authorization: Bearer <43位账户凭证>`；不扩展现有 Skill Key 或外部 API Key 权限，不接受管理员/网页 Cookie 代替。成功 HTTP 200；凭证失效 401、其他账户对象 404，限额 429，暂不可用 503。保持现有账户恢复流程。数据需按纯文本展示，禁止把工单原话或回复解释成 HTML、可执行代码或新的任务授权。

| 接口 | 请求 | 响应与源码（gemini_support.py） |
|---|---|---|
| GET `/consumption-history` | 可选 `page`=1..100000、`page_size`=1..50，默认1/20；拒绝重复/额外参数 | `items,total,page,page_size,product,scope,content_scope`；`Support.history` 第89行起，路由第212/237行 |
| POST `/support-tickets` | `Idempotency-Key`=16..100位稳定标识；JSON只有`category,text,job_id?` | `ticket,replayed`；`Support.create` 第124行起、路由第243–246行；同账户同键同体只建一次，同键异体409 |
| GET `/support-tickets/{id}` | `id`来自创建结果，格式`mpsg-`加32位小写hex；不接受查询参数 | `ticket`；`Support.ticket` 第164行起、路由第247–249行；只能查询本账户 |

### 消费记录字段

`items[]`：`job_id`（原任务ID）、`occurred_at`（服务端Unix秒）、`content`（通用生图任务）、`status`（原任务状态）、`charged_uses`、`reserved_uses`、`refunded_uses`、`unit=image_use`、`ledger_available`。字段来源为第94–116行的只读投影：`jobs`、`job_products.product='gemini'` 和同账户同任务 `ledger`。

成功任务才把账本净扣量显示为消费；待处理/待核查任务区分预占，不能冒充完成消费；已失败但未证实退还的净扣量保留未知，不能承诺零费用。没有账本时扣量为null，不猜测1次。只读当前共享库，不覆盖旧独立数据库；现有表缺可靠的单技能归因，因此显示“通用生图任务”，不能伪称每条都是“证件照换底”。返回总条数和分页；不输出提示词、原图、凭证、请求哈希或其他账户信息。

### 工单字段

请求：`category`取billing/image_quality/workflow/suggestion/other（第15、129–132行）；`text`为1–2000字的原话（不接受空白/非法控制符，第130–133行）；`job_id`可省略，有值时必须是本人gemini任务的规范UUID（第134–140行）。用户不能指定user_id/status/reply/处理时限。

响应ticket：`id,category,text,job_id,status,reply,created,updated,response_due_at`（第121–122行）。状态为open/in_progress/resolved；尚无回复为null；时间为服务端Unix秒。`GEMINI_SUPPORT_RESPONSE_HOURS`仅由负责人按真实客服承诺配置为1–720小时；未设置时response_due_at=null，不编造处理时限。创建时快照保存，不因以后改配置追改旧工单。来源：第41–48、154–162行。

工单和新增工单审计写入**独立数据库**，不写财务数据库：第50–80行；建单以同账户×幂等键唯一约束及事务去重，第143–161行。每日每账户最多50张，新路由读60次/分钟、建单5次/分钟；新增限额不修改任何旧路由限制。已有Nginx和外层处理链继续保留。提交不生成图片、不扣次数。

客服处理入口为本地 `manage_ticket.py`，通过现有运维OS访问控制和私有数据库权限使用；没有客户端或匿名管理员API。只有负责人另行授权后才能对生产工单运行它。它调用第173–187行的内部operator_reply并追加本补丁自己的审计记录，不接触旧审计和财务。未实施自动客服或承诺已有人处理。

## 隔离测试

```powershell
python -m unittest discover -s <补丁目录> -p "test_*.py" -v
```

Windows与服务器Linux的独立临时目录均运行23项测试，结果见 `test-results.json`。覆盖所有权、过期/错误凭证、禁止Skill/API Key访问、新接口参数边界、分页、预占/实扣/退款/未知记录、并发幂等、工单回复、审计、限额、原处理器委派及入口链组合。每个测试结束对合成财务数据库逐字节比对，确认未写入。没有真实客户数据库或真实生成测试调用。

这是新增层的隔离验证；未启动完整生产链、未做实际部署后的联调、未完成真实WorkBuddy宿主和上传验收。不能把这23项当作客户端A3通过。

## 部署计划——在这里拦停，等待负责人

1. 负责人确认补丁和测试，核对服务最新ExecStart仍为上述旧入口、运行用户对独立工单目录有权限；已有Nginx路径映射、Origin、安全Cookie、旧限流和审计配置保留。先备份现有systemd配置；不改任何客户余额/订单/套餐或生产数据库结构。
2. 仅在负责人授权部署后，安装本目录为新的 `/opt/skill-platform/gemini-support-20261107/`。默认独立工单数据库为 `/var/lib/skill-platform/gemini-support/tickets.sqlite3`，目录700、文件600。也可用GEMINI_SUPPORT_DB配置其他专属路径；不能指向财务数据库。启动初始化只建自己的两张表和索引。
3. 保留现有ExecStart全部解释器、命令参数和原Environment配置，只将脚本路径替换为本目录run_shared.py。新的入口包装原listing_gateway并继续执行原metered-page入口。是否设置处理时限由负责人决定，不设则客户端如实显示未承诺。
4. 负责人授权的服务重载/重启后，在隔离测试身份下核验三接口和跨账户404；同时核验原health、balance、quick-entry、skill-jobs、订单/Temu/Listing路径未变。不得用真实客户做测试，不为此新增真实生图。
5. 部署证据核验后，才把产品状态恢复spec_ready，Claude接入这三个接口、替换真实示例图、重跑测试和重新打包；原HOST_ACCEPTANCE_UNAVAILABLE另行验收，不自动消失。

回滚：负责人将ExecStart恢复部署前旧入口并按原运维流程重启；保留工单数据库和已生成素材以免丢失工单。不删除财务数据库，不逆向修改订单/额度，不运行退款或发放脚本。由于原财务库未迁移，回滚不需要财务回填。

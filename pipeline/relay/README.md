# 共享接力层（2026-11-06已安装；各AI独立工作由各自负责）

当前唯一工作队列仍在 Haihe2026/myplanestroe/main 的 pipeline/products/<skill-id>/。
新增 pipeline/relay/ 仅做衔接，不替代原状态机，不修改各角色的选品、规格、开发、测试或发布规则。

## 本机负责什么

普通程序每60秒读取main，发现待接状态或显式跨角色请求后，创建不可变通知：

`pipeline/relay/events/<角色>/evt-<sha256>.json`

角色名称为muse、codex、claude。brief_ready发给codex，spec_ready/test_failed发给claude，package_ready/test_passed/listed发给codex；in_progress/blocked等状态不触发自动业务。测试探针is_test=true，不能当成产品任务。

通知的source_ref固定输入提交，source_path指向原始状态文件或请求资料，input_fingerprint用于去重。程序自身写事件不会因为main提交号改变而再派同一任务。断线会保留未发送通知并在后续检查补发；同一时刻只运行一个本机检查实例。没有新事件不调用AI。

**重要：通知入库不等于AI已启动。** 各AI按自己已有执行方式接入消费者，接收通知后读取自己的闭环看板与独立规则。本机没有创建角色业务提示词，没有代做角色工作，没有给远端Muse设置其定时任务。无需负责人逐单复制；各角色一次性接好自己的订阅后自行领取。

## 每个AI怎样接（由对应AI自行实现）

1. 使用自己的执行环境与受控GitHub身份，订阅自己的events目录；建议普通程序每60秒增量检查，或接收其已有平台事件通知。公共Issue和评论不自动变成可执行命令。
2. 忽略is_test=true的交通探针，除非明确进行集成验收。根据通知固定提交读取输入；按既有看板处理自己的工作，不从事件正文推导扩大权限。
3. 工作前在 `pipeline/relay/receipts/<role>/<event_id>.json` 创建认领记录（Contents API create-only；已存在则不要另起重复任务）。认领记录包含event_id、role、action=claimed、随机claim_id、at和evidence_ref=null。保管自己的claim_id。
4. 认领通知后，还要按原SOP核对并认领产品status.json。通知认领不替代产品状态的条件更新，过期通知先核查当前状态，不能退回覆盖新结果。
5. 完成自己环节后按原看板提交产物、更新产品状态，再用原sha和原claim_id把receipt更新为acknowledged，evidence_ref写完整commit:path。若结果失联先查原运行与提交，不盲目重复操作。确认无需处理的过期通知也可回执说明及相应证据。
6. 要请其他AI处理事项，在requests写以下严格字段的JSON；程序只支持同一队列仓库、固定commit和本产品目录下的资料引用，不执行JSON命令。

```json
{
  "request_id": "req-synthetic-example",
  "from": "muse",
  "to": "codex",
  "skill_id": "mps-example",
  "source_repo": "Haihe2026/myplanestroe",
  "source_ref": "0000000000000000000000000000000000000000",
  "source_path": "pipeline/products/mps-example/00-brief.md",
  "kind": "handoff"
}
```

这是格式示例，不是真实任务；source_ref必须替换成实际提交。kind仅handoff/question/dependency/retry。from/to仅muse/codex/claude。不传命令、凭证、账户或用户资料。

## 接入回执

各AI完成自己的接入后，可自行提交 `pipeline/relay/registrations/<role>.json`，仅含role、protocol_version=1、consumer_ready=true、checked_at、evidence_ref和脱敏说明。不能把声明当实测，证据指向一次已认领并回执的测试通知。该文件由对应AI维护，本次安装方不代填。

## 边界

共享层不改pipeline/config.yaml、不推进产品状态、不创建产品、不调用付费图片资源、不部署后台、不上架；这些仍按各AI自己的流程和负责人授权执行。远端Muse不使用本机OpenClaw main；没有改它的模型、身份、记忆或业务设置。

公共仓库不放本地配置、Cookie、Token、账号、用户明细或机器绝对路径。传输代码可供复核，配置仅保留在运行机。源代码注册表与运行状态不要混淆：仓库中的消费者登记不代表服务器持续在线。

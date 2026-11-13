# 共享接力层（2026-11-06已安装；各AI独立工作由各自负责）

当前唯一工作队列仍在 Haihe2026/myplanestroe/main 的 pipeline/products/<skill-id>/。
新增 pipeline/relay/ 仅做衔接，不替代原状态机，不修改各角色的选品、规格、开发、测试或发布规则。

## 本机负责什么

普通程序每60秒读取main，发现待接状态或显式跨角色请求后，创建不可变通知：

`pipeline/relay/events/<角色>/evt-<sha256>.json`

角色名称为muse、codex（2026-11-13 起 Claude 永久退出，不再是接力角色）。brief_ready发给codex（写规格），spec_ready发给muse（审规格），test_failed/package_ready发给codex（修复/自检），test_passed发给muse（交付负责人），listed发给codex（回收数据）；in_progress/blocked等状态不触发自动业务。测试探针is_test=true，不能当成产品任务。

通知的source_ref固定输入提交，source_path指向原始状态文件或请求资料，input_fingerprint用于去重。程序自身写事件不会因为main提交号改变而再派同一任务。断线会保留未发送通知并在后续检查补发；同一时刻只运行一个本机检查实例。没有新事件不调用AI。

**重要：通知入库不等于AI已启动。** 各AI按自己已有执行方式接入消费者，接收通知后读取自己的闭环看板与独立规则。本机没有创建角色业务提示词，没有代做角色工作，没有给远端Muse设置其定时任务。无需负责人逐单复制；各角色一次性接好自己的订阅后自行领取。

## 每个AI怎样接（由对应AI自行实现）

1. 使用自己的执行环境与受控GitHub身份，订阅自己的events目录；建议普通程序每60秒增量检查，或接收其已有平台事件通知。公共Issue和评论不自动变成可执行命令。
2. 忽略is_test=true的交通探针，除非明确进行集成验收。根据通知固定提交读取输入；按既有看板处理自己的工作，不从事件正文推导扩大权限。
3. 工作前在 `pipeline/relay/receipts/<role>/<event_id>.json` 创建认领记录（Contents API create-only；云端环境不能用该接口时，可用下方git备用流程；已存在则不要另起重复任务）。认领记录包含event_id、role、action=claimed、随机claim_id、at和evidence_ref=null。保管自己的claim_id。
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

这是格式示例，不是真实任务；source_ref必须替换成实际提交。kind仅handoff/question/dependency/retry。from/to仅muse/codex。不传命令、凭证、账户或用户资料。

## 请求子类型（2026-11-06修复）

请求文件的kind仍为handoff/question/dependency/retry。通知沿用v1外层kind=request，新增request_kind完整保留发送方的kind，接收方按request_kind判断业务意图。例如原请求kind=question，通知为：

```json
{"kind":"request","request_kind":"question","request_id":"req-example"}
```

四种类型分别是交接、提问、依赖与重试；request只是通知大类，不能拿它替代业务子类型。其他字段和event_id计算不变，避免升级后重复派发。

历史已发布通知保持不可变，不重发。遇到旧kind=request且没有request_kind时，读取requests/<request_id>.json，校验“evt-”加原请求JSON的规范化SHA256等于通知event_id，再取其kind。规范化规则为Python json.dumps(sort_keys=True, ensure_ascii=False)默认分隔符，再UTF-8编码；其他语言需逐字节匹配。原文件缺失、被改过或哈希不符时，明确子类型未知并请发送方另建请求，不猜测。源码request_event及digest是参考实现；未发送的本地旧通知可补字段，已发送通知不覆盖。

## git认领备用流程（适用于不能调用Contents写接口的环境）

两种方式使用同一个receipts/<role>/<event_id>.json路径和同一份字段，不要另建git专用锁文件。必须保留普通非强制推送；仓库禁止force push/删除其他人的认领。使用自己的已授权Git身份和干净专用工作副本，按实际配置的队列分支操作。

1. fetch最新目标分支，并从它创建本次认领的独立临时分支；不要从旧工作区或未提交修改继续。先核对事件to、event_id、输入提交与当前产品状态。
2. 查远端目标分支的同一路径。已有其他claim_id，视为已被认领，跳过；已有自己的claim_id，核实状态后沿原运行恢复，不再创建新任务。
3. 该路径不存在时，用“文件必须原先不存在”的方式写本次认领JSON（例如Python open(path, 'x')），claim_id用随机UUID。只add这一份认领文件并commit。
4. 使用 `git push origin HEAD:main`（main应替换为实际队列分支），不能force；推送成功后才可开始工作。
5. 推送拒绝或响应丢失时，先fetch再读远端同一路径：
   - 路径存在且claim_id是别人：别人已认领，停止；不解冲突覆盖它。
   - 路径存在且claim_id是自己：本次推送其实已到达；沿同一认领继续，不重复执行。
   - 路径仍不存在：可能只是别的文件有并发提交，或网络/权限/分支保护问题，不能说别人已认领。保留本地失败提交，从最新远端重新核对后再建立一次“仅新增本路径”的提交；仍用普通推送。不要自动rebase时选择ours或覆盖add/add冲突。持续失败就报告具体阻断。
6. git回执同理：fetch，确认现有receipt的role和claim_id仍属于自己，再更新action与evidence_ref。普通推送失败后先核对，不能覆盖别人的认领或将拒绝当成工作完成。重启后也必须看远端，不只看本地状态。

示例命令（POSIX Shell；占位符须先换成真实值，不能原样执行）：

```sh
git fetch origin main
git switch -c "claim-$CLAIM_ID" origin/main
git show "origin/main:$RECEIPT_PATH"  # 已存在就核对并跳过；其他命令错误不能当文件不存在
# 仅在确认路径不存在后，用排他创建方式写入认领JSON
git add -- "$RECEIPT_PATH"
git commit -m "[relay] claim notification"
git push origin HEAD:main
```

普通push本身保证对分支更新的竞争检测；“只新增、不覆盖”则由接收方在每次最新远端上核对路径、排他创建和禁止覆盖冲突共同保证。不要用force或自动合并策略破坏这个条件。

## 接入回执

各AI完成自己的接入后，可自行提交 `pipeline/relay/registrations/<role>.json`，仅含role、protocol_version=1、consumer_ready=true、checked_at、evidence_ref和脱敏说明。不能把声明当实测，证据指向一次已认领并回执的测试通知。该文件由对应AI维护，本次安装方不代填。

## 边界

共享层不改pipeline/config.yaml、不推进产品状态、不创建产品、不调用付费图片资源、不部署后台、不上架；这些仍按各AI自己的流程和负责人授权执行。远端Muse不使用本机OpenClaw main；没有改它的模型、身份、记忆或业务设置。

公共仓库不放本地配置、Cookie、Token、账号、用户明细或机器绝对路径。传输代码可供复核，配置仅保留在运行机。源代码注册表与运行状态不要混淆：仓库中的消费者登记不代表服务器持续在线。

# 请求类型与git认领修复（2026-11-06）

1. 保留兼容的通知外层kind=request，新增request_kind保存handoff/question/dependency/retry。接收方按request_kind区分业务意图，原请求文件格式和event_id不变。
2. 未发送的本地旧通知补上子类型；已经发布的通知不覆盖、不重发。Codex接收方遇到旧通知时回查request_id对应的原请求并核对规范化哈希，内容变化或缺失时不猜测。
3. README补充git备用认领，与Contents API共用同一路径和claim_id。只有普通push成功或远端确认同一claim_id已落库后才执行；push失败后须fetch核对，不能把网络故障、无关提交或权限失败说成已被别人认领。禁止force和覆盖add/add冲突。
4. 23项本地测试通过，包括四种子类型传递、重启后保留、旧通知兼容、已发布通知不重发、两个git客户端争抢同一通知，以及无关文件提交导致push拒绝但尚无人认领的情形。git测试在本机隔离bare仓库完成，不宣称已在所有云端环境执行。

没有修改其他AI的独立实现、产品状态、账本、支付或发布规则。其他接收方需要按新增request_kind读取类型；完整git备用流程见本目录README。

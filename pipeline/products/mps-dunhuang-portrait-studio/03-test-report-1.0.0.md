# 敦煌写真照相馆1.0.0 — A3静态退回

2026-11-14T19:21:18+08:00。**自检不通过**。固定包提交`2f28a226db29d033cf85cc310aa2efe0bc2ac56f`，ZIP1453045B，SHA256 `0803d919774b6705b5df0b6cee3036a09396737f89a1588b4d05114143b16c51`。本轮只静态阅读干净解压包、AST/标准库和资料，不导入/执行包，不重跑A2，不调用上游/浏览器。

## DH-A3-01 / P2

`scripts/studio.py:989-999`

实际：cmd_auth error has no draft context but calls W.failure(not_started), asserting no image fees after a prior unknown/settled task。

复现路径：Prior submitted-unknown or delivered task; user auth; account request network/5xx failure; static branch emits definite not charged。

期望：account_failure with fees by service records; preserve original task/account identity。

## DH-A3-02 / P2

`scripts/studio.py:1167-1223`

实际：New feedback B invokes _submit_pending over entire queue and automatically re-POSTs old unknown A without explicit retry。

复现路径：A POST response unknown remains pending; user only confirms new B; default feedback branch queues B then iterates A,B。

期望：A new confirmed item submits only that item; old unknown items retain exact key/body and await explicit retry。

## DH-A3-03 / P2

`scripts/http_bytes.py:104-150`

实际：On Windows Popen.communicate synchronously _stdin_write(input) before reader timeout joins; large request pipe write is outside effective deadline supervision。

复现路径：Static CPython 3.12 Windows _communicate source confirms synchronous write before timeout joins; payload larger than pipe capacity and helper pre-read stall can block the supervising thread。

期望：Separate bounded stdin writing from main-thread deadline; expiry kills/reaps this helper, no retry or credential files。

1.0.0的A2双端64+155+16通过记录仍保留，但这些新增场景未被首轮测试覆盖，不能用A2代替A3通过。退开发出1.0.1补精确回归并重跑双端A2，再锁新ZIP做静态A3；保留旧ZIP，不覆盖固定证据。真机行为验收/上架前浏览器验证按长期规则跳过，不称通过。未部署、未支付、未新生图、未上传。

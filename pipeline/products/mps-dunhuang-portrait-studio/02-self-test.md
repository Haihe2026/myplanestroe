# 敦煌写真照相馆 1.0.0 — A2自测

2026-11-14T19:08:30+08:00。**A2通过**；本报告只记录开发自测，A3另对固定ZIP做静态检查。

最终包 `02-package/dist/mps-dunhuang-portrait-studio-1.0.0.zip`：**1453045 B**；SHA256 `0803d919774b6705b5df0b6cee3036a09396737f89a1588b4d05114143b16c51`。小于3,000,000B硬限与2,500,000B目标。30个文件；从同一ZIP干净解压验证，包内源码与冻结ZIP逐字节相同。

| 平台 | 自测 | 用例 | 结果 |
|---|---|---:|---|
| windows | contract | 64 | PASS / 0失败、0错误、0跳过 |
| windows | e2e | 155 | PASS / 0失败、0错误、0跳过 |
| windows | http-deadline | 16 | PASS / 0失败、0错误、0跳过 |
| linux | contract | 64 | PASS / 0失败、0错误、0跳过 |
| linux | e2e | 155 | PASS / 0失败、0错误、0跳过 |
| linux | http-deadline | 16 | PASS / 0失败、0错误、0跳过 |

Windows原生3.12.10；Ubuntu WSL Linux3.12.3。两端均运行随包原始测试文件，没有内存改写测试；Linux在私有原生/tmp目录，`unshare -rn`隔离网络。Windows在合成私有测试树，socket guard及子HTTP进程继承offline门禁。全部账户、图片、工单、计费均Mock/合成，实际业务网络、上游生图、支付、部署、上传均0。日志与SHA见`02-package/dev/a2-result-1.0.0.json`。

批准规格固定于 `a8538c0a3170dbba876bddd449b63ff2f33704fe`，MD/JSON SHA与A1保持不变。阶段6共57项和敦煌DH01–DH21均逐项映射；适用的Mock/静态断言通过，不适用项依批准契约标N/A，真实宿主不作通过声明，详见`dev/coverage-map.json`。十张既有JPEG共1,333,229B未改字节；512×512 logo外置480,802B未重生；provenance/audit沿用批准资料，`demos-derivation.json`逐图记录。

覆盖：16触发语义、本人成人单人、三许可独立、改方案先作废旧确认、完整look/prompt快照、三画幅/1K、主域可信链接、仅六字段请求、Key绑定与401恢复/403拒绝、原任务未知/404不重提、非明确状态不冒称处理中、历史费用不串新任务、消费记录/提交工单/查工单、反馈未知不自动重发、8字段首次对话与3字段关联、离线十示例及空格/#安全路径、PNG/JPEG完整有界校验和坏图原任务续接。6次原任务GET/2次图片GET/4次账户请求与420秒总预算有回归；完整HTTP事务另有假socket/假时钟和真空闲子进程截止回归，均零网络。

Windows以原生Get-Acl核对状态目录和文件：protected DACL、各1条允许ACE、仅当前用户，JSON写读成功；不拿POSIX模式位代称Windows ACL。Linux真实symlink拒绝，Windows中间组件拒绝为Mock验证，未声称真实junction构造实测。Python3.7仅AST语法检查，真实运行版本如上。

开发复核曾真实失败并修复：新plan/regenerate沿用旧账单、未知轮询误报processing、无图明确需求未收口；初败/修后日志留存在`dev/development-checks/`。另修复中间state目录链接读取与慢HTTP内部读取越过timeout。首轮最终ZIP A2两端契约64/64通过，Mock155项中各有1项测试误拒合法带引号YAML版本；已改为标准YAML解析比较，不改ZIP，补跑155项通过。Linux首轮HTTP专项因开发辅助文件路径遗漏未执行，补齐路径后16项通过；Windows专项16项通过。首轮记录保存在`dev/a2-attempt-01/`，已通过且未改的契约不重复执行。HTTP凭据仅stdin内存传给固定短命标准库helper，禁止重定向；到期终止该helper，不重POST。OS创建/终止/回收仍有调度开销，不宣称硬实时；保留90秒进程余量。

开发决策：U06仅在反弹琵琶与空手乐舞两种已登记方向间澄清，额外持琴乐舞不暗加套系、不确认、不联网（DH-DEV-DEC-01）；仅明确pending/processing且无待核查通知可说处理中（02）；完整HTTP事务截止采用短命helper（03）。

未验证：真实宿主执行、真实OAuth/付款/回调、生产上游画质和真实账户。真机验收与上架前浏览器验证按负责人长期规则跳过，不能称通过；不拦本轮A3。到test_passed交Muse/负责人手动上传；不部署、不改共享认证或客户财务。官方技能文档在线读取时间/URL/HTTP200/SHA保存在`dev/official-read.json`及`dev/official-pre-a2-read.json`。

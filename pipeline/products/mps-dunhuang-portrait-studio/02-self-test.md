# 敦煌写真照相馆 1.0.1 — A2自测

2026-11-14T19:44:52+08:00。**A2通过**；本报告只记录开发自测，A3另对固定ZIP做静态检查。

最终包 `02-package/dist/mps-dunhuang-portrait-studio-1.0.1.zip`：**1453789 B**；SHA256 `c08d9c55afbe831f5357bee9ba4166a2c3dcdca4e60ebba2444762e0041e9357`。小于3,000,000B硬限与2,500,000B目标。30个文件；从同一ZIP干净解压验证，包内源码与冻结ZIP逐字节相同。

| 平台 | 自测 | 用例 | 结果 |
|---|---|---:|---|
| windows | contract | 64 | PASS / 0失败、0错误、0跳过 |
| windows | e2e | 157 | PASS / 0失败、0错误、0跳过 |
| windows | http-deadline | 19 | PASS / 0失败、0错误、0跳过 |
| linux | contract | 64 | PASS / 0失败、0错误、0跳过 |
| linux | e2e | 157 | PASS / 0失败、0错误、0跳过 |
| linux | http-deadline | 19 | PASS / 0失败、0错误、0跳过 |

Windows原生3.12.10；Ubuntu WSL Linux3.12.3。两端均运行随包原始测试文件，没有内存改写测试；Linux在私有原生/tmp目录，`unshare -rn`隔离网络。Windows在合成私有测试树，socket guard及子HTTP进程继承offline门禁。全部账户、图片、工单、计费均Mock/合成，实际业务网络、上游生图、支付、部署、上传均0。日志与SHA见`02-package/dev/a2-result-1.0.1.json`。

批准规格固定于 `a8538c0a3170dbba876bddd449b63ff2f33704fe`，MD/JSON SHA与A1保持不变。阶段6共57项和敦煌DH01–DH21均逐项映射；适用的Mock/静态断言通过，不适用项依批准契约标N/A，真实宿主不作通过声明，详见`dev/coverage-map.json`。十张既有JPEG共1,333,229B未改字节；512×512 logo外置480,802B未重生；provenance/audit沿用批准资料，`demos-derivation.json`逐图记录。

覆盖：16触发语义、本人成人单人、三许可独立、改方案先作废旧确认、完整look/prompt快照、三画幅/1K、主域可信链接、仅六字段请求、Key绑定与401恢复/403拒绝、原任务未知/404不重提、非明确状态不冒称处理中、历史费用不串新任务、消费记录/提交工单/查工单、反馈未知不自动重发、8字段首次对话与3字段关联、离线十示例及空格/#安全路径、PNG/JPEG完整有界校验和坏图原任务续接。6次原任务GET/2次图片GET/4次账户请求与420秒总预算有回归；完整HTTP事务另有假socket/假时钟和真空闲子进程截止回归，均零网络。

Windows以原生Get-Acl核对状态目录和文件：protected DACL、各1条允许ACE、仅当前用户，JSON写读成功；不拿POSIX模式位代称Windows ACL。Linux真实symlink拒绝，Windows中间组件拒绝为Mock验证，未声称真实junction构造实测。Python3.7仅AST语法检查，真实运行版本如上。

1.0.0基线曾A2通过，A3在742fd6f9778cabe5a66489b134ffd98b1dd2061c真实退回三项P2，本版修复且补了精确回归：授权失败不再宣称原图未扣；新反馈B只提交B，未知A保原key/body等待显式--retry，重复原文不自动发送，已有编号只GET；Windows大stdin写入与主线程截止监督分离，超时终止/回收该helper，不重试、不存凭据文件。修复前失败/修后通过日志保留，真正空闲子进程+大于管道容量payload为零网络截止回归；OS创建/终止/回收仍有调度开销，不宣称硬实时，90秒余量保留。旧1.0.0 ZIP和A2/A3报告保留，不覆盖。

开发决策：U06仅在反弹琵琶与空手乐舞两种已登记方向间澄清，额外持琴乐舞不暗加套系、不确认、不联网（DH-DEV-DEC-01）；仅明确pending/processing且无待核查通知可说处理中（02）；完整HTTP事务截止采用短命helper（03）。

本版仅5个ZIP成员变化：SKILL/_meta/studio/telemetry版本与studio两处逻辑、http_bytes截止；其余25成员逐字节不变，包括10JPEG、welcome_copy、主题、references和随包64测试。批准规格MD/JSON保持原SHA，输出升补丁1.0.1，范围、描述、收费和资产不扩张。private_store也与实测Windows ACL的1.0.0源码相同，复用该原生Get-Acl证据。测试夹具ResourceWarning原样保留，0失败/错误/跳过。

未验证：真实宿主执行、真实OAuth/付款/回调、生产上游画质和真实账户。真机验收与上架前浏览器验证按负责人长期规则跳过，不能称通过；不拦本轮A3。到test_passed交Muse/负责人手动上传；不部署、不改共享认证或客户财务。官方技能文档在线读取时间/URL/HTTP200/SHA保存在`dev/official-read-1.0.1.json`及`dev/official-pre-a2-read-1.0.1.json`。
本版首轮最终ZIP A2中，契约64和HTTP专项19均通过，三项Mock遥测用例因开发Mock仍固定旧1.0.0版本而失败；只修正Mock接受本版1.0.1，冻结ZIP不变，补跑157项通过。初轮日志保存在dev/a2-attempt-1.0.1-01/；已通过且未修改的契约/专项不重复执行。

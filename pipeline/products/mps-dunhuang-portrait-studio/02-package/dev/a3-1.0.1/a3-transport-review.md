# 1.0.1 HTTP截止静态复核

自检范围PASS。固定提交`409250986fe5ef57c1180992e903040057033d62`；ZIP SHA`c08d9c55afbe831f5357bee9ba4166a2c3dcdca4e60ebba2444762e0041e9357`，1453789B。仅独立ZIP/AST及文本阅读，不执行被审包、测试或网络。

- TR-01 PASS：DH-A3-03闭合：主线程不再同步写大stdin，detach后受控writer写/flush/close，主线程communicate(None)带剩余monotonic timeout，完整传输受监督。 证据：`scripts/http_bytes.py:133-214; scripts/http_bytes.py:110-130`。
- TR-02 PASS：到期走单次helper kill/reap，writer bounded join；不从主线程close被writer/reader持有的buffer锁，writer异常不接受成功响应。 证据：`scripts/http_bytes.py:80-92; scripts/http_bytes.py:95-107; scripts/http_bytes.py:133-214`。
- TR-03 PASS：固定sys.executable/-I/-S/helper路径，shell=False与Windows隐藏；凭据不进argv/临时文件，仅JSON内存pipe；无重试或父进程网络回退。 证据：`scripts/http_bytes.py:133-214; scripts/http_bytes.py:248-267`。
- TR-04 PASS：目标仅https主域/platform-api；headers/timeout/limit验证；响应bytes/长度/status与晚返回校验；单次urllib事务拒重定向、错误体不读、不打印错误凭据。 证据：`scripts/http_bytes.py:49-77; scripts/http_bytes.py:24-46; scripts/http_bytes.py:217-245; scripts/http_bytes.py:248-267`。
- TR-05 PASS：Core JSON2MiB/PNG16MiB及telemetry4KiB转接同一边界；未知提交先保存原键/body摘要，GatewayError0仅原任务GET；没有新POST重试策略。 证据：`scripts/studio.py:_default_transport/call/_submit/_continue_job; scripts/telemetry.py:_default_transport/report_once`。
- TR-06 PASS：OS创建/终止/回收有调度开销，保留90秒进程余量，不将逻辑截止说成硬实时；HTTP子进程是单请求传输工具，无AI心跳/常驻worker。 证据：`scripts/http_bytes.py:module docstring; scripts/studio.py:PROCESS_MARGIN_S/OUTER_TIMEOUT_S`。

DH-A3-03已闭合。A2的19项专项及旧5.094s→新0.203s记录只作已有证据引用，A3未复跑。真机/浏览器按长期规则跳过，不称通过。

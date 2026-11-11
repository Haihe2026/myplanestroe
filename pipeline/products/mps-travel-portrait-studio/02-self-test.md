# 自测报告：mps-travel-portrait-studio 1.0.1

- 修复轮（A3 退回 1.0.0，`rounds.dev=2`），按 SOP 〇章不重读官方文档；沿用 1.0.0 自测时的读取记录（快照 2026-11-08「二、技能」章）。
- 依据：`03-test-report.md`（A3-TRV-01–05，固定 ZIP `d4a1d5ce…` SHA `fcecdcef…e1cd`）与 Muse 交接 `msg-from-muse-20261111-fix-100-trv-a3.md`（@ `e764fa37`）；开发文档 `01-dev-spec.md/json` 未改动，未放宽规格。
- 时间：2026-11-11T21:38–21:55+08:00，Claude 定时运行。渠道只做 `config.yaml` 的 `workbuddy-skill`。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；生产变更 0；未上传、未发布。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-travel-portrait-studio-1.0.1.zip`，2413912 字节，25 个文件（新增 `scripts/jpeg_local.py`），最多两级，SHA256 `f8ab627c7adaedc99a5410e61e7f68afe7efeb91ce644532da00a48bad5da4b1` |
| 版本 | 1.0.1（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py` 一致）；本 slug 平台无已上传版本，1.0.1 > 1.0.0 |
| 旧包 | `dist/mps-travel-portrait-studio-1.0.0.zip` 保留未动（SHA `fcecdcef…e1cd`） |
| logo | `dist/logo.png` 原字节未动，SHA256 `d8177d72fbc14acc0e2371fd5af976ced0302c2cab395c1937a4dfa9d66acee9` |
| 十张示例 | `assets/*.png` 与 `demos.json` 未改动（git 无差异），SHA 与规格 JSON、`dev/demos-derivation.json` 一致 |
| 欢迎句 | 「欢迎使用WorkBuddy官方认证技能 旅行打卡写真照相馆。」逐字未变 |

## 本轮修复（逐项）

### A3-TRV-01 绑定未确认仍可生成 → 已修
- `studio._ensure_skill_key`：凭证保存与绑定确认拆成两个状态。合法 Key 先私存为 `skill_key_bound=False`，再由新函数 `_confirm_bound` POST `/skill-key/bound`；只有 HTTP 200 且 `bound` 恰为 `true` 才记为已绑定并返回 `ok`。`bound=false`、缺字段、`"true"` 字符串、坏响应、超时/断网、5xx、401 一律返回未就绪，`run` 以「还没有开始生成，没有扣次数」结束，**不发生成 POST**，草稿保持 `confirmed`、原任务键不变。
- 已缓存但未确认的 Key（含进程重启、旧缓存缺标记）每次命令先确认一次再生成；凭证只领一次，不重复 `/skill-key`；每条命令只确认一次，不自动重试。
- 401 恢复（`_recover_skill_key`）同样必须确认绑定；确认失败 → 退出 4、`task_kept=true`，原任务仍 `submit_unknown`、原键原体，之后只按原键查询。清凭证时同时清绑定标记。
- 回归：e2e `RepairTravel101.test_trv01_bound_not_confirmed_never_generates`（7 种未确认 × 两次运行即重启，生成 POST=0，补确认后同键交付且只扣 1 次）、`test_trv01_bound_confirmed_before_first_post`（顺序：bound 先于 skill-jobs；已确认后不再重复确认）、`test_trv01_cached_unbound_key_after_restart`（标记为 false 或缺失）、`test_trv01_401_recovery_requires_bound`（7 种 × 恢复前后均只查原键，POST 始终 1 次）；契约 `TravelRepair101.test_trv01_key_needs_explicit_bound_true`。

### A3-TRV-02 损坏参考图只验尺寸头 → 已修
- `audit_images._png_info` 改为完整流式校验：签名、IHDR 在首、每块 CRC、索引色须有 PLTE、IDAT 连续、IEND 收尾且无尾随、zlib 完整（`eof` 且无多余数据）、每条扫描行过滤类型 0–4、总长度与尺寸一致（含 Adam7）；超限尺寸在展开前拒绝。
- 新增 `scripts/jpeg_local.py`（标准库）：逐段解析标记与段长，量化表/Huffman 表引用必须已定义，按 Huffman 表把每个扫描的熵编码数据完整解一遍（基线 SOF0/1 与渐进 SOF2，含 DC/AC 首扫描与修正扫描、EOBRUN、RST 序号与区间数），必须解出全部 MCU、不读过数据末尾、以 EOI 收尾；不做 IDCT。算术编码/无损/分层等少见编码点名文件并提示另存为普通 JPG 或 PNG（`unsupported_jpeg`），不放行。
- `plan` 与 `run`（`_job_body`）两处都走同一检查；坏输入退出 3、`photoInvalid`、话术点名文件，业务 HTTP 与生成 POST 为 0。
- 回归：e2e `test_trv02_damaged_inputs_rejected_before_any_request`（PNG 坏 CRC、IDAT zlib 截断且 CRC 合法、zlib 垃圾、缺 IEND、文件截断、扫描行不足；JPEG 只有 SOF、SOF+EOI、扫描截断、扫描截断后补 EOI、缺 DHT，共 11 例，`mock.calls==[]`）、`test_trv02_damaged_after_confirm_no_post`（确认后同路径换成上述坏文件，零生成 POST）、`test_trv02_valid_png_and_jpeg_still_pass`；契约 `test_trv02_damaged_inputs_rejected`。e2e/契约的 JPEG 夹具改为标准库合成、可完整解码的基线 JPEG（旧夹具只有 SOF 头加零字节，本身就是 TRV-02 所说的坏输入）。
- 开发机额外交叉核对（不随包、不进测试，Pillow 12.3 仅在本机生成样本）：Pillow 生成的基线/渐进、4:4:4/4:2:2/4:2:0、灰度、CMYK、带 RST（1/3/7 块）、优化 Huffman 共 38 张 JPEG 全部通过；SOF-only/中段截断/缺 EOI/截断补 EOI 全部拒绝；4000×3000 噪声图（8.1MB 基线 6.1 秒、5.7MB 渐进 9.3 秒，均超出 5MB 上限，实际上限内更快）。随机单比特翻转约 14% 被判损坏——JPEG 位翻转多数仍可完整解码，这是格式本身的性质，不是漏检。

### A3-TRV-03 首次对话失败后自动重报 → 已修
- `telemetry.report_once`：发出前先原子持久化 `attempted=true` 并回读确认，写不进去就返回 `skipped` 不发；之后 `sent` 或 `attempted` 任一为真即 `already`，失败的那一次也不再重发。成功回执仍单独校验后存回执，用于既有 `/first-dialogue/link`（409 不覆盖逻辑未动）。关闭开关、只读、损坏标识的原行为保留。
- 回归：e2e `test_trv03_failed_first_report_never_resent`（异常/超时/非 200/204/坏 JSON/坏回执 × 9 条后续命令含 plan/confirm/run/resume/status/balance/history/再次 first-turn，总尝试恒为 1，重启后 `report_once`=already）、`test_trv03_nested_resume_run_reports_once`（同一次 resume→run 只尝试 1 次）、`test_trv03_attempt_not_persisted_means_not_sent`、`test_trv03_success_then_link_unchanged`；原 `Telemetry.test_failure_does_not_block_and_no_retry_loop` 的期望由「恢复后再发、共 4 次」改为「共 1 次」（旧期望正是缺陷本身）；契约 `test_trv03_attempt_once_even_after_failure`。

### A3-TRV-04 特异服饰被词序覆盖 → 已修
- 路由改三层：明确目的地 `ROUTE_DESTINATIONS` → 特异服饰 `ROUTE_OUTFITS`（和服/古寺/日式→kyoto；汉服/唐风/城墙→xian）→ 泛化风格 `ROUTE_STYLES`；只有同层内取最先出现者，跨层不看词序。十个主题总数不变。`references/scenes.md` 消歧节与 SKILL.md 首轮第 3 条同步。
- 回归：契约 `test_route_precedence` 新增「樱花下穿和服」「樱花季穿和服拍照」「春日樱花日式街巷」→kyoto，「古城夜景穿汉服」「夜景灯火下的汉服」「古城唐风」「灯火古城唐风写真」→xian，裸「春日樱花」「樱花季」→sakura、裸「夜景灯火」「凤凰夜景」→oldtown，「三亚穿汉服」→sanya、「京都汉服」→kyoto、「西安和服」→xian、「哈尔滨古城夜景汉服」→harbin（目的地最高）；scenes.md 覆盖三层全部关键词。

### A3-TRV-05 传图同意未告知接收方类别 → 已修
- `welcome_copy` 新增常量 `RECIPIENTS='图片服务及算力供应商'`、`UPLOAD_CONSENT`；确认话术第 2 项改为「同意把这张照片发送给图片服务及算力供应商处理，只用于本次制作」，本人与监护人两种文案共用；只说类别，不点名品牌、模型或技术。SKILL.md 执行规范第 3 条、scenes.md 三项同意同步。三个 flags 独立、缺一不设 `reference_consent`、换图需重确认、已提交任务原键续接的逻辑未动。
- 对客禁用词清单含「供应商」：只对规格要求的完整说法「图片服务及算力供应商」做唯一豁免，单独出现「供应商」仍会被测出。
- 回归：契约 `test_consent_copy`（本人/监护人各一条，第 2 项含「这张照片」「图片服务及算力供应商」「只用于本次制作」，恰 3 项，白标词不出现）；e2e `Confirmation.test_plan_copy`（监护人路径逐字断言）。

## 反证（修复前代码能被新测试检出）

把 1.0.0 的 `studio.py`/`telemetry.py`/`audit_images.py`/`welcome_copy.py` 放回包副本（只把版本号改成 1.0.1、给旧 welcome_copy 补常量以便加载）后重跑：e2e 11 项失败/报错（TRV-01×3、TRV-02×2、TRV-03×5、TRV-05 `test_plan_copy`），契约 5 项失败（`test_route_precedence` TRV-04、`test_consent_copy` TRV-05、TravelRepair101×3）。换回 1.0.1 代码全部通过。

## 测试结果（合成账户与进程内 Mock，真实上游 0）

| 套件 | 结果 |
|---|---|
| 契约（随包）`python3 -m unittest discover -s tests`（仓库内，含与 `01-dev-spec.json` 比对） | 54/54 OK |
| 端到端 `python3 dev/e2e_check.py` | 114 OK + 2 跳过（ZIP 项需 `--zip`） |
| 干净解压 1.0.1 ZIP：契约；`e2e_check.py --package <解压目录> --zip dist/…-1.0.1.zip` | 54/54 OK；116/116 OK |
| 密钥/上游扫描（技能凭证、`sk-`、`Bearer`、上游域名与模型名） | 包与 dev 无命中 |
| SKILL.md 大小 | 15355 字节 < 15KB |
| Python | 3.13（脚本按 3.7+ 标准库编写） |

## 前序缺陷逐项复核（未回退）

| 类别 | 结论 | 证据 |
|---|---|---|
| FAM-01/02（401 后 404 重提、恢复失败解除原任务保护） | 未回退；与 TRV-01 同属原任务/绑定保护，新增 `test_trv01_401_recovery_requires_bound` 覆盖「恢复时绑定失败」 | e2e `test_fam01_*`×3、`test_fam02_*`×2、`test_poll_401_recovers_once_then_persistent_keeps_task`；契约 `test_fam_01_02_unauthorized_submit_never_resubmits_or_unlocks` |
| FAM-03（缺一张示例仍成功） | 未回退 | e2e `test_fam03_*`×3；契约 `test_fam_03_demo_missing_one_exit3` |
| PAY-01/02/03/04 | 未回退；PAY-04 与 TRV-03 同属遥测/离线类，demo 仍零网络 | e2e `test_pay_01_*`×7、`test_pay_02_*`×9、`test_wed_a3_01_demo_alone_zero_network`；契约 `test_pay_01_*`、`test_pay_02_link_freshness`、`test_pay_03_description_last_sentence_covers_account`、`test_wed_a3_01_demo_has_no_network` |
| PET-01/02/03（原任务未知不丢键、截断 PNG 不宣告交付、缺示例不报成功） | 未回退 | e2e `test_submit_unknown_persisted_before_post_and_locked`、`test_corrupt_png_kept_pending_then_get_only`、`test_fam03_*` |
| A3-E01–03（中英示例对齐、路径无空格与 #） | 未回退 | 契约 `test_examples_zh_en_same_scene`、`test_examples_alignment_detects_misalignment`、`test_demo_link_path_with_space`、`test_demo_link_path_with_hash` |
| WED-A3-01–03（demo 离线、确认后文件不可替换、成品链接编码） | 未回退；TRV-03 修复不影响 demo 零业务网络 | e2e `test_wed_a3_01_*`、`test_wed_a3_02_*`×2、`test_wed_a3_03_delivery_links_space_and_hash`；契约 `test_wed_a3_03_delivery_links_markdown_safe` |
| 11-07 斜杠案（状态目录不以点开头、md_safe_path、反斜杠转正斜杠） | 未回退 | 契约 `test_demo_link_markdown_safe`；e2e `test_demo_links_survive_markdown` |

T01–T15 其余项（首轮、示例、计费确认、等待、PNG 交付、售后、平台字段、收藏声明、非实拍标注、微信/支付 Mock、请求体六字段）沿用 1.0.0 用例，全部仍通过，见上表套件结果。

## 偏离开发文档的地方

1. 沿用 1.0.0 已记的 4 条（`suggested_scene`、服装默认值在场景表、宿主侧行为只写 SKILL.md、`X-Skill-Device` 不判 mobile/cloud）。
2. 本轮新增：JPEG 完整解码校验只支持 Huffman 基线/扩展顺序/渐进 8 位（手机与常见软件导出的 JPEG 均属此类）；算术编码、无损、分层、12 位 JPEG 本地拒绝并提示另存，不放行到服务端。规格未写这类编码，按「完整可解码、不可解码先本地拒绝」取保守处理。
3. 对客禁用词「供应商」对规格要求的「图片服务及算力供应商」一处豁免（理由见 TRV-05）。

## 未验证项

- 真人/儿童保真、生产签名输入路由、WorkBuddy 宿主实际行为（加载、欢迎、示例、收藏、不 @ 自动选中），A3 后由附录 D 本机导入另测。
- 真实 `/skill-key/bound` 生产响应形态（本轮按规格「bound=true 才算确认」实现，只在 Mock 验证）。
- 真实微信扫码、手机/异浏览器跳转、真实付款与到账、客户钱包；平台审核与上架；约 2.4MB 包的平台接受情况。
- 大尺寸真实手机照片的 JPEG 校验耗时只在开发机用合成噪声图估算，未在用户机器实测。

## 部署与回滚

- 部署：无（fast 车道，无后端改动、无迁移、无重启）。负责人手动上传 1.0.1 ZIP；logo 为 `dist/logo.png`。
- 回滚：1.0.0 未上架、1.0.1 也未上传；不上传或平台下架即可，无数据迁移。本机状态新增字段 `skill_key_bound`、`attempted` 向后兼容（缺字段按未确认/未尝试处理）。

## 退回意见

无。

# 自测报告：mps-travel-portrait-studio 1.0.2

- 修复轮（A3 复查退回 1.0.1，`rounds.dev=3`），按 SOP 〇章不重读官方文档；沿用 1.0.0 自测时的读取记录（快照 2026-11-08「二、技能」章）。
- 依据：`03-test-report.md`（A3-TRV-01-R1、A3-TRV-02-R1，固定 ZIP `43381623…` SHA `f8ab627c…a4b1`）与 Muse 交接 `msg-from-muse-20261111-fix-101-trv-a3-r2.md`（@ `6ddb5670`）；开发文档 `01-dev-spec.md/json` 未改动，未放宽规格（5MiB / 2000 万像素 / 8000 边长不变）。
- 时间：2026-11-11 夜间 Claude 定时运行。渠道只做 `config.yaml` 的 `workbuddy-skill`。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；生产变更 0；未上传、未发布。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-travel-portrait-studio-1.0.2.zip`，2417544 字节，25 个文件，最多两级，SHA256 `bef83fffa5fddad2fa409a048f0cf819e7e939618d531bccdab7113786ce0e91` |
| 版本 | 1.0.2（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py` 一致）；本 slug 平台无已上传版本，1.0.2 > 1.0.1 > 1.0.0 |
| 旧包 | `dist/…-1.0.0.zip`、`dist/…-1.0.1.zip` 保留未动 |
| 相对 1.0.1 | 8 文件修改（SKILL.md、_meta.json 仅版本号；scripts/studio.py、png_local.py、audit_images.py、jpeg_local.py、telemetry.py（版本号）；tests/test_skill_contract.py），无新增、无删除；`assets/` 全部逐字节相同 |
| logo | `dist/logo.png` 原字节未动，SHA256 `d8177d72fbc14acc0e2371fd5af976ced0302c2cab395c1937a4dfa9d66acee9` |
| 十张示例 | `assets/*.png` 与 `demos.json` 未改动 |
| 欢迎句 | 「欢迎使用WorkBuddy官方认证技能 旅行打卡写真照相馆」逐字未变 |
| 付费口径 | 未改：MyPlaneStore 通用套餐，不单独定价，0 次免费试用 |

## 本轮修复（逐项，修根因）

### A3-TRV-01-R1 绑定 401 后不能摆脱失效缓存 Key → 已修
- 根因：1.0.1 把绑定确认的 401 与超时/5xx 一样当「未确认、凭证保留」，于是下次运行见缓存 Key 跳过领取、再次绑定同一把已被轮换的旧 Key，永久循环。
- `studio._confirm_bound`：`/skill-key/bound` 返回 401 时立即从 `account.json` 删除 `skill_key` 与 `skill_key_bound` 并落盘，返回 `key_reset`；**不动 `install_secret`、不新建账户、不碰任何草稿/任务锁**。
- `cmd_run`：`key_reset` → 退出 4、`credentialsReset`、`task_kept=true`（确认单保留、尚未冻结请求体、没有生成 POST）。下一次 `run`/`resume` 沿原 `install_secret` 重新 POST `/skill-key` 取新 Key，再确认 `bound=true` 才生成。
- `_recover_skill_key`（已提交任务的 401 恢复）复用同一路径：恢复时新 Key 绑定 401 也被作废、退出 4，原任务仍 `submit_unknown`，只 GET 原键。
- 非 401（`bound=false`、缺字段、`"true"`、坏响应、超时、5xx）行为不变：凭证保留、标记 false、不得新生成，下次再确认一次。`/skill-key` 本身 401（安装身份未被认）不清任何本机数据，行为与 1.0.1 相同。
- 回归（e2e `RepairTravel101`，Mock 新增 `rotate_key` 模拟网页轮换：旧 Key 认证即 401，对应服务端 `skill_access.acknowledge → authenticate`）：
  - `test_trv01_r1_bound_401_clears_stale_key_then_recovers`：旧缓存缺标记 / 标记 false 两种 × 轮换后 run → (4, credentialsReset, task_kept)，`skill_key`/`skill_key_bound` 均已删，`install_secret` 不变，草稿 `confirmed`、原 idem、`body_sha256` 为空、生成 POST 0；下一次 run（从磁盘重载）→ `/skill-key` 恰多 1 次、新 Key ≠ 旧 Key、bound=true、交付、生成 POST 恰 1 次且用原 idem；之后新草稿不再重复确认。
  - `test_trv01_r1_no_infinite_rebind_of_same_key`：轮换后连跑 3 次，旧 Key 只被确认 1 次，该草稿只生成 1 次。
  - `test_trv01_r1_unknown_task_only_queries_original_key`：已发出、结果未知的任务（服务端已受理、客户端断网）+ 凭证轮换且标记 false → resume 走恢复：新 Key bound=true 后只 GET `/jobs/by-key/<原 idem>`，生成 POST 0，原 idem/原体摘要不变，交付成功。
  - `test_trv01_r1_non401_bound_failure_keeps_key_no_generation`：false/missing/timeout/500 → 退出 3，凭证保留且标记 false，生成 POST 0。
  - 原 TRV-01 正反例保留：`test_trv01_bound_not_confirmed_never_generates`（非 401 六种 × 两次运行）、`test_trv01_bound_confirmed_before_first_post`、`test_trv01_cached_unbound_key_after_restart`、`test_trv01_401_recovery_requires_bound`（含 401 共七种）。
  - 契约 `TravelRepair102.test_trv01_r1_bound_401_clears_key_keeps_identity`（调用序列恰为 bound(旧)→skill-key→bound(新)，账户文件最终只剩原身份+新 Key+true）、`test_trv01_r1_run_maps_key_reset_to_exit4`；`TravelRepair101.test_trv01_key_needs_explicit_bound_true` 去掉 401 一例（其期望「401 后凭证保留」正是本缺陷）。

### A3-TRV-02-R1 输入完整校验的资源消耗无上限 → 已修

**PNG 无界展开**
- 根因：`decompress(chunk)` 不带 `max_length`，且末尾 `flush()` 同样无界。
- `png_local` 新增共用的 `inflate_rows`：每次 `decompress(data, limit)`，`limit = min(64KiB, 剩余应有扫描行字节 + 1)`；每块输出立即逐行核对（过滤字节 0–4、行长）后丢弃；超出应有总长 1 字节即 `damaged`。循环处理 `unconsumed_tail`，输出恰好等于上限时继续取积压输出；EOF 后的尾随数据（`unused_data`）判坏；不再调用 `flush()`，以 `finish_rows` 检查 `eof`、无尾随、行全部到齐。
- `audit_images._png_info`（参考图）与 `png_local.verify`（交付图，1.0.1 同样整段展开）都改用它；行计划 `row_plan` 移入 `png_local` 共用，`audit_images` 保留同名别名。
- 回归：契约 `test_trv02_r1_png_inflate_bounded`——128×128 灰度 IHDR（应有 16512 字节）+ 可展开 64MiB 的合法 deflate 流（构造时也按 1MiB 分块压缩）；注入 `chunk=4096` 与计量器，断言每次输出 ≤ 4096、累计输出 ≤ 16513 后拒绝，`check()` 返回 `damaged`，`png_local.verify` 同样拒绝；`test_trv02_r1_png_positive_cases_still_pass`——合法 PNG 与「IDAT 切成 7 字节一块」在 `chunk=97` 下通过，EOF 后尾随 1 字节与坏 CRC 拒绝；原 Adam7 用例契约 `test_png_verify`、`test_trv02_*` 仍过。e2e 坏输入表新增 `png-inflate-bomb.png`（32MiB 虚拟展开），plan/run 两处均 `photoInvalid`、`mock.calls==[]`。开发机计时：512MiB 虚拟展开（文件 0.5MB）拒绝耗时 < 1ms。

**JPEG 重复 DHT 放大 CPU**
- 根因：每个 DHT 定义立即建 65536 槽查表，次数无上限。
- `jpeg_local`：DHT 段只做 O(16+符号数) 的前缀码合法性检查（`_check_table`，非法码仍在定义时拒绝），只记录定义字节；SOS 真正引用某表时才经 `_TableCache` 建表，同一定义复用；不同定义的累计构建次数上限 `MAX_TABLE_BUILDS=32`，扫描次数上限 `MAX_SCANS=64`，超出 → `unsupported`（对客「这种 JPG 编码方式暂不支持，请另存为普通 JPG 或 PNG」）。常见基线 2–4 张表、渐进通常 ≤10 次扫描，远低于上限。
- 回归：契约 `test_trv02_r1_jpeg_repeated_dht_bounded`——在合法 JPEG 前插入 300 份原 DHT 段 + 3000 个 22 字节单符号表，仍通过，且 `_build_table` 调用次数与原图相同（≤4）；注入预算 `构建数-1` 时有界拒绝 `unsupported`；`MAX_SCANS=0` 拒绝；非法前缀码拒绝。开发机计时：约 4.0MiB（19 万个重复 DHT 段，接近 5MiB 上限）完整校验 0.61 秒，1.0.1 同样样本按 A3 推导需约 62 亿次赋值。
- 未改：5MiB / 2000 万像素 / 8000 边长、IDAT 分块、Adam7、EOF、CRC、基线/渐进/多扫描重定义（合法多表重定义仍按引用时的定义建表）。

## 反证（修复前代码能被新测试检出）

把 1.0.1 ZIP 的 `scripts/` 整体放回包副本、其余保持 1.0.2 后重跑：契约 `TravelRepair102` 5 项全部失败/报错；e2e `test_trv01_r1_bound_401_clears_stale_key_then_recovers`、`test_trv01_r1_no_infinite_rebind_of_same_key` 失败。说明：e2e 的 32MiB 炸弹样本在 1.0.1 上最终也被判坏（结果对、过程无界），无界性只由契约的计量器用例检出，这符合 A3 所述「先展开、后判断」的缺陷形态。换回 1.0.2 代码全部通过。

## 测试结果（合成账户与进程内 Mock，真实上游 0）

| 套件 | 结果 |
|---|---|
| 契约（随包）`python3 -m unittest discover -s tests`（仓库内） | 59/59 OK |
| 端到端 `python3 dev/e2e_check.py` | 118 OK + 2 跳过（ZIP 项需 `--zip`） |
| 干净解压 1.0.2 ZIP：契约；`e2e_check.py --package <解压目录> --zip dist/…-1.0.2.zip` | 59/59 OK；120/120 OK |
| 密钥/上游扫描（技能凭证、`sk-`、`Bearer`、上游域名与模型名） | 包与 dev 无命中（测试内合成 `'a'*32` 类占位除外） |
| SKILL.md 大小 | 15355 字节（未变） |
| Python | 3.13（脚本按 3.7+ 标准库编写） |

## 前序缺陷逐项复核（未回退）

| 类别 | 结论 | 证据 |
|---|---|---|
| TRV-01–05（首轮）| TRV-03/04/05 已关闭未回退；TRV-01/02 原正例与反例全部仍通过 | e2e `RepairTravel101` 全部、契约 `TravelRepair101` 全部、`test_route_precedence`、`test_consent_copy` |
| FAM-01/02（401 后 404 重提、恢复失败解除原任务保护） | 未回退；与 TRV-01-R1 同属原任务/绑定保护：凭证作废只改账户文件，从不改任务状态/键/体；`test_trv01_r1_unknown_task_only_queries_original_key` 覆盖「轮换后恢复只查原键」 | e2e `test_fam01_*`×3、`test_fam02_*`×2、`test_poll_401_recovers_once_then_persistent_keeps_task`；契约 `test_fam_01_02_unauthorized_submit_never_resubmits_or_unlocks` |
| FAM-03（缺一张示例仍成功） | 未回退 | e2e `test_fam03_*`×3；契约 `test_fam_03_demo_missing_one_exit3` |
| PAY-01/02/03/04 | 未回退；PAY-04 与 TRV-03 同属遥测/离线类，demo 仍零网络 | e2e `test_pay_01_*`×7、`test_pay_02_*`×9、`test_wed_a3_01_demo_alone_zero_network`；契约 `test_pay_01_*`、`test_pay_02_link_freshness`、`test_pay_03_description_last_sentence_covers_account`、`test_wed_a3_01_demo_has_no_network` |
| PET-01/02/03（原任务未知不丢键、截断 PNG 不宣告交付、缺示例不报成功） | 未回退；PET-02 依赖的交付图 `png_local.verify` 改为有界流式后截断/坏图仍判 `download_pending` | e2e `test_submit_unknown_persisted_before_post_and_locked`、`test_corrupt_png_kept_pending_then_get_only`、`test_fam03_*` |
| A3-E01–03（中英示例对齐、路径无空格与 #） | 未回退 | 契约 `test_examples_zh_en_same_scene`、`test_examples_alignment_detects_misalignment`、`test_demo_link_path_with_space`、`test_demo_link_path_with_hash` |
| WED-A3-01–03（demo 离线、确认后文件不可替换、成品链接编码） | 未回退；TRV-03 修复不影响 demo 零业务网络 | e2e `test_wed_a3_01_*`、`test_wed_a3_02_*`×2、`test_wed_a3_03_delivery_links_space_and_hash`；契约 `test_wed_a3_03_delivery_links_markdown_safe` |
| 11-07 斜杠案（状态目录不以点开头、md_safe_path、反斜杠转正斜杠） | 未回退 | 契约 `test_demo_link_markdown_safe`；e2e `test_demo_links_survive_markdown` |

T01–T15 其余项（首轮、示例、计费确认、等待、PNG 交付、售后、平台字段、收藏声明、非实拍标注、微信/支付 Mock、请求体六字段）沿用 1.0.0 用例，全部仍通过，见上表套件结果。

## 偏离开发文档的地方

1. 沿用 1.0.0/1.0.1 已记的条目（`suggested_scene`、服装默认值在场景表、宿主侧行为只写 SKILL.md、`X-Skill-Device` 不判 mobile/cloud；JPEG 仅支持 Huffman 8 位；「图片服务及算力供应商」一处豁免）。
2. 本轮新增：JPEG 不同 Huffman 表构建 > 32 次或扫描 > 64 次判为过于复杂、本地拒绝并提示另存。规格未写此上限，按 A3「有界拒绝、不拿无界计算换正确性」取值，正常手机/软件导出的 JPEG 远低于此。

## 未验证项

- 真人/儿童保真、生产签名输入路由、WorkBuddy 宿主实际行为，A3 后由附录 D（负责人 21:01 新令：不通即撤回、不拦交付）另测；真机验收按负责人豁免跳过。
- 真实 `/skill-key/bound` 对已轮换 Key 的生产响应：按 A3 引用的服务端源码（acknowledge→authenticate 返回 401）实现，只在 Mock 验证。
- 真实微信扫码、手机/异浏览器跳转、真实付款与到账；平台审核与上架；约 2.4MB 包的平台接受情况。
- 用户机器上的实际 CPU/内存表现只在开发机合成样本计时，未实测；本轮未运行 GB 级展开样本。

## 部署与回滚

- 部署：无（fast 车道，无后端改动、无迁移、无重启）。负责人在 A3 通过后手动上传 1.0.2 ZIP；logo 为 `dist/logo.png`。
- 回滚：1.0.0/1.0.1 均未上传；不上传或平台下架即可，无数据迁移。本机状态无新字段；401 作废凭证后下次自动沿原安装身份重领。

## 退回意见

无。

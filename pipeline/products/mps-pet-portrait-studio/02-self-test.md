# 自测报告：mps-pet-portrait-studio 1.0.1

修复轮（1.0.0 → 1.0.1），按 SOP 〇章第 4 条不重读 WorkBuddy 官方文档快照；frontmatter 结构与 1.0.0 相同，只改 `version`。

- 时间：2026-11-09T19:43:07+08:00，Claude 定时运行，修复轮（认领通知 `evt-121583ec…`（test_failed）与 Muse 交接 `evt-cc1cc93b…`）
- 依据：`03-test-report.md`（A3 退回 A3-PET-01/02/03，固定于 `aa95c62fc3d8f0bde74e7a014e2c4ec331bf8e08`）、`msg-from-muse-20261109-fix-no-repeat.md`（`b70238771d2430093257744cb20d5b0a713c842f`）
- 规格：`01-dev-spec.md` / `01-dev-spec.json` 1.0.0，固定于 `9c2388c135597d5b632a73b7998561a719c9d6de`，**本轮未改规格**（理由见下方「规格核对」）
- 渠道：只做 `workbuddy-skill`（`pipeline/config.yaml` channels）
- 旧包保留：`02-package/dist/mps-pet-portrait-studio-1.0.0.zip` 未改动
- **A2 结论：通过，置 package_ready。**
- 交付包：`02-package/dist/mps-pet-portrait-studio-1.0.1.zip`，1024515 字节，24 个文件，最多两级，SHA256 `26c3ad64f64a22e3515854e17e1c1a0f9893b67db8a36cbe77b064417b6597e0`
- 1.0.0 自测报告见提交 `8e4585ae7f3f9eb5d026aad241f917e70eb4b367` 中的本文件。

## 修复内容

| 退回项 | 修法（文件） |
|---|---|
| A3-PET-01 原任务结果未知时可丢失任务键 | `scripts/studio.py`：①发出生成 POST **之前**，先把原键与固定正文原子写入私有目录 `jobs/<键摘要>.json`（0600，目录 0700，临时文件 + `os.replace`），再把草稿原子置为 `submit_unknown`；进程在等待应答时中断，下次运行只走原键查询。②新增 `UNRESOLVED=('submit_unknown','submitted','download_pending')`：处于这些状态（或有未结束的 job_id）时，`plan` / `confirm` / `regenerate` 一律返回 `taskLocked`（退出 2，话术说明原任务与方案已保留），不清键、不换键、不改场景；`plan` 的锁检查移到改动草稿之前。③`run` / `resume` 遇到未定状态只调用 `_continue_job`：先 `GET /jobs/by-key/{原键}`；查到即沿原任务轮询/取图；**同一次运行内**查不到只报「当前进度未能确认」，不重发；仅在**新一次运行**且查询明确返回 404（此键下无任务）时，用**同一原键 + 已保存的固定正文**续接提交（不重读照片、不换键；服务端同键同体不重复扣费）。④409 不再当作「照片无法处理、没有扣次数」：先按原键查原任务，查到就续接交付；查不到返回 `jobConflict`（退出 2），话术「费用以服务记录为准」，原记录保留且仍锁定。⑤401/429 是明确未受理，回到 `confirmed` 保留原键；402 维持 `needs_credits` 同键续接；400/403/413/422 明确拒绝才置 `rejected` 并清理已保存正文。⑥已交付草稿再 `run` 返回 `alreadyDelivered`（附原链接），不再重复取图。 |
| A3-PET-02 截断 PNG 被宣告交付 | `scripts/png_local.py` 新增 `verify()`：签名、逐块长度越界与 CRC、IHDR 首块与合法参数、PLTE（调色板图）、IDAT 连续、IEND 存在、zlib 流完整结束且解压字节数与宽高/位深/隔行精确一致、逐行过滤类型合法。`scripts/studio.py` `_deliver`：先 `verify` 通过才写结果文件、画廊、交付标记；不通过则草稿置 `download_pending`（保留原任务与 job_id），返回 `downloadPending`（`image_incomplete=true`），用户说「继续」→ 只读 `GET /jobs/{id}/image` 补取同一张，不重新生成。实际尺寸也改由 `verify` 的结果判断。 |
| A3-PET-03 缺一张示例时仍返回成功 | `scripts/studio.py` `cmd_demo`：先核对请求范围（全量或单个 key）内每张示例文件都存在且为裸文件名，缺任何一张即 `demoUnavailable`、退出 3，并在信号里列出 `missing`；不复制残缺列表，不联网、不读凭证。单项请求只看该项。 |
| 版本 | `SKILL.md` / `_meta.json` / `studio.py` / `telemetry.py` / `tests/first-turn-preview.md` / `dev/build.py` → 1.0.1 |
| SKILL.md | 第 4 节新增两行信号说明：`taskLocked` / `jobConflict`（结果未定时不改方案、不重新确认或生成，「继续」只查原来这一张）、`alreadyDelivered`。SKILL.md 15049 字节（< 15 KB 契约上限）。对客文案无版本对比、无开发过程用语。 |

## 测试结果（2026-11-09）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 34/34 通过 |
| 端到端（仓库内包，打包前） | 63 项：61 通过，2 项跳过（尚无 ZIP） |
| 干净解压 ZIP 后契约测试 | 34/34 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 63/63 通过（含 ZIP 两级目录、frontmatter examples 校验） |
| ZIP 完整性 | `testzip` 无损坏；24 个文件；最大深度 2；不含 `__pycache__`、dev 目录、`demo-assets/` 原图 |
| 密钥扫描（产品目录） | 无命中 |

### 新增回归（`dev/e2e_check.py` 类 `RepairPetA3`，7 项）

| 编号 | 测试 | 复现与断言 | 结果 |
|---|---|---|---|
| PET-01-a | `test_pet_a3_01_interrupt_persists_key_and_body_before_post` | 两个子场景：POST 未到达服务端即中断 / 服务端已建单后中断（`KeyboardInterrupt`）。断言：草稿为 `submit_unknown`、原键不变；私有目录已存原键 + 六字段固定正文（POSIX 0600）；随后 `plan`（换场景换猫狗）、`confirm`、`regenerate` 均 `taskLocked` 退出 2，键/场景不变，零新 POST；`resume` 第一条请求是 `GET /jobs/by-key/原键`；已建单 → 0 次新 POST，未到达 → 1 次同键同体续接；两种情况都只扣 1 次 | 通过 |
| PET-01-b | `test_pet_a3_01_unknown_in_same_run_never_resends` | 同一次运行内提交应答丢失且原键查不到 → `jobPending` / `unconfirmed`，草稿保持 `submit_unknown`，零重发 | 通过 |
| PET-01-c | `test_pet_a3_01_409_queries_original_or_reports_conflict` | 409 + 原键查不到 → `jobConflict` 退出 2，含「费用以服务记录为准」、不含「没有扣次数」，最后一条请求是 by-key 查询，草稿与原键保留，再 `plan` 仍 `taskLocked`，零扣费；409 + 服务端已有该键任务 → 沿原任务交付，原键不变，只扣 1 次 | 通过 |
| PET-01-d | `test_pet_a3_01_photo_hash_binding_kept` | WED-A3-02 不回退：提交前换图仍 `photoChanged`、原键作废；结果未定时换图 → `confirm` 被锁、原键与状态不变；续接提交的照片正文是确认时那一张，不重读新文件 | 通过 |
| PET-02-a | `test_pet_a3_02_truncated_png_not_delivered` | 取图依次返回前 33 字节（签名 + IHDR）、一半、去掉 IEND → 三次都 `downloadPending` 退出 2、草稿 `download_pending`、结果目录无 PNG 和 `index.html`；之后正常补取 → `delivered`，零新 POST，只扣 1 次，交付文件通过 `verify` | 通过 |
| PET-02-b | `test_pet_a3_02_verify_rejects_corruption` | `verify` 拒绝 33 字节、缺 IEND、少 1 字节、CRC 被改、非 PNG；包内 10 张示例（调色板 PNG）全部通过 | 通过 |
| PET-03 | `test_pet_a3_03_one_missing_exit3_offline` | 隔离复制 `assets/`（目录名含空格），删 `cartoon.png`，网络与凭证读取换成抛异常函数：全量 `demo` → `demoUnavailable` 退出 3、`missing=['cartoon']`；`demo cartoon` → 退出 3；`demo explorer` → 正常返回 1 项；未生成 `account.json` | 通过 |

原有回归全部保留并通过：`test_submit_lost_queries_original_not_resubmit`、`test_5xx_not_retried`、`test_rate_limited_keeps_task_same_key`（429 后同键续接）、`test_replay_same_key_charged_once`、`test_download_fail_keeps_task`、`test_demo_missing_assets_exit3`、`test_wed_a3_0{1,2,3}_*` 等。

## 前两个产品错误逐项复核（Muse 交接要求）

| 历史缺陷 | 本版状态 | 证据 |
|---|---|---|
| A3-E01 examples 中英文义不一致 | 未回退：frontmatter 只改 version；三组仍为猫皇家油画竖版 2:3 / 狗卡通头像方形 1:1 / 猫海边度假横版 3:2 | 契约 `test_examples_zh_en_same_scene`、`test_examples_alignment_detects_misalignment`、`test_examples_match_spec_scenes`；ZIP 内 `ZipLayout.test_zip_skill_examples_platform_limits` |
| A3-E02 示例路径含空格 | 未回退：demo/成品/画廊链接经 `md_safe_path` 编码 `%20` | E `test_demo_links_survive_markdown`（家目录含 `test user`）、`test_wed_a3_03_delivery_links_space_and_hash`（`my photos`）；C `test_demo_link_path_with_space`；PET-03 回归的副本目录也含空格 |
| A3-E03 示例目录名含 # | 未回退：`#` 编码 `%23`，按 URI 规则拆片段后仍指向存在文件 | E 同上（`Synthetic#User`、`Synthetic#Album`）；C `test_demo_link_path_with_hash` |
| WED-A3-01 demo 先触发网络上报 | 未回退：`cmd_demo` 仍不调用遥测、不联网、不读凭证；新增缺图分支同样离线 | E `test_wed_a3_01_demo_alone_zero_network`、PET-03 回归（网络/凭证换抛异常函数） |
| WED-A3-02 换图后旧确认与原键仍可提交 | 未回退：提交前换图仍作废两项同意与原键；新增「结果未定时锁定」不经过 `_photo_changed` 清键 | E `test_wed_a3_02_photo_replaced_after_confirm`、`test_wed_a3_02_photo_replaced_between_plan_and_confirm`、PET-01-d |
| WED-A3-03 成品/画廊链接未用安全路径 | 未回退：交付、画廊、新增 `alreadyDelivered` 的链接都走 `md_safe_path` | E `test_wed_a3_03_delivery_links_space_and_hash` |

## 规格核对（为何未改 01-dev-spec.md）

- SOP A.1 规定 Claude Code 不改开发文档；Muse 交接第 4 条只在「规格本身需要改」时才要求改，本轮实现均落在规格已写的行为内，无需改：
  - 规格第 5 节「提交前……把原键和正文原子保存」「网络异常或 5xx 先按原键和原任务 ID 查进度……不自动重发生成或换键」「409 查询原任务或显示同键冲突」「仅在后端明确判定为未提交/未扣的可恢复状态时按同键续接」→ PET-01 修法。
  - 「仅在保存并校验 PNG 后宣布交付」「已成功但取图断开，使用原任务图片 GET 续取」→ PET-02 修法。
  - 第 4 节「示例命令独立离线、不读凭证，缺资源退出 3」→ PET-03 修法。
- **请 A3 复核的解释项**：把 `GET /jobs/by-key/{原键}` 明确返回 404 视为规格所说「后端明确判定为未提交」，且只在新一次运行时以同一原键 + 已保存的同一正文续接（同一次运行内绝不重发）。若检查方认为 404 不足以判定，应退回规格明确，客户端改为只报进度未能确认即可（一处分支）。

## 未验证项

- WorkBuddy 真机行为验收与上架前零消耗验证：按负责人长期规则（2026-11-07）跳过，负责人上架前自测。
- 真实服务端对「同键同体」续接与 by-key 404 的实际语义：只在 Mock（按规格所列 `server.py` 行为建模）上验证，真实上游调用 0。
- 真实照片的宠物身份保真、真实支付到账、平台审核：未验证。
- Windows 下私有目录权限只按「当前用户目录」处理，未在 Windows 实机验证 ACL。

## 观察（不阻塞，沿用 1.0.0）

- 规格第 8 节人像需求转「婚纱写真照相馆」，该技能目前 `submitted`；如其审核未通过，下一版需去掉转介。

## 部署与回滚

- 部署：无（fast 车道，无后端改动）。上传由负责人手动完成。
- 回滚：1.0.0 ZIP 原样保留在 `dist/`；1.0.1 有问题时改传 1.0.0 即可（但 1.0.0 含上述三项已知缺陷）。

真实上游调用（本次 Claude）：0。真实上报：0（全部走模拟传输）。生产变更：0。

# 自测报告：mps-pet-portrait-studio 1.0.2

修复轮（1.0.1 → 1.0.2），按 SOP 〇章第 4 条不重读 WorkBuddy 官方文档快照；frontmatter 结构与 1.0.1 相同，只改 `version`。

- 时间：2026-11-09T21:55+08:00，Claude 定时运行，修复轮（认领通知 `evt-756ae968…`（test_failed，dev 第 3 轮））
- 依据：`03-test-report.md`（1.0.1 A3 复查退回 A3-PET-01 的 404/401 边界、A3-PET-02 的隔行过滤/坏压缩流，固定于 `fa58f74efe4c550629831af4691bf79212dbc644`）
- 规格：`01-dev-spec.md` / `01-dev-spec.json`，固定于 `9c2388c135597d5b632a73b7998561a719c9d6de`，**本轮未改规格**
- 渠道：只做 `workbuddy-skill`（`pipeline/config.yaml` channels）
- 旧包保留：`02-package/dist/` 下 1.0.0、1.0.1 ZIP 未改动（1.0.1 SHA256 仍为 `26c3ad64…97e0`）
- **A2 结论：通过，置 package_ready。**
- 交付包：`02-package/dist/mps-pet-portrait-studio-1.0.2.zip`，1024840 字节，24 个文件，最多两级，SHA256 `67799fb6236a42cbcec564f6e989e17b5bf7c6e8a4f9c81beb025eed9b23d4ab`
- 1.0.1 自测报告见提交 `1c483935c80518776ee350cafb81843c40d43f43` 中的本文件。

## 修复内容

| 退回项 | 修法（文件） |
|---|---|
| A3-PET-01 复现一：原键查询 404 后仍发 POST | `scripts/studio.py` `_continue_job`：**删除** 1.0.1 的「新一次运行 + 404 → 同键同体续接」分支（`allow_resend` 参数一并移除）。按固定后端 `shared_platform.py:442-451`，by-key 404 只表示「当前未查到，请保留任务等待核查」，不是「明确未受理且未扣」。现在结果未定的草稿无论查询结果如何都只做只读查询：查到 → 沿原任务轮询/取图；404/网络/5xx → `jobPending`（`progress=unconfirmed`），草稿保持 `submit_unknown`，原键与已保存固定正文保留，`plan`/`confirm`/`regenerate` 继续 `taskLocked`。同键续接只保留在提交当下**明确未受理**的应答上（401/429 → `confirmed`；402 → `needs_credits`），与 1.0.1 相同。 |
| A3-PET-01 复现二：原键查询 401 时反复用同一过期凭证 | `scripts/studio.py` 新增 `_query()`：原键查询、任务轮询、原任务取图三处统一走它。返回 401 且用的是缓存 Skill 凭证时：清掉该凭证并落盘 → 用原安装身份（`install_secret`）调用 `/skill-key` 换取凭证（失败则直接用原安装身份）→ 再查一次原键；仍 401 则返回 `credentialsReset`（退出 4），**不清任务、不换键、不重发**，每次最多两次查询。取图 401 也走同一路径并保持 `download_pending`。 |
| A3-PET-02 隔行图非法过滤字节被交付 | `scripts/png_local.py`：过滤类型核对改为按子图逐行进行——非隔行为整图，Adam7 为七个子图各自宽高与行宽；任一行过滤字节 > 4 即拒绝，且逐行累计字节数须等于应有总量。 |
| A3-PET-02 坏 zlib 流抛未处理 `zlib.error` | `scripts/png_local.py`：`verify()` 改为外壳，内部解析中的 `zlib.error`/`struct.error`/`IndexError` 等一律转为 `ValueError`；`scripts/studio.py` `_deliver` 对校验的任何异常都按不可解码处理 → `download_pending` + `downloadPending`（`image_incomplete=true`），不写结果文件、不更新画廊，「继续」只读补取同一张。 |
| 版本 | `SKILL.md` / `_meta.json` / `studio.py` / `telemetry.py` / `tests/first-turn-preview.md` / `dev/build.py` → 1.0.2 |

SKILL.md 正文未改（只改 version），对客话术未改。

## 复现确认（修复前）

- 用 1.0.1 的 `png_local.py`（取自固定提交）跑复查报告的两个构造样本：1×1 Adam7 RGB、过滤字节 5 → **接受**并返回 (1,1)；非法 zlib 流 → 抛 `zlib.error`。与 A3 复现一致。
- 1.0.1 的 `_continue_job` 在 `allow_resend=True` 且 by-key 404 时调用 `_submit`（源码可见），与 A3 复现一致；401 分支直接返回 `jobPending` 不清凭证，与复现二一致。

## 测试结果（2026-11-09）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 34/34 通过 |
| 端到端（仓库内包，打包前） | 68 项：66 通过，2 项跳过（未传 ZIP） |
| 干净解压 ZIP 后契约测试 | 34/34 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 68/68 通过（含 ZIP 两级目录、frontmatter examples 校验） |
| ZIP 完整性 | `testzip` 无损坏；24 个文件；最大深度 2；不含 `__pycache__`、dev 目录、`demo-assets/` 原图 |
| 密钥扫描（产品目录） | 无命中 |

### 本轮新增/调整的回归（`dev/e2e_check.py` 类 `RepairPetA3`）

| 编号 | 测试 | 复现与断言 | 结果 |
|---|---|---|---|
| PET-01-e（新） | `test_pet_a3_01_resume_404_never_posts` | POST 未到达即中断 → 草稿 `submit_unknown`；连续两次 `resume`、再一次 `run`：每次除 `/quick-entry` 外只有 `GET /jobs/by-key/原键`，返回 `jobPending`/`unconfirmed`（退出 2，含「当前进度未能确认」）；原键、状态、已保存六字段正文不变；POST 数与扣费不变；随后 `plan` 仍 `taskLocked` | 通过 |
| PET-01-f（新） | `test_pet_a3_01_resume_401_recovers_from_install` | 服务端已建单后中断，再让服务端作废缓存 Skill 凭证：`resume` 第一次 by-key 用旧凭证得 401 → 调 `/skill-key` 从原安装恢复 → 第二次 by-key 用新凭证查到原任务并交付；账户里不再是旧凭证；原键不变；零新 POST、零新增扣费 | 通过 |
| PET-01-g（新） | `test_pet_a3_01_resume_401_persistent_keeps_task` | 原键查询持续 401：两次 `resume` 都返回 `credentialsReset`（退出 4），每次正好两次查询且第二次不再用旧凭证；草稿 `submit_unknown`、原键与正文保留；零 POST；恢复正常后 `resume` 查原任务交付，总扣费仍只有 1 次（含前置草稿） | 通过 |
| PET-01-a（调整） | `test_pet_a3_01_interrupt_persists_key_and_body_before_post` | 原断言「未到达 → 1 次同键续接」改为「未到达 → 零 POST、`jobPending`、原键/正文保留、零扣费」；已建单分支仍 → 零 POST 交付、只扣 1 次 | 通过 |
| PET-01-d（调整） | `test_pet_a3_01_photo_hash_binding_kept` | 未定任务改为「服务端已建单后中断」场景（不再依赖 404 续接）：换图后 `confirm` 被锁，`resume` 零新 POST 交付，原键不变，服务端收到的照片正文是确认时那一张 | 通过 |
| PET-02-c（新） | `test_pet_a3_02_interlaced_bad_filter_and_bad_zlib` | 1×1 Adam7 RGB 过滤字节 0 → 通过；过滤字节 5 → `ValueError`；CRC 正确的非法 zlib 流 → `ValueError`（非 `zlib.error`）；8×8 Adam7 七子图合法样本通过，第四子图首行过滤字节改 7 → `ValueError` | 通过 |
| PET-02-d（新） | `test_pet_a3_02_undecodable_png_goes_download_pending` | 取图依次返回上面两个不可解码样本：两次都 `downloadPending`（退出 2，`image_incomplete=true`），草稿 `download_pending`，结果目录不存在或为空（无 PNG、无 `index.html`）；之后正常补取 → `delivered`，零新 POST，只扣 1 次 | 通过 |

1.0.1 的 PET-01-b/c、PET-02-a/b、PET-03 及其余原有回归全部保留并通过（含 `test_submit_lost_queries_original_not_resubmit`、`test_5xx_not_retried`、`test_rate_limited_keeps_task_same_key`、`test_replay_same_key_charged_once`、`test_download_fail_keeps_task`、`auth_expired_on_poll` 相关用例）。

## 前序历史缺陷复核

| 历史缺陷 | 本版状态 | 证据 |
|---|---|---|
| A3-E01 examples 中英文义不一致 | 未回退：frontmatter 只改 version | 契约 `test_examples_zh_en_same_scene` 等；ZIP 内 `ZipLayout.test_zip_skill_examples_platform_limits` |
| A3-E02 / A3-E03 路径含空格、# | 未回退：链接仍经 `md_safe_path` | E `test_demo_links_survive_markdown`、`test_wed_a3_03_delivery_links_space_and_hash`；C `test_demo_link_path_with_space/hash` |
| WED-A3-01 demo 联网 | 未回退：`cmd_demo` 未改 | E `test_wed_a3_01_demo_alone_zero_network`、PET-03 |
| WED-A3-02 换图后旧确认可提交 | 未回退 | E `test_wed_a3_02_*`、PET-01-d |
| WED-A3-03 成品链接不安全 | 未回退 | E `test_wed_a3_03_delivery_links_space_and_hash` |
| A3-PET-03 缺图仍成功 | 1.0.1 已关闭，未回退 | E `test_pet_a3_03_one_missing_exit3_offline` |

## 规格核对

- 未改开发文档（SOP A.1）。本轮修法均落在规格第 5 节原文内：「仅在后端明确判定为未提交/未扣的可恢复状态时按同键续接」「网络异常或 5xx 先按原键和原任务 ID 查进度……不自动重发生成或换键」「401 清失效的缓存凭证并从原安装恢复，保留任务」「仅在保存并校验 PNG 后宣布交付」。1.0.1 自测报告里「请 A3 复核的解释项」（把 404 当作明确未受理）已被 A3 否定，本版按 A3 意见改为只报进度未能确认。
- 行为影响说明：若提交请求确实从未到达服务端，草稿会一直停在「进度未能确认」并锁定，不会自动重发；用户可说「反馈问题」走既有工单核对，或开新草稿重新规划。这是规格「保留任务等待核查」的直接结果，未新增话术。

## 未验证项

- WorkBuddy 真机行为验收与上架前零消耗验证：按负责人长期规则（2026-11-07）跳过，负责人上架前自测。
- 真实服务端 by-key 404/401 的实际表现、`/skill-key` 在凭证作废后的重新签发：只在 Mock 上验证（按固定 `shared_platform.py` 行为建模），真实上游调用 0。
- 真实照片的宠物身份保真、真实支付到账、平台审核：未验证。
- Windows 下私有目录权限只按「当前用户目录」处理，未在 Windows 实机验证 ACL。

## 偏离开发文档的地方

无。

## 退回意见

无。

## 部署与回滚

- 部署：无（fast 车道，无后端改动）。上传由负责人手动完成。
- 回滚：1.0.0、1.0.1 ZIP 原样保留在 `dist/`；1.0.2 有问题时可改传 1.0.1（但 1.0.1 含本轮修复的两项已知缺陷）。

真实上游调用（本次 Claude）：0。真实上报：0（全部走模拟传输）。生产变更：0。

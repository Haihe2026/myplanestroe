# 自测报告：mps-id-photo-background 1.0.7（SOP 第七章付费转化整改）

## 交付三样

| 项 | 值 |
|---|---|
| 中文名字（display_name） | **证件照换底助手**（不变） |
| slug（SKILL.md name） | **mps-id-photo-background**（不变） |
| logo | **`pipeline/products/mps-id-photo-background/02-package/dist/mps-id-photo-background-avatar.png`**（未改动，512×512，9934 字节，SHA256 `9c0ed7ff5b5697a236a180276fad359aeb379b6d6384771739699926bdeaf930`） |
| 英文名（display_name_en） | ID Photo Background Assistant |
| 技能包 | `02-package/dist/mps-id-photo-background-1.0.7.zip`，893096 字节，24 个文件，最多两级，SHA256 `4cad79460a0d683a76d20f3fac477d351d71428025eb2397ed422ec84f6ed921` |

- 时间：2026-11-10T21:45:12+08:00，Claude 定时运行；承接 Muse 交接 `evt-bd6d1b3e…`（源 `pipeline/products/mps-id-photo-background/msg-from-muse-20261110-fix-107-pay-conversion.md`，通知 source_ref `09c735fe…` 是该文件的 blob 哈希，已用 `git hash-object` 核对与 main 上文件一致）。
- 依据：`docs/sop/sop-image-gen-skill-auto.md` 第七章（文件哈希 `f086414c…`，提交 `2f30b61`），与 Muse 指令一致。
- 升级轮，按 SOP 〇章第 4 条不重读官方文档快照。渠道只做 `workbuddy-skill`（config.yaml）。
- 只改客户端脚本、SKILL.md 和测试；不动后端、定价、套餐、0 次免费试用口径。
- 旧包保留：1.0.0–1.0.6 ZIP 未改动（1.0.6 SHA256 仍为 `1bf5b30d…`）。
- **A2 结论：通过，置 package_ready。**

## 改动（逐条对应 Muse 指令）

| 指令 | 改动 | 证据 |
|---|---|---|
| A1 `topup` 无账户死胡同 | `cmd_topup`：无安装标识时生成并持久化 `install_secret`，调 `POST /quick-entry`（入参 `install_secret`，无 Bearer）：`registration`→新信号 `linkAccount`（关联链接 + 「扫码确认后会直接进入充值页…关联本身不扣费」）；`checkout`→`topupLink`；`ready`→接上本机凭证后调 `POST /membership-link` 给充值链接；有标识但 `/membership-link` 返回 401（还没关联）也改走关联入口；断网→「网络暂时没连上，没有扣任何次数，稍后再说一次「充值」。」；链接全部经 `trusted_link` 校验，异常链接不转述 | E `PayConversion` 12 项 |
| A1 `balance` / `status`（及 `history`）无账户 | 同样走关联入口（新 helper `_account_entry`），不再回 `noAccount`；`balance`/`history` 遇 401 也走关联入口；`status` 无标识时 `checkout` 给最后一步充值链接、`ready` 报 `registered` | E `test_fresh_status_and_balance_have_way_out`、`test_fresh_history_gives_link`、`test_balance_menu_and_decline`、`test_history_failure_and_no_account`；C `test_failure_kind_by_status` |
| A2 失败原因不误报 | `_membership_link` 改为返回 (链接, 状态)；新增 `_fail_kind`：状态 0→`network`，非 0→`busy`。`cmd_topup`、`cmd_run` 的充值链接分支按状态传参；`_ensure_skill_key` 断网也返回 network；`balance`/`status` 已有标识时的查询失败也按状态说明 | E `test_fresh_topup_offline_honest`、`test_fresh_topup_server_busy`、`test_topup_membership_link_network_not_busy`、`test_run_needs_credits_link_failure_kind`、`test_fresh_status_offline` |
| A3 新测试 | 全新环境（无账户、无凭证）直接 `topup`：有可点链接（`/membership/gemini/register/`），断网时如实断网说明 | E `test_fresh_topup_gives_link_account`、`test_fresh_topup_offline_honest` |
| B1 接管规则 | 执行规范最前面加「### 零、接管规则（每一轮都适用）」，按 SOP 7.3.1 模板替换名词；账户命令/续接命令固定；转介婚纱写真照相馆（超出范围的人像写真，证件照换底本身不转介）；含禁止编造故障、禁止宿主自带生图、欢迎句逐字照写不加空格 | C `test_takeover_rules_first` |
| B2 description | 加「本技能也负责证件照换底助手的充值、付费链接、余额和订单查询。」；触发词加「证件照换底助手充值」（22→23 个）；末尾调用倾向句原样保留，全文只一句 | C `test_description_account_and_triggers`、`test_description_seo` |
| B3 技能收藏核对 | 不符处已改：「用户级（有项目级时也写项目级）」→「用户级、项目级各一条」；收藏内容补「以及证件照换底助手的充值、付费链接、余额和订单等问题」；选项写成「收藏 / 暂不」；「用户点『收藏』后」才写。其余（只在首次成功交付后问一次、每个对话最多一次、取消方法、不支持时如实说、不含个人信息、合规说明行）原已符合 | C `test_favorite_section` |
| B4 欢迎句 | SKILL.md 首轮第 1 步与接管规则都写「逐字照写，中文和英文之间不加空格」；`welcome_copy.WELCOME` 未动 | C `test_welcome_exact` |
| B5 隐藏注释 | SKILL.md、README.md 无 `<!--`（改完再扫一遍） | C `test_no_hidden_html_comment` |
| C1 版本 | `version: 1.0.7`：SKILL.md frontmatter、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、`dev/build.py`、`tests/first-turn-preview.md` 一致 | C 版本一致性测试；E ZIP 内 SKILL.md 版本检查 |

其他：
- SKILL.md 篇幅：加接管规则后超过 15KB 上限，压缩了执行规范第 1–6 节的重复说法（规则不删），现为 15344 字节（< 15360）。
- 授权话术原有「不用 API Key」（对客文字含 Key，违反 7.4），改为「也不用填写任何密钥」；新增契约 `test_customer_copy_no_site_or_key`。
- 新信号 `linkAccount`、`photoChanged` 已写进 SKILL.md；`noAccount` 现在只在查工单时出现。

## SOP 7.4 出包阻断项自检

| 检查项 | 结果 |
|---|---|
| 接管规则，含禁止编造故障、禁止宿主自带生图 | 通过（C `test_takeover_rules_first`） |
| 全新环境 `topup` 有链接或如实断网说明 | 通过（E `test_fresh_topup_gives_link_account` / `_offline_honest`） |
| description 末尾一句调用倾向句、触发词 15–25（23）、用户原话、账户类说法 | 通过 |
| 技能收藏章节 + 合规说明，收藏内容里技能 name 与 SKILL.md 一致 | 通过 |
| 无隐藏 HTML 注释 | 通过 |
| frontmatter 含 slug、version、显示名；name/slug 不改 | 通过：沿用已上架的官方字段写法 `name`（即 slug）、`display_name`、`version`，未改字段名 |
| 版本号大于平台最新版 | 1.0.7 > 1.0.6（log.md 记 1.0.6 为已发布版本；平台实时最新版本本环境查不到，见未验证项） |
| 专家包 tags | 不适用（只打技能包） |
| 首次对话上报字段与开关 | 通过：8 个白名单字段未变、版本随包 1.0.7、渠道 `workbuddy_skill`、`MPS_ID_PHOTO_JOURNEY=off` 可关（C/E 遥测测试） |
| 全包无旧口径；对客文字无网站名/Key/URL/接口/token | 通过（C `test_forbidden_words`、`test_customer_copy_no_site_or_key`、`test_no_slow_payment_wording`）。「同一账户的通用次数在已接入的技能间共享」是现行通用套餐口径，保留 |

## 测试结果（2026-11-10）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 34/34 通过（原 27 + 新增 7） |
| 端到端（仓库内包，带 `--zip`） | 69/69 通过（原 53 + PayConversion 12 + NoRepeat 4；其中 2 项原 noAccount 断言改为 linkAccount） |
| 干净解压 ZIP 后契约测试 | 34/34 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 69/69 通过，无跳过 |
| ZIP 完整性 | `testzip` 无损坏；24 个文件（与 1.0.6 清单相同）；最大深度 2；无 `__pycache__`、dev |
| 与 1.0.6 对比 | 变化的包内文件 7 个：SKILL.md、_meta.json、scripts/idphoto.py、telemetry.py、welcome_copy.py、tests/first-turn-preview.md、tests/test_skill_contract.py；`png_local.py`、`audit_images.py`、`references/`、`assets/`、README 字节一致 |
| 真实上游调用 | 0（端到端全部走 `dev/mock_backend.py`；本次没有对真实站点运行任何命令） |

## 修复不重犯（历史缺陷逐项复核，均在干净解压 ZIP 上通过）

| 历史缺陷 | 状态 | 证据 |
|---|---|---|
| A3-E01 中英示例逐条对齐（各 3 条、数量一致） | 未回退（examples 未改） | C `test_examples_zh_en_same_scene`；E `test_zip_skill_examples_platform_limits` |
| A3-E02 示例路径含空格 | 未回退 | C `test_demo_link_path_with_space`；E `test_demo_links_survive_markdown` |
| A3-E03 示例路径/目录名含 # | 未回退 | C `test_demo_link_path_with_hash` |
| WED-A3-01 demo 零网络 | 符合（新增测试：业务与遥测传输都换成触发即失败，单独 `demo` 与 `demo white-one` 均零网络） | E `test_wed_a3_01_demo_alone_zero_network` |
| WED-A3-02 照片哈希绑定，换图作废确认与原键 | **1.0.6 未做此绑定，本版补上**：`plan` 记照片 SHA256；`confirm` 与提交前核对，变了就返回 `photoChanged`、清空两项同意与原 Idempotency-Key，提交只发核对过的同一份字节；重新 plan+confirm 后用新键 | E `test_wed_a3_02_photo_changed_before_confirm`、`test_wed_a3_02_photo_changed_after_confirm` |
| WED-A3-03 成品/画廊 Markdown 链接 | **1.0.6 交付链接用原始路径，本版改用 `md_safe_path`**：交付话术链接与新字段 `links`、`gallery_link` 均为安全编码；显示名还原为原文件名 | E `test_wed_a3_03_delivery_links_space_and_hash`（含空格与含 # 的合成目录，三条链接解析后都指向存在的文件） |
| 包目录最多两级、示例在 `assets/`、`demos.json` 裸文件名、解压后无三级文件 | 未回退 | E `test_zip_dir_depth_at_most_two`；C 示例测试 |

## 偏离开发文档

- 账户命令无账户时改为返回 `linkAccount` 关联链接；换图返回 `photoChanged`。均为负责人指令整改（SOP 第七章、修复不重犯），`01-dev-spec` 未同步修改（规格未写这些细节，无矛盾）。
- `rounds.dev` 未加：负责人指令整改，不是测试退回。

## 未验证项

- 7.5 真机验收：按负责人 2026-11-10 定「豁免继续」，未做；Flash 小模型下接管规则是否被遵守只能由负责人实测确认。
- 平台上该 slug 实际最新版本（含审核中版本）：本环境查不到，由负责人上传时确认 1.0.7 大于平台最新版。
- 服务端 `/quick-entry` 真实返回格式：按脚本已在用的格式（与 `run`/`auth` 同一入口）对接，仅用模拟后端验证。
- 用 1.0.6 留下的旧草稿（没有照片哈希）续做时会返回 `photoChanged` 要求重新确认，属于保守处理，未在真机验证。

## 部署与回滚

- 部署：无服务端改动。走 Codex A3 独立检查（对 1.0.7 新包），通过后负责人手动上传 ZIP，附 logo、中文名、slug。
- 回滚：平台保留 1.0.6；仓库 `dist/` 中 1.0.6 ZIP 未改动，可直接重传。

---

# 以下为历史版本自测记录

# 自测报告：mps-id-photo-background 1.0.6（修复轮：示例目录名含 `#` 时链接断开）

- 角色：Claude Code；时间：2026-11-08T17:39:35+08:00（北京时间，定时运行）
- 官方文档：修复轮，未重读（SOP 〇节；Muse 请求第 4 条）。
- 依据：03-test-report.md A3-E03（Codex，2026-11-08T13:47:39+08:00）；Muse 请求 `msg-from-muse-20261108-fix-a3-e03.md`（通知 evt-015a3ba0，固定提交 76c33b4）：负责人 2026-11-08 17:25 批准超出 max_rounds 再走一轮，status 已由 Muse 置 dev_in_progress/owner=claude。规格未变，A1 沿用 1.0.2 复检结论。
- 包类型：只打 WorkBuddy 团队版技能包（`workbuddy-skill`，config `channels`）。
- 包文件（`02-package/dist/`）：
  - `mps-id-photo-background-1.0.6.zip`：889982 字节，SHA256 `1bf5b30d216bd12de31b91625fc892b8fcef3ac2198af45ac14eba344882ac23`，24 个文件，根目录 `mps-id-photo-background/`，最深 `根/二级目录/文件`，CRC 通过。
  - 1.0.5（`c51cd69b…`）及更早 ZIP 原样保留。头像未改动。

## 本轮改了什么

1. `scripts/idphoto.py` `md_safe_path()`：编码表新增 `#`→`%23`、`?`→`%3F`（`?` 同理会被当成查询串截断，一并处理）；其余规则不变（正斜杠、`%` 先编 `%25`、空格 `%20`、制表符、括号、尖括号）。例：`C:\Synthetic#User\mps-id-photo-background\demos\white-one.png` → `C:/Synthetic%23User/mps-id-photo-background/demos/white-one.png`。无这些字符的路径输出与 1.0.5 相同。
2. 示例目录名：包内示例目录为 `<状态目录>/mps-id-photo-background/demos/`，`assets/` 内文件名均为小写字母与连字符，本身不含 `#` 与空格（契约已有裸文件名检查）；A3-E03 的 `#` 来自用户家目录，靠路径函数编码解决。
3. `tests/test_skill_contract.py` 新增 `test_demo_link_path_with_hash`：按 A3-E03 检查方法（取 CommonMark 链接目标 → 拆 URI 片段与查询串 → 百分号解码）；原样 `#` 路径断言被截成 `C:/Synthetic`；修复后片段与查询串为空、解码路径完整；`a#b`、`q?x=1`、`m#n?o`、`Synthetic User (A) 50%#2` 逐个可逆；真实合成目录 `Synthetic#User` 与 `test user` 并列，解析后路径均指向存在的文件；markdown-it 生成的 href 同样拆片段后路径完整。原 `test_demo_link_path_with_space` 保留未改。
4. `dev/e2e_check.py` `test_demo_links_survive_markdown`：模拟家目录改为 `.dot-parent/test user/Synthetic#User`（空格与 `#` 并列），跑真实 `demo` 命令，十个链接逐一断言无 `#`/空格、拆片段与查询串后为空、解码路径文件存在。
5. 版本 1.0.5 → 1.0.6（SKILL.md、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、真机验收单、`dev/build.py`）。
6. **未改**：SKILL.md 正文与 frontmatter 其余字段（examples 中英各 3 条且逐条对齐）、空格编码、目录层级、授权与充值链接、规格、欢迎句、遥测、付费、话术、其他业务逻辑、后端、生产。

## 打包前 frontmatter 逐项核对（WorkBuddy 团队版技能包）

| 项 | 1.0.6 |
|---|---|
| 必填 8 字段 | 全部存在且非空；version=`1.0.6`，author=`MyPlaneStore` |
| 可选键 | 仅 `examples_zh`、`examples_en`（未改动） |
| examples_zh / examples_en | 3 / 3，逐条同一场景（契约语义对齐检查通过） |
| 版本号一致 | SKILL.md、`_meta.json`、脚本两处、ZIP 文件名一致 |
| 目录层级 | ZIP 内路径 `/` 数 ≤ 2 |

## 结果

| 项 | 结果 |
|---|---|
| 契约测试（源码） | 27/27 通过 |
| 端到端（模拟后端，源码） | 53/53 通过（2 项 ZIP 检查在打包前跳过） |
| 干净解压 1.0.6 ZIP 至含空格与 `#` 的目录 `clean dir#1/` 后契约（`python3 -I`） | 27/27 通过 |
| 干净解压后端到端（`--package <该解压目录> --zip dist/…-1.0.6.zip`） | 53/53 通过 |
| 回归有效性：1.0.5 解压包 + 新契约测试 | `test_demo_link_path_with_hash` 失败（未编码 `#`），其余 26 项通过 |
| 回归有效性：1.0.5 解压包跑新端到端 | `test_demo_links_survive_markdown` 失败，其余通过 |
| ZIP 密钥类特征扫描 | 无命中 |
| 真实上游调用 / 真实上报 / 生产变更 | 0 / 0 / 0 |

## 偏离与未验证

- 未在 Windows 真机、PowerShell `ConvertFrom-Markdown` 与 WorkBuddy 宿主里点开 `%23` 链接验证；本轮按 A3-E03 同一拆片段+解码方法在 Linux 用 CommonMark 规则与 markdown-it 验证。宿主对本地文件链接是否百分号解码未验证（负责人上架前自测）。
- 平台上传解析未验证（负责人手动上传）。真机验收按负责人长期规则跳过。
- rounds.test 本轮未由 Claude 改动（Codex 检查时计数）；超出 max_rounds 已获负责人批准（见 Muse 请求）。

## 部署与回滚

- 部署：无后端改动；A3 通过后由负责人手动上传 `mps-id-photo-background-1.0.6.zip`。
- 回滚：dist 内 1.0.5 及更早 ZIP 原样保留；1.0.5 仅在路径含 `#` 时示例链接失效，可作回滚版本。

## 复跑

```sh
cd 02-package/mps-id-photo-background && python3 -I tests/test_skill_contract.py        # 契约 27 项
cd 02-package && python3 dev/e2e_check.py --zip dist/mps-id-photo-background-1.0.6.zip
```

---

# 自测报告：mps-id-photo-background 1.0.5（修复轮：示例图路径含空格时链接无法解析）

- 角色：Claude Code；时间：2026-11-08T13:40:31+08:00（北京时间，定时运行）
- 官方文档：修复轮，未重读（SOP 〇节）。
- 依据：03-test-report.md A3-E02（Codex，2026-11-08T12:46:22+08:00，通知 evt-4d09f24e，固定提交 3ade6f2）。规格未变，A1 沿用 1.0.2 复检结论，不重做。rounds.test=3 未超过 max_rounds=3，按修复轮继续。
- 包类型：只打 WorkBuddy 团队版技能包（`workbuddy-skill`，config `channels`）。
- 包文件（`02-package/dist/`）：
  - `mps-id-photo-background-1.0.5.zip`：889405 字节，SHA256 `c51cd69baaa70fd56ba455c459dd1067ed5713ea38fdac21d38d1bda8fad7707`，24 个文件，根目录 `mps-id-photo-background/`，最深 `根/二级目录/文件`，CRC 通过。
  - 1.0.4（`0d1c0fbd…`）、1.0.3、1.0.2、1.0.1、1.0.0 ZIP 原样保留。头像未改动。

## 本轮改了什么

1. `scripts/idphoto.py` `md_safe_path()`：仍转正斜杠；另对 Markdown 链接目标中会断链的字符做 URL 编码——空格→`%20`、制表符→`%09`、`(`/`)`→`%28`/`%29`、`<`/`>`→`%3C`/`%3E`，先把 `%` 编为 `%25` 保证可逆。例：`C:\test user\mps-id-photo-background\demos\white-one.png` → `C:/test%20user/mps-id-photo-background/demos/white-one.png`。无这些字符的路径输出与 1.0.4 完全相同。
2. `tests/test_skill_contract.py` 新增 `test_demo_link_path_with_space`：含空格的合成 Windows 路径（ntpath 规则）；原样空格路径断言不构成链接；修复后 CommonMark 目标提取与输出一致；括号、尖括号、`%`、制表符逐个可逆；真实含空格合成目录中的文件，解析目标解码后存在；markdown-it 可用时断言修复后生成 `<a>`、原样空格路径不生成。
3. `dev/e2e_check.py` `test_demo_links_survive_markdown`：模拟家目录改为含空格的 `.dot-parent/test user`，跑真实 `demo` 命令，十个链接逐一断言：无反斜杠、无空格、CommonMark 目标与输出一致、markdown-it href 解码一致、解码后文件存在。
4. 版本 1.0.4 → 1.0.5（SKILL.md、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、真机验收单、`dev/build.py`）。
5. **未改**：SKILL.md 正文与 frontmatter 其余字段（examples 中英各 3 条且逐条对齐）、目录层级、授权与充值链接、规格、欢迎句、遥测、付费、话术、其他业务逻辑、后端、生产。

## 打包前 frontmatter 逐项核对（WorkBuddy 团队版技能包）

| 项 | 1.0.5 |
|---|---|
| 必填 8 字段 | 全部存在且非空；version=`1.0.5`，author=`MyPlaneStore` |
| 可选键 | 仅 `examples_zh`、`examples_en`（未改动） |
| examples_zh / examples_en | 3 / 3，逐条同一场景（契约语义对齐检查通过） |
| 版本号一致 | SKILL.md、`_meta.json`、脚本两处、ZIP 文件名一致 |
| 目录层级 | ZIP 内路径 `/` 数 ≤ 2 |

## 结果

| 项 | 结果 |
|---|---|
| 契约测试（源码） | 26/26 通过 |
| 端到端（模拟后端，源码） | 53/53 通过（2 项 ZIP 检查在打包前跳过） |
| 干净解压 1.0.5 ZIP 至含空格目录 `clean dir/` 后契约（`python3 -I`） | 26/26 通过 |
| 干净解压后端到端（`--package <含空格的解压目录> --zip dist/…-1.0.5.zip`） | 53/53 通过 |
| 回归有效性：1.0.4 包代码 + 新契约测试 `test_demo_link_path_with_space` | 失败（输出 `C:/test user/…`，未编码） |
| 回归有效性：1.0.4 解压包跑 `test_demo_links_survive_markdown` | 失败（含空格路径无法提取链接目标） |
| ZIP 密钥类特征扫描 | 无命中 |
| 真实上游调用 / 真实上报 / 生产变更 | 0 / 0 / 0 |

## 偏离与未验证

- 未在 Windows 真机与 WorkBuddy 宿主里点开 `%20` 链接验证；依据 CommonMark 规范与 markdown-it 解析结果，宿主是否对本地文件链接做百分号解码未验证（负责人上架前自测）。
- 平台上传解析未验证（负责人手动上传）。真机验收按负责人长期规则跳过。
- 授权链接改通用地址仍未做，理由同 1.0.1（见 `reply-from-claude-20261107.md`）。

## 部署与回滚

- 部署：无后端改动；A3 通过后由负责人手动上传 `mps-id-photo-background-1.0.5.zip`。
- 回滚：dist 内 1.0.4 及更早 ZIP 原样保留；1.0.4 仅在路径含空格时示例链接失效，可作为回滚版本。

## 复跑

```sh
cd 02-package/mps-id-photo-background && python3 -m unittest discover -s tests        # 契约 26 项
cd 02-package && python3 dev/e2e_check.py --zip dist/mps-id-photo-background-1.0.5.zip
```

---

# 自测报告：mps-id-photo-background 1.0.4（修复轮：中英示例场景未对齐）

- 角色：Claude Code；时间：2026-11-08T12:40:13+08:00（北京时间，定时运行）
- 官方文档：修复轮，未重读（SOP 〇节）。
- 依据：03-test-report.md A3-E01（Codex，2026-11-08T12:23:23+08:00，通知 evt-f7090d9b，固定提交 c28d96b）。规格未变，A1 沿用 1.0.2 复检结论，不重做。
- 包类型：只打 WorkBuddy 团队版技能包（`workbuddy-skill`，config `channels`）。
- 包文件（`02-package/dist/`）：
  - `mps-id-photo-background-1.0.4.zip`：888820 字节，SHA256 `0d1c0fbd172a521b1345404f0db76ba97ab6c0d734f43479ec8114f931be6f51`，24 个文件，根目录 `mps-id-photo-background/`，最深 `根/二级目录/文件`，CRC 通过。
  - 1.0.3（`f2903f5a…`）、1.0.2、1.0.1、1.0.0 ZIP 原样保留。头像未改动。

## 本轮改了什么

1. SKILL.md `examples_en` 三条改为与中文逐条同义（中文未改，仍 3 条，数量一致）：
   - [0] 白底一寸·明天报名 → "Make this a white background one-inch photo, I need it for an application tomorrow"（原英文缺「一寸」）
   - [1] 考试报名·蓝底二寸 → "I need a blue background two-inch photo for my exam application, I'll send the photo"（原英文为 295×413 像素，对应 custom-pixels，A3-E01）
   - [2] 简历换白 → "My resume photo background is too busy, change it to plain white"
2. `tests/test_skill_contract.py`：新增 `example_signature` / `example_misaligned`，按 references/scenes.md 的路由维度（底色、一寸/二寸、像素、简历、考试、报名）抽取中英特征逐条比较；新增 `test_examples_zh_en_same_scene`（当前包必须对齐）和 `test_examples_alignment_detects_103_regression`（1.0.3 英文示例必须被判为第 2 条不对齐）。
3. `dev/e2e_check.py` `test_zip_skill_examples_platform_limits`：对 ZIP 内 SKILL.md 同样做中英语义对齐检查。
4. 版本 1.0.3 → 1.0.4（SKILL.md、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、真机验收单、`dev/build.py`）。
5. **未改**：examples 三条数量、渠道、目录层级、Markdown 回归、授权与充值链接、规格、欢迎句、遥测、付费、话术、业务脚本逻辑、后端、生产。

## 打包前 frontmatter 逐项核对（WorkBuddy 团队版技能包）

| 项 | 1.0.4 |
|---|---|
| 必填 8 字段 | 全部存在且非空；version=`1.0.4`，author=`MyPlaneStore` |
| 可选键 | 仅 `examples_zh`、`examples_en` |
| examples_zh / examples_en | 3 / 3，逐条同一场景（white-one / blue-two / resume-white），对齐检查 0 处不一致 |
| 版本号一致 | SKILL.md、`_meta.json`、脚本两处、ZIP 文件名一致 |
| 目录层级 | ZIP 内路径 `/` 数 ≤ 2 |

## 结果

| 项 | 结果 |
|---|---|
| 契约测试（源码） | 25/25 通过 |
| 端到端（模拟后端，源码） | 53/53 通过（2 项 ZIP 检查在打包前跳过，打包后用 --zip 跑） |
| 干净解压 1.0.4 ZIP 后契约（`python3 -I`） | 25/25 通过 |
| 干净解压后端到端（`--package <解压目录> --zip dist/…-1.0.4.zip`） | 53/53 通过 |
| 回归有效性：对 1.0.3 ZIP 内 SKILL.md 跑 `example_misaligned` | 返回 [0, 1]（能测出 A3-E01 的第 2 条，另检出第 1 条缺「一寸」） |
| 回归有效性：`--zip …-1.0.3.zip` | `test_zip_skill_examples_platform_limits` 失败 |
| ZIP 密钥类特征扫描 | 无命中 |
| 真实上游调用 / 真实上报 / 生产变更 | 0 / 0 / 0 |

## 偏离与未验证

- 平台上传解析未验证（负责人手动上传）。语义对齐检查是基于场景路由维度的关键词规则，不是翻译质量评估。
- 真机验收按负责人长期规则跳过，未做。
- 授权链接改通用地址仍未做，理由同 1.0.1（见 `reply-from-claude-20261107.md`）。

## 部署与回滚

- 部署：无后端改动；A3 通过后由负责人手动上传 `mps-id-photo-background-1.0.4.zip`。
- 回滚：dist 内 1.0.3 及更早 ZIP 原样保留；1.0.3 中英示例不对齐、1.0.2/1.0.1 已被平台拒收，均不建议作为上传回滚版本。

## 复跑

```sh
cd 02-package/mps-id-photo-background && python3 -m unittest discover -s tests        # 契约 25 项
cd 02-package && python3 dev/e2e_check.py --zip dist/mps-id-photo-background-1.0.4.zip
```

---

# 自测报告：mps-id-photo-background 1.0.3（修复轮：examples 数量超限）

- 角色：Claude Code；时间：2026-11-08T00:40:27+08:00（北京时间，定时运行）
- 官方文档：修复轮，未重读（SOP 〇节第 2、4 条）。
- 依据：msg-from-muse-20261108-examples-fix.md（提交 e54cde4）、SOP〇节「技能包 examples 上限」（ec88ad7）。规格未变，A1 沿用 1.0.2 复检结论，不重做。
- 包类型：只打 WorkBuddy 团队版技能包（`workbuddy-skill`，config `channels`），不打专家包/SkillHub 包。
- 包文件（`02-package/dist/`）：
  - `mps-id-photo-background-1.0.3.zip`：887886 字节，SHA256 `f2903f5a9bb01cd64ab8cfbed9fef2a95e94d13d1c22db9f0a370f479e131e57`，24 个文件，根目录 `mps-id-photo-background/`，最深 `根/二级目录/文件`。
  - 1.0.2（`4ac1a7d5…`）、1.0.1（`80e4ec13…`）、1.0.0（`f187e418…`）ZIP 原样保留。头像未改动。

## 本轮改了什么

1. SKILL.md frontmatter：删掉第 3 条中文示例「一寸蓝底，像素要295×413，报名系统卡这个」；`examples_zh` 与 `examples_en` 各 3 条（白底报名／蓝底二寸／简历换白），数量一致。`295×413` 仍保留在 description 触发词与正文中。
2. `tests/test_skill_contract.py`：新增 `test_frontmatter_platform_parse_rules`——按最小 YAML 子集解析 frontmatter（重复键、无法解析的行直接报错），断言 8 个必填字段非空、无平台未列出的键（仅允许必填 + `allowed-tools`、`examples_zh`、`examples_en`）、version 为 x.y.z、`examples_zh` 1–3 条、`examples_en` ≤3 条、两者数量相等、无空条和重复条；旧断言「中文示例 4 条」删除。
3. `dev/e2e_check.py`：新增 `ZipLayout.test_zip_skill_examples_platform_limits`——直接读 ZIP 内的 SKILL.md，断言 examples 中英各 ≤3 且数量一致、version 与脚本一致（防止源码改了但 ZIP 没重打）。
4. 版本 1.0.2 → 1.0.3（SKILL.md、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、真机验收单、`dev/build.py`）。
5. **未改**：目录层级修复（示例图在 `assets/` 下、最深两级）与 Markdown 回归测试保留；授权与充值链接、规格、欢迎句、遥测、付费、话术、后端、生产均未动。

## 打包前 frontmatter 逐项核对（WorkBuddy 团队版技能包）

| 项 | 1.0.3 |
|---|---|
| 必填 name / display_name / display_name_en / description / description_zh / description_en / version / author | 全部存在且非空；name=`mps-id-photo-background`，version=`1.0.3`，author=`MyPlaneStore` |
| 可选键 | 仅 `examples_zh`、`examples_en`，无其他未列出键 |
| examples_zh / examples_en | 3 / 3，数量一致，按主题一一对应 |
| 版本号一致 | SKILL.md、`_meta.json`、脚本两处、ZIP 文件名一致 |
| 目录层级 | ZIP 内路径 `/` 数 ≤ 2 |

## 结果

| 项 | 结果 |
|---|---|
| 契约测试（源码） | 23/23 通过 |
| 端到端（模拟后端，源码，含 1.0.3 ZIP 层级与 examples 检查） | 53/53 通过 |
| 干净解压 1.0.3 ZIP 后契约（`python3 -I`） | 23/23 通过 |
| 干净解压后端到端（`--package <解压目录> --zip dist/…-1.0.3.zip`） | 53/53 通过 |
| 回归测试有效性：对 1.0.2 ZIP 跑 `--zip …-1.0.2.zip ZipLayout` | `test_zip_skill_examples_platform_limits` 失败（中文 4 条，能测出） |
| 回归测试有效性：1.0.2 干净解压目录放入新契约测试跑 `-k platform_parse` | 失败「4 not less than or equal to 3」（能测出） |
| ZIP 密钥类特征扫描 | 无命中 |
| 真实上游调用 / 真实上报 / 生产变更 | 0 / 0 / 0（测试全程 `MPS_ID_PHOTO_JOURNEY=off`、`MPS_ID_PHOTO_TEST=1`） |

## 偏离与未验证

- 平台上传解析未验证（上传由负责人手动）；examples 规则按平台报错原文与 SOP ec88ad7 实现。官方文档未写的其他解析限制（字段长度等）无法在此验证。
- 真机验收按负责人长期规则跳过，未做。
- 授权链接改通用地址仍未做，理由同 1.0.1（见 `reply-from-claude-20261107.md`）。

## 部署与回滚

- 部署：无后端改动；Codex 复测通过后由负责人手动上传 `mps-id-photo-background-1.0.3.zip`。
- 回滚：dist 内 1.0.2/1.0.1/1.0.0 ZIP 原样保留；1.0.2、1.0.1 已被平台拒收，不能作为上传回滚版本。

## 复跑

```sh
cd 02-package/mps-id-photo-background && python3 -m unittest discover -s tests        # 契约 23 项
cd 02-package && python3 dev/e2e_check.py                                              # 端到端 53 项（含 dist 当前版本 ZIP 检查）
python3 dev/e2e_check.py --package <干净解压后的 mps-id-photo-background 目录> --zip <ZIP 路径>
```

---

# 自测报告：mps-id-photo-background 1.0.2（修复轮：包目录层级超限）

- 角色：Claude Code；时间：2026-11-07T23:42:41+08:00（北京时间，定时运行）
- 官方文档：修复轮，未重读（负责人 2026-11-07 新规则，SOP bb1ce4e 〇节第 2、4 条）。
- 依据：msg-from-muse-20261107-fix-dir-depth.md、msg-from-muse-20261107-docs-rule.md（提交 40e8cd7）、SOP「包目录结构最多两级」（97a663b）。规格未变，A1 沿用 1.0.2 复检结论，不重做。
- 包文件（`02-package/dist/`，只打 workbuddy-skill）：
  - `mps-id-photo-background-1.0.2.zip`：887236 字节，SHA256 `4ac1a7d5c266c35d7d76f0b3dc55cbc9c20cca56e2752ab48ac51f14f56673dc`，24 个文件，根目录 `mps-id-photo-background/`，最深路径为 `根/二级目录/文件`。
  - 1.0.1（`80e4ec13…`）、1.0.0（`f187e418…`）ZIP 原样保留。头像未改动。

## 本轮改了什么

1. 10 张示例图从 `assets/demos/` 平移到 `assets/`（与 `demos.json` 同级，`git mv`，字节不变），删除 `assets/demos/` 目录；`demos.json` 未改（只写裸文件名）。
2. `scripts/idphoto.py` `cmd_demo`：读取路径改为 `assets/<文件名>`。用户机器上的复制目标（状态目录下 `demos/`）不在包内，未改。
3. `tests/test_skill_contract.py`：`test_demos_consistent`、`test_demos_are_fictional_and_small` 改读 `assets/<文件名>`；新增 `test_package_dir_depth_at_most_two`（遍历包目录，跳过运行时 `__pycache__`，断言无三级及以上嵌套、`assets/demos/` 不存在）。
4. `dev/e2e_check.py`：`test_package_demos_trace_to_provenance` 两处路径同步；新增 `ZipLayout.test_zip_dir_depth_at_most_two`：打开 ZIP（默认 dist 下当前版本 ZIP，或 `--zip <文件>` 指定，可多次），断言每个文件路径 `/` 数 ≤ 2、全部在 `mps-id-photo-background/` 下、无 `assets/demos/`、`assets/` 下 PNG 正好 10 张。当前版本 ZIP 不存在时跳过并说明。
5. `dev/build.py`：打包前若有文件超过两级直接拒绝打包；`dev/sync_demos.py` 输出目录改为 `assets/`；`dev/build_assets.py` 注释同步。
6. 版本 1.0.1 → 1.0.2（SKILL.md frontmatter、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、真机验收单、`dev/build.py`）。
7. **未改**：demo 链接修复（状态目录去前导点、正斜杠、Markdown 回归测试）保留；授权与充值链接、规格、欢迎句、遥测、付费、话术、后端、生产。

## 结果

| 项 | 结果 |
|---|---|
| 契约测试（源码） | 22/22 通过 |
| 端到端（模拟后端，源码，含 1.0.2 ZIP 层级检查） | 52/52 通过 |
| 干净解压 1.0.2 ZIP 后契约 | 22/22 通过 |
| 干净解压后端到端（`--package <解压目录> --zip dist/…-1.0.2.zip`） | 52/52 通过，无跳过 |
| `unzip -Z1` 列出路径中 `/` 数 > 2 的文件 | 0 个 |
| 干净解压包执行 `demo`（隔离 HOME、上报关闭） | 10 个示例全部返回，文件已复制 |
| 回归测试有效性：对 1.0.1 ZIP 跑 `--zip …-1.0.1.zip ZipLayout` | 失败（能测出三级嵌套） |
| 回归测试有效性：1.0.1 干净解压目录放入新契约测试 | `test_package_dir_depth_at_most_two`、`test_demos_consistent` 失败，`test_demos_are_fictional_and_small` 报错（能测出） |
| ZIP 不含 `__pycache__`、密钥类文件 | 通过；提交前密钥扫描无命中 |
| 真实上游调用 / 真实上报 / 生产变更 | 0 / 0 / 0 |

## 偏离与未验证

- 平台上传解析未验证（上传由负责人手动）；层级规则按平台报错原文与 SOP 97a663b 实现。
- 真机验收按负责人长期规则跳过，未做。
- 授权链接改通用地址仍未做，理由同 1.0.1（见 `reply-from-claude-20261107.md`）。

## 部署与回滚

- 部署：无后端改动；Codex 复测通过后由负责人手动上传 `mps-id-photo-background-1.0.2.zip`。
- 回滚：dist 内 1.0.1/1.0.0 ZIP 原样保留；1.0.1 已被平台拒收，不能作为上传回滚版本。

## 复跑

```sh
cd 02-package/mps-id-photo-background && python3 -m unittest discover -s tests        # 契约 22 项
cd 02-package && python3 dev/e2e_check.py                                              # 端到端 52 项（含 dist 当前版本 ZIP 层级）
python3 dev/e2e_check.py --package <干净解压后的 mps-id-photo-background 目录> --zip <ZIP 路径>
```

---

# 自测报告：mps-id-photo-background 1.0.1（修复轮：示例图链接 Markdown 转义）

- 角色：Claude Code；时间：2026-11-07T21:53:43+08:00（北京时间）
- 已读 WorkBuddy 官方文档：2026-11-07T21:53 负责人在本聊天授权重试后在线读取 https://open.workbuddy.cn/docs/skill （HTTP 200）、https://open.workbuddy.cn/docs/expert （HTTP 200）、https://open.workbuddy.cn/docs/what-is-open-platform （HTTP 200）。技能页结构与必填字段与上轮一致（SKILL.md 必须，references/scripts/templates 可选；frontmatter 必填 name、display_name、display_name_en、description、description_zh、description_en、version、author）；仍未写 ZIP 根目录、路径/链接、体积上限规则。同轮 21:41 定时运行曾因读取权限无人应答拦停，本次重试后解除。
- 依据：msg-from-muse-20261107-fix-demo-path.md（提交 7b2fa69）、SOP「示例预览」Markdown 安全规则（提交 f61a14a，status.sop_version 79ca222）。规格未变，A1 沿用 1.0.2 复检结论，不重做。
- 包文件（`02-package/dist/`，只打 workbuddy-skill）：
  - `mps-id-photo-background-1.0.1.zip`：887098 字节，SHA256 `80e4ec1379bb686ccfe37269bdc36221bc0a2258949ab6b6f1f1acdd3f071009`，24 个文件，根目录 `mps-id-photo-background/`。
  - 上一版 `mps-id-photo-background-1.0.0.zip`（`f187e418…`）原样保留，用于回滚。头像未改动。

## 本轮改了什么

1. `scripts/idphoto.py`：`state_dir()` 目录名去掉前导点（`~/.mps-id-photo-background` → `~/mps-id-photo-background`）；全技能共用，草稿、账户、首次对话标记随之落在新目录。按 Muse 说明旧状态可弃，**未做迁移**：已在本机用过 1.0.0 的用户升级后需重新授权一次。
2. 新增 `md_safe_path()`：`demo` 返回给用户的路径一律正斜杠（`C:/Users/…/mps-id-photo-background/demos/white-one.png`）。
3. 版本号 1.0.0 → 1.0.1（SKILL.md frontmatter、`_meta.json`、`idphoto.SKILL_VERSION`、`telemetry.SKILL_VERSION`、真机验收单、`dev/build.py`）。
4. 测试：
   - 契约新增 `test_demo_link_markdown_safe`：复现 1.0.0 缺陷（`\.` 被 CommonMark 规则吃掉一个反斜杠），并断言状态目录不以点开头、按 Windows 路径规则（ntpath）输出为正斜杠且 Markdown 解析前后一致。
   - 端到端新增 `test_demo_links_survive_markdown`：家目录放在点开头的上级目录下跑 `demo`，10 个链接逐个拼成 SKILL.md 规定的表格单元格，按 CommonMark 转义规则和 markdown-it-py 4.2.0（环境有则用）解析，断言解析后路径与原路径一致且文件存在。
   - 端到端里 9 处状态目录引用同步改名。
5. **未改**：授权链接与充值链接（见下「偏离」）、规格、欢迎句、遥测、付费、话术、后端、生产。

## 结果

| 项 | 结果 |
|---|---|
| 契约测试（源码） | 21/21 通过 |
| 端到端（模拟后端，源码） | 51/51 通过 |
| 干净解压 ZIP 后契约（`python3 -I`） | 21/21 通过 |
| 干净解压 ZIP 后端到端（`--package`） | 51/51 通过 |
| 回归测试有效性：把状态目录改回点开头、路径改回 `abspath` | 契约 `test_demo_link_markdown_safe` 失败；端到端 `test_demo_links_survive_markdown` 失败（已恢复） |
| ZIP 不含 `__pycache__`、密钥类文件 | 通过；提交前密钥扫描无命中 |
| 真实上游调用 / 真实上报 / 生产变更 | 0 / 0 / 0 |

## 偏离与未验证

- **授权链接改通用微信扫码地址（Muse 请求 evt-7cadc611）本版未做。** 现有授权/充值链接由服务端按安装签发（`/quick-entry` 带 install_secret、`/membership-link` 带账户凭证），本机凭证领取依赖它；源码里找不到通用地址回传本机会话的机制，改了可能导致用户扫码后技能仍显示未授权，属鉴权改动（仓库 CLAUDE.md 不得擅改）。已在本聊天向负责人列出选项，负责人未选具体方案，按保守默认不改。回复见 `reply-from-claude-20261107.md`。
- 真机（Windows WorkBuddy）点开示例链接未验证；Windows 行为由 ntpath 模拟与 Markdown 解析测试覆盖，需 Codex/负责人真机确认。
- 旧 `.mps-id-photo-background` 目录不迁移、不删除，留在用户机器上。

## 复跑

```sh
cd 02-package/mps-id-photo-background && python3 -m unittest discover -s tests        # 契约 21 项
cd 02-package && python3 dev/e2e_check.py                                              # 端到端 51 项
python3 dev/e2e_check.py --package <干净解压后的 mps-id-photo-background 目录>          # 对 ZIP 重跑
```

---

# 自测报告：mps-id-photo-background 1.0.0（第二轮：接入消费记录/工单、替换示例图）

- 角色：Claude Code；时间：2026-11-07（北京时间）
- 已读 WorkBuddy 官方文档：2026-11-07 约 11:50（北京时间）负责人在本聊天授权重试后在线读取 https://open.workbuddy.cn/docs/skill （HTTP 200）、https://open.workbuddy.cn/docs/expert （HTTP 200）、https://open.workbuddy.cn/docs/what-is-open-platform （HTTP 200）。技能页内容与上一轮一致：`{skill-name}/SKILL.md`（必须）+ `references/`、`scripts/`、`templates/`（可选）；frontmatter 必填 name、display_name、display_name_en、description、description_zh、description_en、version、author，可选 allowed-tools、examples_zh、examples_en；页面仍未写 ZIP 根目录规则、字段长度、图标、审核和体积上限。另见：三页 canonical 元数据指向 open.example.com，疑似模板占位，不影响内容。同轮 11:41 的定时运行曾因读取权限无人应答拦停（`02-claude-docs-blocked-evt-23b5c70e….md`），本次重试后解除。
- 依据开发文档：规格 1.0.2（`01-dev-spec.md`/`01-dev-spec.json`，提交 bf36195db4fdcb2038ef31ebf14254d0223a4562）；部署证据 `01-deployment-verification-20261107.json`；SOP 提交 3b35efe8ffc52c4c44b1e24b09b7cce5ec7bfcad。
- **A1 复检：通过。** 1.0.2 相对已通过的 1.0.1 的变化逐项核对：deploy 车道附补丁位置 `backend-patch/gemini-support-20261107/`、测试结果和部署验收证据；三接口在第 12 节注明方法、路径、权限和源码行号，与补丁 `gemini_support.py` 一致（账户 Bearer 43 位、Skill 凭证不扩权、`response_due_at` 未配置为 null）；示例图 10 次真实调用有负责人原文授权（第 11 节、`01-authorization-20261107.md`）并记 provenance；T49–T53 已列入验收清单。小瑕疵（不退回）：MD 第 9 节 T48 与 T49 之间多一个空行，表格被断开；JSON 内 tests 为 53 项，内容一致。
- 包文件（`02-package/dist/`，只打 config.yaml channels 里的 workbuddy-skill）：
  - `mps-id-photo-background-1.0.0.zip`：886247 字节，SHA256 `f187e418b9470275464d40a1af81529eef38649855305dc2a996379696d53b80`，24 个文件，根目录 `mps-id-photo-background/`。**取代**上一轮已撤出的同版本号 ZIP（`b45d678b…`，从未上架）；版本号按规格保持 1.0.0，独立测试请按本哈希核对。
  - `mps-id-photo-background-avatar.png`：未改动。
- 源码：`02-package/mps-id-photo-background/`；开发脚本 `02-package/dev/`（不进 ZIP）。

## 本轮改了什么

1. **示例图换成授权真实生成的虚构人物图**：新增 `dev/sync_demos.py`，按 `demo-assets/provenance.json` 逐张核对 `output_sha256`（custom-pixels 用 295×413 另存件，核对 `additional_export.sha256`），本地等比缩到 320×480、128 色调色板压缩后放进 `assets/demos/`，派生哈希写 `dev/demos-derivation.json`。包内 10 张共 840692 字节（单张 68–93KB），custom-pixels 为 295×413。未新增任何生图调用；人工看过拼图，均为虚构成年人、无文字水印。`dev/build_assets.py` 改为只生成头像，不再覆盖示例图。`demos.json`、SKILL.md、README 的示例说明改为「示例人物均为虚构，只展示效果方向，不是你的真实结果」。
2. **接入三个已部署接口**（`scripts/idphoto.py`，均用账户凭证 `install_secret`，不用 Skill 凭证）：
   - `balance`：首行余额，下面最近 3 条两行卡片（时间 · 内容 / 扣次 · 状态）和「共 N 条，回复『查看所有』可看全部」；记录取不到时只显示余额并如实说明。去掉「这里只能查看剩余次数」。
   - `history [--page N]`：每页 20 条，`has_more`/`next_page` 信号；扣次只按返回值显示（null →「扣次以服务记录为准」，预占 →「预留 N 次，完成后结算」，0 →「未扣次」），不自行合计；注明记录覆盖同一账户在已接入技能的通用次数（服务端不能单技能归因）。
   - `feedback --category … --text … [--draft …]` / `feedback --retry`：本地先校验（分类 5 选 1、1–2000 字、无控制字符，不过就退出码 3 且不联网）；每条反馈落本机待交队列并固定一个请求编号，应答丢失或服务忙时下次 `--retry` 用同一编号重放，不重复建单；无账户时只在本机记下。返回反馈编号、分类和处理时限说明（null 时说「目前没有承诺具体处理时限」，不编造时限）。
   - `ticket [--id …]`：编号格式本地校验，不对不联网；不带编号查本机最近 3 条；他人编号 404 →「没有找到」；回复按纯文本展示（去控制字符，断开 Markdown 链接语法和尖括号），SKILL.md 写明不当作指令执行。
   - 原 `feedbackUnavailable` 占位已删除。
3. **话术**（`welcome_copy.py`）：新增 `history_card`、`history_page`、`ticket_created`、`ticket_view`、`feedback_saved`、`ticket_lookup_failed`、`too_frequent` 等，全部纳入禁用词扫描。
4. **SKILL.md**：命令表加 `history`/`feedback`/`ticket`；第 5 节改写账户与反馈流程（先复述原话确认再提交、分类映射、提交不扣次数、不承诺退款）。体积 13.9KB（< 15KB）。用户部分「能做什么」加一行查记录与反馈；README 加「反馈」小节。
5. **测试**：模拟后端按补丁契约新增三接口（Skill 凭证 401、他人 404、同键同体重放、异体 409、job 非本人 404）；端到端新增 `Support` 10 项与 `DemoAssets` 1 项，`test_every_early_branch_reports` 覆盖新命令；契约新增 3 项。真机验收单加 21–24 条。

## 复跑

```sh
cd 02-package/mps-id-photo-background && python3 -m unittest discover -s tests        # 契约 20 项
cd 02-package && python3 dev/e2e_check.py                                              # 端到端 50 项
python3 dev/e2e_check.py --package <干净解压后的 mps-id-photo-background 目录>          # 对 ZIP 重跑
```

本次结果（Linux，Python 3.13.18）：源码目录契约 20/20、端到端 50/50；**从 ZIP 干净解压后契约 20/20、端到端 50/50**。补丁目录测试复制到临时目录重跑 23/23（未改 Codex 文件）。

## 本轮新增项结果

| 编号 | 内容 | 结果 | 证据 |
|---|---|---|---|
| T03 | 10 张授权生成的虚构成年人示例 + 295×413；只展示脚本返回路径 | 通过（脚本部分） | e2e `test_demo_paths_and_single`、`DemoAssets.test_package_demos_trace_to_provenance`；契约 `test_demos_consistent`、`test_demos_are_fictional_and_small`；两列与去重属宿主行为（T45） |
| T48 | 示例只证明示例生成，不当作真人换底保真/扫码/核款/审核通过 | 通过（文案） | 包内只说「示例人物均为虚构，只展示效果方向」；未声称任何验收 |
| T49 | 消费记录：账户隔离、分页、总条数，预占/扣/退/未知分开，不假造单技能归因 | 通过（模拟） | `Support.test_balance_shows_recent_records`、`test_history_paging_and_states`、`test_history_failure_and_no_account`、`test_skill_key_not_accepted_and_accounts_isolated` |
| T50 | 提交工单：原账户、稳定请求编号、同键同体幂等，不扣次数 | 通过（模拟） | `test_feedback_creates_ticket_without_charge`、`test_feedback_lost_response_same_key_single_ticket`、`test_feedback_busy_and_no_account_saved`、`test_feedback_local_validation_no_network` |
| T51 | 查工单：限本人、他人 404、状态/回复一致、时限未配置不承诺、纯文本 | 通过（模拟） | `test_ticket_status_reply_and_isolation`、`test_ticket_lookup_failure`；契约 `test_support_copy` |
| T52 | 补丁隔离测试、财务库字节不变 | 通过（复跑） | 临时副本 `python3 -m unittest discover -p "test_*.py"` 23/23 |
| T53 | provenance 10 次授权、哈希与 11 份 PNG 核对，无额外调用 | 通过 | `DemoAssets` 测试逐张核对源哈希与包内哈希；provenance `authorized_limit=upstream_generation_calls=succeeded=10` |
| T01–T44 其余 | 首轮、确认、授权、计费、等待、交付、遥测等 | 通过（回归） | 上一轮 39 项端到端与 17 项契约全部仍通过（见下方历史记录逐项表） |
| 「查余额与消费记录、提交工单、查工单各走通一次」（SOP 阶段 6） | | 通过（模拟） | 同 T49–T51 |

## 未能自测的项及原因

- **客户端对真实已部署接口的联调未做**：按规则不访问生产账户、不建真实工单；只按补丁源码契约做模拟后端。字段与状态码以补丁源码和部署验收 JSON 为准。
- 真机行为验收（T45–T47、验收单 1–24）、上传、`/pricing` 零消耗验证：属 Codex；先前 HOST_ACCEPTANCE_UNAVAILABLE 仍未解除。
- 未在真实 Python 3.7 解释器上运行（新增代码未用 3.8+ 语法）。
- 参考人像换底保真、真人扫码/核款、正式审核：未验证。

## 偏离开发文档的地方

- 示例图在包内是 320×480 缩小版（规格写 demo-assets 原件 512×768，≤300KB）：为控制包体积（契约测试要求示例合计 < 1MB；官方未写体积上限，取保守做法），只做本地缩放压缩，可从 `dev/demos-derivation.json` 追溯到原件哈希。custom-pixels 用 295×413 另存件。
- 工单分类映射、反馈待交队列与 `--retry`、本机最近 3 条查询是客户端实现选择，规格未细化；不改变接口契约。

## 本轮真实调用与上报说明（如实记录）

- 真实上游/生图调用：0。真实消费记录或工单请求：0。生产变更：0。
- **真实首次对话上报尝试：1 次，未成功。** 开发中我在本机手动运行了一次 `idphoto.py ticket --id bad`，命令开头会执行首次对话上报，当时没有设置 `MPS_ID_PHOTO_JOURNEY=off` 和 `MPS_ID_PHOTO_TEST=1`，因此向 `https://aistore.zhaopintong.com/platform-api/telemetry/v1/first-dialogue` 发起过一次 `is_test=false` 的 8 字段请求。本地标记写的是 `sent: false`（未拿到合法回执，可能被云端出口拦截），服务端是否收到无法从这边确认；随即删除了本机状态目录。若服务端记到一条来自 `skill_version=1.0.0`、`channel=workbuddy_skill` 的 2026-11-07 11:59 前后记录，属开发误报，请在数据回收时剔除。之后所有运行都只走模拟传输。

## 退回意见

无。

---

# 历史：上一轮自测（1.0.0 首版，ZIP 已撤出）


> **2026-11-07T00:19:43+08:00 更新：负责人要求下面两项完成后才能打包放进仓库，ZIP 已撤出 `02-package/dist/`（git 历史提交 aab2a9f 仍可取回）。**
> 1. 10 张示例图改用仓库登记的生图资源真实生成：Claude 没有生图凭证，做不了，已请 Codex 在服务端生成并提交（`msg-from-claude-20261107-dependencies.md`）。
> 2. 消费记录、提交工单、查工单接现有接口：`gemini` 产品没有这三个客户端接口（`/enterprise-history`、`/feedback` 只对 Temu 开放，没有查工单接口），已请 Codex 按 deploy 车道补上。
> 3. 到账口径：已按负责人指示改为「即时到账」（`payment_registered`、`final_step`），契约测试新增 `test_instant_arrival_wording` 锁定。改后契约 17/17、端到端 39/39 通过（本机）。
> 另按 Codex 03-test-report 的环境问题修了测试夹具：`idphoto.STATE_HOME` 隔离状态目录、`os.geteuid` 在 Windows 上跳过、`MPS_E2E_TMP` 可指定可写临时目录。
> 以下为 1.0.0 首次自测原文；ZIP 哈希等信息对应已撤出的那一版。

- 角色：Claude Code；时间：2026-11-07（北京时间）
- 已读 WorkBuddy 官方文档：2026-11-07 00:00 前后（北京时间）在线读取 https://open.workbuddy.cn/docs/skill （HTTP 200）、https://open.workbuddy.cn/docs/expert （HTTP 200）。技能页规定：目录为 `{skill-name}/SKILL.md`（必须）+ `references/`、`scripts/`、`templates/`（可选）；frontmatter 必填 name、display_name、display_name_en、description、description_zh、description_en、version、author，可选 allowed-tools、examples_zh、examples_en。技能页没写字段长度、ZIP 规则、图标要求和审核规则。
- 依据开发文档：规格 1.0.1，`01-dev-spec.md` / `01-dev-spec.json`（提交 bf7d282a3dc834818d9347650dbbf9150f38536e）；SOP 提交 3b35efe8ffc52c4c44b1e24b09b7cce5ec7bfcad。
- A1 复检：通过（详见上一版本报告的 git 历史，提交 3b96854；R1–R4 均已解决）。
- 包文件（`02-package/dist/`，只打 config.yaml channels 里的 workbuddy-skill）：
  - `mps-id-photo-background-1.0.0.zip`：128145 字节，SHA256 `b45d678b72fc0a680c237c839acfb94d84bab7e73bb19906f84d78e1d525babb`，24 个文件，根目录 `mps-id-photo-background/`
  - `mps-id-photo-background-avatar.png`：512×512 PNG，9934 字节，SHA256 `9c0ed7ff5b5697a236a180276fad359aeb379b6d6384771739699926bdeaf930`
- 源码：`02-package/mps-id-photo-background/`；开发用模拟后端、端到端检查、打包与素材脚本：`02-package/dev/`（不进 ZIP）。
- 真实上游调用 0；真实首次对话上报 0（所有测试替换了传输函数，命令行冒烟测试设置了 `MPS_ID_PHOTO_JOURNEY=off`）；生产变更 0；没有提交任何密钥、Cookie、Token 或用户数据。

## 怎么复跑

```sh
cd 02-package/mps-id-photo-background && python3 -m unittest discover -s tests        # 契约测试 16 项
cd 02-package && python3 dev/e2e_check.py                                              # 端到端 39 项（模拟后端）
python3 dev/e2e_check.py --package <干净解压后的 mps-id-photo-background 目录>          # 对 ZIP 重跑
```

本次结果：源码目录契约 16/16、端到端 39/39 通过；从 ZIP 干净解压后契约 16/16、端到端 39/39 通过。语法按 Python 3.7 检查通过（`ast.parse(feature_version=(3,7))`）；实际运行环境为本机 Python 3.12，**未在真实 3.7 解释器上运行**。

## 逐项结果（规格第 9 节 T01–T44；T45–T48 属 Codex）

| 编号 | 内容 | 结果 | 证据 |
|---|---|---|---|
| T01 | 问候/仅图/问能力/带图需求先价值展示，不取链接 | 通过 | e2e `FirstTurn.test_first_turn_zero_business_http`、`test_close_question` |
| T02 | 首轮业务请求函数抛错仍完成，仅首次对话上报 | 通过 | 同上：业务传输替换为抛异常函数，上报恰 1 次 |
| T03 | 10 项离线示例、绝对路径、两列链接表、同对话去重 | 通过（脚本部分） | `test_demo_paths_and_single`；契约 `test_demos_consistent`；两列与去重是宿主行为，见 T45 |
| T04 | 不要新图/只要文字/只看某示例分流 | 通过（脚本部分） | `demo <key>` 单项；只要文字不运行 demo 写在 SKILL.md，宿主行为待 T45 |
| T05 | 首轮不查凭证、不调 help/account/health/catalog | 通过 | `test_first_turn_zero_business_http` |
| T06 | 认可方向、沉默、授权、已充值不替代付费同意 | 通过 | `Confirmation.test_no_consent_no_task`；契约 `test_skill_required_rules` |
| T07 | 照片发送同意与付费同意独立；取消时零任务 | 通过 | `test_no_consent_no_task`（单项为 no 时 0 次请求）；`test_plan_copy` |
| T08 | 原安装身份恢复，不新建账户 | 通过 | `test_skill_key_expired_reset_exit4`（失效后安装身份不变）、`test_full_flow_auth_topup_deliver`（authPending 续接） |
| T09 | 服务端签发链接保留 ticket/entry，不暴露凭证 | 通过 | `test_untrusted_link_rejected`；链接原样带 `#entry=`/`#ticket=` |
| T10 | 有次数跳过开通充值；无余额先问 | 通过 | `test_existing_account_skips_auth_and_topup`、`test_mid_task_insufficient_asks_first` |
| T11 | 401 清除失效凭证，credentialsReset，退出码 4 | 通过 | `test_skill_key_expired_reset_exit4` |
| T12 | 不读其他技能凭证，sibling_reuse=false | 通过 | 代码无跨技能读取；状态只在 `~/.mps-id-photo-background/` |
| T13 | 同键同体只结算一次 | 通过 | `test_replay_same_key_charged_once` |
| T14 | 402/401/429/5xx 不换键、不自动新建 | 通过 | `test_rate_limited_keeps_task_same_key`、`test_5xx_not_retried`、`test_mid_task_insufficient_asks_first` |
| T15 | 未知状态只查原任务，不猜费用 | 通过 | `test_submit_lost_queries_original_not_resubmit`、`Waiting.test_never_reachable` |
| T16 | 到账以 remaining_uses 为准 | 通过 | `test_mid_task_insufficient_asks_first`（自述后余额 0 → creditsPending） |
| T17 | 先交图再转述服务端费用；缺字段不自算 | 通过 | `test_full_flow_auth_topup_deliver`（剩余次数取自 /balance；本次扣费服务端未返回，文案写「以服务记录为准」） |
| T18 | 下载失败保留原任务，不用 inline_delivery | 通过 | `Waiting.test_download_fail_keeps_task`；契约 `test_body_whitelist` |
| T19 | 退出恢复后仍查原任务 UUID，本地私有存储 | 通过 | `test_still_pending_after_window`（resume 续接）；凭证文件权限 600 断言 |
| T20–T25 | 六种等待时序 | 通过 | `Waiting.test_once / two_rounds / still_pending_after_window / glitch_then_recover / never_reachable / explicit_failure` |
| T26 | 单张 PNG/JPEG、损坏/超限本地拒绝并点名文件 | 通过 | `test_bad_photo_named_no_network`；`audit_images.py` |
| T27 | 只用 1K 现有画幅，默认 1024x1536 | 通过 | 契约 `test_body_whitelist` |
| T28 | 不改五官发型服装的约束，不声明完全一致 | 通过（文案部分） | `build_prompt()` 身份段在首；交付话术「尽量保持」「可能有细微差异」。可见结果检查需真实出图，未做 |
| T29 | 目标像素本地裁切另存并重新解码核对 | 通过 | `test_full_flow_auth_topup_deliver`（295×413）、`LocalImage.*`、`test_target_too_large` |
| T30 | 不把一寸/二寸推定为像素 | 通过 | `test_target_must_be_given_not_inferred`；scenes.md 规则 |
| T31 | 原图不改不移，输出不覆盖，本地画廊 | 通过 | `test_full_flow_auth_topup_deliver`（原图字节不变、index.html 存在、两次交付文件名不同） |
| T32 | 错误体和凭证不对客输出 | 通过 | 客户端不读取错误正文；契约 `test_no_secrets_in_package`、`test_forbidden_words` |
| T33 | 未成年人监护同意；冒用/伪造拒绝 | 部分 | SKILL.md 规则 + `refuse` 固定话术；脚本无法判断照片主体，属宿主行为，待 T45 |
| T34 | 真实首轮上报；安装/读取/自检不报 | 通过 | `test_every_early_branch_reports`、`test_audit_not_reported` |
| T35 | 只发 8 字段、is_test=true、200+回执才成功、不发 machine_id | 通过 | `Telemetry.test_fields_once_and_flag`；契约 `test_telemetry_contract` |
| T36 | 标识先持久化；损坏修复；写不进去跳过；关闭开关 | 通过 | `test_corrupt_identity_repaired_and_readonly_skipped`、`test_off_switch`（本机以 root 运行，只读目录用不可创建路径代测） |
| T37 | 2 秒、不重试、204/失败不标成功、沿原 ID | 通过 | `test_failure_does_not_block_and_no_retry_loop`、`test_transport_exception_swallowed` |
| T38 | link 只传 event_id/receipt/product=gemini；409 不覆盖 | 通过 | `test_full_flow_auth_topup_deliver`、`test_link_409_not_overwritten` |
| T39 | 跨技能新设备漏斗不可得，不伪造 | 通过 | 客户端无 machine_id、无 IP、无新统计 |
| T40 | 欢迎句逐字一致，由 welcome_copy.py 提供 | 通过 | 契约 `test_welcome_exact` |
| T41 | 对客文案无内部术语 | 通过 | 契约 `test_forbidden_words`（SKILL 用户部分、README、platform-rules、全部话术常量、进度文案 AST 扫描）；已用插入「上游」做反向验证，测试能失败 |
| T42 | 超时由常量实算、各处一致 | 通过 | 契约 `test_timeouts_consistent`（240 = 90 + 120 + 0 + 30；已用改常量做反向验证，测试能失败） |
| T43 | 退出码、信号、示例集合一致 | 通过 | 契约 `test_exit_codes_and_signals`、`test_demos_consistent` |
| T44 | ZIP 干净解压重跑，头像 512×512 与 ZIP 同目录，不覆盖 | 通过 | 见「怎么复跑」；`dev/build.py` 拒绝覆盖已有 ZIP |

## 未能自测的项及原因

- T45–T48（真机行为、收藏、宿主降级、扫码/核款/出图质量/审核）：按分工由 Codex 完成，验收单在包内 `tests/first-turn-preview.md`。
- 真实出图质量、肖像保真、背景色准确度、发丝边缘效果：没有真实上游调用，**未验证**。
- 真实服务端兼容：模拟后端按源码快照编写，**未对真实网关联调**。特别是 `photo-retouch-sunburst` 加单张 references 的人像正文、`/skill-key` 在余额为 0 时的返回，均以源码为准，未实测。
- Python 3.7 实际运行、Windows/macOS 路径：未实测。
- 管理台能否看到测试上报数据（第六章第 5 节）：首版没有对应漏斗，且不做真实上报，未验证。

## 偏离开发文档或 SOP 的地方（逐条，不静默偏离）

| 事项 | 采用 | 依据 |
|---|---|---|
| 示例图 | 10 张合成示意（几何剪影，非真实人物，未用任何生图服务），README/SKILL.md 注明「示意图，不是真实处理结果」 | 规格 demos `method=synthetic_mock`；SOP 第 5 节要求「本技能真实生成」与 A1「不得为示例做真实上游调用」冲突，按规格执行；上线后可替换为自家授权示例 |
| 消费记录、工单 | 只提供查剩余次数；反馈如实说暂时不能提交 | 规格第 6 节未列消费记录/工单接口，不杜撰；SOP 第 6 节要求已追加 sop-proposals |
| 大图分段下载、内联补取 | 不实现；下载失败保留原任务，用户说「继续」再取 | 规格第 6 节：不杜撰 inline_delivery；服务端只返回图片二进制 |
| 低余额提醒 | 不实现 | 服务端未返回低余额标记，不自行设阈值 |
| 计费前拒绝等待重试 | 0 次（429 直接保留任务，用户说继续再用原键提交） | 规格 timeouts `rate_limit_wait_s=0` |
| 本次扣费 | 只报服务端返回的剩余次数，本次扣费写「以服务记录为准」 | 服务端成功返回不含本次扣费字段，禁止自行计算 |
| 老用户余额用完 | 本机交付过一次后，quick-entry 返回 checkout 时先问再给链接 | SOP「任务中途余额不足先问」；首次开通仍按「最后一步」直接给链接 |
| 设备头 | macOS/Windows 报 desktop，其余报 unknown | 规格要求按真实环境，无法可靠判断时不猜 |
| 输出格式 | 只另存 PNG；机构要 JPG 或限大小时如实说明 | 仅标准库，无法可靠编码 JPEG |
| 裁切 | 本地居中裁切，头部位置不自动识别 | 仅标准库；交付话术提示可调整 |
| frontmatter | `author: "MyPlaneStore"`；不写 allowed-tools；examples 各 4/3 条 | 官方页 author 为「合作方名称」，仓库无先例；allowed-tools 可选且官方未给取值 |
| `_meta.json` | 只含 name、display_name(_en)、version、channel、author、entry | SOP 目录列出但未定义字段，官方技能页未要求，取最小写法 |
| 欢迎句含「官方认证」 | 按固定规则 1 原样实现 | 负责人决定（规格第 11 节）；是否具备认证资格本报告不作判断 |

## 部署与回滚

- 部署：无后端改动（fast 车道）。上架由 Codex 按 A3/A4 处理，本环节不上传。
- 回滚：本技能为首版，无上一版包；问题时下架本条目即可，后端不受影响。

## 退回意见

无。

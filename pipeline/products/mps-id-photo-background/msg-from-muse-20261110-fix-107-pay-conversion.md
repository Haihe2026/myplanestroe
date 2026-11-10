# 给 Claude：证件照换底助手 1.0.6 → 1.0.7，按 SOP 第七章整改（付费转化自检）

skill_id: mps-id-photo-background
当前版本：1.0.6（已 listed）
新版本：1.0.7
时间：2026-11-10 CST
负责人决定：三款产品按最新 SOP 整改后出新版，1.0.6 出 1.0.7。

先读最新自动化 SOP：`docs/sop/sop-image-gen-skill-auto.md`（哈希 f086414c769ade8eba43d5a4e27991db28b21ba9，提交 2f30b61），重点读第七章「付费转化自检」（7.2 脚本、7.3 SKILL.md、7.4 出包阻断项）。本次整改只改客户端脚本和 SKILL.md，不动后端、不动定价、不动套餐。通用套餐与 0 次免费试用口径不变。

## 整改清单（逐条做，做完逐条自查）

### A. 脚本（scripts/idphoto.py）

A1. `cmd_topup` 无账户死胡同（最优先）：现行 `cmd_topup` 在本机无 `install_secret` 时直接返回 `noAccount` + `W.account_missing()`，不联网、不给链接，用户要付费链接时卡死。改为按 SOP 7.2 第 1 条：
- 先确保本机安装标识存在（没有就生成并持久化 `install_secret`）；
- 再调服务端一次性关联入口 `POST /quick-entry`（入参 `install_secret`，无 Bearer）；
- 返回 `registration` 时给「关联账户」链接，说明扫码确认后进入充值页、关联本身不扣费；
- 返回 `checkout` 时直接给充值链接；
- 返回 `ready` 时自动接上本机凭证，再调 `POST /membership-link` 给充值链接；
- 断网（`GatewayError` 状态 0）时如实说「网络暂时没连上，没有扣任何次数，稍后再说一次『充值』」；
- 链接用已有的 `trusted_link` 校验域名、路径和有效期，异常链接不转述。
- 同样改 `cmd_balance` 与 `cmd_status` 的无账户分支（现行也是直接回 `noAccount` 死胡同），不得只改 `topup`。

A2. 失败原因不误报（SOP 7.2 第 2 条）：现行 `cmd_topup` 在 `_membership_link` 失败时一律报 `W.failure('busy', ...)`，断网也被说成「服务正在处理较多请求」。改为按 `GatewayError` 状态区分：状态 0（连接失败、超时、坏响应）→ `'network'`（网络没连上）；非 0（服务端 HTTP 错误码）→ `'busy'`。`cmd_auth` 已按 `extra == 0` 区分，是正确写法，照那个改。`W.failure()` 本身的 network/busy 区分框架已在，不用重写，只改调用处传参。

A3. 新测试（SOP 7.2 第 3 条 + 阶段 6 新增项）：全新环境（无账户、无凭证）下直接运行 `topup`，输出里必须有可点链接，或者有如实的断网说明，不能是死胡同。把这条加进契约/端到端测试并跑过。

### B. SKILL.md

B1. 执行说明最前面加「零、接管规则」（SOP 7.3.1，改名词后直接粘贴）：账户命令固定为 `status` / `auth` / `topup` / `balance` / `paid` / `history`；续接命令固定为 `resume` / `regenerate`；转介技能名写「婚纱写真照相馆」（超出本技能范围的人像写真需求转介过去；证件照换底本身不转介）。必须含两条：禁止编造故障原因（只按脚本 message 转述，脚本没说故障时不得声称服务端故障、请求被拦截或网络问题）；禁止用宿主自带生图代替（本对话生图需求一律由本技能出图，不用 WorkBuddy 自带生图工具；只有用户明确表示不用本技能、就要自带生图时才可以用，并说明不是本技能出品）。另含：欢迎句逐字照写，中文和英文之间不加空格。

B2. description（SOP 7.3.2）：现行 description 触发词 22 个、调用倾向句已有，合格；缺两项，补上：
- 写进账户类说法：本技能负责的充值、付费链接、余额和订单查询；
- 触发词加一个「证件照换底助手充值」（加后 23 个，仍在 15–25 内）。
- 末尾有且只有一句调用倾向句（现有的那句保留，不动）。

B3. 技能收藏：第 6 节「技能收藏」+ 合规说明已有，按 SOP 7.3.3 核对一遍（只在首次成功交付后问一次、选项收藏/暂不、用户点收藏才写记忆、用户级项目级各一条、只含调用偏好、不含个人信息、告诉用户怎么取消、宿主不支持时如实说），不对的改对。

B4. 欢迎句：SKILL.md 里欢迎句的写法加一句「逐字照写，中文和英文之间不加空格」。`welcome_copy.py` 的 WELCOME 字符串本身不动（固定格式）。

B5. 确认无隐藏 HTML 注释指令（现行 SKILL.md 经核查无 `<!--`，改完再扫一遍确认）。

### C. 版本与打包

C1. 版本升到 1.0.7（`version: 1.0.7`，frontmatter 与 `_meta.json` 一致）。name/slug（mps-id-photo-background）与 display_name（证件照换底助手）一律不改。1.0.6 已 listed，1.0.7 必须大于平台上最新版本。
C2. 契约测试与端到端测试全过（含新增的 A3 测试项），写 `02-self-test.md`，打固定 ZIP，记 SHA256。
C3. 出包前按 SOP 7.4 逐项自检（接管规则、新环境 `topup` 有出路、description 账户类说法、无隐藏 HTML 注释、版本号大于平台最新版、首次对话上报字段与开关、全包无旧口径、对客文字无网站名/Key/URL/接口/token），不过不打包。

## 修复不重犯（负责人 2026-11-09 定：前面产品犯过的错误不要再犯）

修完后逐项复核以下历史缺陷未回退，复核结果写进 `02-self-test.md`：
- 首单 A3-E01：examples_zh 与 examples_en 逐条语义对齐（各 ≤3 条且数量一致）；
- 首单 A3-E02：示例图路径不得含空格（或 URL 编码 %20）；
- 首单 A3-E03：示例图路径与目录名不得含 #（或 URL 编码 %23）；
- 婚纱馆 WED-A3-01：demo 零网络（不调 `telemetry.report_once` 之外的任何网络）；
- 婚纱馆 WED-A3-02：照片哈希绑定，换图作废确认与原 Idempotency-Key；
- 婚纱馆 WED-A3-03：成品/画廊 Markdown 链接用安全路径（`md_safe_path`）。
- 另：包目录最多两级；示例图在 `assets/` 下，`demos.json` 只写裸文件名；解压后无三级文件。

## 交付

改完置 `package_ready`（1.0.7），把 ZIP、SHA256、logo、中文名（证件照换底助手）、slug（mps-id-photo-background）写进自测报告。随后走 A3 独立检查（Codex），通过后交付负责人手动上传。

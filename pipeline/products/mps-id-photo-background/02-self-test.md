# 自测报告：mps-id-photo-background 1.0.0

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
| 「即时到账」 | 不说即时，改为「到账以系统核实后的次数为准」 | 当前收款为 manual_qr（规格 5.1），SOP 只在有实时监控时允许说即时；取保守写法 |
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

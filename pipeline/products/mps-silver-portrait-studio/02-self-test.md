# 自测报告：mps-silver-portrait-studio 1.0.0

- 已读 WorkBuddy 官方文档快照（快照日期 2026-11-08，读「二、技能」章：目录结构、frontmatter 八个必填字段、examples、references/scripts/templates 用法）。本次为首次开发新包；规格另记 2026-11-12T08:36:10+08:00 在线读取记录，Claude 本次未在线重读。
- 依据：`01-dev-spec.md` / `01-dev-spec.json` @ `3eb43035ef3c80363b0c9527cb82ec63aa758bb8`（通知 `evt-275458e4…` 的 source_ref）；SOP `docs/sop/sop-image-gen-skill-auto.md` 当前版。
- 时间：2026-11-12 上午 Claude 定时运行，第一轮开发（`rounds.dev` 0 → 1）。渠道只做 `config.yaml` 的 `workbuddy-skill`。
- **A1 复检：通过**（16 项逐条对照 `01-a1-validation.json` 与规格正文：立项/词表 23 个、官方文档读取记录、十主题路由、被摄人/代购/老兵条件与三基线、10 示例 + provenance、立体 logo、计费默认值、模型/成本/毛利 76.47%、fast 车道、接口源码位置、漏斗、相邻技能、不承接清单、T01–T17 与 S6-01…57、决策记录、MD/JSON 一致）。串行规则：前序六个包均为 `submitted`，满足。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；生产变更 0；未上传、未发布。契约测试与端到端检查在 `unshare -rn`（无网络命名空间）里对干净解压包再跑一次，仍全部通过。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-silver-portrait-studio-1.0.0.zip`，2603008 字节，25 个文件，逻辑根最多两级，SHA256 `b06ce740ca094ee56dd9483c368599dc4ecbe2e4ff0f858f6fa7b258f3deb44c` |
| 版本 | 1.0.0（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py`、first-turn-preview 一致）；本 slug 无已上传版本 |
| logo | `02-package/dist/logo.png`（Codex 生成，外置不进 ZIP），原字节未动：SHA256 `9909cf071a9e64cb18707ec846b6cf5c921754979151075bfcf77756420acf1e`，与 `01-logo-provenance.json` output_sha256 一致 |
| 十张示例 | `demo-assets/*.png` 按 `provenance.json` 逐张核 SHA 后原字节复制到 `assets/`（`dev/sync_demos.py`，派生记录 `dev/demos-derivation.json`）；每张 512×768，合计 2519807 字节；未缩放、未重编码、未新增生图 |
| 平台字段 | name `mps-silver-portrait-studio`、display_name `银发写真照相馆`、display_name_en `Silver Portrait Studio`、author `MyPlaneStore`；description / description_zh / description_en 双引号标量；examples_zh / examples_en 各 3 条，与规格 14 节逐字一致 |
| 欢迎句 | 「欢迎使用WorkBuddy官方认证技能 银发写真照相馆。」逐字 |
| 付费口径 | MyPlaneStore 通用套餐，不单独定价，0 次免费试用，不写死单价；代购时扣下单人账户 |
| SKILL.md | 15334 字节（< 15360）；触发词 23 个，与 `01-dev-spec.json.description_terms` 逐项一致；description 末尾唯一调用倾向句与规格一致 |
| 开发目录（不进 ZIP） | `02-package/dev/`：`mock_backend.py`、`e2e_check.py`、`build.py`、`sync_demos.py`、`demos-derivation.json` |

完整 ZIP 目录：`README.md`、`SKILL.md`、`_meta.json`、`assets/`（demos.json + 10 PNG）、`references/`（platform-rules.md、prompts.md、scenes.md）、`scripts/`（audit_images.py、jpeg_local.py、png_local.py、studio.py、telemetry.py、welcome_copy.py）、`tests/`（first-turn-preview.md、test_skill_contract.py）。

## 实现要点

- 基座：固定孕妈 1.0.1（`108761fb…`，规格 1 节指定）的账户 / 原安装恢复 / 绑定 401 只清技能凭证 / 原任务只读 / 有界 PNG·JPEG / HTTP 前本地验图（MAT-A3-02）/ 资格未知先补问（MAT-A3-03）/ 合法 YAML 检查（MAT-A3-01）/ 一次上报等实现原样继承，并保留其随包回归；去掉孕期视觉档，不复制孕期主题或示例人口属性。
- 十主题 `SCENES`（studio、tang、lawn、oil、beach、qipao、garden、veteran、rural、winter，全部默认竖版 2:3 / 1024×1536）；三层路由：特异主题/服饰（老兵、唐装、旗袍、油画、园林、田园、海边、草坪、冬日/室内、棚拍）→ 一般风格词 → 泛化词（优雅、银发、阳光、暖阳）；生日、金婚、父母节等送礼动机不参与路由，「退休」不路由到老兵。
- 下单人与被摄人分开：`plan --orderer self/family_proxy/unknown --adult yes/no/unknown [--informed yes/no/unknown]`。本人下单视为本人知情；代购必须 `--informed yes`。明确未成年 → `notEligible/minor`；家人本人明确不同意 → `notEligible/not_informed`；任一未知 → `needsEligibility`（退出 2，一次合并补问，不联网，不索证明）。账户、钱包、售后属于下单人，不转移、不读取其他技能凭证。
- 老兵条件绑定被摄本人：仅 `veteran` 主题需要 `--veteran retired_confirmed --veteran-consent yes`；未知 → `needsVeteranInfo`（一次补问，提示「退休」和「退役」不一样）；`active` / `not_veteran` / 不同意 → `veteranNotApplicable`，可改选其他主题；prompt 额外写无军衔、勋章、番号、姓名牌、国徽军徽、武器，不表现现役或服役证明。
- 三项同意：被摄本人照片许可、被摄本人同意这张文件发给图片服务及算力供应商、下单人计费同意；代购时确认话术写明前两项由下单人转述本人意思、从下单人账户扣次数，并写明「付过款不能代替前两项同意」。
- prompt 五段：身份与原照 → 自然年龄外观（发际线、发量、银/灰/黑发实际分布、自然皱纹；不磨皮扮嫩、不返老还童、不强行染白/补发/加皱纹/老化；不从外貌推断年龄或健康）→ 主题服装（不推断性别、民族或身份）→ 构图 → 文字与安全。合成 70 岁女性示例设定不进入任何 prompt。
- 请求体仍恰六字段，不发 age / orderer / veteran / people_count 等字段；私有草稿另存 `orderer`、`subject_adult`、`subject_informed`、`subject_veteran_status`。
- 「爸妈各拍一张」拆成两份单人方案，各自确认、各自任务键、各自扣一次；两人合照返回 `peopleUnsupported`（三人及以上或寿宴转全家福写真照相馆）。
- 可见标注「AI 生成银发写真，非实拍」：SKILL.md 用户部分、README、platform-rules、demos notice 与每条 note、确认话术、交付话术、结果一览页。示例 notice 说明同一位虚构成年人、不代表年龄/性别/发量默认、老兵示例不代表真实服役。
- 首次对话上报仍为 8 字段，开关 `MPS_SILVER_PORTRAIT_JOURNEY=off`；不含年龄、家人或服役信息。

## 自测结果

命令（开发目录 `02-package/`）：

| 命令 | 结果 |
|---|---|
| `cd mps-silver-portrait-studio && python3 -m unittest discover -s tests`（仓库内，含规格 JSON 对照） | Ran 60, OK |
| 干净解压 ZIP 后 `unshare -rn python3 -I -m unittest discover -s tests` | Ran 60, OK |
| `unshare -rn python3 -I dev/e2e_check.py --package <解压目录> --zip dist/mps-silver-portrait-studio-1.0.0.zip` | Ran 131, OK，0 跳过（含 ZipLayout 两项与 FrontmatterYaml 对 ZIP 原始字节用 PyYAML 6.0.3 解析） |
| `python3 dev/e2e_check.py`（仓库源码） | Ran 131, OK（2 项 ZIP 用例因未给 --zip 跳过） |
| scripts/、tests/ 按 `ast.parse(feature_version=(3,7))` | 通过（运行环境 Python 3.13，未在 3.7 解释器实跑） |
| 包与 dev 目录密钥形态扫描 | 无 |

| 编号 | 内容 | 结果 | 证据（测试） |
|---|---|---|---|
| T01 | 首轮与十主题路由 | 通过 | 契约 `test_route_precedence`（特异词优先、逆词序、送礼动机与「退休」不当主题、规格关键词逐个命中）、`test_first_turn_copy_clean`；e2e `FirstTurn.*`、`SilverSpec.test_t01_suggested_scene_in_first_turn`；首轮业务 HTTP 0 |
| T02 | 本人/家人代购及资格、三项同意 | 通过 | 契约 `test_plan_people_rules`、`test_consent_copy`、`test_consent_and_lock_rules`；e2e `OriginalTaskSpec.test_self_or_proxy_eligibility_and_three_consents`、`RepairMat101.test_mat_a3_03_*`、`Confirmation.*` |
| T03 | 十示例与安全路径 | 通过 | 契约 `test_demos_consistent`、`test_fam_03_demo_missing_one_exit3`、`test_demo_link_*`（真实创建 `Silver Demo Assets/`、`Silver#Demo/`、`Silver%Demo/` 并按 CommonMark 定位）；e2e `FirstTurn.test_demo_*`、`DemoAssets.test_package_demos_trace_to_provenance` |
| T04 | 原身份及绑定恢复 | 通过 | e2e `PayConversion.*`、`InheritedRepairTrv101.test_trv01_*`；契约 `InheritedRepairTrv102.test_trv01_r1_*` |
| T05 | 零试用和真实计费 | 通过 | e2e `AccountBilling.*`、`RepairPay103.*`、`SilverSpec.test_t13_reported_payment_not_credited`；契约 `test_skill_required_rules`、`test_instant_arrival_wording`、`test_no_slow_payment_wording` |
| T06 | 失败等待与未知 | 通过 | e2e `Waiting.*`、`OriginalTaskSpec.*`；契约 `test_timeouts_consistent`（90/15/120/30/0/240 逐处一致） |
| T07 | 完整有界输入/交付 | 通过 | 契约 `test_png_verify`、`InheritedRepairTrv102.test_trv02_r1_*`；e2e `RepairMat101.*`（确认后删/截断图 → photoInvalid 业务 HTTP 0；换图 → photoChanged）、`Waiting.test_size_mismatch_reported`、`OriginalTaskSpec.test_corrupt_png_kept_pending_then_get_only` |
| T08 | 消费记录及售后 | 通过（Mock） | e2e `Support.*`；契约 `test_support_*` |
| T09 | 首次上报一次 | 通过 | e2e `Telemetry.*`、`InheritedRepairTrv101.test_trv03_*`、`SilverSpec.test_t12_age_info_never_sent_as_field`（上报与 link 不含年龄/家人/服役） |
| T10 | 真实 YAML 及元数据 | 通过 | 契约 `test_frontmatter_*`、`test_examples_*`（三对逐字等于规格；主题/下单人/老兵/年龄/人数/画幅/像素逐维对齐，错配可测出）、`test_package_dir_depth_at_most_two`；e2e `FrontmatterYaml.*`、`ZipLayout.*` |
| T11 | 接管与收藏 | 通过（声明检查） | 契约 `test_takeover_rules_first`、`test_favorite_section`、`test_welcome_rule_and_copy`、`test_no_hidden_html_comment` |
| T12 | 自然年龄与发量、AI 标注 | 通过 | 契约 `test_prompt_baselines`（每主题五段、发量/染白/补发/老化/扮嫩约束、不含示例 70 岁女性设定）、`test_disclosure_everywhere` |
| T13 | 被摄人老兵条件 | 通过 | 契约 `test_plan_people_rules`（未知补问、active/not_veteran/不同意不做、非老兵主题不受影响）；e2e `SilverSpec.test_t13_veteran_condition_belongs_to_subject`（不联网、prompt 无标识约束、请求体无服役字段） |
| T14 | 冻结和多人分界 | 通过 | 契约 `test_consent_and_lock_rules`（改代购关系作废确认与键；锁定态 taskLocked）、`test_fam_01_02_*`；e2e `SilverSpec.test_t14_parents_each_split_into_independent_tasks`（两份独立键、各扣一次；合照不支持）、`RepairA3.*` |
| T15 | 资源与支付 Mock | 通过（只 Mock） | e2e `SilverSpec.test_t15_request_body_has_only_six_fields`、`test_t13_*`、`AccountBilling.test_client/server_rejects_unregistered_field`；契约 `test_body_whitelist`、`test_no_secrets_in_package` |

阶段 6 逐项（S6-01…S6-57）：applicable_mock 的 53 项由上表 T01–T15 覆盖并通过；S6-39/40/41/42 按规格为 `not_applicable_current_contract`（无 Range / inline_delivery / 计费前重试字段，sibling_reuse=false），未实现，以 T06/T07/T14「原任务只读」测试代替。S6-52/53/55/57（收藏写入宿主记忆、不 @ 触发）只做了 SKILL.md 声明检查，真实宿主未验。

## 未验证项

- 真实 WorkBuddy 宿主导入/解析与对话行为、收藏写入与不 @ 触发（真机验收按负责人长期规则跳过）；frontmatter 的平台解析结论仅来自 PyYAML 与标准库检查。
- 真人银发皱纹保真、不同性别/发量效果、老兵纪念造型的实际出图、真实付款与微信关联，均未做（真实上游 0）。

## 部署与回滚

- 无后端改动（fast 车道），无部署。上传由负责人手动。
- 回滚：本 slug 无已上传版本，回滚即不上传本包。

## 偏离开发文档

无。`plan` 的 `--orderer/--informed/--veteran/--veteran-consent` 取值与 `needsVeteranInfo`、`veteranNotApplicable` 信号是对规格 4 节私有 plan 状态与 T13 的实现细化；下单人未知时一并补问家人知情同意（三问合一），属于「一次合并补问」的实现。

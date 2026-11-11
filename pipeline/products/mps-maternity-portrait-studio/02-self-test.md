# 自测报告：mps-maternity-portrait-studio 1.0.1

- 修复轮（1.0.0 A3 退回 → 1.0.1），按 SOP〇章修复轮不重读官方文档。
- 依据：`03-test-report.md`（Codex 2026-11-12T01:04:45+08:00，test_failed）、`msg-from-muse-20261112-fix-100-mat-a3.md` @ `ae3bc8d376b1cdd84956b47fbeac17ad1f1b1057`；开发规格未改，仍为 `98ff2a5471031ff380a30bbd68c4ee69c2067ee1`；SOP `9b2282f1fda805234c2a9adb59c5f4a62d0684cb`。
- 时间：2026-11-12 凌晨 Claude 定时运行，`rounds.dev` 1 → 2。渠道只做 `workbuddy-skill`。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；生产变更 0；未上传、未发布。1.0.0 固定 ZIP 未改动。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-maternity-portrait-studio-1.0.1.zip`，2353236 字节，25 个文件，逻辑根最多两级，SHA256 `f958c1cc8eb4351e1fc7fc66adbaa5b62be03600ac15d08f8194bfc6447be8a6` |
| 旧包 | `mps-maternity-portrait-studio-1.0.0.zip` 原样保留，SHA256 仍为 `1997c54f29a1080e0d639832c19872630ddbca5da6e3670585a0292b08bcd475`（build.py 拒绝覆盖已有 ZIP） |
| 版本 | 1.0.1（SKILL.md、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py`、first-turn-preview 一致） |
| logo | `dist/logo.png` 未动：SHA256 `940b00c1a771779945a666de96a73dcbc7346c6435b5fdc7fded7028902ac333`，不进 ZIP |
| 十张示例 | 1.0.0 与 1.0.1 ZIP 内 10 张 PNG 逐字节相同（脚本对比） |
| 与 1.0.0 的差异文件 | SKILL.md、_meta.json、scripts/studio.py、scripts/telemetry.py（仅版本号）、scripts/welcome_copy.py、tests/test_skill_contract.py、tests/first-turn-preview.md（仅版本号）；其余 18 个文件逐字节相同 |
| SKILL.md | 15327 字节（< 15360）；欢迎句「欢迎使用WorkBuddy官方认证技能 孕妈写真照相馆。」逐字未改 |

## 三项缺陷的修复

### MAT-A3-01（P1）frontmatter 不是合法 YAML

- 根因：`description_en` 未引用且含 `portrait: 10 themes`；包内 `parse_frontmatter` 按首个冒号分割，没做 YAML 语法校验。
- 修复：`description`、`description_zh`、`description_en` 三个长文本字段改为双引号标量（内容逐字不变，无内部引号需转义）；`examples_*` 原本就是双引号。没有改测试去迁就：新增独立的语法检查。
- 新增检查：
  - 契约 `test_frontmatter_is_valid_yaml`（随包、标准库）：`frontmatter_scalar_problems` 对原始 frontmatter 做 YAML 严格子集检查（未引用标量不得含「冒号+空格」「空格+#」或以指示符开头；引号标量须闭合、内部引号须转义）；正例：引用后的值含冒号空格；反例：把 `description_en` 去引号、`k: a: b`、`k: "a"b"`、`k: x #y`、`  - a: b` 全部被拦下。有 PyYAML 时再用 SafeLoader（禁重复键）解析，结果须与包内解析逐字段相等，去引号版本须抛 `YAMLError`。
  - e2e `FrontmatterYaml`：用 PyYAML 6.0.3 对源码 SKILL.md 和**最终 ZIP 内原始 SKILL.md 字节**解析，禁重复键、核必填字段为非空字符串、examples 为字符串列表且中英各 ≤3 等量、无未知键、version 与脚本一致、完整英文描述含 `portrait: 10 themes`、大小 <15KiB；反例：去引号报 `YAMLError`、追加重复 `name` 报错；正例：`k: "a: b"` 解析为 `a: b`。
  - `dev/build.py` 打包前先跑同一语法检查（及 PyYAML 解析），不合法拒绝出包。
- 反证：对 1.0.0 的 SKILL.md 跑 `frontmatter_scalar_problems` 报 frontmatter 第 6 行（`description_en`）需引用。
- 篇幅：为容纳新内容，SKILL.md 删去几处重复/冗余表述（如「note 照抄」括注、「卡片原样转述，不自行合计」并入、「不补充原因」与接管规则重复等），所有必测语句仍由契约测试锁住。

### MAT-A3-02（P2）确认后源图坏了，仍先发账户请求

- 修复：`cmd_run` 在「已有 job_id 或 submit_unknown 先续查原任务」之后、`load_account`/`_account_ready`（quick-entry）/取 Key/绑定**之前**调用 `_job_body`：完整有界验图（原 audit_images/png_local/jpeg_local 未改）+ 源 SHA 比对。坏图 → `photoInvalid` 退出 3 并点名文件；换成另一张有效图 → `photoChanged`，作废三项同意与未提交键。`cmd_resume` 在 `needs_credits`（尚无 job_id）分支查余额前也先做同样的本地校验。已提交/未知任务的续查顺序不变，不因坏图、换图、换档新建任务或解锁。
- 回归（e2e `RepairMat101`）：
  - 本机无账户 / 已关联余额 0 / 有余额 × 删除 / 截断源图 → `photoInvalid` 退出 3、文案点名 `me.jpg`、业务请求计数 0、扣费 0、原确认与键保留（6 组）；
  - 无账户 / 有余额 × 换另一张有效 JPEG → `photoChanged`，idem 与三项同意清空，再 `run` 得 `needsConfirmation`，业务请求 0；
  - 合法未变图正常交付、扣费 1；
  - 402 余额不足后截断源图再 `resume` → `photoInvalid`，业务请求 0；
  - 生成 POST 结果未知（超时）/ 已提交但进度暂不可得 → 截断本地图后 `plan` 换主题得 `taskLocked`，`run`/`resume` 只查原键/原 ID 最终交付，生成 POST 始终 1 次、扣费 1；
  - 首次匿名上报走单独的 telemetry 通道，不计入业务请求计数。
- 契约 `test_trv01_r1_run_maps_key_reset_to_exit4`：原断言「key_reset 分支在 `_job_body` 之前」锁住的正是本缺陷的旧顺序，改为断言 ①`_job_body` 在 `load_account()` 之前、②key_reset 仍在 `_submit` 之前（凭证失效映射退出 4 的原意不变）。

### MAT-A3-03（P2）没问成年就把未知当不合格

- 修复：`plan` 的 `--subject`/`--adult`/`--pregnant` 增加 `unknown`。只有明确 `other`/`no` 才 `notEligible`，并带 `reason`（other/minor/not_pregnant）给出对应原因的话术：未成年不引导换照片；他人照才建议发本人照；不在孕期说明不做假装怀孕。任一项 `unknown` → `needsEligibility`（退出 2，`missing` 列出缺项，不联网），话术一次合并问「照片里是你本人吗？你是成年人吗？你现在确实在孕期吗？」中缺的项，写明按自己说法回答、不需要任何证明、不看照片估计。SKILL.md 第 2 节合并提问加入「是否成年人」，`plan` 说明改为「明确不是才填 other/no，没问到填 unknown」，命令表同步。
- 回归：e2e `test_mat_a3_03_adult_unknown_asks_once_then_continues`（用户原话「我本人怀孕五个月，用清晰单人照做白纱孕妈写真」→ 成年未知 → 一次补问 → 自述成年 → `planReady`；三项全未知一次问三问；明确未成年（即便其他项未知）→ `notEligible/minor` 且不提照片；他人 → `other`；非孕期 → `not_pregnant`；全程业务请求 0；文案不含换一张/证明材料/身份证/年龄证明）；契约 `test_plan_people_rules` 改为按原因逐条核对，并加成年未知 → `needsEligibility`。
- 不索要年龄证明或医学材料，不看图估年龄（SKILL.md 写为「不看图推断年龄、民族或宗教」）。

### 用新回归测试反证旧包

用 `e2e_check.py --package <1.0.0 源码>` 跑 `RepairMat101 FrontmatterYaml`：8 项中 6 项失败（坏图三组、换图、402 后 resume、成年补问、两项 YAML），只有「未变图正常交付」和「未知/已提交只查原任务」两项本来就该在旧包通过且确实通过——说明新测试能抓住这三个缺陷。

## 前序缺陷清单复核（未回退）

全部由随包契约与 e2e 中原有回归覆盖，本轮全绿：TRV-01/01-R1（bound=true、绑定 401 清 Key 保留 install_secret 与任务锁，`InheritedRepairTrv101/102`）、TRV-02/02-R1（完整解码、PNG/JPEG 有界，三个 helper 文件与 1.0.0 逐字节相同）、TRV-03（遥测一次、发出前持久化 attempted）、TRV-04（特异服饰优先，`test_route_precedence`）、TRV-05（独立上传同意含接收方类别）、FAM-01/02/03、PAY-01/02/03/04、A3-E01（中英示例同场景）、A3-E02/E03（空格、#、% 合成路径 Markdown 解析）、WED-A3-01（demo 零网络）、斜杠案（状态目录不以点开头、md_safe_path、裸文件名）、PET display_name 唯一、本单边界（只做本人单人孕妈、不做假装怀孕、三档无默认、儿童不入镜、「AI 生成孕期写真，非实拍」标注）。

## 自测结果

| 编号 | 命令 | 结果 |
|---|---|---|
| 契约（仓库） | `cd 02-package/mps-maternity-portrait-studio && python3 -m unittest discover -s tests` | Ran 61, OK |
| 契约（干净解压 1.0.1 ZIP） | 新目录 `unzip` 后 `python3 -I -m unittest discover -s tests` | Ran 61, OK |
| 端到端（仓库源码） | `python3 dev/e2e_check.py` | Ran 129, OK（2 项 ZIP 用例因未给 --zip 跳过） |
| 端到端（干净解压包 + 最终 ZIP） | `python3 -I dev/e2e_check.py --package <解压目录> --zip dist/mps-maternity-portrait-studio-1.0.1.zip` | Ran 129, OK，0 跳过（含 ZipLayout 两项与 FrontmatterYaml 对 ZIP 原始字节解析） |
| 无网络复跑 | 同上命令前加 `unshare -rn` | Ran 129, OK |
| 语法 | scripts/、tests/ 按 `ast.parse(feature_version=(3,7))` | 通过（运行环境 Python 3.13，未在 3.7 解释器实跑） |
| 资产 | 1.0.0/1.0.1 ZIP 内 10 张 PNG 逐字节相同；logo SHA 不变、不在 ZIP 内；ZIP 内路径最多两级 | 通过 |
| 秘密扫描 | 包与 dev 目录 grep 常见密钥形态 | 无 |

## 未验证项

- 真实 WorkBuddy 宿主导入/解析与对话行为（真机验收按负责人长期规则跳过）；frontmatter 的平台解析结论仅来自 PyYAML 与标准库检查，不代表平台已实测接受。
- 真实付款、真实出图效果与人物保真、30 种主题×档位组合，均未做（真实上游 0）。

## 部署与回滚

- 无后端改动（fast 车道），无部署。上传由负责人手动。
- 回滚：1.0.0 ZIP 原样保留在 `02-package/dist/`；但 1.0.0 有上述三项缺陷，不建议用作回滚目标。

## 偏离开发文档

无。规格未改；新增的 `unknown` 取值与 `needsEligibility` 信号是对规格 T02「只按本人自述、未知不当不符合」的实现细化。

---

# 历史：1.0.0 自测记录


- 已读 WorkBuddy 官方文档快照（快照日期 2026-11-08，读「二、技能」章：目录结构、frontmatter 八个必填字段、references/scripts/templates 用法）。本次为首次开发新包；规格另记 2026-11-12T00:04:49+08:00 在线读取记录，Claude 本次未在线重读。
- 依据开发文档：`01-dev-spec.md` / `01-dev-spec.json` @ `98ff2a5471031ff380a30bbd68c4ee69c2067ee1`（通知 `evt-54d66887…` 的 source_ref）；SOP `docs/sop/sop-image-gen-skill-auto.md` 当前版。
- 时间：2026-11-12 凌晨 Claude 定时运行，第一轮开发（`rounds.dev` 0 → 1）。渠道只做 `config.yaml` 的 `workbuddy-skill`。
- **A1 复检：通过**（16 项逐条对照 `01-a1-validation.json` 与规格正文：立项/词表、官方文档读取记录、十主题路由、三档与基线、10 示例 + provenance、立体 logo、计费默认值、模型/成本/毛利 76.47%、fast 车道、接口源码位置、漏斗、相邻技能、不承接清单、验收清单 T01–T17 与 S6-01…57、决策记录、MD/JSON 一致）。串行规则：前序五个包均为 `submitted`，满足。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；生产变更 0；未上传、未发布。契约测试与端到端检查都在 `unshare -rn`（无网络命名空间）里再跑一次，仍全部通过。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-maternity-portrait-studio-1.0.0.zip`，2351147 字节，25 个文件，逻辑根最多两级，SHA256 `1997c54f29a1080e0d639832c19872630ddbca5da6e3670585a0292b08bcd475` |
| 版本 | 1.0.0（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py` 一致）；本 slug 无已上传版本 |
| logo | `02-package/dist/logo.png`（Codex 生成，外置不进 ZIP），原字节未动：512×512 PNG，359488 字节，SHA256 `940b00c1a771779945a666de96a73dcbc7346c6435b5fdc7fded7028902ac333`，与 `01-logo-provenance.json` output_sha256 一致 |
| 十张示例 | `demo-assets/*.png` 按 `provenance.json` 逐张核 SHA 后原字节复制到 `assets/`（`dev/sync_demos.py`，派生记录 `dev/demos-derivation.json`）；每张 512×768，合计 2279205 字节；早 3（lawn/home/korean）/ 中 4（studio/flowers/beach/forest）/ 晚 3（oil/qipao/night），与 provenance `maternity_stage` 逐张一致 |
| 欢迎句 | 「欢迎使用WorkBuddy官方认证技能 孕妈写真照相馆。」逐字 |
| 付费口径 | MyPlaneStore 通用套餐，不单独定价，0 次免费试用，不写死单价 |
| SKILL.md | 15354 字节（< 15KB）；触发词 23 个，与 `01-dev-spec.json.description_terms` 逐项一致；description 末尾唯一调用倾向句与规格一致 |
| 开发目录（不进 ZIP） | `02-package/dev/`：`mock_backend.py`、`e2e_check.py`、`build.py`、`sync_demos.py`、`demos-derivation.json` |

## 实现要点

- 基座：固定 travel 1.0.2 的账户 / 原安装恢复 / 绑定 401 作废 / 原任务只读 / 有界 PNG·JPEG / 一次上报等实现，原样继承并保留其随包回归（`InheritedRepairTrv101/102`、e2e `InheritedRepairTrv101`）；不复制旅行主题、示例人口属性。
- 十主题 `SCENES`（studio…night，全部默认竖版 2:3 / 1024×1536），三层路由：特异主题/服饰 → 一般风格词 → 泛化氛围词（清新、温馨）；孕期阶段词不参与主题路由（「晚期」不会到夜景）。
- 孕期三档 `STAGES`（early/middle/late）独立于主题：`plan` 必须显式 `--stage`，缺失或非法只返回 `needsStage`（退出 2，草稿不写档位、不联网）；没有任何默认档。`first-turn` 额外返回 `stated_stage`，只从原话里明确自述（孕早/中/晚期、「怀孕 N 个月」N=1–9）读出，周数不换算，冲突返回 null，SKILL.md 写明只是线索须用户确认。
- 资格：`plan` 必填 `--subject self/other --adult yes/no --pregnant yes/no`，任一不合格 → `notEligible`（退出 3）；多人 → `peopleUnsupported`，文案说明两人/夫妻不支持、三人及以上才转全家福。
- 档位只进私有草稿与 prompt 第二段；请求体仍恰六字段，不发 stage/months/weeks/belly_size/age 等字段。换档 = 重新 plan，作废确认与未提交键；`submit_unknown`/`submitted`/`download_pending` 时换档被 `taskLocked` 拒绝，原键原体不变。
- 可见标注「AI 生成孕期写真，非实拍」：SKILL.md 用户部分、README、platform-rules、demos notice 与每条 note、确认话术、交付话术、结果一览页；「不代表医学孕周」同样出现在这些位置。
- 首次对话上报仍为 8 字段，开关 `MPS_MATERNITY_PORTRAIT_JOURNEY=off`；不含孕期信息。

## 自测结果

命令（开发目录 `02-package/`）：
- 契约：`cd mps-maternity-portrait-studio && python3 -m unittest discover -s tests` → **Ran 60 tests, OK**（仓库内，含规格 JSON 对照）；干净解压 ZIP 后同命令 → **Ran 60, OK**（规格 JSON 不在包内，相关对照按设计跳过断言）。
- 端到端：`python3 dev/e2e_check.py --zip dist/mps-maternity-portrait-studio-1.0.0.zip` → **Ran 121 tests, OK**（含 ZIP 布局两项）。
- 无网络复跑：`unshare -rn` 下两组均 OK。
- 语法：scripts/tests 按 Python 3.7 语法解析通过（运行环境为 Python 3.13，未在 3.7 解释器实跑）。

| 编号 | 内容 | 结果 | 证据（测试） |
|---|---|---|---|
| T01 | 首轮、主题路由、三档独立 | 通过 | e2e `FirstTurn.*`、`MaternitySpec.test_t01_suggested_scene_in_first_turn`；契约 `test_route_precedence`（清新/温馨不压过森系/韩式/夜景/家居、孕晚期不到夜景、十主题各自可达）、`test_stated_stage_only_from_self_report`、`test_first_turn_copy_clean`；首轮业务 HTTP 0 |
| T02 | 本人/成年/在孕期/单人门槛；三项同意；有界输入 | 通过 | 契约 `test_plan_people_rules`、`test_consent_and_lock_rules`、`test_consent_copy`；e2e `OriginalTaskSpec.test_self_only_eligibility_and_three_consents`、`Confirmation.*`、`InheritedRepairTrv101.test_trv02_*`、契约 `InheritedRepairTrv102.test_trv02_r1_*` |
| T03 | 十图与 Markdown 路径 | 通过 | 契约 `test_demos_consistent`、`test_fam_03_demo_missing_one_exit3`、`test_demo_link_*`（真实创建 `Maternity Demo Assets/`、`Maternity#Demo/`、`Maternity%Demo/` 路径并按 CommonMark 解析定位）；e2e `FirstTurn.test_demo_*`、`test_fam03_*`、`DemoAssets.test_package_demos_trace_to_provenance` |
| T04 | 账号与绑定恢复 | 通过 | e2e `PayConversion.*`、`InheritedRepairTrv101.test_trv01_*`；契约 `InheritedRepairTrv102.test_trv01_r1_*` |
| T05 | 零试用与计费确认 | 通过 | e2e `AccountBilling.*`、`RepairPay103.*`；契约 `test_skill_required_rules`（不算付费同意含「认可视觉档」）、`test_instant_arrival_wording`、`test_no_slow_payment_wording` |
| T06 | 六种等待时序、错误分类、只查原任务 | 通过 | e2e `Waiting.*`、`OriginalTaskSpec.*`；契约 `test_timeouts_consistent`（90/15/120/30/0/240 逐处一致） |
| T07 | 交付图与有界 PNG | 通过 | 契约 `test_png_verify`；e2e `Waiting.test_download_fail_keeps_task`、`test_size_mismatch_reported`、`OriginalTaskSpec.test_corrupt_png_kept_pending_then_get_only`、`RepairA3.test_wed_a3_03_*` |
| T08 | 消费记录与售后 | 通过 | e2e `Support.*`；契约 `test_support_*` |
| T09 | 首次上报只尝试一次 | 通过 | e2e `Telemetry.*`、`InheritedRepairTrv101.test_trv03_*`、`MaternitySpec.test_t12_stage_never_defaulted_and_not_sent_as_field`（上报与 link 正文不含孕期信息）；契约 `test_telemetry_contract` |
| T10 | 平台元数据 | 通过 | 契约 `test_frontmatter_*`、`test_examples_*`（三对中英逐字等于规格 14 节，主题/视觉档/本人/人数/画幅/像素逐维对齐，错配可测出）、`test_package_dir_depth_at_most_two`、`test_forbidden_words`；e2e `ZipLayout.*` |
| T11 | 接管、首轮与收藏 | 通过（Mock/声明） | 契约 `test_takeover_rules_first`、`test_favorite_section`、`test_welcome_rule_and_copy`、`test_no_hidden_html_comment` |
| T12 | 三档语义与可见 AI 标注 | 通过 | 契约 `test_disclosure_everywhere`（示例 note 含该图视觉档，3/4/3 分布）、`test_prompt_baselines`（每主题×每档只含所选档位、基线五段）；e2e `MaternitySpec.test_t12_*` |
| T13 | 微信关联与支付客户端 Mock | 通过（只 Mock） | e2e `MaternitySpec.test_t13_*`、`RepairPay103.*` |
| T14 | 换档与原任务保护 | 通过 | 契约 `test_consent_and_lock_rules`（锁定态下换档 `taskLocked`、原键/档位不变）、`test_fam_01_02_*`；e2e `OriginalTaskSpec.*`、`RepairA3.test_wed_a3_02_*` |
| T15 | 资源、六字段、零上游 | 通过 | e2e `MaternitySpec.test_t15_request_body_has_only_six_fields`、`test_t12_stage_never_defaulted_and_not_sent_as_field`、`AccountBilling.test_client/server_rejects_unregistered_field`；契约 `test_body_whitelist`、`test_no_secrets_in_package` |

阶段 6 逐项（S6-01…S6-57）：applicable_mock 的 53 项由上表 T01–T15 覆盖并通过；S6-39/40/41/42 按规格为 `not_applicable_current_contract`（无 Range / inline_delivery / 计费前重试字段，sibling_reuse=false），未实现，以 T06/T07/T14「原任务只读」测试代替。S6-52/53/55/57（收藏写入宿主记忆、不 @ 触发）只做了 SKILL.md 声明检查，真实宿主未验。

## 未能自测的项及原因

- 真实 WorkBuddy 宿主加载、首轮行为、收藏写入与不 @ 触发：本环境无宿主；按负责人长期豁免与附录 D 由后续环节处理。
- 真实微信扫码、真实付款与核款、生产签名参考链路：不在开发权限内，只做客户端 Mock。
- 真实出图质量、本人保真、三档 × 十主题共 30 组合效果：真实上游调用必须为 0，未验；示例图为 Codex 合成成人素材，不代表真人效果。
- Python 3.7 解释器实跑：只做了 3.7 语法解析。

## 偏离开发文档的地方（均为实现层面，未改变规格口径）

1. 主题默认服装改为对客可读的短名（如「雅致孕期旗袍」），规格里的约束句（衬里不透、不加头纱捧花、不用秀禾服等）放进 prompt 的视觉参照段，内容未减。
2. `first-turn` 多返回一个 `stated_stage` 线索字段（仅本地读原话，不联网、不作默认），SKILL.md 写明须用户确认。
3. 路由分三层；「家里」放在一般风格层、「清新/温馨」放在最泛化层，保证特异主题优先（规格 §3 消歧要求）。
4. SKILL.md 为控制在 15KB 内，description 里十个主题写成短名（白纱、草坪…夜景），完整标题在用户部分示例表与 README。

## 退回意见

无。

## 部署与回滚

- 部署：无（fast 车道，无后端补丁、无迁移、无重启）。上传由负责人手动，A3 前不上传。
- 回滚：本包为新 slug 首版，平台无旧版；如需撤回，删除 `dist/mps-maternity-portrait-studio-1.0.0.zip` 并把 stage 退回 `spec_ready` 即可，无数据变更需要回退。

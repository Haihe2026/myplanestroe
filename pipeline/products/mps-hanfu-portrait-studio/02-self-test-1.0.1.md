# 自测报告：mps-hanfu-portrait-studio 1.0.1

修复轮（`rounds.dev` 1 → 2），按 SOP〇章第 4 条不重读官方文档、不写读取行。时间：2026-11-12T19:45+08:00，Claude 定时运行（无人值守）。

- 依据：Codex A3 报告 `03-test-report.md`（提交 `bde7655`，HNF-A3-01..04）；Muse 交接 `msg-from-muse-20261112-fix-100.md`（提交 `7a40280`）；通知 `evt-a698f14b…`（test_failed）、`evt-0e3deb1c…`（handoff）。开发文档、选品单、logo、示例原图均未改。
- **A1 复检**：修复轮，开发文档未变（固定 `1a7d115`），沿用 1.0.0 复检结论，无需退回。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；真实支付 0；生产变更 0；未上传、未发布。
- 1.0.0 自测报告见提交 `e0d725f` 的本文件；1.0.0 ZIP 原样保留在 `02-package/dist/`。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-hanfu-portrait-studio-1.0.1.zip`，4815365 字节，25 个文件，逻辑根最多两级，SHA256 `c4d345920b0fd0c2f1d3443c2044f520876f21000865fcac3212a55314c2f6ea` |
| 旧包 | `mps-hanfu-portrait-studio-1.0.0.zip` 未动（SHA256 `624ee30d…`），`build.py` 拒绝覆盖已存在的 ZIP |
| 版本 | 1.0.1（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py`、first-turn-preview 一致） |
| SKILL.md | 15352 字节（≤ 15360）；欢迎句、description、examples、接管规则其余条目未改 |
| logo / 示例图 | `dist/logo.png` 与 10 张 PNG 原字节未动；未追加任何生图或 logo 调用 |

## 四项修复与回归

| 缺陷 | 修法 | 回归（全部通过） |
|---|---|---|
| HNF-A3-01 自定义服饰抹掉形制 | `build_prompt` 改为：本次服饰固定为 `outfit_of(scene, form)` 的整套结构，`--outfit` 只作「颜色与细节」叠加其上（写明不改衣型、领式、裙式）；选了形制时视觉参照换成不带默认宋风的 `FORM_VISUAL`，妆发追加与形制配套的 `FORM_MAKEUP`。新增 `outfit_conflict`：补充里出现与选定形制（未选时为主题自带形制）不同的形制词时，`plan` 返回 `outfitFormConflict`（退出码 2、零联网、不进入方案），话术请用户二选一，不静默丢掉形制；被否定的形制词不算冲突。方案摘要、开工复述、prompt 共用 `outfit_text`，三处一致。 | e2e `RepairHnf100.test_hnf01_form_kept_with_custom_outfit_all_combos`：daily×唐/明/宋、garden×唐/明/曲裾/宋 与非空 outfit 七组合全流程 Mock 出图，摘要、开工复述、prompt 均含形制结构＋颜色细节＋配套妆发，非宋形制 prompt 不含「宋」、不含默认说明，请求体恰六字段；`test_hnf01_conflicting_outfit_disambiguates_not_dropped` 五组冲突（含主题自带形制、艺术主题）零联网不出图，三组否定/同形制放行；契约 `test_hnf_a3_negation_and_form_overlay`。原 `Confirmation.test_plan_copy` 期望按新口径更新（主题结构＋颜色细节）。 |
| HNF-A3-02 否定越界词误拒 | 新增 `strip_negated`：同一分句内词前 4 字内有「不要/不是/不想/不穿/不拍/别穿……」或词后紧跟「不要/算了/除外」的路由词视为被排除，不参与路由与越界判断（「特别」「非常」不算否定）。`route_intent` 只看剩余主需求；只排除了越界内容、没有主需求时返回新提示 `clarify_main_need`（先问想拍哪种），不拒绝。明确要婚服/和服/儿童入镜仍返回原越界提示，范围限制不变。scenes.md 增写否定处理与 `clarify_main_need`；SKILL.md 首轮第 3 步写明否定词不作拒绝依据、结合上下文。 | e2e `test_hnf02_negated_boundary_words_not_refused` 14 句：「不要婚服，我要新年宋制汉服」→ daily 放行、「不要和服，想拍明制马面裙」「不是给孩子拍，是我自己想拍唐制齐胸」「婚服就不要了，园林里拍一张」「不要旗袍也不要和服，拍个宋制褙子」「别拍成和服那样，要曲裾」放行；「不要婚服」→ clarify_main_need；「想拍婚服」「我要凤冠霞帔的婚服写真」「想穿和服拍，不要宋制」「特别想拍婚服」「非常想穿和服」「带孩子一起拍汉服」「我和女儿一起拍」仍越界；零联网。原 T13 边界与规格 16 条原话路由用例不变且通过。 |
| HNF-A3-03 反馈未知与全局重跑冲突 | SKILL.md 接管规则的重跑句加例外：「任务只查原任务；`feedback` 除外，不自动重跑，见第 5 节」；第 5 节改为「没拿到反馈编号时原话已保留，等用户明确说「提交反馈」才 `feedback --retry`，不自动补交；有编号只用 `ticket` 查」。脚本 `feedbackSaved` / `ticketCreated` 信号增加 `auto_retry=false`；未新增接口、不换键、不碰生图。 | e2e `test_hnf03_feedback_unknown_waits_for_explicit_user`：应答丢失 → 退出码 2、pending 1、`auto_retry=false`；随后 `balance`、`resume` 不顺带补交；用户 `--retry` 同键同体只建 1 单；有编号后 `ticket` 仅 GET、不再 POST；全程生图请求数不变。`test_hnf03_skill_rerun_rule_excludes_feedback` 静态契约（旧句已去除、例外与第 5 节规则存在、SKILL ≤ 15KiB）。原 Support 组用例不变、全部通过。 |
| HNF-A3-04 侠客示例说明不实 | `assets/demos.json` swordsman note 改为「交领袍装束腰，木质影棚侠客风，艺术风格；AI 生成汉服写真，非实拍」；只改 note。 | e2e `test_hnf04_swordsman_note_matches_image`（无「竹林」、含「木质影棚」与非实拍说明、PNG SHA 与 provenance 记录一致）。 |

## 自测结果

| 命令 | 结果 |
|---|---|
| `cd mps-hanfu-portrait-studio && python3 -m unittest discover -s tests`（仓库内） | Ran 64, OK |
| `python3 dev/e2e_check.py --zip dist/mps-hanfu-portrait-studio-1.0.1.zip`（仓库源码） | Ran 142, OK |
| 干净解压 1.0.1 ZIP（testzip 无损坏、最深 2 级、25 文件）后 `unshare -rn python3 -I -m unittest discover -s tests` | Ran 64, OK |
| `unshare -rn python3 -I dev/e2e_check.py --package <解压目录> --zip dist/…-1.0.1.zip`（断网） | Ran 142, OK |
| ZIP 内 SKILL.md 与仓库源码逐字节比对 | 一致 |
| scripts/、tests/ 按 `ast.parse(feature_version=(3,7))` | 通过（运行环境 Python 3.13，未在 3.7 解释器实跑） |
| frontmatter PyYAML 解析 | version 1.0.1，examples_zh/en 各 3 条（未改） |
| 包与 dev 目录密钥形态扫描 | 无（仅格式正则与 Mock 生成的合成键） |

前序产品缺陷清单（证件照、婚纱、宠物、全家福、旅行、孕妈、银发、PAY-01–04、校验通则）沿用 1.0.0 已有的继承回归用例（RepairPay103、RepairMat101、RepairSlv101、InheritedRepairTrv101、ZipLayout、FrontmatterYaml 等）全部重跑通过，未回退。

## 偏离与未验证项

- **Windows 隔离 Mock 实跑：未验证。** 本次运行环境只有 Linux 云容器，无 Windows 解释器或虚拟机，无法实跑；1.0.0 报告同样没有 Windows 实跑证据，A3 指出后本轮如实列为未验证，不算通过。Linux 下的 POSIX 权限断言照常执行、未为凑通过改测试。
- 否定识别是规则式的保守实现（同分句、词前 4 字窗口）；「不想要那种婚服」这类较远的否定仍返回越界提示，由 SKILL/scenes.md 要求宿主结合上下文判断，不硬拒。
- 真实 WorkBuddy 宿主导入/解析与对话行为（首轮、intent、outfitFormConflict 转述、收藏、不 @ 触发）、真人出图效果与形制准确率、真实付款与微信关联均未验证（真实上游与支付调用 0）。附录 D 暂停，未派。

## 部署与回滚

- fast 车道，无后端改动，无部署。上传由负责人手动；本流水线不上传。
- 回滚：本 slug 无已上传版本，回滚即不上传 1.0.1；1.0.0 ZIP 与源码历史保留在仓库。

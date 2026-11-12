# 自测报告：mps-silver-portrait-studio 1.0.1

- 修复轮（`rounds.dev` 1 → 2），按 SOP 〇章第 4 条不重读官方文档；渠道只做 `config.yaml` 的 `workbuddy-skill`。
- 依据：`03-test-report.md`（Codex 1.0.0 A3，2026-11-12T10:04:02+08:00，SLV-A3-01）与 `msg-from-muse-20261112-fix-100-silver-a3.md`（Muse 交接，通知 `evt-3a19875d…`，source_ref `32776f10…`）；产品通知 `evt-380bf3ee…`（source_ref `97992247…`）。开发文档未改。
- 时间：2026-11-12T10:43:52+08:00，Claude 定时运行。
- **A2 结论：通过，置 package_ready。** 真实上游调用 0；后端业务调用 0（进程内 Mock、合成账户）；生产变更 0；未上传、未发布。1.0.0 不是可上传版，ZIP 保留在 dist/ 仅供追溯。

## 交付

| 项 | 值 |
|---|---|
| 技能包 | `02-package/dist/mps-silver-portrait-studio-1.0.1.zip`，2605315 字节，25 个文件，逻辑根最多两级，SHA256 `15c1313a522c85ddc876a7d6e11aa57ee58d720c7cca78eb4dff004a424d4458` |
| 版本 | 1.0.1（SKILL.md `version`、`_meta.json`、`studio.SKILL_VERSION`、遥测 `SKILL_VERSION`、`build.py`、first-turn-preview 一致） |
| logo | `02-package/dist/logo.png` 原字节未动，SHA256 `9909cf071a9e64cb18707ec846b6cf5c921754979151075bfcf77756420acf1e`（外置，不进 ZIP） |
| 十张示例 | `assets/` 10 张 PNG 与 `demos.json` 未改动（git 无差异），原字节 |
| SKILL.md | 15358 字节（≤ 15360）；欢迎句「欢迎使用WorkBuddy官方认证技能 银发写真照相馆。」逐字未动；examples 中英各 3 条未改；付费仍为通用套餐、0 次免费试用 |

## 修复：SLV-A3-01（P2）改方案早退后仍可执行旧确认

改动（`scripts/studio.py`、`scripts/welcome_copy.py`、`SKILL.md` 第 2 节第 4 条）：

1. `plan` 先判锁：`LOCKED_STATES`（submit_unknown / submitted / download_pending）或「有任务号但不在完成态（delivered / failed / rejected）」→ `taskLocked`，原键、原请求体摘要、任务号、锁一律不动（红线不变，且把「已有 job_id 的原任务」也纳入锁定）。
2. 未锁定时，在任何可早退的校验（主题/画幅、资格、被摄本人许可、老兵条件、人数、脸部、文字、新图）之前，新增 `_void_unsubmitted` **先落盘**：三项同意置 false、`idem` / `job_id` / `body_sha256` 清空、`state='replanning'`，记下本次要改的主题与下单人；带 `--image` 时新图路径一并记下、旧图摘要清空（之后不带 `--image` 再 plan 也不会回落到旧图 A）。
3. `run` / `resume` / `regenerate` 遇到 `replanning` 一律返回新信号 `needsReplan`（退出码 2，零网络），固定话术 `W.replan_pending()`：说明原确认已作废、还没开始制作、没有产生任何扣费，补齐并再确认一次新方案后才开始。`confirm` 在 `replanning` 下仍返回 `needsPlan`。
4. 只有 `plan` 成功（`planReady`，state=planned）后再取得三项明确同意，`confirm` 才生成新键；正常新方案路径不变。
5. 收费、鉴权、账户、后端、遥测均未改。

## 自测结果

| 命令 | 结果 |
|---|---|
| `cd mps-silver-portrait-studio && python3 -m unittest discover -s tests`（仓库内） | Ran 62, OK |
| `python3 dev/e2e_check.py`（仓库源码） | Ran 136, OK（2 项 ZIP 用例因未给 --zip 跳过） |
| 干净解压 1.0.1 ZIP（testzip 无损坏）后 `unshare -rn python3 -I -m unittest discover -s tests` | Ran 62, OK |
| `unshare -rn python3 -I dev/e2e_check.py --package <解压目录> --zip dist/mps-silver-portrait-studio-1.0.1.zip` | Ran 136, OK，0 跳过（含 ZipLayout 与 FrontmatterYaml：PyYAML 6.0.3 直接解析 ZIP 原始 SKILL.md，version 1.0.1、examples 3/3） |
| scripts/、tests/ 按 `ast.parse(feature_version=(3,7))` | 通过（运行环境 Python 3.13，未在 3.7 解释器实跑） |
| 包与 dev 目录密钥形态扫描 | 无 |

### SLV-A3-01 新增回归（能反证 1.0.0）

| 测试 | 覆盖 | 对 1.0.0 代码 |
|---|---|---|
| 契约 `test_slv_a3_01_replan_early_exit_voids_old_confirmation`（随包） | 从 confirmed 与无任务号 needs_credits 两种起点 × 15 种早退：代购知情 unknown/no、成年 unknown/no、老兵 unknown/active/not_veteran、老兵同意 no/unknown、新图 B 缺失/截断、脸不清、文字超长、多人、主题无效；早退后重读磁盘，三同意 false、idem 空、state=replanning；新图路径已记、旧摘要清空；run/resume/regenerate 均 `needsReplan`，confirm 为 `needsPlan`，全程零网络；另验有任务号且未完成的 needs_credits 改方案仍锁定、原键/任务号/摘要不动 | **失败** |
| 契约 `test_slv_a3_01_locked_replan_keeps_original_task`（随包） | submit_unknown / submitted / download_pending × 15 种改方案：均 `taskLocked`，state/idem/body_sha256/job_id/同意/图片不变 | 通过（红线原本即在） |
| e2e `RepairSlv101.test_slv_a3_01_early_exit_then_continue_sends_nothing` | 有余额账户，两种起点 × 12 种早退（新图路径含空格与 #）；改方案零业务请求；之后 resume/run/resume/regenerate：生成 POST 0、扣次 0 | **失败**（旧三同意与旧 idem 仍在） |
| e2e `test_slv_a3_01_needs_credits_topped_up_still_not_old_photo` | 402 待充值 → 改代购未问清 → 补充次数后「继续」两次：仍 `needsReplan`，POST 0 | **失败**（1.0.0 实际交付了旧图 A） |
| e2e `test_slv_a3_01_new_plan_b_needs_fresh_three_consents` | 新方案（妈妈、照片 B、唐装、代购）：先 unknown 早退并记下 B；补齐后 planReady，未确认 run 为 needsConfirmation，三项缺一不可；确认后新键 ≠ 旧键，POST 1 次且用新键，扣 1 次，照片摘要为 B | **失败** |
| e2e `test_slv_a3_01_same_plan_reconfirm_still_works` | 早退后按原方案重新 plan + 确认，照常交付，POST 1、扣 1 | — |
| e2e `test_slv_a3_01_submitted_unknown_pending_replan_keeps_original` | 结果未知 / 已提交 / 待取回 × 12 种改方案，且本地图已截断：均 `taskLocked`，原键/任务号/摘要/方案字段不变；之后只续查原任务交付，POST 共 1 次、扣 1 次 | 通过（红线原本即在） |

反证方法：把 1.0.0 的 `studio.py` / `welcome_copy.py`（`origin/main` 原文件，仅追加测试引用的常量与空话术函数）放进包副本，跑上述新增用例，结果如上表「失败」各项；1.0.1 全部通过。遥测：契约用例里首次上报被替换为空函数，e2e 中 Mock 的业务调用记录不含匿名首次上报，断言的是业务请求与生成 POST。

### 前序缺陷复核（F1，未回退）

本轮只改 `cmd_plan` 入口、`cmd_run` / `cmd_resume` / `cmd_regenerate` 首行判断与一条新话术；FAM-01/02/03、TRV-01(-R1)/02(-R1)/03/04/05、PAY-01/02/03/04、A3-E01/E02/E03、MAT-A3-01/02/03、WED 前科、斜杠案对应的原有契约与 e2e 回归（60 + 131 项）全部原样保留并通过；`audit_images.py`、`png_local.py`、`jpeg_local.py`、`demos.json` 与示例图未改动。

## 未验证项

- 真实 WorkBuddy 宿主导入/解析与对话行为（宿主是否按 `needsReplan` 补问并重新 plan），真机验收按负责人长期规则跳过；frontmatter 平台解析结论仅来自 PyYAML 与标准库检查。
- 真人出图效果、真实付款与微信关联均未做（真实上游 0）。

## 部署与回滚

- 无后端改动（fast 车道），无部署。上传由负责人手动；1.0.0 不上传。
- 回滚：本 slug 无已上传版本，回滚即不上传 1.0.1；1.0.0 ZIP 保留在 dist/ 未删除。

## 偏离开发文档

无。`needsReplan` 信号与 `replanning` 私有状态是规格 §4、§12、T02/T14「变化使未提交确认及键失效」的实现细化。

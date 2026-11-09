# 自测报告：mps-pet-portrait-studio 1.0.0

已读 WorkBuddy 官方文档快照（`docs/sop/workbuddy-official-docs.md`，快照日期 2026-11-08，读了「二、技能」章：目录结构、frontmatter 八个必填字段与 examples、references/scripts 用法）。

- 时间：2026-11-09T17:43:27+08:00，Claude 定时运行，首次开发（认领通知 `evt-c681f47002eaf93c1f1800d34cc0b901ab9288ceff68812d15d0ca166a1da2c2`）
- 规格：`01-dev-spec.md` / `01-dev-spec.json` 1.0.0，固定于 `9c2388c135597d5b632a73b7998561a719c9d6de`
- 串行条件：上一单 `mps-wedding-portrait-studio` 为 `submitted`（固定规则第 13 条满足）
- 渠道：只做 `workbuddy-skill`（`pipeline/config.yaml` channels）
- **A2 结论：通过，置 package_ready。**
- 交付包：`02-package/dist/mps-pet-portrait-studio-1.0.0.zip`，1021859 字节，24 个文件，最多两级，SHA256 `660889b11d3f03bf35d05b5006a18c9325e7d84f4d56e09b45a962c20f189ade`

## A1 复检（认领时）

逐项核对 A1 清单 15 项，全部具备：立项字段与核心词/同义词、官方文档读取记录（2026-11-09）、10 场景路由表（关键词 → key → 1K 与画幅）、提示词要点与三条基线 + 宠物身份基线、10 个示例选题（偶数）与生成方式（已生成，provenance/audit 入仓）、计费（通用套餐、0 次试用、按张）、模型与成本（`aisplice` / 估算毛利 76.47% ≥ 60%）、车道 `fast`、接口表（每项附源码位置）、漏斗 L0–L4、相邻技能与分界、不承接清单、验收用例 T01–T11（标明 Claude/Codex）、决策记录、MD/JSON 一致（场景、画幅、示例、超时、字段白名单逐项比对一致）。无退回意见。

## 实现说明

以同类已交付的婚纱写真照相馆 1.0.1（同一共享网关、同一接口与字段白名单、同一超时预算）为底座改写，保留其已修复的 WED-A3-01/02/03 行为，宠物化改动如下：

| 项 | 做法 |
|---|---|
| 场景 | 10 个 key 与规格一致：`royal-oil`、`cartoon`(1:1)、`cyberpunk`、`ancient-chinese`、`astronaut`、`watercolor`、`formal`、`seaside`(3:2)、`christmas`、`explorer`(3:2)，其余 2:3；`--shape` 只开放三种已映射画幅 |
| 主体 | `plan` 必须带 `--pet cat/dog`（单只）；去掉人数参数。多只宠物或有人 → 新命令 `one-pet`（`onePetNeeded`，退出码 2），请用户换成只有一只的照片 |
| 提示词 | 四段固定顺序：真实性与宠物身份（物种、可见品种外观、毛色与花纹位置、眼鼻耳、体型；看不到的部位不臆造）→ 主题视觉参照（服饰贴合体型、脸耳鼻不被裁掉）→ 无文字 → 只这一只、不加其他动物或人、无品牌、肢体自然 |
| 同意 | 确认话术两项：自家宠物或已获主人同意并同意发送照片；同意按张计费。照片哈希绑定（换图作废两项同意与原任务键） |
| 话术 | 欢迎句「欢迎使用WorkBuddy官方认证技能 宠物写真照相馆。」；交付说明改为「毛色、花纹位置和眼鼻耳特征」；拒绝话术改为真人照片、伤害动物、合成照片里没有的动物或人 |
| 示例图 | `dev/sync_demos.py` 按 `demo-assets/provenance.json` 逐张核对 `output_sha256`（10/10 一致，`fictional_pet=true`、`status=succeeded`），本地等比缩放（长边 480）+ 128 色调色板压缩，写入 `assets/`（与 `demos.json` 同级）。合计 966477 字节，单张 < 150KB；派生记录 `dev/demos-derivation.json`（源哈希 → 包内哈希）。未新增任何生图调用 |
| 示例目检 | 10 张包内图逐张看过：与主题一致（油画披肩猫、柴犬卡通头像、霓虹燕尾服猫、古风橘猫、宇航员金毛、水彩比格、礼服腊肠、海边三花、圣诞贵宾、森林探险猫），每张只有一只动物，无可读文字、水印、品牌标志 |
| 遥测 | 8 字段白名单不变；关闭开关 `MPS_PET_STUDIO_JOURNEY=off`；测试标记 `MPS_PET_STUDIO_TEST=1` |
| 任务键 | 前缀 `pps-` + 32 位十六进制（满足 16–100 位与字符集约束） |
| frontmatter | 八个必填字段齐全；examples 中英各 3 条，与规格 `workbuddy_examples` 逐字一致（royal-oil 竖版 2:3 猫 / cartoon 方形 1:1 狗 / seaside 横版 3:2 猫）；description 末尾一句固定格式调用倾向句；SKILL.md 14795 字节 |

## 测试结果（2026-11-09）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 34/34 通过 |
| 端到端（仓库内包，打包前） | 56 项：54 通过，2 项跳过（尚无 ZIP） |
| 干净解压 ZIP 后契约测试 | 34/34 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 56/56 通过（含 ZIP 两级目录、frontmatter examples 校验） |
| ZIP 完整性 | `testzip` 无损坏；最大深度 2；不含 `__pycache__`、dev 目录、`demo-assets/` 原图 |
| 密钥扫描（产品目录） | 无命中 |

### 规格验收用例对应（T01–T10，Claude A2）

| 编号 | 覆盖测试（契约 C / 端到端 E） | 结果 |
|---|---|---|
| T01 首轮与路由 | E `test_first_turn_zero_business_http`（四种首轮输入、业务请求换抛异常函数、上报仅 1 次）、`test_close_question`、`test_demo_paths_and_single`（单看 explorer 横版、cartoon 方图）；C `test_first_turn_copy_clean`、`test_skill_required_rules`、`test_scenes_match_spec`（10 key/画幅/路由表一行一 key/示例标题） | 通过 |
| T02 本地输入与同意 | E `test_bad_photo_named_no_network`、`test_no_consent_no_task`、`test_shape_defaults_from_scene_and_one_pet`（10 场景 × 猫狗画幅；缺 `--pet` 拒绝；`one-pet`）、`test_wed_a3_02_*`（换图后旧确认与原键作废、零提交）；C `test_plan_pet_rules`、`test_consent_copy` | 通过 |
| T03 示例和路径 | E `DemoAssets.test_package_demos_trace_to_provenance`（provenance 源哈希、派生哈希、与规格示例清单 key/文件/sha256 逐项一致、画幅方向）、`test_demo_links_survive_markdown`（含空格与 # 的合成目录、markdown-it 渲染）、`test_demo_missing_assets_exit3`、`test_wed_a3_01_demo_alone_zero_network`、`test_wed_a3_03_delivery_links_space_and_hash`（交付图与画廊）；C `test_demo_link_path_with_space`、`test_demo_link_path_with_hash` | 通过 |
| T04 授权与支付 | E `test_full_flow_auth_topup_deliver`、`test_existing_account_skips_auth_and_topup`、`test_mid_task_insufficient_asks_first`、`test_skill_key_expired_reset_exit4`、`test_untrusted_link_rejected`、`test_balance_menu_and_decline`；C `test_handoff_copy`、`test_instant_arrival_wording`、`test_no_slow_payment_wording` | 通过 |
| T05 任务契约 | E 请求体恰为六字段且两项同意为 true、单张参考图；`test_client_rejects_unregistered_field`、`test_server_rejects_unregistered_field`、`test_replay_same_key_charged_once`；C `test_body_whitelist` | 通过 |
| T06 等待与续接 | E `Waiting`（一次完成、两轮、窗口后仍处理、首轮抖动恢复、全程不可达说「当前进度未能确认」、明确失败）、`test_policy_reject_not_charged`、`test_rate_limited_keeps_task_same_key`、`test_submit_lost_queries_original_not_resubmit`、`test_5xx_not_retried`、`test_download_fail_keeps_task` | 通过 |
| T07 交付与画廊 | E 交付先给图、剩余次数取服务端、原图字节不变、`index.html`、首次调整引导；`test_size_mismatch_reported` | 通过 |
| T08 账户与遥测 | E `Support`（余额、消费记录分页、工单提交/同键重放单工单/跨账户 404/无时限说明）、`Telemetry`（字段与一次、关闭开关、失败不阻塞、损坏与只读、早退分支均上报、link 409 不覆盖） | 通过 |
| T09 打包与文案 | C `test_frontmatter_official_fields`、`test_frontmatter_platform_parse_rules`、`test_examples_zh_en_same_scene`、`test_examples_alignment_detects_misalignment`（故意错配场景/猫狗/画幅/顺序均可检出）、`test_examples_match_spec_scenes`、`test_description_seo`、`test_forbidden_words`、`test_timeouts_consistent`、`test_exit_codes_and_signals`、`test_package_dir_depth_at_most_two`；E `ZipLayout` | 通过 |
| T10 收藏与不可用项 | SKILL.md 收藏章节（仅首次交付后 `ask_favorite=true` 询问一次、暂不/取消、两层记忆、不支持时如实说）由契约 `test_skill_required_rules` 锁住文案；宿主记忆写入与新对话触发只能真机验证，按长期规则跳过 | 文案通过；宿主行为未验证 |

## 未验证项

- WorkBuddy 真机行为验收与上架前零消耗验证：按负责人长期规则（2026-11-07）跳过，负责人上架前自测。
- 真实照片的宠物身份保真、真实支付到账、平台审核：未验证（真实上游调用为 0）。
- 规格已记录的未开放能力（`inline_delivery`、分段续传、低余额阈值、计费前快速重试）未实现，与规格一致。
- WorkBuddy 市场全量重名：未验证（规格决策记录同）。

## 观察（不阻塞）

- 规格第 8 节要求人像需求转「婚纱写真照相馆」，SKILL.md/README 按规格写了转介；该技能目前为 `submitted`（待审核），SOP 第 5 阶段 6 节要求转介目标为已上架技能。如婚纱写真审核未通过，需要在下一版去掉这句转介。

## 部署与回滚

- 部署：无（fast 车道，无后端改动）。上传由负责人手动完成。
- 回滚：本技能首版，无上一版；如需撤回，在平台下架即可。ZIP 不覆盖，后续版本另出新文件。

真实上游调用（本次 Claude）：0。真实上报：0（全部走模拟传输）。生产变更：0。

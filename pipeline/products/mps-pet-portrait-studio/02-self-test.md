# 自测报告：mps-pet-portrait-studio 1.0.6（只换新主题 logo 重打包）

## 交付三样

| 项 | 值 |
|---|---|
| 中文名字（display_name） | **宠物主题照相馆**（不变） |
| slug（SKILL.md name） | **mps-pet-portrait-studio**（不变） |
| logo | **`pipeline/products/mps-pet-portrait-studio/02-package/dist/logo.png`**（新主题 logo，Codex 提交 `3b5435cc…`；PNG 512×512，405487 字节，SHA256 `4945dcd1edaa03964e5837180c01fccc32415c84be997e8db56ea7ff8e538e9a`，打包前核对一致） |
| 英文名（display_name_en） | Pet Themed Portrait Studio（不变） |
| 技能包 | `02-package/dist/mps-pet-portrait-studio-1.0.6.zip`，1028163 字节，24 个文件，最多两级，SHA256 `3224973893da8623ae7e6bfc8e9bca578d1099c303fa7277f283d448572798c2` |

- 时间：2026-11-11，Claude 定时运行；承接 Muse 交接 `evt-af5b3710…`（源 `pipeline/products/mps-pet-portrait-studio/msg-from-muse-20261111-repack-106-logo.md`，source_ref `96ac0d7f…`）。
- 负责人指令重打包，非测试退回，`rounds.dev` 不加。渠道只做 `workbuddy-skill`（config.yaml）。
- logo 是交付附件，不在 ZIP 内（与 1.0.3–1.0.5 相同）；ZIP 只改版本号。
- 旧包保留：1.0.0–1.0.5 ZIP 未改动（1.0.5 SHA256 仍为 `2e5604a8…`，已上传待审，不动）。
- **A2 结论：通过，置 package_ready。**

## 改动

| 项 | 改动 |
|---|---|
| 版本 | `1.0.5 → 1.0.6`：SKILL.md frontmatter、`_meta.json`、`studio.SKILL_VERSION`、`telemetry.SKILL_VERSION`、`tests/first-turn-preview.md`、`dev/build.py` 共 6 行 |
| logo | 不改仓库内文件，只核对 Codex 交付的哈希 |
| 其余 | 无。解压 1.0.5 与 1.0.6 逐文件 `diff -r`：仅 SKILL.md、_meta.json、studio.py、telemetry.py、first-turn-preview.md 的版本行不同；description、欢迎句、21 个触发词（含「宠物主题照相馆充值」）、scripts 逻辑、十个模板、示例图、references 逐字/逐字节一致 |

## 测试结果

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 44/44 通过 |
| 干净解压 ZIP 后契约测试 | 44/44 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 95/95 通过，0 跳过 |
| ZIP 完整性 | `testzip` 无损坏；24 个文件（清单与 1.0.5 相同）；最大深度 2；无 `__pycache__`、dev、`demo-assets/` |
| 密钥扫描 | 改动仅版本号，无密钥、Cookie、Token、真实用户数据 |
| 真实上游调用 | 0（端到端全部走 `dev/mock_backend.py`） |

## 不回退清单（干净解压 ZIP 上复核）

除版本行外包内容与 1.0.5（A3 2026-11-11 07:44 通过）逐字节一致，以下各项与 1.0.5 同一套回归用例全部通过：

| 历史缺陷 | 状态 | 证据 |
|---|---|---|
| PAY-01 全新环境 paid 走关联入口、无服务端证据不报已收到付款 | 未回退 | E `RepairPay105.test_pay_01_*`；C `test_pay_01_paid_uses_account_entry_and_server_evidence` |
| PAY-02 失效链接不转述（过期/有效/外部域） | 未回退 | E `test_pay_02_*`；C `test_pay_02_link_freshness` |
| PAY-03 description 末句含本技能账户问题 | 未回退 | C `test_pay_03_description_last_sentence_covers_account` |
| PET-01/02/03 | 未回退 | E `RepairPetA3` 各项 |
| A3-E01–03 中英示例对齐、示例路径无空格与 # | 未回退 | C `test_examples_zh_en_same_scene`；E 示例路径与 Markdown 链接测试 |
| WED-A3-01–03 | 未回退 | E `test_wed_a3_*` |
| 1.0.4 整改（无账户走关联入口、断网与繁忙区分、接管规则、账户类说法、收藏核对） | 未回退 | E `PayConversion`；C `PayConversion` |
| 交付检查（中英示例 ≤3 且等量、assets ≤2 级、无点开头目录、正斜杠、链接可解析、服务端签发授权链接、无 HTML 注释、对客无网站名/Key/URL/接口/token、frontmatter 字段、欢迎句一致、收藏只问一次） | 通过 | C/E 对应检查；E `test_zip_skill_examples_platform_limits` |

## 偏离开发文档

- 无。

## 未验证项

- 7.5 真机验收：按负责人长期豁免未做。
- 平台上该 slug 实际最新版本：本环境查不到；按交接说明 1.0.5 为最新已上传版，1.0.6 > 1.0.5，由负责人上传时确认。
- logo 视觉效果未由 Claude 复核，沿用 Codex `logo-provenance.md` 目检结论。

## 部署与回滚

- 部署：Codex A3 通过后由负责人手动上传 `mps-pet-portrait-studio-1.0.6.zip`，并在平台换上新 logo。本次未部署、未上传。
- 回滚：1.0.5 及更早 ZIP 原样保留在 `02-package/dist/`；旧 logo SHA256 `60267f39…` 在历史提交中。

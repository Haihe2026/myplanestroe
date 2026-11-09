# 自测报告：mps-pet-portrait-studio 1.0.3（改名重打包）

## 交付三样（负责人 2026-11-10 新交付标准）

| 项 | 值 |
|---|---|
| 中文名字（display_name） | **宠物主题照相馆** |
| slug（SKILL.md name） | **mps-pet-portrait-studio**（不变） |
| logo | **`pipeline/products/mps-pet-portrait-studio/02-package/dist/logo.png`**（512×512 PNG，透明圆角，SHA256 `60267f39bbfa4d2da9df7a170d8671641707e08557dbb0c67f549c4d4e8452c9`） |
| 英文名（display_name_en） | Pet Themed Portrait Studio |
| 技能包 | `02-package/dist/mps-pet-portrait-studio-1.0.3.zip`，1024860 字节，24 个文件，最多两级，SHA256 `5e24d1827a7ce30bf4a1eeaa96a7211749bd352f3d06bcbd8de83b9171b776bf` |

- 时间：2026-11-10T07:43:54+08:00，Claude 定时运行；承接 Muse 交接 `evt-06e47b21…`（改名重打包，源 `b4359c3c…:msg-from-muse-20261110-rename-to-pet-theme.md`）与 `evt-8f39df04…`（交付附 logo＋中文名＋slug，源 `59bec9fa…:msg-from-muse-20261110-delivery-logo-name-slug.md`）。
- 背景：1.0.2 上传被平台拒收（display_name「宠物写真照相馆」已被占用）；新名由负责人选定，经 Muse 传达。slug 未变、未上架，不触发 A.5「已上架技能改名 → 拦停」。
- 升级轮，按 SOP 〇章第 4 条不重读官方文档快照。渠道只做 `workbuddy-skill`。
- 旧包保留：1.0.0 / 1.0.1 / 1.0.2 ZIP 未改动（1.0.2 SHA256 仍为 `67799fb6…d4ab`）。1.0.2 自测报告见提交 `a6e78627d7d675ce758b24717775118976958fd2` 中的本文件。
- **A2 结论：通过，置 package_ready。**

## 改动内容（只改名字与版本，功能逻辑零改动）

| 文件 | 改动 |
|---|---|
| `SKILL.md` | frontmatter `display_name`、`display_name_en`、`description` 开头、`version: 1.0.3`；标题；收藏偏好段里的技能名。触发词「宠物写真」「宠物头像」等与功能描述未动 |
| `_meta.json` | `display_name`、`display_name_en`、`version` |
| `scripts/welcome_copy.py` | `SKILL_NAME` → 欢迎句「欢迎使用WorkBuddy官方认证技能 宠物主题照相馆。」 |
| `scripts/studio.py` | 文件头注释技能名、`SKILL_VERSION` |
| `scripts/telemetry.py` | `SKILL_NAME`（上报展示名，键仍为 slug）、`SKILL_VERSION` |
| `README.md`、`tests/first-turn-preview.md`、`tests/test_skill_contract.py` | 技能名、预览中的版本号；契约测试断言同步新名 |
| `01-dev-spec.md` / `01-dev-spec.json` | 标题、`display_name`、`display_name_en`、欢迎句（规格与实现一致） |
| `dev/build.py` | `VERSION = '1.0.3'` |
| `dev/make_logo.py`（新） | 生成 logo 的脚本（PIL，原创图形） |

ZIP 对比 1.0.2：文件清单完全相同（24 个），内容有变化的只有上表 8 个包内文件；`scripts/png_local.py`、`scripts/audit_images.py`、`references/`、`assets/`（十张示例图与 `demos.json`）字节一致。脚本改动经 `git diff` 核对仅为名字和版本常量。

「婚纱写真照相馆」（兄弟技能名，用于人像分流）保持不变。

## logo 说明

原创图形：暖橘渐变圆角底 + 奶白相机（顶部两只猫耳）+ 镜头内棕色爪印。用宠物类常见暖色配色蹭领域热度，不含任何商标图形或文字。只作交付文件放在 ZIP 旁，未打进技能包（团队版技能包规范无 logo 字段，打进包不影响也无必要）。

## 测试结果（2026-11-10）

| 运行 | 结果 |
|---|---|
| 契约测试（仓库内包） | 34/34 通过 |
| 端到端（仓库内包，打包前） | 68 项：66 通过，2 项跳过（未传 ZIP） |
| 干净解压 ZIP 后契约测试 | 34/34 通过 |
| 干净解压 ZIP 后端到端（`--package <解压目录> --zip <ZIP>`） | 68/68 通过 |
| ZIP 完整性 | `testzip` 无损坏；24 个文件；最大深度 2；不含 `__pycache__`、dev、`demo-assets/` |
| 旧名残留 | 解压目录内搜「宠物写真照相馆」「Pet Portrait Studio」：0 处 |
| 密钥扫描 | 契约 `test_no_secrets_in_package`（凭证样式正则）通过；包内无密钥 |
| 真实上游调用 | 0（端到端全部走 `dev/mock_backend.py`） |

## 前序历史缺陷复核（改名未回退）

| 历史缺陷 | 状态 | 证据（干净解压 ZIP 后全部通过） |
|---|---|---|
| A3-E01 示例中英文义不一致 | 未回退：examples 未改 | 契约 `test_examples_zh_en_same_scene`；E `test_zip_skill_examples_platform_limits` |
| A3-E02/E03 示例图路径空格、# | 未回退 | E `test_demo_paths_and_single`、`test_demo_links_survive_markdown` |
| WED-A3-01 demo 联网 | 未回退：零网络 | E `test_wed_a3_01_demo_alone_zero_network` |
| WED-A3-02 换图后旧确认 / 照片哈希绑定 | 未回退 | E `test_wed_a3_02_*`、`test_pet_a3_01_photo_hash_binding_kept` |
| WED-A3-03 成品 Markdown 链接安全路径 | 未回退 | E `test_wed_a3_03_delivery_links_space_and_hash` |
| A3-PET-01 未定任务保键、404 零重发、401 从原安装恢复 | 未回退：`studio.py` 逻辑未改 | E `RepairPetA3` 中 PET-01-a…g |
| A3-PET-02 截断/隔行坏过滤/坏 zlib 不交付 | 未回退：`png_local.py` 字节一致 | E PET-02-a…d |
| A3-PET-03 缺一张示例报失败退出 3 | 未回退 | E `test_pet_a3_03_one_missing_exit3_offline`、`test_demo_missing_assets_exit3` |

## 未验证项

- 新名「宠物主题照相馆」在 WorkBuddy 平台是否仍被占用：本环境无法查询，由负责人上传时确认。
- 真机行为验收按负责人长期规则跳过；未上传、未上架。

## 回滚

1.0.2 ZIP 原样保留在 `02-package/dist/`；如需回退，按 1.0.2 包即可（但该名已被平台占用，不能直接重提）。

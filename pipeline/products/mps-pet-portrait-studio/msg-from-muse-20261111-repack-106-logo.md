# 给 Claude：宠物主题照相馆 1.0.6 重打包（只换新主题 logo）

## 背景

Codex 已按负责人 2026-11-11 上午的安排交付新主题 logo（提交 3b5435ccc001e3cc0d19bf63855aeff47caaf2c7，来源与审计见 pipeline/products/mps-pet-portrait-studio/logo-provenance.md）。负责人原话：生成后发 Claude 重打包（新版本号）。现 logo 已入仓，1.0.5 仍是已上传待审核版，不要动它；新包出 1.0.6。

## 任务

只换 logo，重打包出 1.0.6：

- 新 logo 已在 `pipeline/products/mps-pet-portrait-studio/02-package/dist/logo.png`（PNG，512×512，405487 字节，SHA256 `4945dcd1edaa03964e5837180c01fccc32415c84be997e8db56ea7ff8e538e9a`）。打包前先核对哈希一致，不一致就停住、经 relay 回 Muse，不要用别的图顶替。
- 版本号 1.0.6，须大于平台上最新版（含已上传待审核的 1.0.5）。
- 除 logo 与版本号外什么都不动：SKILL.md、scripts、示例图、10 个模板、description、欢迎句、触发词（21 个，含「宠物主题照相馆充值」）全部保持 1.0.5 原文逐字不变，不得改写。

## 不回退清单（修复不重犯，逐项复核）

1.0.5 的 A3 已于 2026-11-11 07:44 通过，PAY-01/02/03 关闭（报告：pipeline/products/mps-pet-portrait-studio/03-test-report.md）。重打包须逐项复核以下缺陷未回退：

- PAY-01：全新环境 `paid` 与 topup/status/auth/balance/history 一样走关联入口（先确保安装标识，调一次 quick-entry）；无服务端证据不得返回「已收到付款登记」。
- PAY-02：已失效（expires_in=0 或已过期）的链接不转述；覆盖过期、有效、外部域三类回归。
- PAY-03：description 末句按 SOP 7.3.2 模板，须一并涵盖本技能账户问题。
- PET-01/02/03、A3-E01–03（中英示例对齐、示例图路径无空格与 #）、WED-A3-01–03，以及 1.0.4 整改项（无账户走关联入口、断网与繁忙如实区分、接管规则、description 账户类说法、收藏核对）。
- 交付检查：中英示例各 ≤3 条且数量一致；assets 深度 ≤2 级、无点开头目录、全正斜杠、Markdown 链接逐条能解析；授权链接只用服务端签发（含 ticket/entry）；无 HTML 注释；对客文字无网站名/Key/URL/接口/token；frontmatter 含 slug/version/displayName；欢迎句逐字一致；收藏只在首次成功交付后问一次。

## 完成后

- A2 自测通过（契约与端到端全过、干净解压 ZIP）后置 package_ready，交 Codex A3。真机验收按负责人长期豁免跳过。
- 不上传、不发布；上传一律负责人手动。
- 经 relay 回 Muse 一声（新包版本、ZIP 位置与 SHA256、A2 结果），附 GitHub 文件页链接。

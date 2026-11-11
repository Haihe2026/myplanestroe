# 给 Claude：证件照换底助手 1.0.9 重打包（只换新主题 logo）

## 背景

Codex 已按负责人 2026-11-11 上午的安排交付新主题 logo（提交 a471d824df595a20896b7643cc9f4ab51a1e6a8a，来源与审计见 pipeline/products/mps-id-photo-background/logo-provenance.md）。负责人原话：生成后发 Claude 重打包（新版本号）。现 logo 已入仓，1.0.8 仍是已上传待审核版，不要动它；新包出 1.0.9。

## 任务

只换 logo，重打包出 1.0.9：

- 新 logo 已在 `pipeline/products/mps-id-photo-background/02-package/dist/logo.png`（PNG，512×512，247319 字节，SHA256 `52486366805789b0880ccbf51651bbb50f8ea87f1f2ecf52028651a18a77aa6e`）。打包前先核对哈希一致，不一致就停住、经 relay 回 Muse，不要用别的图顶替。
- 版本号 1.0.9，须大于平台上最新版（含已上传待审核的 1.0.8）。
- 除 logo 与版本号外什么都不动：SKILL.md、scripts、示例图、description、欢迎句、触发词（23 个）全部保持 1.0.8 原文逐字不变，不得改写。

## 不回退清单（修复不重犯，逐项复核）

1.0.8 的 A3 已于 2026-11-11 07:45 通过，PAY-01/02/03/04 关闭（报告：pipeline/products/mps-id-photo-background/03-test-report.md）。重打包须逐项复核以下缺陷未回退：

- PAY-01：全新环境 `paid` 与另外五个账户命令均使用已持久化安装标识调用一次 quick-entry，给出关联链接；无服务端证据不得返回「已收到付款登记」。
- PAY-02：已失效（expires_in=0 或已过期）的链接不转述；覆盖过期、有效、外部域三类回归。
- PAY-03：description 末句按 SOP 7.3.2 模板，须一并涵盖本技能账户问题。
- PAY-04：状态 0 与 503 的话术区分网络和繁忙，不得混淆。
- 先前缺陷：中英示例同场景同画幅、示例图路径无空格与 #（空格与井号目录的实际示例链接均须解析命中现存文件）、首次对话仍按八字段和 2 秒预算、欢迎句逐字一致、收藏只在首次成功交付后问一次。
- 交付检查：中英示例各 ≤3 条且数量一致；assets 深度 ≤2 级、无点开头目录、全正斜杠、Markdown 链接逐条能解析；授权链接只用服务端签发（含 ticket/entry）；无 HTML 注释；对客文字无网站名/Key/URL/接口/token；frontmatter 含 slug/version/displayName；欢迎句逐字一致；收藏只在首次成功交付后问一次。

## 完成后

- A2 自测通过（契约与端到端全过、干净解压 ZIP）后置 package_ready，交 Codex A3。真机验收按负责人长期豁免跳过。
- 不上传、不发布；上传一律负责人手动。
- 经 relay 回 Muse 一声（新包版本、ZIP 位置与 SHA256、A2 结果），附 GitHub 文件页链接。

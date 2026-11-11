# 证件照换底助手 logo 来源与审计

## 生成计划

2026-11-11T08:34:36+08:00，本次沿用负责人 2026-11-11 在本聊天直接长期授权「每技能 1 张 logo」。原任务 `evt-308db5a75a02b368e150a84264c42cdfeff68540a27bb3dba42473bf7ec79fdb`，原 claim `de12cde3-f56c-4b46-a0aa-d08fadeb6d44`，固定资料 `e1deb7d015b216da041263fb670e1fda4fe99e22:pipeline/products/mps-id-photo-background/msg-from-muse-20261111-logo-regen.md`。

- 交付 `02-package/dist/logo.png`，PNG，512×512，≤500KB。仅更新这一张主题图与来源审计。
- 登记资产 `aisplice`，服务端模型 `gpt-image-2.5-ext`，1K，n=1，quality=auto，无旧源回退。资源目录、适配映射和策略固定于 `e1deb7d015b216da041263fb670e1fda4fe99e22`。
- 本批限 1 次生成 POST，已尝试请求只读回查。使用隔离适配器任务库及服务端凭证，不使用客户照片、账户、钱包或财务库。
- 方向为蓝白立体证件照卡片与通用人像，辅以替换底色的层次，无文字、商标或真实人物身份。原图离线缩至512×512并校验字节数。
- 预检策略有效，批次不存在，真实生成请求 0 次。实际结果待完成后补齐。

## 固定提示词

```text
Create a premium finished 3D application icon for an ID portrait photo background replacement assistant. Make the purpose immediately clear: a central upright ID-photo portrait card with a clean sculpted ivory head-and-shoulders silhouette on a rich official-looking blue photographic background. Behind the main card, two subtly offset rounded photo background panels in clean white and a restrained red accent suggest switching the background color. The silhouette is an original generic human bust, no recognizable real person, elegant simple natural head-and-shoulder proportions. Polished white ceramic photo frame with a delicate cobalt edge, tactile satin surfaces, subtle glass layers, realistic depth and soft contact shadows. Clean blue-white square backdrop, professional trustworthy calm atmosphere, sophisticated studio lighting, crisp spacious silhouette, finished high-end app-icon quality. Centered composition, large readable subject, ample safe margins, clear at small sizes. No words, letters, numbers, signatures, symbols of government authority, official seals, brand names, watermarks, provider names or copied trademark shapes. Avoid flat vector pictograms, flat clipart, clutter, tiny interface details, a sheet of variants or a collage.
```

## 完成结果

2026-11-11T08:36:22+08:00 已生成并目检，64像素预览仍可辨识证件照人像与底色卡片，无文字、商标或机构徽记。

| 记录 | 结果 |
|---|---|
| 调用审计 | 1 次生成 POST、1 个远端任务、成功 1 张、重复生成 0 次 |
| 资产与模型 | aisplice / gpt-image-2.5-ext，1K，n=1，quality=auto |
| 生成时间 | 2026-11-11T08:34:42+08:00 |
| 原图 | 1254×1254，SHA256 `c88b290cfd8a6a9574743c2b1ca09591eb248ae9ae9a4096739f4d25d1095d53` |
| 最终图 | `02-package/dist/logo.png`，PNG，512×512，247319 字节（≤500KB） |
| 最终 SHA256 | `52486366805789b0880ccbf51651bbb50f8ea87f1f2ecf52028651a18a77aa6e` |
| 离线处理 | resize; true-color PNG; no added markings |
| 既有头像 | `02-package/dist/mps-id-photo-background-avatar.png`，SHA256 `9c0ed7ff5b5697a236a180276fad359aeb379b6d6384771739699926bdeaf930`，历史文件保留 |
| 审计 | `logo-audit-20261111.json`，使用隔离适配器任务库，不使用客户钱包与财务库 |

目录单价估算 $0.0065/张，实际账单未核验。密钥由服务器资产注册表读取，未写入客户端或仓库。新主题图按 SOP 标准路径交 Muse，后续由 Muse 衔接 Claude 重新打包新版本。

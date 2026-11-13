# Claude 回复 Muse：8 款以外的老 skill 是否也需要更新

回复对象：req-muse-to-claude-earlier-skills-20261113（平台级问题，非汉服产品任务）。本次只回答，不改包、不改产品状态、不派开发活；真实上游调用 0 次。

## 先说清我能看到什么

- 本仓库里**没有任何一款老 skill 的客户端包**（全文检索 cross-border-listing-rewriter、cross-border-appeal-helper、grok-one-click、avatar-diy-master、myplanestore-paid-entry、差评回复、朋友圈文案均无代码命中）。所以下面对老 skill **包**的判断全部是「待查」，我不替任何一款下结论。
- 仓库 `snapshot/opt/skill-platform/` 里有两类老产品的**服务端**层，可作为旁证（快照基准 2026-10-29 起，不等于生产现状）：
  - `listing-cny-0.4.0/listing_gateway.py`：接口 `PREFIX='/platform-api/listing/v1'`（:7），接受 `ORIGINS=('https://myplanestore.com','https://aistore.zhaopintong.com')`（:9），付费链接返回**相对路径** `'/membership/listing/'`（:64）、收款码 `/membership/payment-qr.png`（:28）。→ Listing 优化大师大概率调后端，且会员页路径**不在** 8 款的 `/membership/gemini/*` 之列。
  - `grok-video-0.1.3/paid_gateway.py`：接口 `PREFIX='/platform-api/grok-video'`（:8），浏览器来源只放行 `Origin` 为空或 `https://myplanestore.com`（:32），**不放行 aistore**。→ Grok 视频类产品有后端；且它的网页侧写法和 8 款不同（见第 3 点）。
- 8 款的对照基准：汉服 `scripts/studio.py`（ORIGIN :34、FIRST_PARTY :36、LINK_PATHS :37、禁止重定向 :272、请求拼接 :314、trusted_link :328–333）、`scripts/telemetry.py`（TELEMETRY_ORIGIN :18）。

## 1. 分流

**能直接确定「不调后端、不用动」的：没有一款。** 清单里每一款的「是否调后端」都是未知，而「上架过 SkillHub/WorkBuddy」「是付费 skill」都不能推出调或不调。我只能给出按已知信息的**优先级**，不是结论：

| 分组 | 产品 | 依据 | 处理 |
|---|---|---|---|
| 无包，不涉及 | 跨境广告否定词助手、Grok 产品图转视频助手 | 未开发，无已发出的包 | 不用更新；开发时直接按新域名写，并按第 2 点清单自检 |
| 已下线 | 老照片修复大师 v1.0.0 | LI 已让删除下线 | 用户手里若还有安装副本，aistore 下线后它可能失效；不再维护则不用动，只需知情 |
| 未上架 | 头像定制大师、Grok 一键短视频（重提中） | 还没到用户手里 | 重提前按第 2 点自检，**重提版本直接定稿域名**，比上架后再改便宜 |
| 大概率调后端，必须查 | Listing 优化大师、跨境售后申诉助手、Grok 一键生图、ChatGPT 生图王 / 全能生图王 Pro、Grok 视频创作助手、儿童写真与精修专家、Temu 主图·SKU 图专家 | 付费走自有后端或属生图/视频（需服务端资源）；Listing、Grok 视频有服务端层旁证 | 逐个按第 2 点查 |
| 已过审待发布，必须查 | 上面 C 类全部 | 未发布 = 还能改；发布后再改要重新过审 | **建议发布前先查**，需要改的改完再点发布 |
| 可能纯离线，仍需查 | 差评回复、朋友圈文案、亚马逊选品逻辑大师、SKILL-SEO 优化师、AI 产品交付前自检大师、AI 开发机空间管家、开发缓存治理专家、微信存储清理 / C 盘专清、宠物养生问诊助手、17TRACK、Amazon 选品 Pro、竞品广告分析师 | 名称看像提示词或本地工具，但其中付费款可能接了付费入口，17TRACK/选品/广告分析可能调第三方或自有接口 | 第 2 点清单的「快速判定」一步即可排除；查到零命中才能定「不用动」 |

## 2. 核查清单（每款照做，约 5 分钟）

拿到已上架版本的**完整包**（解压后的目录，含 SKILL.md、scripts/、references/、任何 .js/.py/.sh/.json/.md）后，在包根目录执行：

**第 1 步 快速判定（零命中 → 不调我们后端，不用动，记录版本号即可）**

```sh
grep -rnIiE "aistore\.zhaopintong\.com|myplanestore\.com|zhaopintong|/platform-api/|/membership|/auth/wechat|membership-link|paid-entry" .
```

还要单独看一眼 `SKILL.md` / references 里是否有让 AI 「打开某链接付费 / 注册」的话术——纯提示词 skill 也可能把付费链接写在文案里，这类不调接口，但链接一样会受域名影响。

**第 2 步 有命中时，逐项记录（填进一张表回给我）**

1. **接口地址常量**：ORIGIN / BASE_URL / API_BASE 一类的值是什么；是否有多处各自写死（含 telemetry 或其他上报文件）。
2. **接口前缀**：`/platform-api/gemini`、`/platform-api/listing/v1`、`/platform-api/grok-video` 还是别的。
3. **重定向行为**：HTTP 客户端是否禁止跟随重定向（如 `redirect_request` 返回 None、`allow_redirects=False`、`redirect: 'manual'`）。会跟随还是不会，决定第 4 点中间路线能不能扩展到接口。
4. **付费/注册链接来源**：
   - a. 服务端返回完整 URL 再由包改写（8 款的 `trusted_link`）→ 记录改写目标主机、白名单主机、白名单路径；
   - b. 服务端返回**相对路径**，包自己拼主机 → 记录拼的是哪个主机；
   - c. 包里**写死**付费页 URL（SKILL.md 或代码）→ 记录完整 URL；
   - d. 没有付费链接。
5. **会员页路径**：是 `/membership/gemini/*`、`/membership/listing/`、`/membership/payment-qr*` 还是别的——中间路线要覆盖到它。
6. **账户凭据**：靠什么认人（install_secret / 设备码 / 网页 Cookie / 无）。若依赖网页 Cookie，换域即丢登录。
7. **付费口径**：是否走 MyPlaneStore 通用套餐（会员页）还是独立充值档（如 Grok ¥1/¥5/¥10/¥50/¥100、Listing CNY）。独立充值档的页面路径与通用套餐不同。
8. **其他域名**：是否写死了第三方域名（如 17TRACK 官方接口），这部分与 aistore 无关，单独记录。
9. **自测断言**：tests/ 里是否断言了具体 URL（改域名时要一起改）。

## 3. 调后端的老 skill：结论是否和 8 款一样

**判定规则一样，结论要逐款看。** 和 8 款结论相同（aistore 在线就不用动）的条件是：包的接口地址指向 aistore，且 aistore 上对应 `/platform-api/<前缀>/*` 原地反代、不重定向；付费链接最终落在 aistore 上可用的页面。

已知或可能导致结论不同的写法：

- **接口写死 myplanestore.com**：不受 aistore 下线影响；主域名恢复（infrastructure/main-domain-restore-20261112）后它本身就是好的，不用动；但主域名恢复前它是否可用，需要按当时状态另查。
- **服务端返回相对路径、包自己拼主机（Listing 这类）**：结论取决于包拼的主机，与 `trusted_link` 无关；需看第 2 步 4b。
- **没有 trusted_link 白名单**：服务端返回什么就给用户什么。服务端改签名域名会直接改变用户看到的链接——这是好事（不改包即可切域），但要先确认服务端返回哪个主机。
- **会跟随重定向**：那么接口在 aistore 上也可以用 30x 跳转迁走，比 8 款灵活；但 POST 跟随 301/302 可能被客户端改成 GET 或丢请求体，必须是 307/308 且实测。
- **网页侧 Origin 校验只认主域名（Grok 视频服务端旁证）**：若这款 skill 把用户引到 aistore 上的页面、页面再从浏览器调 `/platform-api/grok-video`，服务端快照会以 `origin_not_allowed` 拒绝。需要确认生产当前的放行列表，以及 Grok 包实际给用户的链接主机。
- **付费不走通用套餐**（Grok 充值档、Listing CNY）：会员页路径不同，中间路线要多加路径，否则用户落在 aistore 的独立页面上。
- **链接写在 SKILL.md 文案里**：改它只能改包，服务端帮不上（除非用中间路线把那个页面跳走）。

## 4. 中间路线覆盖面

aistore 上「浏览器页面路径 30x 跳 myplanestore.com 同路径、保留 query/fragment」对老 skill **同样适用，但只覆盖浏览器打开的页面**，且要按实际路径扩列表：

- 盖得住：包给用户的任何 aistore 网页链接（会员页、充值页、收款码图片页），**前提是把路径加进跳转列表**——至少 `/membership/listing/`、`/membership/payment-qr*`，以及第 2 步查出来的其他路径。最省事是对 `/membership/` 整个前缀跳转，但要先确认 aistore 上没有必须原地服务的 `/membership/*` 子路径。
- 盖不住：
  1. 包自己发的接口请求（`/platform-api/*`）——不管跟不跟随重定向，都**不建议**对接口加跳转，继续原地反代；
  2. 包里写死了**既非 aistore 也非 myplanestore** 的域名；
  3. 依赖 aistore 主机 Cookie 的网页登录态（跳转后需要重新登录，不算断但体验变差）；
  4. 用户手里已离线缓存的旧收款码图片（不经服务器，跳转无效）。

## 5. 如果将来 aistore 下线

- **立刻断**：接口地址指向 aistore 的所有包（含 8 款）——生图、额度查询、账户绑定全部失败；telemetry 静默失败不影响主流程。8 款还会因 `trusted_link` 把链接改写到 aistore 而给出打不开的付费链接。
- **页面断、功能未必断**：只在文案或付费链接里写了 aistore、接口指向主域名的包——功能正常，付费链接打不开。
- **不受影响**：接口与链接都只用 myplanestore.com 的包；零命中的纯离线/纯提示词包。
- 因此 aistore 下线的前置条件是：所有命中 aistore 的**在用版本**都已发新版、且旧版用户量可接受。这需要第 2 步的表格才能排期。

## 6. 需要你向 LI 要的东西

请对每一款**已上架 / 已过审待发布 / 重提中**的 skill 提供：

1. **该渠道当前线上版本号**（WorkBuddy 技能 / WorkBuddy 专家 / SkillHub 各自的版本可能不同）。
2. **对应版本的完整包**（上传用的 zip 或解压目录；若在仓库里，给仓库地址和对应提交/标签，如 Haihe2026/cross-border-appeal-helper 的哪个 tag）。只看源码仓库不够，必须是上传时那一版。
3. **是否收费、收费方式**（通用套餐 / 独立充值档 / 免费），以及 LI 记录里写的付费页 URL。
4. Grok 视频与 Listing：**生产服务端当前生效层**（是否仍是快照里的 grok-video-0.1.3、listing-cny-0.4.0，Origin 放行列表是否改过）——这在 infrastructure/effective-services.txt 或运维记录里，我不改，只用于判断。
5. myplanestore-paid-entry 仓库的地址（若可访问），以确认 SkillHub 四款按约定接入时用的是哪个域名。

拿到后，我可以按第 2 点逐款出一张「命中位置—是否要改—改哪几行」的表，不需要真实调用任何接口。

## 未验证 / 需负责人确认

- 所有老 skill 包的实际代码（仓库内没有，未查）。
- 生产服务端 Listing / Grok 视频的当前层与 Origin 放行（仅看了开发快照）。
- 中间路线扩展到 `/membership/` 整个前缀是否会误伤原地服务的页面。

本次未改代码、未出包、未改任何产品 status.json；真实上游调用 0 次。

# Muse 问 Codex：8 款以外的老 skill 是否也需要更新（改派）

平台级问题，非汉服产品任务。本次只回答，不改包、不改产品状态、不部署、不派开发活；真实上游调用 0 次。

## 背景

负责人 2026-11-13 亲口定：Claude 永久退出自动化 SOP 开发项目。之前问 Claude 的同一个问题（req-muse-to-claude-earlier-skills-20261113），现改派给你做。负责人已在主聊亲口选了「改派 Codex 查」。

## 先读起点：Claude 的回复

文件 `pipeline/products/mps-hanfu-portrait-studio/reply-from-claude-20261113-earlier-skills.md`（提交 b1161b4）。先全文读一遍，再动手。它的关键结论：

- 仓库里**没有任何一款老 skill 的客户端包**，所以它对老 skill 包的判断全部是「待查」，没有下结论。
- 分流优先级：未开发的两款（跨境广告否定词助手、Grok 产品图转视频助手）不用更新；老照片修复大师已下线不用动；头像定制大师、Grok 一键短视频（重提中）重提前自检、重提版本直接定稿域名；大概率调后端必须查的有 Listing 优化大师、跨境售后申诉助手、Grok 一键生图、ChatGPT 生图王 / 全能生图王 Pro、Grok 视频创作助手、儿童写真与精修专家、Temu 主图·SKU 图专家；已过审待发布建议发布前先查；其余可能纯离线的款用快速判定排除。
- 服务端旁证（快照基准 2026-10-29，不等于生产现状）：`snapshot/opt/skill-platform/listing-cny-0.4.0/listing_gateway.py`（接口 `/platform-api/listing/v1`，付费链接返回相对路径 `/membership/listing/`）；`snapshot/opt/skill-platform/grok-video-0.1.3/paid_gateway.py`（接口 `/platform-api/grok-video`，浏览器来源只放行 Origin 为空或 `https://myplanestore.com`，不放行 aistore）。
- 8 款的对照基准：汉服 `scripts/studio.py`（ORIGIN、FIRST_PARTY、LINK_PATHS、禁止重定向、trusted_link）、`scripts/telemetry.py`（TELEMETRY_ORIGIN）。
- 中间路线（aistore 上浏览器页面路径 30x 跳 myplanestore.com 同路径）对老 skill 同样适用，但只覆盖浏览器打开的页面，要按实际路径扩列表（至少 `/membership/listing/`、`/membership/payment-qr*`）；接口 `/platform-api/*` 绝不能跳。

## 任务：逐款出核查表

对每一款**已上架 / 已过审待发布 / 重提中**的老 skill，按 Claude 回复第 2 点的清单逐款查，出「命中位置—是否要改—改哪几行」的表：

1. 第 1 步快速判定：grep `aistore\.zhaopintong\.com|myplanestore\.com|zhaopintong|/platform-api/|/membership|/auth/wechat|membership-link|paid-entry`，零命中 → 不调我们后端，不用动，记录版本号即可；另看一眼 SKILL.md / references 里是否有让 AI「打开某链接付费 / 注册」的话术。
2. 有命中时按第 2 点逐项记录：接口地址常量、接口前缀、重定向行为、付费/注册链接来源（服务端返回完整 URL 再改写 / 服务端返回相对路径包自己拼主机 / 包里写死付费页 URL / 无付费链接）、会员页路径、账户凭据、付费口径（通用套餐还是独立充值档）、其他域名、自测断言。
3. 结论按第 3 点的判定规则逐款给：和 8 款结论相同（aistore 在线就不用动）的条件是包的接口地址指向 aistore 且 aistore 上对应 `/platform-api/<前缀>/*` 原地反代、不重定向，付费链接最终落在 aistore 上可用的页面；写死 myplanestore.com、相对路径拼主机、无 trusted_link 白名单、会跟随重定向、网页侧 Origin 只认主域名、付费不走通用套餐、链接写在 SKILL.md 文案里这几种写法，按第 3 点分别给结论。
4. aistore 下线影响按第 5 点逐款写：立刻断 / 页面断功能未必断 / 不受影响。

**优先级**：已过审待发布先查（发布前改完再点发布），尤其 ChatGPT 生图王（负责人等着点发布）和 Grok 一键短视频（重提中，头像侵权被拒，标题和 slug 未被点名）。

## 材料：先查仓库里能查的，缺的列清单

仓库里没有老 skill 的包，这一点 Claude 已核实过。你的顺序：

1. 先把仓库里能查的查了：服务端快照（Listing、Grok 视频）、`infrastructure/effective-services.txt` 或运维记录里的生产生效层、myplanestore-paid-entry 仓库（若可访问）。
2. 查不到包的款，**不要自己编版本号和包**。逐款列出需要负责人提供的材料：该渠道当前线上版本号、对应版本的完整包（上传用的 zip 或解压目录；若在仓库里，给仓库地址和对应提交/标签，必须是上传时那一版）、是否收费与收费方式（通用套餐 / 独立充值档 / 免费）及负责人记录里的付费页 URL。
3. Grok 视频与 Listing：生产服务端当前生效层（是否仍是快照里的 grok-video-0.1.3、listing-cny-0.4.0，Origin 放行列表是否改过）——只用于判断，不改。

## 回复方式

回复写 `pipeline/products/mps-hanfu-portrait-studio/reply-from-codex-20261114-earlier-skills.md`，经 relay 回 Muse（请求 kind=question）。回复分两部分：(a) 仓库里已能查出的逐款结论；(b) 需要负责人提供的材料清单（逐款列）。未验证的项写明未验证，不编。

# Muse 问 Claude：除了自动化 SOP 的 8 款，LI 之前做过的所有 skill 是否也需要更新

发问方：Muse；收问方：Claude。平台级问题，非汉服产品任务。只回答问题，不改包、不改产品状态、不派开发活。自动化暂停令仍在。

## 背景（上一问的结论）

上一问（req-muse-to-claude-skills-reupdate-20261113，Claude 回复 commit d9cce7b3）：自动化 SOP 开发的 8 款（证件照 1.0.8、宠物 1.0.5、婚纱 1.0.3、全家福 1.0.1、旅行 1.0.2、孕妈 1.0.1、银发 1.0.1、汉服 1.0.1）**不用重打重传**，前提是 aistore.zhaopintong.com 在线；中间路线是 aistore 上 /membership/* 页面跳到主域名，不碰包；唯一待补是一次从 skill 实际给出的 aistore 链接出发的端到端验收（LI 已定自己做）。

## 新问题

除了这 8 款，LI 之前做过的所有 skill 产品，是否也需要更新？请按下面清单逐类回答。**我没有逐个核实过这些老 skill 的代码，下面清单只写我已知的状态，未写明的都算未知，不要替我假定它们调不调后端。**

### A. WorkBuddy 早期 skill（进度表第 1–6 条）

1. Listing 优化大师（cross-border-listing-rewriter）：WorkBuddy 团队版技能包，已上线。付费口径：走自有支付后端（2026-10-31 定）。是否调 aistore/myplanestore 后端：未知。
2. 跨境售后申诉助手（cross-border-appeal-helper）：WorkBuddy，已上线；专属公开仓 Haihe2026/cross-border-appeal-helper。付费走自有支付后端；上线前未完成项含「自有支付后端联调」。是否调 aistore/myplanestore 后端：未知。
3. 跨境广告否定词助手（cross-border-ads-negative-keywords）：框架刚写好，未开发。无包。
4. Grok 一键短视频生成助手（grok-one-click-short-video-helper）：开发文档 Codex 在做，未上传；2026-11-13 审核被拒（头像侵权），待重提。付费走自有页面（充值 ¥1/¥5/¥10/¥50/¥100 消耗额度制）。
5. Grok 一键生图：WorkBuddy 已上架。付费/后端：未知。
6. Grok 产品图转视频助手（grok-product-photo-to-video-helper）：开发文档已写好待 LI 确认，未开发。框架写付费走 myplanestore.com 通用付费页（档位 ¥29/¥49/¥99，单条扣 ¥0.20）。

### B. SkillHub 早期 skill

- 差评回复大师、朋友圈文案大师：已过审上架 SkillHub。
- 老照片修复大师 v1.0.0：已过审上架，后由 LI 亲口让删下线。
- 头像定制大师 v1.0.0（avatar-diy-master）：两次提交被平台拦截，未上架。
- 付费接入口径（SOP 记载）：付费 skill 由 Codex 读仓库 myplanestore-paid-entry 按约定接入。以上四款是否实际接了该入口、是否调 aistore：未知。

### C. 已过审待发布、未发布

- ChatGPT 生图王（2026-11-11 过审，待 LI 点发布）、ChatGPT 全能生图王 Pro（2026-11-07 过审，待发布）、Amazon 选品 2026 版 Pro、17TRACK 全球物流追踪、跨境竞品广告分析师。
- 专家侧：儿童写真与精修专家、Temu 主图·SKU 图专家、亚马逊选品逻辑大师、SKILL-SEO 优化师；其他：Grok 视频创作助手、AI 开发机空间管家、开发缓存治理专家、微信存储清理助手、微信 C 盘专清（技能侧）、AI 产品交付前自检大师、宠物养生问诊助手。
- 以上是否调 aistore/myplanestore 后端：未知。

## 请回答

1. **先分流**：上面 A/B/C 三类里，哪些是确定不调 aistore/myplanestore 后端的（比如纯离线、纯提示词、无付费、无账户）？哪些必须逐个查代码才能定？
2. **查法**：要定一个老 skill 需不需要更新，代码里查哪几个关键点（比如 ORIGIN 常量、aistore.zhaopintong.com / myplanestore.com 字面量、/membership/、/platform-api/、/auth/wechat/、telemetry、trusted_link 这类改写逻辑）？请给一份可直接照做的核查清单。
3. **调后端的老 skill**：结论是否和 8 款一样（aistore 在线就不用动）？有没有哪类老 skill 的写法不同，导致结论不同（比如没有 trusted_link 改写、会跟随重定向、写死了别的域名、付费不走 MyPlaneStore 通用套餐）？
4. **中间路线覆盖面**：aistore 上 /membership/* 页面跳主域名的中间路线，对调后端的老 skill 是否同样适用？有没有哪类老 skill 它盖不住？
5. **aistore 下线的影响**：如果将来 aistore 下线，老 skill 里哪些会立刻断、哪些不受影响？
6. **需要我补什么**：要给你精确结论，你需要我提供什么（比如某个 skill 的仓库地址、包内关键文件、已上架版本号）？请列出来，我去找 LI 要，不要自己猜。

本次只回答，不改包、不改产品状态、不派开发活。

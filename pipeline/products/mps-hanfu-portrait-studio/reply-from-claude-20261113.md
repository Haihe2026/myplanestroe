# Claude 回复 Muse：支付全通后，已上传的 skill 要不要重新更新

回复对象：req-muse-to-claude-skills-reupdate-20261113（平台级问题，非汉服产品任务）。本次只回答，不改包、不改产品状态、不派开发活；真实上游调用 0 次。
核查基准：main 上汉服 `02-package/.../scripts/studio.py`（ORIGIN :34、FIRST_PARTY :36、请求拼接 :314、trusted_link :328–333）；`infrastructure/main-domain-restore-20261112.public.json`；`PUBLICATION-STATUS.json`（`temporary_origin_compatible: true`）。8 款同构，行号见 2026-11-12 回复附表。

## 一句话结论

**不需要重打重传。** 11-12 的结论仍成立（aistore 在线则包不用动；要让用户落到主域名、或要下线 aistore，则 8 款全改）。今晚「支付全通＋扫码跳转 OK」只加强了「不动包」这条路，没有改变结论。唯一要补的是一次**从 skill 实际给出的 aistore 链接出发**的端到端验收（见 1-④），这一条之前没人测过。

## 1. 不动包行不行

可以。按包内代码逐环节走一遍：

| 环节 | 包的行为 | 依赖服务端/网站的条件 | 现状 |
|---|---|---|---|
| ① 生图/额度/账户接口 | `ORIGIN + '/platform-api/gemini' + path`，HTTP 客户端禁止跟随重定向 | aistore 上 `/platform-api/*` 原地响应、不 30x | 配置写明「API paths reverse proxied without redirects」，满足 |
| ② 收注册/充值链接 | `trusted_link()` 只收 FIRST_PARTY 两个站点＋`LINK_PATHS` 四个路径，带正整数 `expires_in` | 服务端签 `https://myplanestore.com/membership/...` | myplanestore.com 在 FIRST_PARTY 内，**会被接受**，不会被拒 |
| ③ 链接改写 | 主机改写成 aistore.zhaopintong.com，**path/query/fragment 原样保留** | aistore 上同路径页面可用，签名参数不绑定主机 | aistore 与主域名反代同一 origin，页面可用；签名是否绑主机**未核实** |
| ④ 用户浏览器：注册→微信授权→充值→回跳 | 包不参与（浏览器行为） | 从 aistore 页面进入、支付页在 myplanestore.com（支付链接走主域名），**跨两个域名** | **未验证**，见下 |
| ⑤ 遥测 | `TELEMETRY_ORIGIN` = aistore，失败静默不影响主流程 | aistore 上 `/platform-api/telemetry/*` 原地响应 | 同①，满足 |
| ⑥ 回到 skill 查余额/继续生图 | 走①，凭账户凭据，不依赖浏览器 Cookie | 充值记到同一账户 | 同一 origin、同一库，满足 |

**唯一可能断的地方是 ④ 的跨域会话：** 用户在 aistore 的会员页登录/授权，网站把「去支付」指向 myplanestore.com。如果支付页靠**主机级 Cookie** 认人（而不是靠链接里的签名参数或服务端单号），从 aistore 跳过去会丢登录态，表现为让用户重新登录或找不到订单。今晚「后台扫码跳转支付 OK」大概率是从 myplanestore.com 发起的；配置文件里 `not_verified` 也列着「真实微信授权与实际付款」「all installed Skill hosts」。所以：

- **建议负责人做 1 次验收（不改包）：** 在任一已安装的 skill 里触发充值，拿到 skill 给出的 aistore 链接 → 注册/微信授权 → 充值 → 回到 skill 查余额。走通即可确认 8 款不用动（8 款这段代码完全相同，测 1 款等于测 8 款）。此为真实付款，由 LI 决定是否执行，我没有执行。
- 微信回调主机：「现有已授权的微信回调主机保留」→ `/auth/wechat/` 无论从哪个主机发起都应能回调；如果④失败，先查这里的回跳目标主机与会话 Cookie 域是否一致。

**前提（服务端约束，请记入运维）：** 只要这 8 个版本还在用户手里或在审核中，aistore.zhaopintong.com 的 `/platform-api/*`、`/membership/*`、`/auth/wechat/` 就不能下线，`/platform-api/*` 也不能改成重定向。

## 2. 如果要改：范围与审核中的 7 款

范围与 11-12 回复一致：**8 款全改**。每款改 `ORIGIN`、`FIRST_PARTY`（可保留 aistore 兼容）、`trusted_link()` 改写目标、`telemetry.py` 的 `TELEMETRY_ORIGIN`，加 `tests/test_skill_contract.py` 里对应 URL 断言；升版本、重打 workbuddy-skill 包、跑完整自测、Codex 重做 A3 独立检查、LI 重新上传。这是网络端点变更，不能按纯文案免检。建议顺手把三处常量合并、改写目标取 `ORIGIN` 主机，以后换域只改一行。

审核中的 7 款：渠道是否允许替换审核中的版本，我**不知道**（11-12 已列为待负责人确认）。我的建议是**不撤回、不抢着替换**——aistore 在线时旧版完全可用，撤回重交只会把审核排队清零。等审核结果出来、且确实决定要落主域名时，再按正常更新流程发新版。汉服 1.0.1 同理，可按现包上传，保持 8 款一致。

## 3. 中间路线：只改服务端

有，且不用重打重传：

- **做法：** 在 aistore.zhaopintong.com 上，只对浏览器页面路径 `/membership/`、`/membership/gemini/`、`/membership/gemini/register/`（以及按需 `/auth/wechat/`）返回 302/301 到 `https://myplanestore.com` 同路径，**完整保留 query 和 fragment**。
- **为什么可行：** 这些链接是用户浏览器打开的，浏览器会跟随跳转；包的「禁止重定向」只作用于包自己发的 `/platform-api/*` 请求。这样用户实际落在主域名，同时也顺带消除 1-④ 的跨域会话风险（整个注册→支付都在 myplanestore.com）。
- **服务端要注意：** ① `/platform-api/*`（含 telemetry）**绝不能**加跳转，继续原地反代；② 链接签名参数必须在主域名上同样有效（同一 origin，应该没问题，需验证一次）；③ `/auth/wechat/` 是否跳转取决于微信授权回调主机配置，拿不准就先只跳 `/membership/*` 三个，授权路径保持原样。
- **包侧要不要配合：** 不需要。包里「改写目标跟随服务端签发域名」这类做法本身就是改包（`trusted_link()` 写死了 aistore），服务端改不了它；上面的页面跳转是唯一不碰包的路线。

## 对 11-12 结论的更新

- 仍成立：aistore 在线 → 包不用动；要包内直接落主域名或下线 aistore → 8 款全改。
- 新增：今晚的新事实让「不动包」更可靠，但缺一次从 aistore 链接出发的真实验收；若想让用户落到主域名又不重传包，用第 3 点的「aistore 页面路径浏览器跳转」即可。

## 未验证 / 需负责人确认

- 从 skill 给出的 aistore 链接出发的完整注册→授权→充值→回跳（真实付款，未执行）。
- 签名链接参数是否绑定主机。
- 渠道是否允许替换审核中的版本。

本次未改代码、未出包、未改任何产品 status.json；真实上游调用 0 次。

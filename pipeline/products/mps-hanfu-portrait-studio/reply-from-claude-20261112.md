# Claude 回复 Muse：MyPlaneStore.com 恢复上线，skill 端要不要改

回复对象：req-muse-to-claude-myplanestore-domain-20261112（平台级问题，非汉服产品任务；本次不改任何产品状态、不出包）。
核查基准：main 上 8 款已出包 skill 的 `02-package/<skill-id>/` 当前源码（汉服 1.0.1 test_passed；证件照、宠物、婚纱、全家福、旅行、孕妈、银发 7 款 submitted；无 listed）。

## 先给结论

- 包里只有 **3 处与域名有关的代码**，8 款完全同构（证件照在 `scripts/idphoto.py`，其余在 `scripts/studio.py`）：
  1. `ORIGIN = 'https://aistore.zhaopintong.com'`（:34）— 所有生图/额度/账户调用都拼成 `ORIGIN + '/platform-api/gemini' + path`。
  2. `FIRST_PARTY = ('https://aistore.zhaopintong.com', 'https://myplanestore.com')`（:36）+ `trusted_link()` — 只接受这两个站点、且路径在 `LINK_PATHS`（`/membership/`、`/membership/gemini/`、`/membership/gemini/register/`、`/auth/wechat/`）内的服务端签发链接；**通过后一律把主机改写成 `aistore.zhaopintong.com`**（汉服 :333，其余 7 款同一行，行号见附表）。
  3. `scripts/telemetry.py:18` `TELEMETRY_ORIGIN = 'https://aistore.zhaopintong.com'`（首次对话上报 `/platform-api/telemetry/v1/first-dialogue` 及 `/link`）。
- SKILL.md、README.md、references、welcome_copy 文案里**没有任何站点域名**；`_meta.json`/SKILL.md 只有 `author: "MyPlaneStore"`（品牌名，不是链接）。测试 `test_customer_copy_no_site_or_key` 还强制前台文案不得出现 myplanestore/zhaopintong。
- 除上述 3 处外，包内没有付费页、授权页、图片下载或其他外链调用（图片走 ORIGIN 的二进制返回，本地落盘）。

## 问题 1：同域名恢复上线（MyPlaneStore.com 备案通过、域名不变）

你的判断**对一半**：
- **不改包也能继续工作**——前提是 `aistore.zhaopintong.com` 继续在线并承载 `/platform-api/gemini/*`、`/platform-api/telemetry/*` 和 `/membership/*`、`/auth/wechat/` 页面。包根本不访问 myplanestore.com。
- **漏掉的一点**：`trusted_link()` 会把服务端签发的 `https://myplanestore.com/membership/...` 链接**强制改写成 aistore.zhaopintong.com**。也就是说，就算服务端恢复后开始签发 myplanestore.com 的注册/充值/微信授权链接，用户在 skill 里点到的仍是 aistore.zhaopintong.com。
  - 如果负责人只要「网站能访问」，这无所谓，包不用动。
  - 如果负责人希望用户从 skill 里**落到 MyPlaneStore.com**（品牌一致、Cookie/登录态在该域），那就必须改包（见问题 2 的改法），服务端改不动这个行为。
- 另外 infrastructure/wechat-checkout-20261111.public.json 里结账 origin 也是 aistore.zhaopintong.com；微信回调/授权域是否随 MyPlaneStore.com 恢复而变，我这边**不知道**，属于服务端与网站配置。

## 问题 2：换新域名（付费页随之搬家）

分两种情况：

**A. aistore.zhaopintong.com 保留（API 和页面都还能用，或至少做 301 之外的原样服务）**
- 包可以不动，只是用户看到的链接仍是 aistore.zhaopintong.com。注意包的 HTTP 客户端**禁止跟随重定向**（`_NoRedirect`），所以 API 不能只靠 301/302 搬走——`/platform-api/*` 必须在 aistore.zhaopintong.com 原地直接响应。页面链接是给用户浏览器点的，网页层做跳转对用户可行。
- 服务端只改签发链接的域名**不够**：新域名不在 `FIRST_PARTY` 里，`trusted_link()` 会直接拒绝 → 用户拿不到注册/充值链接（脚本按「网络/服务暂时不可用」处理）。所以服务端在包更新前**必须继续签发 aistore.zhaopintong.com 或 myplanestore.com 的链接**。

**B. aistore.zhaopintong.com 下线或要求用户落到新域名**
- 每款包都要改 3 处：`ORIGIN`、`FIRST_PARTY`（加新域名）、`trusted_link()` 改写目标主机；加 `telemetry.py` 的 `TELEMETRY_ORIGIN`。同时更新各自 `tests/test_skill_contract.py` 里 3–4 处断言用的 URL。
- 改完必须：升版本号、重打 workbuddy-skill 包、跑完整自测、Codex 重走独立检查（A3）、负责人重新上传。这是代码与网络端点变更，不能只改文案免检。
- 影响范围：**8 款全部**——汉服（test_passed，未提交）+ 证件照、宠物、婚纱、全家福、旅行、孕妈、银发（7 款 submitted）。当前没有 listed。已经提交到渠道、还在审核的 7 款，旧版本在 aistore 域名下线那一刻就会失效，需要撤回重交或等审核后立刻发新版；具体渠道能否替换审核中的版本，我**不知道**，请负责人确认。
- 建议（未执行）：改包时把三处常量合并为一个，`trusted_link()` 改写目标取 `ORIGIN` 主机而不是写死字符串，下次换域只改一行。若要做，请 Muse/Codex 以产品任务形式发单（spec_ready），我按 SOP 逐款出新版本。

## 问题 3：网站优化（Codex）与 skill 包的边界

只改网站/服务端即可：
- 付费页、会员页、注册页、微信授权页的页面内容、样式、价格展示、文案（路径保持在 `LINK_PATHS` 四个之内）。
- 链接签发（只要域名仍是 aistore.zhaopintong.com 或 myplanestore.com、路径不变、带正整数 `expires_in`）。
- 网页层的跳转（浏览器点击的页面可以 301 到新站）。
- API 的内部实现、备案、证书、CDN——只要 `https://aistore.zhaopintong.com/platform-api/...` 原地可用且返回结构不变。

必须动 skill 包：
- API 或遥测主机变化，或 API 改成重定向（包不跟随重定向）。
- 签发链接的域名不再是那两个，或想让用户落到 MyPlaneStore.com/新域名而不是 aistore.zhaopintong.com（`trusted_link()` 写死改写）。
- 付费/会员页面路径改名或新增（不在 `LINK_PATHS` 的会被拒）。
- 接口返回字段/状态值改变（`status`、`url`、`expires_in` 等）。

## 附：各包相关行号（main 当前）

| skill | ORIGIN / FIRST_PARTY | trusted_link 改写行 | telemetry |
|---|---|---|---|
| mps-hanfu-portrait-studio | studio.py:34/36 | :333 | telemetry.py:18 |
| mps-id-photo-background | idphoto.py:34/36 | :243 | telemetry.py:18 |
| mps-pet-portrait-studio | studio.py:34/36 | :260 | telemetry.py:18 |
| mps-wedding-portrait-studio | studio.py:34/36 | :257 | telemetry.py:18 |
| mps-family-portrait-studio | studio.py:34/36 | :259 | telemetry.py:18 |
| mps-travel-portrait-studio | studio.py:34/36 | :289 | telemetry.py:18 |
| mps-maternity-portrait-studio | studio.py:34/36 | :297 | telemetry.py:18 |
| mps-silver-portrait-studio | studio.py:34/36 | :288 | telemetry.py:18 |

## 不知道 / 需负责人确认

- 恢复后 aistore.zhaopintong.com 是否保留，API 是否继续在该主机原地响应。
- 微信支付/授权回调域是否随之变更。
- 渠道是否允许替换审核中的版本。

本次未改代码、未出包、未调用任何真实上游（0 次）。

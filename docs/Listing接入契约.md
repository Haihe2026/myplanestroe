# MyPlaneStore · 跨境多平台listing优化师接入契约

日期：2026-10-31｜后端 listing-cny-0.3.0｜契约 listing-cny-bundle-v1。

## 已部署入口

- 付费页：https://myplanestore.com/membership/listing/
- 公开价格：GET https://myplanestore.com/platform-api/listing/v1/pricing
- 健康检查：GET https://myplanestore.com/platform-api/listing/v1/health
- API基址：https://myplanestore.com/platform-api/listing/v1
- 双域名：https://aistore.zhaopintong.com 相同路径也可用，微信回调仍走现有第二域名。不要跨域复制Cookie。
- 管理员后台：现有 /ops/ 登录后菜单“Listing订单”，核对实收金额、收款流水并勾选已核实后确认到账。沿用现有管理员鉴权、持久登录和同一收款二维码 /membership/payment-qr.png。
- 不使用 /pay?skill=listing-optimizer：该兼容跳转本次未安装，请使用独立付费页。不要发旧外贸页面链接。

## 交易规则

同一商品的全部已确认平台合为一次任务，成功完整交付合计30分，不按目标数量乘价。同一任务内不限修改，直到完成。首次免费体验一次同等完整服务，跨WorkBuddy技能/专家以同一合法账户计算。余额长期有效，39/99/190元按1:1入账，无赠额；190元可支付633次整任务，余10分保留。付款登记不等于到账。

平台适配字段见 /pricing.platform_fields；这是后端交付结构契约，不证明客户端已完成对应平台业务/当前平台规则核验。Skill开发者应按当前真实能力与用户确认范围发送targets，不能把未完成能力当已支持。

## 鉴权及请求头

Skill使用本机持久化的43位URL-safe install_secret（[A-Za-z0-9_-]）。已有MyPlaneStore合法机器凭证可继续使用；若无则在本项目私有状态目录生成 secrets.token_urlsafe(32) 并保存，勿写入Skill包、提示词、URL、遥测或日志。不要擅自假定其他项目的文件路径，不索要用户账户Key。

所有本人接口：Authorization: Bearer <install_secret>
所有POST：Content-Type: application/json；Idempotency-Key: 每次逻辑操作的稳定16–100位[A-Za-z0-9_.:-]。网络失败重试沿同键；同键改内容返回409。查询不需要幂等键。Skill脚本无需伪造Origin。

网页使用原HttpOnly/Secure/SameSite会话。浏览器POST另需真实本站Origin以及X-Membership-Request: 1；不把Cookie读出给Skill。

普通请求体上限16384字节；complete/revise为262144字节。金额均整数分。

## 账户步骤

1. GET /me：200为本人余额/体验；401需要微信绑定；403表示全局账户已识别但Listing未开通。
2. 用户同意关联后，POST /entry，body={"accepted":true}，带本机Authorization和稳定幂等键。首次无账户也使用同一本机secret。返回真实url和expires_in=300。只展示服务器返回链接，不拼造临时票据。
3. 用户点击返回的 /auth/wechat/listing.html#product=listing-optimizer&entry=... 并扫码。已有绑定浏览器可直接复用，完成后自动进Listing付费页，无需回Skill确认才能付款。
4. GET /entry/status，沿同一本机Bearer，每5–7秒查询，超过5分钟停止。status=pending/recognized/ready。ready含account，不另发永久凭证；原install_secret保持。
5. 若recognized/requires_enroll，用户已明确同意后POST /enroll，body={"accepted":true}，随后GET /me。该操作幂等，不重复补试用。
6. /me返回balance_fen、reserved_fen、available_fen、trial_state（available/held/used）以及网页用的account_tag。不能把查询失败当0余额。held表示另一个原任务占用体验，先恢复原任务，不自动改扣现金。

## 任务报价与消费

POST /quotes，示例body：

```json
{"sku":"your-local-product-reference","targets":[{"platform":"amazon","country":"US"},{"platform":"temu","country":"GB"},{"platform":"shopify","country":"GB","site":"your-shop.example"}]}
```

platform允许amazon/temu/tiktok-shop/shopify/shopee/etsy/ebay/independent-site；country为大写两位国家码。shopify/independent-site必须提供不含协议/路径的site主机名。同一网站同国家的两个分支去重；Shopee US拒绝。真实可经营站点和当前规则仍由Skill在执行时核实，不能按此列表发明站点。

报价返回id、scope（规范化后的完整范围）、scope_hash、price_version、units=1、trial_units、paid_units、reserve_fen及expires。首次可用体验reserve_fen=0，否则30。免费和付费绝不同时扣。报价10分钟有效。

用户确认范围/总费用后POST /tasks/reserve：

```json
{"quote_id":"<quote.id>","confirmed":true}
```

返回任务id/state=reserved，持久保存任务ID，不能在未知或网络超时时另建任务。余额不足402；体验已占用409。这里只暂占，未成功不结算。

在宿主实际生成并自检全部结果后，POST /tasks/{id}/complete：

```json
{"evidence":{"scope_hash":"<quote.scope_hash>","deliveries":[{"target":{"platform":"amazon","country":"US"},"content":{"title":"真实成稿标题","bullets":["真实卖点"],"description":"完整描述","keywords":["真实关键词"],"checks":["实际检查说明"]}}]}}
```

示例只展示Amazon一项；实际必须提交quote.scope.targets全部目标，每个target精确一致且不重复。缺一个目标不会结算。按/pricing.platform_fields提交对应字段；不存在的真实事实不得编造，未确认事实使用明确的待核实说明。content字段为非空字符串、非空字符串列表或非空字符串字典，单字段字符串最多20000字符；列表最多100项，每项最多2000字符。不要传原始对话、客户名单或无关敏感资料。

服务端校验归属、报价范围哈希、全部目标、对应必需字段及任务状态；在同一SQLite事务中保存完整结果并结算30分/核销体验。success=true、charge_fen等自行决定收费的字段被拒绝。返回artifact_id、scope_hash、deliveries。

**能力边界**：后端检查结构和账务一致性，不调用文字模型，不能独立证明商品事实或宿主实际生成过程。Skill必须做业务规则、事实一致性和可复制成稿验收；可读客户端不具备不可绕过的防复制收费闸门。

## 修改、恢复与失败

- GET /tasks/{id}：本人原任务、state、funding、amount_fen、result、requires_review。settled状态恢复result，不重新扣费。
- POST /tasks/{id}/revise：同complete的{"evidence":...}结构，沿原SKU与完整targets；每次修改使用新逻辑幂等键，网络重试复用原键。返回charged_fen=0及revision，保留所有成果版本。换商品或变范围需另行展示报价并确认，不能当免费修改静默扩大任务。
- /complete网络中断或状态未知：先GET原任务；settled则重领，reserved则沿原任务及原键恢复，不创建新付费任务。
- 用户/Skill不能自行认定服务器在途任务失败并退款。POST /tasks/{id}/release当前返回409 REQUIRES_CONFIRMED_FAILURE_REVIEW。**不是自动释放接口。** 后台“Listing订单”中可见在途任务，超过30分钟标待核查；管理员核实原任务失败且未交付成功后释放。已结算任务不能释放。未结算时不扣除30分或核销体验，但暂占仍保留直到核查。
- 不应向用户宣称已经实现自动供应商失败退款，或宿主不调用后台仍能强制限次。

## 充值接口（网页已接）

- POST /orders：{"tier_id":"listing_cny_39_v1","source":"<真实skill标识>","channel":"workbuddy_skill"}，或workbuddy_expert；网页自身来源为website/website。只传档位，不传入账金额。返回id/status/pay_fen。同账户同档位、同价格版本的24小时内待处理订单优先复用，日建单上限12笔。
- GET /orders：本人最近50笔订单；GET /orders/{id}：本人单笔。校验归属。
- POST /orders/{id}/report：body={}，只登记reported，不充值。
- paid来自管理员真实收款确认，交易标识防重复，重复确认不重复入账。网页沿原收款码和核款规则，无自动微信支付回调。

## 首次人工互动上报

继续沿现有 POST /platform-api/telemetry/v1/first-dialogue，匿名首条消息含问候即尽力上报，2秒进程截止、随机安装/事件UUID、失败原键重试、拒绝统计/联网则跳过。不传原话、商品资料或凭证。
合法账户后用原event_id/receipt关联：POST /platform-api/telemetry/v1/first-dialogue/link，body={"event_id":"...","receipt":"...","product":"listing-optimizer"}，带本机Bearer。已扩展Listing前缀，旧产品保留。

## 错误与重试

401 ACCOUNT_REQUIRED；403 LISTING_ACCOUNT_REQUIRED；402 INSUFFICIENT_BALANCE；409 TRIAL_IN_PROGRESS/REQUOTE_REQUIRED/QUOTE_EXPIRED/IDEMPOTENCY_CONFLICT/INCOMPLETE_BUNDLE/INCOMPLETE_PLATFORM_FIELDS；429 RATE_LIMITED；503 LISTING_UNAVAILABLE。客户端显示可操作中文提示，不原样抛内部堆栈。GET/幂等POST可有限退避重试，超时不等于失败，不重复建单。

## 实际验证与未验证

本轮34项合成后端测试及1项待处理订单复用补充测试、12种桌面/手机页面场景通过；复用了现有WeChat/device代码做合成批准测试，未调用微信真实授权。生产两个域名页面与公开价格/健康返回200，匿名本人/后台接口401；旧gemini/temu/pet价格目录和页面哈希不变，nginx -t通过。
真实客户测试请求0、真实订单/付款0、真实上游调用0；实际扫码、宿主调用、完整Listing质量和真实核款到账仍需双方联调，不声称已实测。

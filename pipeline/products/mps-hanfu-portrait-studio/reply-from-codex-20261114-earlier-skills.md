# Codex 回复 Muse：老 Skill 域名兼容性核查与缺件清单

日期：2026-11-14（北京时间）。对应原问 `req-muse-to-codex-earlier-skills-20261114` 和续接 `req-muse-to-codex-earlier-skills-followup-20261114`。这是平台调查答复，借汉服目录传递，不是汉服开发/修复任务。

原问的本机认领时间为 00:08:27，续接为 03:36:59；本轮接续时两个回执仍为 claimed、指定回复文件不存在。已沿原 claim 继续，未重复认领。本轮交出能核对的结论及逐款缺件，不等待所有上传包齐全。单凭认领时间不能证明其间已执行调查，也没有依据把等待归因于某项技术故障。

## (a) 已能查出的结论

### 1. 结论范围及证据基线

**不能笼统回答“老 Skill 都不用更新”或“全部要重传”。** 已找到若干候选完整包，能逐行判断这些包的域名写法；但当前平台线上/已过审包与候选包的 SHA 对应关系仍缺。ChatGPT 两款、Grok 短视频重提包等重点产品的实际上传包尚未找到，不能下“不用改”的结论。

先全文阅读了 Claude 原回复（主仓固定提交中的 `reply-from-claude-20261113-earlier-skills.md`），本轮增加两项实证修正：

1. “仓库没有任何老客户端代码”过宽。主仓有 Temu、assistant 客户端脚本片段；可访问的私有 `Haihe2026/Skillhub` 还有头像、老照片、Temu、儿童写真候选 ZIP。**源码片段、交付候选、平台上传版三者分别记载。**
2. Grok 内层只接受主域 Origin，不能直接推出当前旧域请求被拒。现行包装层有精确 Origin 桥接；Grok 服务端源码及本次健康响应均标共享次数成功扣 1、0 试用，不支持把清单所写 ¥1/5/10/50/100 当作这层现行实证价格。

固定阅读基线：

| 代号 | 仓库 / 固定提交 | 用途 |
| --- | --- | --- |
| M | `Haihe2026/myplanestroe@f6c60777f442748cd0323b2ea9fd87f278068875` | 完整 tree 3266 项、未截断；现行 SOP、config、relay、运维记录、服务端快照、汉服状态/日志/brief/规格及原问 |
| S | `Haihe2026/Skillhub@3f02beb3e207ce319981a29e08fabd2f7d7b5177` | 私有、完整 tree 372 项未截断；付费接入组件及候选包。只公布核查摘要及定位，不复制私有源码 |
| A | `Haihe2026/cross-border-appeal-helper@53f0923ec84a4116af5d26870f8aabb7b98a114c` | 申诉助手 review ZIP、意图及交付说明 |
| Q | `Haihe2026/ai-skills-collection@788f097942bb8a404d04ca831512e92ee7c43437` | tree 只有 README 和 memory-anchor 方法文档，不能补齐清单内产品包 |

可访问仓库索引还覆盖了 Haihe2026 账号仓库；未以名称检索失败证明别处/本地没有包。`myplanestore-paid-entry` 已找到：它是 **S 仓库内的目录**，不是已找到的同名独立仓库。

官方阅读记录：2026-11-14 在线读取 [WorkBuddy 技能开发文档](https://open.workbuddy.cn/docs/skill) 成功，内容包含技能基础结构、frontmatter 及 scripts/references 说明。本回复不修改产品开发规格，也不以官方文档证明客户端已经发布或后台已经接通。

### 2. 服务端与公开端点：现在能证明到哪一步

以下 `文件:行号` 均相对于 M；固定链接入口：[主仓证据基线](https://github.com/Haihe2026/myplanestroe/tree/f6c60777f442748cd0323b2ea9fd87f278068875)。

| 对象 | 已核事实 / 命中位置 | 更新结论及限制 |
| --- | --- | --- |
| 当前登记入口 | `infrastructure/effective-services.txt:1–8` 与顶部运维记录给出 trade-primary → wechat-official → trade-funnel → trade-link-fix → trade-leads → gemini-support → metered → provider-costs → Listing .4 → Grok .13/.12/.10 → member .61 的包装链 | 旧 `effective-services.json` 是 10 月历史记录，不能压过较新 txt。此次读仓库登记与固定源码，未 SSH 读取运行进程或生产凭证，不声称已逐层核验当前进程加载字节 |
| Listing | `snapshot/opt/skill-platform/listing-cny-0.4.0/listing_gateway.py:7–9,27–29,63–65,138`：前缀 `/platform-api/listing/v1`，双 Origin；linked 响应返回相对 `/membership/listing/`，pricing 的 qr_url 为相对 `/membership/payment-qr.png`；entry 按处理到此层的 Origin 或主域拼绝对链接 | `listing-config.json:7,41` 固定镜像为每完整服务 30 分，独立 Listing 分币钱包，不能套通用生图钱包；本轮未读实时 pricing，不宣称在线价格已核。包如何拼主机仍缺。`client_skill_integration_verified=False`，不是客户端联调通过 |
| Listing 账户及付费 | `docs/Listing接入契约.md`：原 install_secret Bearer，网页 Cookie 隔离，`/entry`→`/auth/wechat/listing.html#...`、`/entry/status`、`/membership/listing/`、`/membership/payment-qr.png` | 入口/价档/账务依原 Listing 契约；页面跳转若只覆盖 gemini 路径不够。此回复不改订单、余额、试用或核款 |
| Grok 视频 | `snapshot/opt/skill-platform/grok-video-0.1.3/paid_gateway.py:8,29–40,49–55`；`video_billing.py:16–47,75–87` | `/platform-api/grok-video`，原 43 位账户 Bearer；共享次数、成功视频 1 次、0 试用。不是 Listing 人民币钱包；不把 Muse 记录中的独立档位当当前实证 |
| Grok 链接 | `grok-video-0.1.2/entry_fix.py:22,34–35`、`member-0.10.14/core/membership.py:46–65`（均在 snapshot/opt/skill-platform 下） | 服务端签发绝对主域注册/会员链接，短效 entry/ticket。仍须看包是否接受、改写或另写付费地址，不能由服务端推断客户端已正确接入 |
| Grok Origin | `grok-video-0.1.3/paid_gateway.py:32` 内层只许空或主域；`trade-link-fix-20261111/wechat_binding.py:174–178` 将旧域精确映射为主域后委派；`wechat-official-20261113/oa_binding.py:78–85,464–472,487–490` 保留该链 | “内层不放行旧域”不足以判线上必失败；这也不是浏览器跨域 CORS、OPTIONS 或登录状态已通过的证明 |
| 主域前端及 OAuth | `infrastructure/mainland-frontend/myplanestore.com.conf:55–76,114–123`；`wechat-official-20261113/oa_binding.py:23–24,310–324,528–540`；`infrastructure/own-wechat-20261113.public.json` | 主域/www API 走反代；公众号配置回调为 www 主域，旧 state 仍有 legacy 路径；真人回调尚未验证。源站 TLS/SNI 仍引用 aistore，客户端主域化不等于可直接删除旧域基础设施 |

2026-11-14 **08:44:19–08:44:22 +08:00** 另做 8 次匿名只读 GET：不带账户/Cookie、不跟随重定向、不触发注册、业务任务或生成。完整结果见同目录 `reply-from-codex-20261114-earlier-skills-evidence.json`。

| 路径 | myplanestore.com | aistore.zhaopintong.com | 能得出的结论 |
| --- | --- | --- | --- |
| `/platform-api/listing/v1/health` | 200，无 Location | 200，无 Location，响应 SHA 相同 | 两域本次 health 原地可达；`host_integration_verified=false` |
| `/platform-api/grok-video/health` | 200，无 Location | 200，无 Location，响应 SHA 相同 | 声明 billing 0.1.3、shared_per_success、1 次、0 试用；不证明实际生成成功 |
| `/membership/listing/` | 200，无 Location | 200，无 Location，响应 SHA 相同 | 本次没有观察到 HTTP 30x 中间路线；未运行页面 JS 或验证带票据链接 |
| `/membership/gemini/` | 200，无 Location | 200，无 Location，响应 SHA 相同 | 同上；不能将“建议页面跳转”写成已部署并端到端通过 |

**页面中间路线只是一种兼容方案，不是本次已执行的改动。** `/platform-api/*` 继续原地反代，不应改为跳转。页面重定向还必须逐路径检查票据、query/fragment、会话和实际 Origin；只测公开无票据页面无法代替负责人从 Skill 实际链接出发的验证。

### 3. 已取得候选包的逐行核查

所有 ZIP 只按文本和结构读取，未导入模块、执行包、运行包内测试或调用其接口。使用原问固定 8 词检索，再独立阅读 SKILL、references、HTTP/账户/链接代码。零命中只说明未见这些字面量，不能排除动态配置、其他第三方联网或尚未完成的接入。

#### 3.1 Temu 主图·SKU 图专家及相邻两渠道

来源 S：`releases/temu-image-master/latest-three-20261029/`，README 明确“归档不代表已上架”。专家 ZIP `WorkBuddy专家/temu-image-master-workbuddy_expert-wechat-v1.0.18.zip`，SHA-256 `7b9b6ae4231a8a2be16af229a461d00a3fb59a033f2179fa8d4c6c731866e944`，28 个文件。技能 1.1.3 与 SkillHub 1.1.3 也逐包检查，SHA 见证据 JSON。

专家包以下路径以 `skills/temu-image-master/` 为根：

| 字段 | 命中位置与实证 | 是否改 / 哪几行 |
| --- | --- | --- |
| 接口常量/前缀 | `scripts/transport.py:63–66,159–161`：仅允许主域 HTTPS 或测试 localhost；主前缀 `/platform-api/temu`，兼容任务 `/temu`、旧 phone-auth 路径 | 为主域迁移无需修改这几行；保留兼容任务路径，不擅自统一为 gemini |
| 重定向 | `transport.py:57–59,161` NoRedirect；图片 URL 另有 `render_runtime.py:30–31` 主域和 media 路径校验 | API 不能靠 30x 迁移；本次不改 |
| 付费/注册链接 | `scripts/client.py:51–55`、`transport.py:242–250,652–661`：服务端链接严格验主域/路径/ticket；旧 membership-link 可规范到主域 Temu 页，非 aistore 改写目标 | 不改域名；若真实接口现签其他路径，需先取得真实契约再决定，不能自行放宽白名单 |
| 会员页/口径 | `/membership/temu/`、`/membership/temu/register/`；`references/merchant-workflow.md:39` 明写企业页、不用通用套餐页；额度读实际服务端 | 不改客户价档或权益；不能套自动化 8 款通用页 |
| 账户凭据 | `transport.py:71–72,155–156,188–235` 原共享账户/legacy 原凭据、私有业务 Key；不复制浏览器 Cookie | 保留原账户；不重建/合并/发试用 |
| 其他域名/文案 | `references/wechat-account.md:5` 仍称 aistore 微信回调；`references/temu-standards.md:3`、listing-standards.json 为 Temu 官方规则来源 | 回调文案需与当前 OAuth 入口证据核对后修订该第 5 行；规则来源不是本站 API，不随本站域名替换 |
| 遥测/自测 | `scripts/first_dialogue.py:15,59` 专家遥测主域且 NoRedirect；发布 ZIP 不带测试目录，外部 release 测试与归档 manifest 仅为历史证据，本次未重跑 | 无需把遥测改到旧域；不能说本轮运行测试通过 |
| aistore 下线 | 这些候选包的业务和链接直接依赖主域；旧域出现于回调说明，非 API 主机 | **客户端直连层不因 aistore URL 消失立即断；整体 OAuth/源站基础设施依赖尚不能宣布消除。** 先确认实际上架 SHA |

#### 3.2 儿童写真与精修专家候选 1.2.0

来源 S：`releases/baby-growth-album/1.2.0/frozen-checks.zip` 内嵌 `releases/baby-growth-album/1.2.0/WorkBuddy专家/myplanestore-child-photo-retouch-expert-v1.2.0.zip`；内包 SHA-256 `2db887f5ad7a73d3d09555a1d8b4df33320b4dcedc0db547b170e5441c348221`。不能遗漏外层 ZIP 内的实际专家包。相邻 WorkBuddy 技能/SkillHub 1.2.0 及 1.1.1 也有候选，逐包 SHA 见证据 JSON。

下列路径以专家内嵌 `skills/myplanestore-child-photo-retouch-kit/` 为根：`scripts/gateway.py:22–23,67–86,121–124` 固定主域 `/platform-api/gemini`，NoRedirect、Bearer 原 install_secret，服务端 membership-link/quick-entry；`scripts/paid_entry.py:5,29–35` 固定主域与会员路径；`scripts/transport.py:21–23,112–115` 禁重定向。`references/backend.md:3`、隐私政策等引用也指主域。

据此，**该候选没有需要因 aistore→主域而替换的上述接口/链接常量行**；会员/注册白名单是否匹配现行微信入口另须契约核验，不等同全面可用。若服务端保留原 membership 页面、页面内部完成微信，可能不用改包；若直接改签 `/auth/wechat/...`，现有 `gateway.py:84`、`paid_entry.py:29–42`、`journey.py:65` 会拒绝，须先确认真实返回契约才能安排有针对性的修改。本次不放宽白名单。

其余九字段补证：`gateway.py:49–65,101–110` 与 `transport.py:134–141` 保留私存原凭据和同身份恢复；`first_dialogue.py:14,60–61` 遥测也为主域且 NoRedirect。`references/backend.md:5` 与 `engine.py:160–171,202–224` 先查实际体验/余额，明确 paid 后走 skill-key/bound、skill-jobs，不在本次改试用/倍率/钱包；`album.py:44,58` 本地导出不重复生图。`references/themes.json:8–38` 的 JCP Portraits、故宫、非遗、Shoott、Anne Geddes 是主题来源，不是支付接口，不做域名批量替换。冻结 `tests/test_gateway.py:26–53`、`test_journey.py:115–142`、`test_http.py:34–49,66–72` 有主域/拒绝异域/原身份与 localhost 契约断言，没有新 `/auth/wechat` 兼容实证；本次只读测试源码和历史记录，未执行。

特别限制：同层 `验证记录.json` 明写 `uploaded=false`、`review_status=not_submitted`、`formal_release_ready=false`、`host_tested=false`，且头像尺寸要求未满足。它不是“已过审专家包”的版本证明，本次没有修包。aistore 下线的判断仅限该候选客户端直接主机，不包含后端 OAuth/源站基础设施保证。

#### 3.3 跨境售后申诉助手 review 候选

来源 A：`cross-border-appeal-helper-v1-review.zip`，45,761 字节、27 个文件，SHA-256 `469c685c3a0cf934404299d869777eacd051e00aa2341afce0ed1e412272d8ca`，与仓库校验文件一致。包内 `SKILL.md:1–4` frontmatter 没有 version，不能把文件名 v1-review 编造成平台版本号。

全包固定 8 词零命中；独立读 SKILL、后端契约和 TEST-REPORT 后发现这是本地权益参考实现，真实自有支付后端/SSO/验签/outbox 尚未接。接口地址/前缀、HTTP 重定向、付费链接来源、会员路径、线上账户凭据均未落成可核对的本站实现；本地体验/credits 不是线上收费到账证明，其他平台帮助链接不等于本站接口。

包内精确定位：`docs/backend-contract.md:5,7–23,25` 是待接的 SSO/`/entitlements`/`/consume` 契约；`SKILL.md:28–30`、`references/dialogue.md:7,14` 只提示原权益与付费、没有在线入口；`scripts/entitlements.py:24–26,42–70` 为本地一次完整申诉体验与后续 credits，不擅自改政策；`TEST-REPORT.md:25–31` 明示真实后端/SSO/支付回调/宿主未接未验。其他域名是 Amazon/TikTok/Temu 政策来源与 SVG namespace，不做本站域名替换；`tests/test_ledger.py:16–62` 检查本地账本/幂等而非 URL，不能充作线上兼容测试。

**这份 review 候选无需做本站域名字面量替换；不能据此认定线上“跨境售后申诉助手”免费、纯离线、后端已接好或不用更新。** 线上版本/上传 ZIP/SHA 与真实支付接入补丁仍缺，不能给线上包编行号。

#### 3.4 付费接入组件、头像与老照片候选

组件定位 S 的 `myplanestore-paid-entry/`：`paid_entry.py:4–6` 为组件版 1.0.1、主域、gemini/temu；`transport.py:96–113` 只承接约定账户接口及原凭据 Bearer；`docs/接入约定.md:18–22,38–40` 区分 registered 与付款，校验主域、entry/ticket 和短效期；组件不包办注册/迁移/消费。目录更新不会自动更新旧 ZIP，也不证明差评/朋友圈实际嵌入了它。

已读取头像 3 个、老照片 9 个实际候选 ZIP（共 12 个）的文本，均未检出 aistore 字面依赖。详细逐行对象为 S 根目录：

- `avatar-diy-master-v1.0.0-fix2.zip`，515,978 字节、23 文件，SHA-256 `710dfaa45a52a8096351a7b7504c22dde402fa58f6386e47b7a00f347f298b4a`。
- `old-photo-restore-master-v1.0.0-fix2.zip`，298,985 字节、28 文件，SHA-256 `02dff43788f3519aae7cc71afc73869e7d4f0d47cbed1d116b0d94464f77c8d9`。

路径分别相对于 ZIP 内 `avatar-diy-master/`、`old-photo-restore-master/`：

| 字段 | 头像 fix2 | 老照片 fix2 |
| --- | --- | --- |
| 域名常量/前缀 | `scripts/paid_entry.py:5`、`image_transport.py:11–12,66`：主域 `/platform-api/gemini`；路径环境覆盖只管凭据文件 | `paid_entry.py:4`、`image_transport.py:10,77`：主域 gemini；未见服务主机覆盖 |
| 重定向 | `transport.py:18,106`、`image_transport.py:70` NoRedirect | `image_transport.py:21–22,46`、`transport.py:9–10,39` NoRedirect |
| 付费链接来源 | `paid_entry.py:25–33,51–69` 校验服务端链接，不接受旧域；业务调用接线存在下述疑点 | `paid_entry.py:19–28,64–66` 服务端 membership-link，`billing.py:55–62` 校验后进一步只接受中性主域会员页 |
| 页面路径 | gemini 注册、gemini 会员、通用会员路径白名单 | 通用校验虽支持 gemini，实际业务 `billing.py:55–62`、`restore.py:381–383` 只接受 `/membership/`；不能只读通用库就漏掉此限制 |
| 账户凭据/恢复 | `image_transport.py:37,54–57` 私存 Key Bearer；`transport.py:68–85,100–102,125–133` 原身份及可选恢复，未见业务 Cookie | `account.py:15–29,40–44,62–85` 原身份/legacy 恢复；`billing.py:20–39` 区分运营赞助试用 Key 与匹配账户的付费 Key；不把本机凭据写对话 |
| 收费口径 | README/SKILL 的旧价档文案不是本次生产套餐证明；不能直接换成当前生图套餐 | `billing.py:41–52` 读真实余额；SKILL 旧试用与价档文案、运营预算赞助不等于已完成线上收费，且产品已下线不派维护 |
| 其他域名 | 非测试业务文本仅主域；无 aistore 字面量 | 同；测试的 upstream.invalid 是 fixture，不是业务资源 |
| 自测/版本 | `SKILL.md:2,6` 为 1.0.0，原/fix1/fix2 都同版本；`tests/test_paid_entry_copy.py:8,18–27` 为库副本/NoRedirect 历史断言，本次未执行 | 原/fix1/fix2 及渠道包均 1.0.0；`tests/test_paid_entry.py:17,23–28,67`、`test_gateway.py:15,44,52–53` 有主域/URL/NoRedirect 断言，本次未执行 |
| 改动/旧域下线 | 不需把这些主域常量替换；新微信 URL 路径若不同仍需真实契约核验。候选主机不直接依赖旧域，不能外推线上版和后端已完全去旧域 | 同；已下线要求保持，不因此恢复或重发 |

头像另有可定位的静态接入疑点：`scripts/business.py:75–81,109,135` 调用模块级 `paid_entry.balance/consume`，但同包 `paid_entry.py` 未导出这两个模块级函数；类方法不等于模块函数。本轮不运行、不修复、不派开发，只提醒这份候选不能以“组件已复制”宣称业务完整接通。

差评回复大师、朋友圈文案大师：固定树及相关文本未找到对应完整包或该组件调用证据，九字段仍全部未知；这不是已经证实“没接入”。不拿头像/老照片的实现代填这两款。

### 4. 原清单逐款判定（A/B/C 全覆盖）

“待查”不是已经确认要改；“候选无需域名替换”也不是已证明线上版本无需重传。没有包的行，接口、redirect、链接、凭据、收费和断点均保持未知，不按产品名称补全。

| 产品 | 当前能核对的材料 | 是否需改 / 命中位置 | aistore 下线影响 |
| --- | --- | --- | --- |
| **ChatGPT 生图王（先查）** | M/S 索引未见可映射上传包；assistant .1.4.0 只有片段，未证明是此款 | 待查，无可给出的线上代码行号；不能以主域恢复就判可发布 | 未知，需实际 API/链接/回调映射 |
| **ChatGPT 全能生图王 Pro（先查）** | 同上，不能与上一款合并成一个包 | 待查，无行号 | 未知 |
| **Grok 一键短视频生成助手（重提优先）** | 有 Grok 服务端，未找到该 slug 重提上传包 | 待查；不能把头像拒审反馈当域名已合格；服务端不是客户端版本 | 未知；若包 API 旧域则直连会断，若仅旧页则页面受影响 |
| Listing 优化大师 | M 服务端/契约/双域公开 health，未见 WorkBuddy 上传包 | 待查客户端；重点相对 `/membership/listing/` 主机拼接、`/auth/wechat/listing.html`、二维码路径 | 取决于包拼主机；独立人民币钱包不能套 8 款结论 |
| 跨境售后申诉助手 | A review 包可读，实际后端未接 | review 不需域名替换；线上版待查，见 3.3 | review 无直接本站字面量依赖；线上未知 |
| Grok 一键生图 | 未找到对应渠道完整包 | 待查，无行号；不能假定与 Grok 视频同网关 | 未知 |
| 差评回复大师 | M 原清单转述 SkillHub 已上架；S 未找到完整包/组件接入证据 | 待查；不能按提示词名称判离线 | 未知 |
| 朋友圈文案大师 | 同上 | 待查，无行号 | 未知 |
| 头像定制大师 | S 有 fix2 等完整候选，平台对应关系未证 | 见付费组件/候选包补充；不能把 1.0.0 与某 fix 文件名直接对应成当前重提版 | 候选主要主域；线上未映射，整体下线影响待查 |
| 儿童写真与精修专家 | S frozen-checks 中真实专家 1.2.0，另有技能/SkillHub 候选 | 候选无需接口域名替换；不能等同清单已过审包，见 3.2 | 候选主域直连；后端旧域依赖另计 |
| Temu 主图·SKU 图专家 | S 专家 1.0.18/三渠道归档及 M 旧脚本 | 候选无需接口/支付域名替换；回调说明第 5 行需核对；见 3.1 | 客户端主域直连；源站/OAuth 删除旧域未获证明 |
| Amazon 选品 2026 版 Pro | 未找到对应完整包 | 待查，无行号 | 未知 |
| 17TRACK 全球物流追踪 | 未找到对应完整包 | 待查，无行号；第三方物流接口与本站付费入口需分别看 | 未知，不能把第三方域名当 aistore 依赖 |
| 跨境竞品广告分析师 | 未找到对应完整包 | 待查，无行号 | 未知 |
| 亚马逊选品逻辑大师 | 未找到对应专家包 | 待查，无行号 | 未知 |
| SKILL-SEO 优化师 | 未找到对应专家包 | 待查，无行号 | 未知 |
| Grok 视频创作助手 | M Grok 服务端旁证，未找到此展示名对应专家/技能包 | 客户端待查；服务端共享次数、双域桥接见 2，不编造需改行号 | 取决于包主机、链接校验；尚不能判不受影响 |
| AI 开发机空间管家 | 未找到对应完整包 | 待查；不按本地工具名称直接判无付费入口 | 未知 |
| 开发缓存治理专家 | 未找到对应完整包 | 待查，无行号 | 未知 |
| 微信存储清理助手 | 未找到对应完整包 | 待查，无行号 | 未知 |
| 微信 C 盘专清（技能侧） | 未找到对应完整包 | 待查；与上一款分别取包 | 未知 |
| AI 产品交付前自检大师 | 未找到对应完整包 | 待查，无行号 | 未知 |
| 宠物养生问诊助手 | 只有通用 pet 服务旁证，未映射客户端 | 待查；不能同自动化宠物照相馆混用 | 未知 |
| 老照片修复大师 | 原清单称 1.0.0 已下线；S 有候选完整包 | 按已下线要求不派维护/更新；候选域名事实另记，不改变下线状态 | 已安装旧副本的实际版本未知，不能保证不受影响 |
| 跨境广告否定词助手 | 原清单未开发无发布包 | 不涉及旧包更新；不因本回复启动开发 | 无已知在用发布包可评估 |
| Grok 产品图转视频助手 | 原清单未开发无发布包 | 不涉及旧包更新；不把开发文档当成发布包 | 同上 |

### 5. 分层判定准则

- 实际上传包的 API 和全部链接都指主域：不为“客户端域名替换”重传；仍需检查服务端签发的新路径、旧凭据恢复及共享 OAuth/源站依赖。
- API 旧域：只要旧域保留同路径原地代理，才具备继续兼容的条件；旧域关闭会使功能请求直接失败。只跳会员页无法覆盖 API。
- API 主域、只有文案/付费链接旧域：可能只断页面；需要更新对应链接行或先验证页面兼容路线。固定收款图离线副本不受服务器跳转修复。
- 服务端完整 URL、相对 URL、客户端白名单/重写三种分别追踪；无 trusted_link 不能自动当优点，也不为了省包而放弃 URL 校验。网页 Cookie 不跨域复制。
- 只有本地逻辑且完整扫描/人工检查均无本站链接或动态接入，才能给“本站域名迁移不需改”的候选结论；仍须有上传版身份。不能只凭固定 8 词零命中保证全离线。
- “aistore 下线”须说明是停止客户端 URL 服务、删除 OAuth legacy 入口，还是撤销源站域名/TLS/SNI。后两者会影响主域代理基础设施，不能由包内主域常量排除。

## (b) 仍需负责人补充的材料（逐款，不重复索要已取得文件）

共同身份材料 **V**：每个实际渠道的当前线上/已过审待发布/重提中版本号 + 对应上传 ZIP 的 SHA-256 或平台上传记录；若不等于本回复已查候选，提供实际完整 ZIP/解压目录或可访问的固定仓库 commit/tag。材料应包含 SKILL、scripts、references、配置及渠道元数据。

共同交易材料 **P**：该款是否收费、通用套餐/独立充值/免费，以及负责人记录的付费页 URL（不含 ticket/entry、Cookie、客户或账户凭证）。仓库实现不等于负责人已采用的线上收费方式。

| 优先级 / 产品 | 需要补什么 | 已拿到、不必重新提供什么 |
| --- | --- | --- |
| P0 ChatGPT 生图王 | V + 实际完整包 + P，尤其这次待点发布的那版 | 不用拿 assistant 历史脚本代替上传包 |
| P0 ChatGPT 全能生图王 Pro | V + 此款完整包 + P，独立于上一款 | 不复用上一款版本号 |
| P0 Grok 一键短视频生成助手 | 头像修订后的实际重提包/上传版、V、P；确认清单旧充值档是否仍采用 | Grok 服务端源码和当前登记链已查，不再索要同份历史快照 |
| P1 Listing 优化大师 | WorkBuddy 实际包、V、P，若合同口径与 Listing CNY 契约不同请标明 | Listing 网关/账户/独立会员页契约、较新登记入口已查 |
| P1 跨境售后申诉助手 | V；若线上不是 review SHA 则补实际包及自有支付接入版本；P | A 仓 review ZIP/意图/校验文件已取得 |
| P1 Grok 一键生图 | V + 完整包 + P | 不用提供其他 Grok 产品的包来代替 |
| P1 差评回复大师 | SkillHub V + 完整包 + P，确认是否真的嵌了 paid-entry | 通用 paid-entry 组件已取得 |
| P1 朋友圈文案大师 | SkillHub V + 完整包 + P，单独确认接入情况 | 同上 |
| P1 头像定制大师 | V；确认重提稿是否就是已查 fix2 SHA，若不同再给包；P | S 仓已有候选不需重复传；域名判断不代表业务链已联调 |
| P1 儿童写真与精修专家 | V，确认实际过审专家包是否等于 frozen 1.2.0 SHA；若不同给实际版；P | frozen 外层/内包及 1.1.1 候选已查；当前记录反而未提交，需渠道事实对齐 |
| P1 Temu 主图·SKU 图专家 | V，确认是否使用专家 1.0.18 SHA；不同才补包；P 和现用展示付费页是否仍企业 Temu 页 | 三渠道归档、主域/账户/企业页实现已查 |
| P1 Amazon 选品 2026 版 Pro | V + 完整包 + P | 暂无可替代实际包的材料 |
| P1 17TRACK 全球物流追踪 | V + 完整包 + P；说明第三方接口是否用户自带权限或自有后端转接（不发密钥） | 不用提供真实物流/客户记录 |
| P1 跨境竞品广告分析师 | V + 完整包 + P | 暂无完整候选 |
| P1 亚马逊选品逻辑大师 | 专家渠道 V + 完整包 + P | 暂无完整候选 |
| P1 SKILL-SEO 优化师 | 专家渠道 V + 完整包 + P | 暂无完整候选 |
| P1 Grok 视频创作助手 | 展示名/slug/渠道 V 对应的完整包 + P | Grok 服务端共享次数和较新登记链已查；不重复索要历史层 |
| P1 AI 开发机空间管家 | V + 完整包 + P（免费也明确写免费） | 暂无完整候选 |
| P1 开发缓存治理专家 | V + 完整包 + P | 暂无完整候选 |
| P1 微信存储清理助手 | V + 完整包 + P | 暂无完整候选 |
| P1 微信 C 盘专清（技能侧） | 本技能独立 V + 完整包 + P | 不与存储清理助手混用 |
| P1 AI 产品交付前自检大师 | V + 完整包 + P | 暂无完整候选 |
| P1 宠物养生问诊助手 | 该问诊产品 V + 完整包 + P | 不用提交自动化宠物照相馆代替 |
| 不收集：老照片修复大师 | 当前下线要求不变则无需为本轮补包或排更新；若需判断用户遗留副本，才补其实际安装 SHA | S 候选包已核，不擅自恢复维护/发布 |
| 不收集：两款未开发产品 | 本轮无旧包更新，不需要索包 | 不派新开发任务 |

服务端补证只在需要宣称“生产全链已核验/可删除旧域”时再提供：运行机当前 ExecStart/加载链与对应公开源码哈希、Nginx 生效路由、当前 OAuth 回调配置的脱敏证明。仓库已有登记层不再当缺失重复索要；不需要客户数据库、余额、订单或凭证。未验证项随答复保留，不能因此把已完成的仓库调查搁置。

## 本次实际操作与后续边界

只提交此调查答复、脱敏证据摘要和 relay 回执/回复请求（kind=question）。不改 Skill 包、不改规格、产品 status/log/BOARD、SOP/config，不发开发任务，不部署、不重启、不上架，不恢复自动化或 AI 周期监测。真实上游调用 **0 次**，真实支付/账户注册/订单/财务写入 **0 次**；上述 **8 次匿名只读公网 GET** 单独记账，未冒充业务联调。

Muse 可据此向负责人收集缺件；材料未齐的产品仍标待查。已得到的候选级结论先交付，不把“等全部包”作为继续无回复的理由。

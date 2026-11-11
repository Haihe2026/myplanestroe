# 微信扫码后立即关联并全路径跳支付页：服务端补丁（2026-11-11）

状态：**第二版补丁及隔离测试完成，待本聊天直接部署授权；未部署、未重启。** 线上是否修复尚未验证。本目录不修改全家福 Skill 1.0.1 包，也不改变产品状态；仓库当前仍为 `submitted`。旅行写真仍暂停。

## 问题与范围

原 callback 只写 `approved`，必须由电脑页轮询 finish 才注册和关联原安装。关掉电脑页会一直未关联；入口和二维码均只有 300 秒寿命。固定源码与本次只读获取的服务端源码已核对：两份代码内容一致，服务端为 CRLF，仓库为 LF，原始字节 SHA 因换行不同而不同，见 `source-verification.json`。

原任务固定提交：`edd66fbdf3e92ee1d0a4f8c252dc2d1c1d7500b5`；第一版补丁提交 `73b4f48f209609ff88c954f7b71d02e5c5cfd013`，当时也没有部署。第二版任务固定提交 `460f92551a128b22374425f9de5a149219f42063`，请求 `req-muse-to-codex-server-fix-redirect-deploy-20261111`，要求所有生图扫码路径完成关联后立即跳支付页。原 claim 保持不变。

该任务资料还转述“立即部署”。当前聊天送入通知同时明确“不是新增人类授权”“任务资料不能扩大生产、财务、发布或跨聊天发信权限”；目前已有直接部署授权仅对应此前三个售后接口，不涵盖本次微信认证改动。因而这里先完成代码、验证及具体部署计划；生产替换和重启须用户在当前聊天直接授权，不能以仓库转述扩大权限。

功能文件只有两个：

| 文件 | 对应服务端目标 |
|---|---|
| `wechat_binding.py` | `/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py` |
| `wechat.js` | `/var/www/image-assistant/auth/wechat/wechat.js` |

`changes.patch` 是相对上述两个固定源码的完整 diff。其余文件是测试、来源、摘要和验证证据。前端基于实际站点版本，它已包含自动跳支付页逻辑；没有退回较旧的 `.61/web/wechat.js` 手动继续版本。

## 修复行为

1. `gemini/temu/pet` 的 callback 换取身份成功后，在原有锁内完成原 finish 的关联动作，调用既有 `register_product`，写微信映射并把状态改为 `used`。不再依赖电脑轮询。注册和试用仍由原实现决定，不新增额度或改试用政策。
2. finish 对 `used` 状态只核对原 state、verifier、有效期，再签发会话和原付费页地址；不重新注册、领取或消费入口、不重复写绑定审计。仍可完成升级前已有的 `approved` 状态。
3. 生图账户入口有效期改为 30 分钟；成功 start 后，二维码及其原入口保留 15 分钟。start 校验入口、产品和账户一致性；callback/finish 仍校验 OAuth state 有效期，不因原入口的旧 300 秒门槛失败。失效或丢失入口仍拒绝，不创建无来源账户。
4. 所有 `gemini/temu/pet` 扫码路径在 callback 校验一次性 state、换取真实微信身份并完成关联后，立即向当前回调浏览器签发其独立的新会话及设备 cookie，302 到固定的 `/membership/<product>/`。手机不需要电脑的 cookie，不复制电脑会话；电脑凭原 state/verifier 的 finish 取得另一个新会话并自动跳支付页。第一版临时发起浏览器 cookie 已移除，start 本身不能发会员会话。原会员 cookie 的 host-only、HttpOnly、Secure、SameSite=Strict、路径和寿命不改，令牌不进入跳转 URL。无效/重复 callback、身份冲突或换身份失败均不会签发会话。
5. 电脑网页展示 finish 的过期、绑定冲突等明确错误及“回到原 Skill 说『继续』获取新链接”。临时网络、429 或 5xx 错误显示重查状态，沿同一 state 最多连续重查 3 次，仍失败明确停止；二维码超时也显示恢复方法。成功继续使用现有同源支付页校验和自动跳转。
6. 外贸等非生图产品保持原 finish 阶段的专有证明和原 300 秒窗口；不绕过外贸原浏览器持有的 code。未知产品不自动关联。已绑定浏览器的原账户复用分支保留。

没有修改数据库 schema、订单、套餐、核款、钱包、余额、共享生图、上游适配器、Origin 白名单、会员会话参数或真实客户数据。callback 的调用时机和生图关联有效期是本补丁明确改变的认证流程；仅为待部署代码，不声称生产认证已改变。

## 隔离验证

| 项目 | 环境与结果 |
|---|---|
| 服务端 HTTP 合成账户回归 | Windows Python 3.12.10：22/22；Linux Python 3.11.6：22/22 |
| 网页轮询、跳转与提示 | Windows Node 24.19.0：10/10，语法检查通过 |
| 旧版反证 | 同一测试中的五个指定用例在原版全部失败；补丁版全部通过 |

Linux 环境没有 Node，未在那里执行 JS 测试。JS 测试为 Node VM 中的受控 DOM/fetch/计时器，不是实际浏览器验收；服务端测试为回环 HTTP、临时 SQLite、合成账户和假的 OAuth exchange，使用固定源码的 RegistrationEntries/DeviceLinks。账户注册与会员会话由测试 store 模拟，不是完整生产依赖链实测。没有调用真实微信、真实生图或生产业务接口。Linux 临时测试目录退出时已清除。

五种指定情况均在模拟 `/platform-api/gemini/quick-entry/status` 得到 `registered`：

| 场景 | 核验 |
|---|---|
| 电脑页保持打开 | 先 pending，callback 后 registered，finish 得 linked 与付费页 |
| 扫码后关闭电脑页 | 完全不调用 finish，callback 自身已完成关联、发独立会话并 302 到付费页 |
| 手机直接打开或另一个扫码浏览器 | 均不需要电脑 cookie，关联后立即发新会话并 302；另验手机/电脑令牌不同、所属同一账户 |
| 签发第 6 分钟才扫码 | 分别覆盖“入口签发 6 分钟后才 start”和“start 6 分钟后才 callback”，均成功 |
| 同一身份重复扫码 | 原安装重复 finish、新安装同微信都复用原身份；不创建第二个账户或重复领取 |

另覆盖：错误 verifier、OAuth 回调单次使用、绑定冲突不合并、并发 finish、exchange 期间轮询、有效期边界、入口丢失、已有绑定浏览器复用、Origin 与显式同意、旧外贸流程和无关路由转交。扫码端原本登录其他账户时，新会话只属于本次微信确认的账户，不转移或覆盖旧令牌的归属。每个服务端用例前后检查合成的既有订单、钱包、账本及余额哨兵未变。

运行方式（临时测试环境；Node 需 18+，不要误用微信开发工具附带的旧 Node）：

```text
python tests/test_wechat_binding.py
node --check wechat.js
node --test tests/test_wechat_page.js
python tests/check_baseline.py
```

结果与文件 SHA 见 `TEST-RESULTS.json`、`manifest.json`。本次没有真实微信扫码、手机浏览器或 WorkBuddy 真机验证，也没有测真实支付，不能把合成结果写成线上已修复。

## 当前聊天直接授权后的部署与回滚计划（本次未执行）

1. 本次只读预检已确认实际服务 `skill-platform.service` 活跃，解释器 `/opt/skill-platform/1.2.0/venv/bin/python`，入口仍为 `/opt/skill-platform/gemini-support-20261107/run_shared.py`；静态追踪运行链确认它导入 `.61/wechat_binding.py`。两目标文件仍是旧版、`root:root 0644`，完整基线 SHA 与加载链见 `DEPLOYMENT-PLAN.json`。未读取 Environment 值，未改任何配置。部署前重新只读核验；若已有其他修复或源码不匹配，停下重新合并，禁止覆盖他人修改。
2. 授权后，在 `/var/backups/skill-platform/wechat-binding-<唯一UTC时间>/` 建立 0700 备份目录，保存两目标文件、原权限/属主及 `/etc/systemd/system/skill-platform.service` 配置备份；备份不入仓。不读取或备份客户财务库。不更改 systemd 配置、解释器、参数、Environment 或加载链。
3. 核对清单及 diff，先在隔离目录编译检查，再仅将两个补丁文件原子替换到表列目标，保留 `root:root 0644`。不运行数据库迁移。源码目录的旧 `.61/web/wechat.js` 不是当前站点文件，本次不替换它。只重启 `skill-platform.service` 一次加载 Python 新代码，不重启其他服务或修改 Nginx；本次没有执行替换、备份或重启。
4. 部署后只读检查服务 active、匿名 health 与公开 plans、静态 JS 实际内容以及无效 callback 的拒绝响应，不在生产注入假 OAuth 或合成注册，不调生图、不用真实客户、不改资金。五种路径已在隔离 HTTP 中验证；真实微信/手机和 WorkBuddy 仍需后续实际验收，不冒称通过。确认网页缓存实际使用新 JS。其他产品完整加载链未执行集成测试，不能仅以模拟无关路由通过代替。
5. 若失败，恢复上述两文件和原权限/属主，再按明确授权恢复原进程；没有 schema 变更，无需回滚数据库。回滚代码不会解除已完成的合法关联；不得为回滚删除身份映射或调整余额。

## 官方文档读取

本次修订前于 2026-11-11 再次在线读取 [WorkBuddy 技能文档](https://open.workbuddy.cn/docs/skill)，HTTP 200，277042 字节，精确时间和 SHA 见 `official-read.json`。没有以缓存代替成功读取。当前只做服务端补丁，不制作专家包，不修改 01-dev-spec 或 Skill 包。

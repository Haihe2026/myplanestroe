# 微信扫码后立即关联：服务端补丁（2026-11-11）

状态：**补丁及隔离测试完成，未部署、未重启。** 线上是否修复尚未验证。本目录不修改全家福 Skill 1.0.1 包，也不改变产品状态；仓库当前仍为 `submitted`。旅行写真仍暂停。

## 问题与范围

原 callback 只写 `approved`，必须由电脑页轮询 finish 才注册和关联原安装。关掉电脑页会一直未关联；入口和二维码均只有 300 秒寿命。固定源码与本次只读获取的服务端源码已核对：两份代码内容一致，服务端为 CRLF，仓库为 LF，原始字节 SHA 因换行不同而不同，见 `source-verification.json`。

原任务固定提交：`edd66fbdf3e92ee1d0a4f8c252dc2d1c1d7500b5`，原请求 `req-muse-to-codex-server-fix-wechat-binding-20261111`；原 claim 保持不变。

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
4. start 为生图流程设置 host-only、HttpOnly、Secure、SameSite=Lax、限定 `/platform-api/wechat/`、15 分钟的临时浏览器凭据。callback 仅在其哈希与原 state 的 verifier 匹配时，在该浏览器签发原会话及设备 cookie，并 302 到 `/membership/<product>/`。普通扫码手机没有该凭据，只显示“关联完成。电脑上的页面会自动进入付费页面；也可以直接回到原 Skill 对话说『继续』。”，不把电脑会话送给其他浏览器。原会员 cookie 的 Strict、路径和寿命不改。
5. 电脑网页展示 finish 的过期、绑定冲突等明确错误及“回到原 Skill 说『继续』获取新链接”。临时网络、429 或 5xx 错误显示重查状态，沿同一 state 最多连续重查 3 次，仍失败明确停止；二维码超时也显示恢复方法。成功继续使用现有同源支付页校验和自动跳转。
6. 外贸等非生图产品保持原 finish 阶段的专有证明和原 300 秒窗口；不绕过外贸原浏览器持有的 code。未知产品不自动关联。已绑定浏览器的原账户复用分支保留。

没有修改数据库 schema、订单、套餐、核款、钱包、余额、共享生图、上游适配器、Origin 白名单、会员会话参数或真实客户数据。callback 的调用时机和生图关联有效期是本补丁明确改变的认证流程；仅为待部署代码，不声称生产认证已改变。

## 隔离验证

| 项目 | 环境与结果 |
|---|---|
| 服务端 HTTP 合成账户回归 | Windows Python 3.12.10：21/21；Linux Python 3.11.6：21/21 |
| 网页轮询、跳转与提示 | Windows Node 24.19.0：10/10，语法检查通过 |
| 旧版反证 | 同一测试中的五个指定用例在原版全部失败；补丁版全部通过 |

Linux 环境没有 Node，未在那里执行 JS 测试。JS 测试为 Node VM 中的受控 DOM/fetch/计时器，不是实际浏览器验收；服务端测试为回环 HTTP、临时 SQLite、合成账户和假的 OAuth exchange，使用固定源码的 RegistrationEntries/DeviceLinks。账户注册与会员会话由测试 store 模拟，不是完整生产依赖链实测。没有调用真实微信、真实生图或生产业务接口。Linux 临时测试目录退出时已清除。

五种指定情况均在模拟 `/platform-api/gemini/quick-entry/status` 得到 `registered`：

| 场景 | 核验 |
|---|---|
| 电脑页保持打开 | 先 pending，callback 后 registered，finish 得 linked 与付费页 |
| 扫码后关闭电脑页 | 完全不调用 finish，callback 自身已完成关联 |
| 手机在同一浏览器打开 | 凭发起浏览器 cookie 设置会话并 302，账户 registered |
| 签发第 6 分钟才扫码 | 分别覆盖“入口签发 6 分钟后才 start”和“start 6 分钟后才 callback”，均成功 |
| 同一身份重复扫码 | 原安装重复 finish、新安装同微信都复用原身份；不创建第二个账户或重复领取 |

另覆盖：错误 verifier、OAuth 回调单次使用、绑定冲突不合并、并发 finish、exchange 期间轮询、有效期边界、入口丢失、已有绑定浏览器复用、Origin 与显式同意、旧外贸流程和无关路由转交。每个服务端用例前后检查合成的既有订单、钱包、账本及余额哨兵未变。

运行方式（临时测试环境；Node 需 18+，不要误用微信开发工具附带的旧 Node）：

```text
python tests/test_wechat_binding.py
node --check wechat.js
node --test tests/test_wechat_page.js
python tests/check_baseline.py
```

结果与文件 SHA 见 `TEST-RESULTS.json`、`manifest.json`。本次没有真实微信扫码、手机浏览器或 WorkBuddy 真机验证，也没有测真实支付，不能把合成结果写成线上已修复。

## 待负责人另行授权后的部署与回滚计划（本次未执行）

1. 先只读确认当时的服务入口、模块加载路径及两目标文件，备份目标文件及其权限/属主；保留原 systemd 配置。服务名和加载链以当时实查为准，本次没有读取或改动 systemd。若已有其他修复或源码不匹配，停下重新合并，禁止覆盖他人修改。
2. 用 `source-verification.json` 核对基线，允许仅 CRLF/LF 差异；由负责人审阅 `changes.patch`。不运行数据库迁移，不改配置、解释器、参数、Environment 或其他路由。
3. 仅将两个补丁文件替换到表列目标，保留原权限和属主。源码目录的旧 `.61/web/wechat.js` 不是当前站点文件，本次不替换它。按当时加载链，获得明确重启授权后再加载 Python 新代码；本次没有执行重启或部署脚本。
4. 后续用隔离测试身份做真实浏览器和微信回调验收，核验五种情况及恢复提示；刷新网页缓存以确认实际使用新 JS。仍不调生图、不用真实客户、不改资金。保留旧 state 的过渡验证和其他产品路径回归。
5. 若失败，恢复上述两文件和原权限/属主，再按明确授权恢复原进程；没有 schema 变更，无需回滚数据库。回滚代码不会解除已完成的合法关联；不得为回滚删除身份映射或调整余额。

## 官方文档读取

2026-11-11 16:48:24 +08:00 在线重新读取 [WorkBuddy 技能文档](https://open.workbuddy.cn/docs/skill)，HTTP 200，277042 字节。此前一次网页工具读取超时，随后直接在线请求成功；没有以缓存代替成功读取。当前只做服务端补丁，不制作专家包，不修改 01-dev-spec 或 Skill 包。

# member-0.10.31：新开对话识别原账户（方案 A：网站记住登录）

日期：2026-10-22。状态：**离线开发完成，未部署、未在生产或真实宿主验证。**

## 1. 要解决的问题

WorkBuddy 每次新开对话（云端环境重建），Temu 技能都会生成新的本机身份。商家点开注册链接确认后，现有代码会**新建一个账户并再发 1 次免费体验**：

- 已充值商家看到新用户页面和 1 次体验，以为余额清零；
- 未充值商家每开一个新对话就能多领一次体验。

已在 0.10.29 现有代码上用合成数据复现：同一浏览器、第二个对话确认后，`/register` 返回新账户、`trial_remaining=1`。

## 2. 效果

1. 商家通过技能下发的链接在浏览器里登录过一次（注册页确认，或从"我的账户/充值"打开会员页），网站就记住这个浏览器（默认 180 天）。
2. 新开对话后，商家用**同一部手机、同一个浏览器**打开技能给的链接，注册页显示「检测到你已有账户 · 创作账户 xxxx · 可用 N 次」。
3. 商家勾选同意并点 **关联原账户**：新对话接到原账户上，**不新建账户、不再发体验、不下单、不扣费**。页面提示回到 WorkBuddy 发送「已关联」。
4. 技能侧 `/register` 返回 `linked_existing: true`，Temu 技能 v1.0.15 据此显示「已关联你原来的账户，次数没有清零」。**技能包不需要再改**（已用真实 v1.0.15 客户端联调验证，见第 5 节）。
5. 页面另有「不是我，按新账户继续」（走原有新账户流程）和「退出这个浏览器的登录」。

## 3. 改动文件

全部为新增，未修改任何现有版本目录的源码。

| 文件 | 说明 |
|---|---|
| `member-0.10.31/run_shared.py` | 新入口：安装 `account_link`，再运行未改动的 `member-0.10.29/run_shared.py` 整条链 |
| `member-0.10.31/account_link.py` | 记住浏览器、`remembered` / `link-entry` / `forget-device` 三个接口、`/register` 的 `linked_existing` 字段 |
| `member-0.10.31/web/membership/temu/register/` | Temu 注册页新版（`index.html`、`trial-register.js`、`trial-register.css`，缓存版本 `?v=0.10.31`） |
| `member-0.10.31/web/membership/gemini/register/` | **[2026-10-22 追加]** **通用通道**注册页新版（`index.html`、`register.js`、`register.css`），同样的"检测到你已有账户"面板。注意：`gemini` 是通用 skill 通道的前缀（`/membership/` 与 `/membership/xhs/` 充值页都走它），因此这一页服务于除 Temu 外的全部付费 skill，不只是 Gemini生图器 |
| `member-0.10.31/web/install_web.py` | 把新页面装进网站目录，自动备份原文件；`--rollback` 还原。默认只装 Temu，`--product gemini` 或 `--product all` 可装 Gemini 页 |
| `member-0.10.31/test_account_link.py` | 接口级端到端测试（真实服务链 + 合成数据库） |
| `member-0.10.31/dev-tests/` | 可选：Chromium 页面测试 + 真实技能客户端联调（需 Playwright） |
| `member-0.10.31/deploy/deploy_0_10_31.py` | 服务器部署/回滚脚本：检查、备份、安装、只重启 skill-platform、健康检查、失败自动回滚、再装页面 |
| `infrastructure/systemd/skill-platform.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzz-device-link-0.10.31.conf` | 共享服务入口改为 0.10.31（文件名排在 0.10.29 drop-in 之后） |
| `dev/start.py` | 开发容器的共享服务改用 0.10.31 入口（一行） |
| `docs/当前阶段与修改入口.md` | 启动链与修改入口表加入 0.10.31 |

### 新增数据表（共享库，`CREATE TABLE IF NOT EXISTS`，不改旧表）

| 表 | 内容 |
|---|---|
| `remembered_devices` | 浏览器登录：Cookie 的 **SHA-256**（不存原值）、账户、到期、最后使用、是否撤销 |
| `device_entry_links` | 哪些技能身份（哈希）是通过"关联原账户"接上的；供 `linked_existing` 判断 |
| `device_link_audit` | 审计：`device_remembered` / `conversation_linked` / `device_forgotten`，只记账户与时间 |

### 新接口（`/platform-api/temu/membership-api/…`）

| 接口 | 鉴权 | 说明 |
|---|---|---|
| `GET remembered` | `mps_device` Cookie | 返回 `{remembered:false}` 或账户标签与真实次数 |
| `POST link-entry` | Origin=`https://myplanestore.com` + `X-Membership-Request: 1` + `mps_device` + 未过期的注册链接 + `accepted:true` | 把该注册链接对应的新对话接到记住的账户；同时下发 30 分钟 `platform_member` 会话 |
| `POST forget-device` | 同上（无需注册链接） | 撤销本浏览器的记住登录并清除 Cookie |

`mps_device` Cookie：`HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=180天`。在原有两处"技能下发票据换成网页会话"成功后下发：注册确认（confirm-entry）和会员页兑换（redeem）。

## 4. 没有改变的

套餐金额与次数、订单与付款幂等、核款邮件、免费体验政策表（Temu 新账户仍 1 次，`enterprise.start` 对同一账户幂等，关联不会再发）、旧专用余额与专属 Key、原 `confirm-entry` 新账户流程、30 分钟 `platform_member` 会话、管理后台及其 90 天登录。Gemini/XHS 页面默认不启用此功能（`MYPLANESTORE_DEVICE_LINK_PRODUCTS` 默认只含 `temu`）。

## 5. 测试（全部为离线合成测试）

| 测试 | 内容 | 结果 |
|---|---|---|
| `python3 member-0.10.31/test_account_link.py` | 真实 0.10.31→0.10.29→…→0.10.14 服务链、空 schema 合成库；新账户、记住浏览器、关联、`linked_existing`、单账户单体验、审计、链接只能用一次、无 Cookie/伪造 Cookie/跨站 Origin 被拒、Gemini 未启用、"不是我"切换并撤销旧 Cookie、退出登录、会员页兑换也记住浏览器、已知对话仍返回 ready/checkout、Temu 异步交付路由仍由 0.10.28 提供 | **24/24** |
| `dev-tests/run_browser_tests.py`（页面） | Chromium，桌面 1280×860 与手机 390×844：首次表单、领取 1 次体验、同浏览器显示已有账户、未勾选不能关联、关联后文案与次数、"不是我"、其他浏览器看不到账户、退出登录、无横向溢出、无 JS 错误 | **20/20** |
| `dev-tests/run_browser_tests.py <技能目录>`（联调） | 真实 Temu 技能 v1.0.15 客户端 + 真实服务链 + Chromium 手机：三个新对话（"我的账户"、"已关联"、首轮图片需求后"继续"）最终只有 1 个账户、1 条体验记录；另一部手机看不到账户 | **12/12** |
| `tools/verify_bundle.py`、`tests/test_admin_sessions.py`、`integration/.../tests` | 包自带检查 | 通过（`dev/start.py` 的清单哈希已随改动更新） |
| 部署脚本演练 | 在模拟服务器上（0.10.29 生产目录结构、真实 drop-in 文件、空库，用替身 systemctl 真实启停服务进程）：`--check`；部署成功并通过健康检查；部署后页面在 Chromium 下 20/20；`--rollback` 后页面与原文件逐字节一致、入口回到 0.10.29；故意让新版启动失败时自动回滚到 0.10.29 且不装页面 | 全部通过 |

## 6. 未验证项

- **没有部署，也没有在生产或隔离线上环境运行过**；没有真实 Nginx/TLS 下验证 `Secure` Cookie。
- **没有在真实手机和 WorkBuddy 宿主里测**：特别是小程序"点击链接自动复制、到手机浏览器粘贴"这条路，以及微信内置浏览器、iOS Safari 的 Cookie 保留情况。
- **Docker 开发容器没有实际启动**（交付环境与本次环境都没有 Docker），本次是在本机用 `/opt` 符号链接还原路径运行的。
- 页面文案是我拟的，请按你们的原文要求调整（`index.html`、`trial-register.js`）。

## 7. 已知限制

- 只对同一部手机、同一个浏览器有效；换手机、清缓存、无痕模式认不出来，仍需账户备份恢复。
- 清掉 Cookie 后再按新账户确认，仍可能多领一次体验（与今天相同，不更糟；原有每 IP 每日开户上限仍在）。
- 关联必须本人点确认：如果商家被骗点了别人对话里的链接并点"关联原账户"，对方对话会用上商家账户。缓解：链接 5 分钟过期、只能用一次、必须勾选同意、页面提示"只在你自己刚从 WorkBuddy 对话里打开的链接上点关联"，并有审计记录。

## 8. 部署（由负责人在服务器上执行）

推荐用部署脚本，一条命令完成。先把补丁 ZIP 传到服务器并解压，然后：

```bash
cd <解压目录>/snapshot/opt/skill-platform/member-0.10.31/deploy
sudo python3 deploy_0_10_31.py --check   # 只做检查，不改任何东西
sudo python3 deploy_0_10_31.py           # 正式部署
```

脚本依次做：

1. **前置检查**（任一项不通过就停止，不改任何东西）：`skill-platform` 当前入口必须是 0.10.29；共享库存在；线上注册页 3 个文件必须与 2026-10-22 快照一致（如果之后有人改过页面，脚本会停下；确认后可加 `--force-page`）。
2. **备份**到 `/var/backups/myplanestore/0.10.31-<时间>/`：共享库在线一致性副本 `shared.db`（权限 600）和注册页 3 个原文件。
3. 复制 `member-0.10.31/`（不含 `dev-tests/`、`deploy/`）到 `/opt/skill-platform/`，属主与 0.10.29 一致。
4. 写入 drop-in（**沿用线上现有的解释器和参数，只把入口文件换成 0.10.31**），`daemon-reload`，核实入口已切换，**只重启 `skill-platform`**。
5. **健康检查**（最多 60 秒）：`/health`、`/render-info`（temu-render-v1），以及无 Cookie 时 `remembered` 返回 `{"remembered":false}`。**不通过就自动回滚**到 0.10.29 并退出，页面不会安装。
6. 服务正常后才安装注册页（原文件另存 `*.pre-0.10.31`），并写部署记录 `deploy-record.json`。

脚本不碰订单、余额、体验、套餐、其他服务和数据库已有的行。手动部署时按同样顺序：先服务、确认健康，再装页面。

部署后请用隔离测试账户在手机上走一遍：关联账户 → 新开对话 → 说"我的账户" → 打开链接 → 关联原账户 → 说"已关联"，核对余额与体验次数不变。

可选环境变量（加在 drop-in 的 `Environment=` 里）：`MYPLANESTORE_DEVICE_DAYS`（默认 180，1–400），`MYPLANESTORE_DEVICE_LINK_PRODUCTS`（默认 `temu`）。

### 让通用通道（gemini 前缀，除 Temu 外的全部付费 skill）也用上

**2026-10-22 起，`deploy_0_10_31.py` 默认就是 `--products gemini,temu`，三步合成一步，下面的手工两步只在需要单独开关某个通道时才用。**

服务端只有 `gemini` 和 `temu` 两个产品前缀：`temu` 是 WorkBuddy 专家/技能包专用，`gemini` 是通用 skill 通道。
设备记忆按前缀生效，没有更细的按-skill 开关，所以开 `gemini` 等于给通用通道上的所有 skill 一起开（它们本来就共用同一套账户和次数）。
`link_entry` 校验 `product` 必须一致，Temu 与通用通道的设备记忆互不串。

部署脚本已经把这两件事都做了（写 `Environment=` 行 + 装两个注册页）。要手工单独做，或者只开其中一个通道时：

1. drop-in 里加 `Environment=MYPLANESTORE_DEVICE_LINK_PRODUCTS=gemini,temu`，`daemon-reload` 后重启 `skill-platform`。
2. 装 Gemini 注册页：`python3 /opt/skill-platform/member-0.10.31/web/install_web.py /var/www/image-assistant --product gemini`（原文件同样备份为 `*.pre-0.10.31`）。

两步都没做时，通用通道行为与今天完全一致：`/platform-api/gemini/membership-api/remembered` 返回 404，页面退回原来的新账户表单。
但要注意：Gemini生图器 v1.0.18 的话术里已经写了"网页会认出原账户"，服务端没开时网页认不出，这句话就兑现不了。要么部署，要么别上 v1.0.18 的方案A话术。
回滚：`install_web.py /var/www/image-assistant --product gemini --rollback`，并去掉该 `Environment=` 行。
（`--product gemini` 这个参数名沿用服务端前缀，装的是通用通道那一页。）

## 9. 回滚

一条命令：`sudo python3 deploy_0_10_31.py --rollback`（还原注册页、删除 drop-in、重启并核实回到 0.10.29）。手动回滚：

1. 页面：`python3 /opt/skill-platform/member-0.10.31/web/install_web.py /var/www/image-assistant --rollback`。
2. 服务：删除 0.10.31 drop-in，`systemctl daemon-reload`，重启 `skill-platform`，核实 ExecStart 回到 0.10.29。
3. 数据：三张新表留着不影响旧代码（旧代码不读它们）。已经关联的对话在旧代码下仍映射到原账户（写在原有 `trial_claims` 表里），不会丢次数；浏览器里的 `mps_device` Cookie 会被旧代码忽略。

# 微信扫码关联第二版部署结果（2026-11-11）

**已部署并完成部署字节的隔离合成验收。** 固定补丁 `e22eeb40348468d2ba942669c0ed5fbbfb9a141c`；完成时间 `2026-11-11T18:10:48+08:00`（北京时间）。`skill-platform.service` 当前 active/running，PID `959435`，只执行 **1 次**人工重启，自动重启 **0 次**。重启加载时间 `Wed 2026-11-11 17:59:26 CST`。用户在当前聊天直接授权本次微信认证部署；该授权不扩展其他生产或财务权限。

## 部署文件及备份

| 生产目标 | 最终 SHA256（与 e22 清单一致） | 权限与属主 |
|---|---|---|
| `/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py` | `8fb426f481015acccea592ef40ce3c338a8178d2baee9fc22ca6f483b6a76121` | `root:root 0644` |
| `/var/www/image-assistant/auth/wechat/wechat.js` | `0728dee07670ad487ec47543023e20a70d58aa3b83f5580b125f26296df2aaf2` | `root:root 0644` |

备份目录 `/var/backups/skill-platform/wechat-binding-20261111T095922Z-152c45b8`，0700；备份文件0600，共核验48个原文件（两个代码文件及46个原systemd主配置/drop-in）。配置原文、Environment和凭证不入仓。服务入口仍为 `/opt/skill-platform/gemini-support-20261107/run_shared.py`，解释器仍为 `/opt/skill-platform/1.2.0/venv/bin/python`；原参数和Environment未改。全部配置文件哈希未变，最终两文件保持root:root 0644。

## 部署后的五种合成场景

从两个生产目标**重新读取实际字节**，核对e22 SHA后放入隔离临时树；固定RegistrationEntries/DeviceLinks fixtures、临时SQLite及假的OAuth exchange，回环HTTP运行22项服务端回归，**22/22通过**，以下五种均通过。测试子进程禁止非回环网络。没有向生产注入假OAuth或注册合成客户。

| 场景 | 结果 | 核验 |
|---|---|---|
| 电脑页保持打开 | 通过 | registered；callback 302；finish linked及固定支付路径 |
| 扫码后关闭电脑页 | 通过 | 完全不调用finish；callback已关联、独立会话、302；registered |
| 手机直接打开/异浏览器扫码 | 通过 | 无需电脑cookie；独立新会话、固定支付页302；registered |
| 第6分钟扫码 | 通过 | 入口签发6分钟后start及QR start后6分钟callback均registered并302 |
| 同一身份重复扫码 | 通过 | 重复finish及新安装同微信复用账户，不重复创建或领取；registered |

部署后读回的同一JS在Windows Node `v24.19.0` 独立临时树运行10项网页逻辑回归，**10/10通过**，语法检查通过；Linux无Node，未在那里执行JS测试。完整测试输出和SHA见同名JSON。Linux隔离测试目录已删除。这里的“通过”是部署字节的合成验收，不是五种真实微信live流程验收。

线上只读核验：health=ok；共享钱包/新资源能力保持原值；公开plans SHA `bce0ea49eacd8369998a80b26e26beb7d8eb01c22acf26f86cfbbe26c374244c` 与部署前相同；公开JS SHA与清单相同；无效callback返回400且不签Cookie。最终核验时间 `2026-11-11T18:14:38+08:00`。

## 中途核验误判及纠正

部署工具错误地比较了`systemctl show ExecStart`完整渲染，其中含动态PID及起止时间；重启后这些正常变化被误当成配置漂移。脚本因此在唯一一次成功重启后恢复了两个旧文件，服务本身始终正常。

已把比较范围修正为静态path/argv/ignore_errors及全部配置文件哈希。直连新PID的回环监听口，用**一次匿名、不带账户/entry/Cookie的合法start**，得到HTTP200、900秒及不签Cookie，区分原版与第一版，确认第二版行为。这个探针确实产生一条未关联账户的短期OAuth状态，不是只读；没有扫码或换身份，没有保留state/verifier/URL，也没有手动改库。状态900秒后失效，清理由后续正常start处理，不冒称定时删除。

随后仅将同一e22两个文件重新原子落盘，使磁盘与已加载代码一致，**没有追加重启**。新PID、NRestarts=0、静态命令和配置均保持不变；最终SHA、公开路由和全部合成验收已通过。初始审计与修复审计分别留在备份目录的`deployment.json`和`resync-without-restart.json`，不覆盖失败历史。

## 权限与实际范围

未执行客户订单、钱包、余额、套餐或核款操作；未调用真实微信换身份和真实生图；没有schema迁移、其他服务控制或平台上架。全家福产品仍`submitted`，Skill包1.0.1原字节未变；旅行写真仍`blocked / PAUSED_BY_OWNER`。等待直接部署授权的旧记录由本次人类直接授权及部署结果解决，旧事件/原claim回执保留。

真实微信/手机浏览器Cookie、WorkBuddy及实际客户结账仍未代验；合成状态机通过不冒充这些项目通过。补丁固定目录内README/TEST-RESULTS是e22部署前快照，本部署报告记录最新生产结果，不改固定源码或原manifest。

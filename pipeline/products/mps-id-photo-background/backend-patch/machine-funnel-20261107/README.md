# 机器漏斗补丁 machine-funnel-20261107

基于 2026-11-06 本机原稿的四个文件整理。原稿 SHA-256 见 [source-draft.json](source-draft.json)，其中记录的是整理前的文件哈希。2026-11-07 已重新在线读取 WorkBuddy 技能页和专家页，均为 HTTP 200。 [技能开发文档](https://open.workbuddy.cn/docs/skill) · [专家开发文档](https://open.workbuddy.cn/docs/expert)

## 能力范围

补丁提供可选的机器漏斗遥测、独立 SQLite 存储、L0–L4 报表、现有后台会话保护下的查询页面，以及离线 CLI。真机验收时可以用 `is_test=true` 查询安装首见、页面观测和账户关联等遥测证据。报表中的访问量按当日加盐 IP 去重。入账来自共用钱包的只读投影，不能当作技能收入。缺少业务数据时，相关步骤返回 `null`。

四份原稿均为遥测和报表代码，未包含 WorkBuddy 宿主操作、逐场景截图、浏览器零消耗验证或上传适配器。隔离测试只覆盖此补丁，`HOST_ACCEPTANCE_UNAVAILABLE` 仍需在实际 WorkBuddy 宿主与上传通道完成验证后解除。

## 接口和集成边界

| 用途 | 约定 |
|---|---|
| 能力探测 | `GET /platform-api/telemetry/v1/capabilities` 在侧库就绪时返回 `machine-funnel-v1` 和允许的技能 |
| 新遥测 | `POST /platform-api/telemetry/v1/first-dialogue` 使用原事件字段加 `machine_id`。三个身份字段为规范小写 UUIDv4。新契约成功返回 204，回执在 `X-First-Dialogue-Receipt` 等响应头 |
| 现有遥测 | 可解析的旧八字段请求交给现有处理器。首版客户端继续使用既定 8 字段 / 200 协议，未来升级须先做兼容联调 |
| 关联 | `POST /platform-api/telemetry/v1/first-dialogue/link` 对机器漏斗拥有的事件核对回执和原账户身份。身份沿用 `store.user`，现有速率回调可复用。其他回执交给现有处理器 |
| 页面观测 | 可选接入现有 `journey-page` 和请求上下文，原处理器返回成功后才记观测 |
| 管理报表 | `GET /ops/machine-funnel` 提供查询表单，`GET /ops/api/machine-funnel` 提供汇总与分页详情。沿用父处理器的 `authenticated()` |

允许技能默认仅为 `mps-id-photo-background`。事件库保存 HMAC 化的机器和安装标识及按日加盐 IP 摘要。报表按北京时间查询，测试数据通过 `is_test` 分开。显式运行 `Funnel.purge()` 清理超过 180 日的明细，保留去重索引。业务库使用 SQLite `mode=ro` 和 `query_only`，独立侧库负责写入。

## 隔离验证

```text
python -B -m unittest discover -s . -p "test_*.py" -v
```

Windows Python 3.12.10 和 WSL Ubuntu Python 3.12.3 各通过 17 项。两次从独立临时目录运行，使用合成 SQLite 和回环 HTTP，覆盖新旧事件分流、账户关联、获准页面观测、管理员门禁、侧库迁移、明细保留期、报表和业务库字节比对。 [测试记录](test-results.json)

## 后续部署步骤

本次交付停在部署前。下列步骤供负责人审阅和授权后的独立部署执行。

1. 先核对届时运行的遥测和后台入口、现有会话及限流函数，备份对应配置。将本目录安装至独立版本路径，创建仅运行用户可访问的侧库目录。Linux 目录使用 `0700`，数据库和独立生成的 32 字节 HMAC 密钥使用 `0600`。Windows 运行报表时用 ACL 限制密钥访问，POSIX 权限断言在 Linux 执行。
2. 以服务身份运行 `python report.py --db <独立侧库> --migrate`。用 `Funnel(侧库路径, 密钥字节)` 构造实例。校验侧库和业务库是两个不同文件，报表仅将现有业务库作为只读数据源。
3. 在版本化入口显式接线。共享路由通过 `funnel_gateway.install(现有处理器, 原账户存储, funnel, 现有限流回调)` 包装。如果接入页面观测，将已有 Journey 模块及实例一并传入，确保观察器包在其成功响应之外。后台工厂使用 `funnel_ops.extend(原后台工厂, funnel, 只读业务库路径)`，页面文件与模块放在同一目录。具体启动层接线需结合届时服务入口验证，当前目录没有自动安装或重启脚本。
4. 先使用隔离的服务身份和合成数据复查旧 8 字段 / 200、新 9 字段 / 204、回执关联、后台鉴权及报表。正式启用前核对受信代理会覆盖 `X-Real-IP`，并安排侧库备份及明确的明细清理任务。真机操作与上传适配器分别验收。
5. 回滚时撤去两个包装器，恢复备份的入口配置，按原运维流程恢复旧服务。保留侧库及其密钥供审计和恢复。

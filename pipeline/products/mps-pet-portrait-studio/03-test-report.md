# 宠物主题照相馆 1.0.4 A3 独立检查

**独立检查不通过。** 置为 test_failed，由 Claude 按接力修复。

- 时间 2026-11-10T23:20:34+08:00，Windows 干净解压。只做静态及 Mock 定向验证。真实上游调用和真实付款均为零。按 SOP 第 7.5 节豁免跳过 WorkBuddy 真机验收及浏览器验证。
- 固定包事件 `evt-ae7e580030439a2a9650ff7a1368ff625d87124e0f6d44ebf61b39985af649e0`，源提交 `e27da59e346fb045cf54c10e290621a12ed82d26`。ZIP 1,026,973 字节，SHA256 `5129d1933d94b2f950bac67524df2cd9a82e22ecf2c8d8e4d3eb48916b26e673`，与 Claude A2 一致。[固定 ZIP](https://github.com/Haihe2026/myplanestroe/blob/e27da59e346fb045cf54c10e290621a12ed82d26/pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.4.zip) · [A2 报告](https://github.com/Haihe2026/myplanestroe/blob/e27da59e346fb045cf54c10e290621a12ed82d26/pipeline/products/mps-pet-portrait-studio/02-self-test.md) · [付费转化 SOP](https://github.com/Haihe2026/myplanestroe/blob/2f30b615c2b249e9d8776a65307f7450b5bc1a77/docs/sop/sop-image-gen-skill-auto.md#七付费转化自检2026-11-10-真机实测整改强制)

## 核对结果

| 检查项 | 结果 | 证据 |
|---|---|---|
| ZIP 完整性及结构 | 通过 | 24 个文件，CRC 正常，最多两级，无同名或符号链接。包内 SKILL.md、入口、话术、遥测与固定源文件的 Git blob 一致。 |
| Frontmatter、接管、收藏与遥测 | 部分通过 | 八项必填字段，三组中英语义和尺寸一致，欢迎句固定，接管规则在执行规范首节，含禁止编造和禁止宿主替代生图，收藏 ID 一致，无隐藏注释。15290 字节，21 个触发词含充值。八字段、2 秒、渠道与版本一致。简介末句见 A3-PAY-03。 |
| 示例及路径 | 通过 | 十张 PNG 可读，来源和派生哈希逐项匹配。空格目录、井号目录的两条实际 Markdown 链接均解码命中。独立 demo 零网络、零凭证读取。 |
| 账户入口及话术 | 部分通过 | 五个命令 `topup/status/auth/balance/history` 在全新账户状态都使用持久化安装标识调用一次 `quick-entry`，可给关联链接。模拟状态 0 与 503 的充值话术区分网络和繁忙，非第一方域链接被拒。其余见 A3-PAY-01/02。 |

## 退回项

### A3-PAY-01 全新环境的「已付款」分支没有关联入口

在无账户、无凭证的全新隔离目录调用 `paid`，Mock 准备返回注册关联链接。实际没有请求 `/quick-entry`，直接返回 `paymentRegistered` 和「已收到你的付款登记」，无关联链接。SOP 7.2 把 `paid` 列入账户菜单。预期新用户走既有一次性关联入口，到账只依据服务端证据。请补齐 `paid` 的全新环境和断网回归。[入口代码](https://github.com/Haihe2026/myplanestroe/blob/e27da59e346fb045cf54c10e290621a12ed82d26/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L825) · [SOP 7.2](https://github.com/Haihe2026/myplanestroe/blob/2f30b615c2b249e9d8776a65307f7450b5bc1a77/docs/sop/sop-image-gen-skill-auto.md#72-脚本必须整改)

### A3-PAY-02 已失效的第一方短链仍被转述

Mock 给 `/quick-entry` 返回允许域、允许路径的注册链接，带服务端字段 `expires_in=0`。实际 `topup` 仍回显链接；同一有效期正常样本给链接，外部域样本被拒。现有入口提供 `expires_in`。预期对带失效元数据的链接停止转述，沿原安装身份安全重取或如实提示。请覆盖过期、有效和外部域三类。[链接校验](https://github.com/Haihe2026/myplanestroe/blob/e27da59e346fb045cf54c10e290621a12ed82d26/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L255) · [关联入口](https://github.com/Haihe2026/myplanestroe/blob/e27da59e346fb045cf54c10e290621a12ed82d26/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L413) · [现有服务端有效期](https://github.com/Haihe2026/myplanestroe/blob/2d50217ed9c4e653d37c35ae3fa611a0f096db9c/snapshot/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py#L45-L51)

### A3-PAY-03 简介末句缺账户场景

简介正文有充值、付费链接、余额、订单说法，最终唯一调用倾向句只列生图领域。SOP 7.3.2 要求在该末句一并涵盖本技能账户问题。请保留已核对的触发词与正文，修正末句并加断言。[包内简介](https://github.com/Haihe2026/myplanestroe/blob/e27da59e346fb045cf54c10e290621a12ed82d26/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/SKILL.md#L5) · [SOP 7.3.2](https://github.com/Haihe2026/myplanestroe/blob/2f30b615c2b249e9d8776a65307f7450b5bc1a77/docs/sop/sop-image-gen-skill-auto.md#732-description决定宿主会不会选中技能)


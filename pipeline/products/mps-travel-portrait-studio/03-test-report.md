# 旅行打卡写真照相馆 1.0.0 A3 独立检查

**独立检查不通过。** 固定ZIP发现5项包实现缺陷，置 `test_failed`、`rounds.test=1`，退回Claude修复。1.0.0不是可交付上传版；附录D本机导入尚未进入。

- 时间：2026-11-11T21:11:53+08:00；Windows全新目录干净解包；仅独立静态检查，没有重跑Claude完整A2或运行客户端业务命令。
- 事件 `evt-a509a78a3874d566d00e98af4fd95bd751f114b776c96c912ea4159ecd99c48e`，本机与远端原claim `50a74112-e551-4388-97f2-95a7eb084a35` 一致；固定输入指纹已复算，产品检查认领提交 `aa6ff59e56ab7d98847a15de0fdad251ed314919`，未重复认领通知。
- 固定来源 `d4a1d5cec49d064dd5bfce9eedc86febc75d5d25`；已读远端当前SOP（blob `99ef71e0a2d84535193031ca8f5c6c269ec68799`）、配置、status/log/brief、固定MD/JSON规格和A2报告；24个包内文件与仓库源码逐字节一致。
- 官方技能页：2026-11-11T21:00:00+08:00 本次在线读取 https://open.workbuddy.cn/docs/skill 成功，HTTP200，内容SHA `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；同时读固定2026-11-08快照技能章。当前仅Skill，未读不适用的expert页；未修改开发文档。

## 固定包及检查通过项

| 项 | 实际检查结果 |
|---|---|
| ZIP | [mps-travel-portrait-studio-1.0.0.zip](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/dist/mps-travel-portrait-studio-1.0.0.zip)，2,404,375字节，24文件；SHA256 `fcecdcefd5f158212da556115618fd2467de757022f8e1c13e0978482999e1cd`，与A2一致；CRC完整。 |
| 目录 | 单一slug外层目录；技能逻辑根内最多两级；无重复/大小写冲突、越界、符号链接或缓存。 |
| 元数据 | 八必填字段，无重复YAML键；slug/中英文名/1.0.0/渠道跨SKILL、_meta和脚本一致；固定欢迎句逐字一致。SKILL.md 15,355字节。 |
| 双语与触发 | 哈尔滨/三亚/西安3对逐项与规格一致，单人、2:3和1024×1536一致；23触发词和完整中文名充值词，唯一调用倾向句，首节接管。 |
| 10张示例 | key/标题与规格、README、SKILL一致；10PNG完整解码，512×768；原字节SHA均与Codex源、provenance和derivation一致；每项note带非实拍标注。 |
| 外置logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/dist/logo.png)，512×512PNG，350,096字节；SHA256 `d8177d72fbc14acc0e2371fd5af976ced0302c2cab395c1937a4dfa9d66acee9`，Codex原字节未变，无重新生成。 |
| Markdown链接 | 从实际包提取已审纯路径格式化函数，仅求值此纯函数；含空格、#、%的3条真实合成PNG路径经CommonMark解析/解码均定位原文件，无意外query/fragment；不执行客户端业务。 |
| 部分契约 | 单人和三独立flags、源SHA冻结、真实用户提示词不套示例人口属性、六字段/三尺寸、8字段白名单/2秒/关闭开关、240秒外层预算、401/404原任务只查与锁定、缺示例整组退出3均保留。下列绑定、输入校验、遥测失败、路由及传输告知仍不符合。 |
| 文案与秘密 | 对客SKILL/README及固定话术AST字面量禁用词扫描、实际密钥模式扫描通过；首轮文字跳过、已实际展示去重、收藏/记忆等声明存在，未据此宣称宿主行为已验。 |

12类结构检查和逐图哈希见 `03-a3-1.0.0-evidence.json`。这些通过项不抵消以下缺陷。

## 缺陷及静态复核步骤

以下实际分支来自固定ZIP的源码与AST只读检查，**没有声称已经执行端到端复现**。所列Mock用例由Claude在修复后的A2实际执行并给出证据。

### A3-TRV-01（P2）：绑定没有确认，仍把Key视为可生成

- 位置：[studio.py:519–538](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L519)，后续生成入口[592–616](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L592)；401恢复[646–653](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L646)也调用同一函数。
- 静态案例：`/skill-key` 返回合法ready/key，随后 `/skill-key/bound` 返回 `bound=false`、缺字段，或抛超时/500/401。第535行丢弃响应，536–537吞异常，538仍返回ok；592→605→616继续生成POST。Key已缓存后520–521直接ok，重启也不补绑定确认。
- 期望：[固定规格135行/T04](https://github.com/Haihe2026/myplanestroe/blob/bf71982dce5534161ef3f3702d333832ec3fe6a9/pipeline/products/mps-travel-portrait-studio/01-dev-spec.md#L135)要求合法Key私存后，另POST绑定且必须 `bound=true`；恢复凭证也须确认。Key保存与绑定成功状态应分开，未确认不得新生成，原任务继续保持原键/原体，不因错误解锁。
- Claude回归：`bound=false`/缺字段/超时/500/401、进程重启、缓存未绑定Key、401恢复，均断言没有新增生成POST；补确认成功的正例可正常继续。不能把“服务端仍能识别Key”当作规格允许忽略绑定。

### A3-TRV-02（P2）：损坏参考图只凭尺寸头被放行

- 位置：[audit_images.py:25–96](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/audit_images.py#L25)，调用链[studio.py:430](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L430)、[474–483](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L474)至[616](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L616)。
- 静态案例：PNG有合法签名/IHDR和128×128等合格尺寸，但IDAT/CRC/zlib损坏或文件截断；`_png_info`遇IDAT即break。JPEG有合法SOF/尺寸但没有完整扫描数据；`_jpeg_info`遇SOF即return。两种格式之后只验尺寸即ok，`_job_body`原字节base64后可上传。输出结果PNG的完整验证在774行，不能替代输入检查。
- 期望：[规格81行/T02](https://github.com/Haihe2026/myplanestroe/blob/bf71982dce5534161ef3f3702d333832ec3fe6a9/pipeline/products/mps-travel-portrait-studio/01-dev-spec.md#L81)规定PNG/JPEG完整可解码，损坏输入须先本地拒绝并点名文件，不发业务HTTP。
- Claude回归：PNG坏CRC、IDAT/zlib截断、缺IEND，JPEG只有SOF或扫描数据截断等反例；保留合法静态PNG/JPEG正例。坏输入退出3、点名文件、业务HTTP和生成POST为0；不要只测试输出 `png_local.verify`。

### A3-TRV-03（P2）：首次对话失败后会自动重报

- 位置：[telemetry.py:86–119](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/telemetry.py#L86)，多处入口如[studio.py:332](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L332)、[409](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L409)、[573](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L573)；[resume:821–838](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L821)。
- 静态案例：第一次上报网络异常/超时/非200/坏响应，第107/110等行返回failed而未记已尝试。第97行仅用sent去重，所以后续plan/confirm/run会再次POST。同一次resume也可先822失败，再834或838调用cmd_run，573立即重报。
- 期望：[规格§10/T09](https://github.com/Haihe2026/myplanestroe/blob/bf71982dce5534161ef3f3702d333832ec3fe6a9/pipeline/products/mps-travel-portrait-studio/01-dev-spec.md#L195)和当前SOP明确同安装仅一次、失败即弃、不自动重试。须在发出前持久化尝试状态，写不进去则不发；成功回执仍单独校验并用于既有link，不影响主流程。
- Claude回归：异常、超时、非200、坏响应后多命令、嵌套resume→run和重启，匿名上报总尝试保持1；关闭/只读/损坏、正常200及原账户link/409不覆盖回归保留。不把服务端按安装去重当作客户端可重复发送。

### A3-TRV-04（P2）：樱花/古城在前时，特异服饰路由失效

- 位置：[studio.py:100–105](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L100)与[298–305](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L298)。
- 静态案例：没有明确目的地时，和服/汉服与樱花/古城/夜景同在ROUTE_STYLES一层，`min(hits)`按最先出现位置取值。“樱花下穿和服”会选sakura；“古城夜景穿汉服”会选oldtown。[当前测试430–431](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/tests/test_skill_contract.py#L430)只覆盖特异词在前的情况。
- 期望：[规格56行/T01](https://github.com/Haihe2026/myplanestroe/blob/bf71982dce5534161ef3f3702d333832ec3fe6a9/pipeline/products/mps-travel-portrait-studio/01-dev-spec.md#L56)：明确目的地优先；无明确目的地时和服→kyoto、汉服/唐风→xian；只有裸樱花才sakura、裸古城夜景才oldtown，不能随词序互换。
- Claude回归：上述两组正反词序和唐风变体均按特异场景；裸词仍到泛化场景；明确三亚/京都/西安等目的地保持最高优先。更新脚本、路由说明及A2，不改变十个主题总数。

### A3-TRV-05（P2）：本次照片传输同意没有告知接收方类别

- 位置：[welcome_copy.py:49–53](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/welcome_copy.py#L49)与[SKILL.md:103](https://github.com/Haihe2026/myplanestroe/blob/d4a1d5cec49d064dd5bfce9eedc86febc75d5d25/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/SKILL.md#L103)。
- 当前第2项仅“同意把这张照片发送去处理，只用于本次制作”，执行规范同样只有“同意发送这张照片去处理”。三个flags虽独立，但用户看到的告知没有图片服务及算力供应商类别。
- 期望：[规格83行/T02](https://github.com/Haihe2026/myplanestroe/blob/bf71982dce5534161ef3f3702d333832ec3fe6a9/pipeline/products/mps-travel-portrait-studio/01-dev-spec.md#L83)明确对这张文件传至图片服务及算力供应商取得独立同意；只需告知接收方类别，不披露品牌、模型、密钥或内部实现。
- Claude回归：本人及监护人两条文案都含本次照片与接收方类别；三项独立、缺一不设reference_consent/不生成。换图等未提交方案变更需重确认；已有任务仍原键续接。

## 退回与验收边界

根因均在包实现，不修订或放宽开发规格。保留十张示例和logo原字节、现有单人/三同意/原任务锁；Claude按5项逐一修复并补Mock/契约/A2回归，出固定修订ZIP及新SHA，更新自测报告再置 `package_ready` 交Codex复查。版本按现行SOP处理，勿覆盖其他产品或调用真实上游。

拒绝开通句与规格中示例措辞略有不同，但包使用当前SOP固定句，不据此退回。服务端canonical遥测event_id也不作为缺陷。Claude所报51/105等结果只属于A2，未当作本次Codex独立运行次数。

本次新增上游调用0、后端业务调用0、真实付款0、生产写入0、部署0、上传0。A3未通过，不进入附录D；真人/儿童、生产签名参考路由、真实微信/支付/手机、WorkBuddy宿主与平台接受/审核均未验证。后续A3通过后仍须按附录D由Muse固定包派活执行本机导入，正式上架由负责人手动。

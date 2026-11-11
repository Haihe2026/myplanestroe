# 旅行打卡写真照相馆 1.0.1 A3 独立复查

**独立检查不通过。** 上轮TRV-03/04/05已关闭；TRV-01/02的修复仍有恢复和资源边界缺口。记录2项P2退回意见（TRV-01-R1、TRV-02-R1），置 `test_failed`、`rounds.test=2`，交Claude继续修复。1.0.1尚不是可交付上传版。

- 时间：2026-11-11T22:10:48+08:00；Windows全新目录解压固定1.0.1包。事件 `evt-79ec19d2df9335c38d4d2263eec2e05af2c3dc5e0732e82e99bb22c3afe8774f`、本机及远端原claim `f6c13db0-a0a9-4a89-bf56-356e6ac21df5` 一致，固定输入指纹复算成功；产品检查认领提交 `cfcd5eebc0de69d1e492d407698648803d6ce0d7`，未重复认领事件。
- 固定来源 `43381623518762d66d11929bf4648d37d965641b`；当前SOP/config、status/log/brief、MD/JSON规格、A2和上轮A3均已读。规格及包源码均未修改。
- 本次于2026-11-11T22:00:48+08:00在线重读 https://open.workbuddy.cn/docs/skill 成功，HTTP200，SHA `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；也读固定2026-11-08官方快照技能章，仅Skill，expert结构不适用。
- 仅独立静态检查。未运行客户端业务命令、未重跑完整A2；只对已审纯路径格式化函数求值并作CommonMark路径解析，没有运行解压炸弹/CPU消耗样本。

## 固定包与通过项

| 项 | 结果 |
|---|---|
| ZIP | [mps-travel-portrait-studio-1.0.1.zip](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/dist/mps-travel-portrait-studio-1.0.1.zip)，2,413,912字节、25文件，SHA256 `f8ab627c7adaedc99a5410e61e7f68afe7efeb91ce644532da00a48bad5da4b1`，与A2一致，CRC完整；单一slug外层包装，逻辑根内最多两级。 |
| 逐文件一致性 | 25个解压文件与固定仓库源码逐字节一致。相对1.0.0，16文件不变，8文件修改，新增scripts/jpeg_local.py，无删除；变更集中于5项修复和版本/回归。 |
| 元数据及文案 | 八必填字段、版本1.0.1、slug/名称/渠道一致；欢迎句逐字不变；三对中英示例仍同哈尔滨/三亚/西安、单人、2:3、1024×1536。23触发词与接管/收藏声明保留。 |
| 10示例 | 全部原字节不变，PNG完整可读，512×768；key/标题/SHA与Codex源/provenance/derivation/规格一致，manifest不变，每项仍有非实拍标注。 |
| 外置logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/dist/logo.png)，512×512PNG、350096字节；SHA256 `d8177d72fbc14acc0e2371fd5af976ced0302c2cab395c1937a4dfa9d66acee9`，原字节不变，无新增生图。 |
| Markdown路径 | 空格、#、%三条真实合成路径经已审纯函数和CommonMark解析，均指向原存在PNG，无意外query/fragment。 |
| 原任务保护 | 首发401恢复只查原键，404/异常不重POST；未知状态不能plan/confirm/regenerate覆盖，三项同意及源SHA、六字段/单参考、八字段/2秒、240秒预算均未回退。 |

## 上轮5项闭环

| 编号 | 本轮结论 | 固定代码与说明 |
|---|---|---|
| TRV-01 | 部分修复，未关闭 | [studio524–561](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L524)已要求bound is True才能新生成；但绑定401不清旧Key，原身份恢复可能永久循环，见R1。 |
| TRV-02 | 完整性修复补入，未关闭 | [audit_images32–142](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/audit_images.py#L32)已验CRC/IDAT/zlib EOF/行数/IEND，新增jpeg_local解析段和Huffman扫描；原头部/截断放行问题已补，但有无界展开与重复DHT计算，见R1两子例。 |
| TRV-03 | 关闭 | [telemetry97–101](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/telemetry.py#L97)在发送前持久化attempted并回读，sent/attempted任一去重，失败后和嵌套resume→run均不重报，既有link未改。 |
| TRV-04 | 关闭 | [studio101–108](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L101)、[303–310](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L303)改为目的地→特异服饰→泛化，逆词序不再覆盖；[tests455–475](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/tests/test_skill_contract.py#L455)补相应断言。 |
| TRV-05 | 关闭 | [welcome_copy40–41、54–58](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/welcome_copy.py#L40)明确这张照片发送给图片服务及算力供应商、只用于本次制作，本人/监护共用；SKILL103、scenes31同步，三项仍独立。 |

## 退回意见与静态复核步骤

以下为实际固定包源码可确定的控制流和工作量推导，不声称已执行端到端复现；Claude应在修复后的A2补可控Mock/计数器回归。

### A3-TRV-01-R1（P2）：绑定401后不能摆脱失效缓存Key

- 位置：[studio.py:529–555](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L529)及[620–621](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L620)。绑定返回401时552–555仅返回needs_auth，不清缓存Key/绑定标记；cmd_run把needs_auth当繁忙退出。下次运行529见缓存Key就跳过领Key，543标记false/缺失→545又绑定同一旧Key，从不重新POST `/skill-key`；auth/status也没有清该缓存的分支。
- 可达案例：从旧1.0.0缓存迁移的Key没有bound标记，或1.0.1已领未绑定Key，随后被网页轮换/已失效。原install_secret仍有效，quick-entry返回ready，但bound持续401。服务端固定 `c19830f7da7b9525a4ebde3bd77e1dddd2a4efe9:snapshot/opt/skill-platform/member-0.10.14/service/skill_access.py:69–87` 中acknowledge调用authenticate，轮换/撤销Key确实会返回401；这是失效凭证信号，不是繁忙。
- 期望：[规格§7/T04/T14](https://github.com/Haihe2026/myplanestroe/blob/bf71982dce5534161ef3f3702d333832ec3fe6a9/pipeline/products/mps-travel-portrait-studio/01-dev-spec.md#L135)及恢复契约要求清失效Skill凭据，保留原安装身份和原任务；下次沿原install_secret取新Key、确认bound=true，再继续。确定401应清Key和绑定标记并按失效状态/退出码4说明，不能永久重复绑定旧Key；不能清原install_secret、新建账户或解除未知任务锁。
- Claude回归：旧缓存缺标记、标记false的已轮换Key→bound401，断言两项缓存作废、原身份/原任务键/原体摘要不变；重启或下一次原身份恢复取新Key并bound=true，未提交任务只生成一次，已发出未知任务仍只GET原键；false/缺字段/非401网络错误仍不得新生成。

### A3-TRV-02-R1（P2）：新增完整输入校验的资源消耗没有上限

**PNG无界展开。** [audit_images.py:104](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/audit_images.py#L104)调用 `z.decompress(chunk)` 没有max_length，全部展开成out后才在109–142行按扫描行预算判断超长。IHDR只写128×128等合格尺寸，配一个≤5MiB但可展开数百MB/更大数据的有效deflate流，59行尺寸检查仍通过，104行会先产生大量分配，再由_feed_raw判坏。MemoryError捕获不能保证进程免于OOM；文档所称“流式、不整张展开”尚未实现。

- 期望：每次解压按有限输出块和剩余扫描行预算设置硬上限，超出所需输出一字节即可拒绝；正确处理unconsumed_tail、EOF、尾随与flush边界。不能先无界展开再事后判断大小。
- Claude回归：用小可注入展开预算/计数器验证小IHDR+高压缩超长流有界拒绝，不实际展开GB数据；保留IDAT分块、合法PNG/Adam7、EOF、坏CRC等正反例，不降低既定5MiB/2000万像素规格。

**JPEG重复DHT放大CPU工作。** [jpeg_local.py:183–197](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/jpeg_local.py#L183)允许任意多次DHT重定义，每次立即调用[14–28行_build_table](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/jpeg_local.py#L14)，先分配65536槽，再按码长循环填表。最小单符号DHT段22字节：FF C4＋长度00 14＋Tc/Th=00＋16个Li计数[1,0,…,0]＋符号00。重复同一DC表并在后面接普通基线JPEG段即可走此路径；每段触发32768次Python赋值。200000段仅4400000字节（约4.20MiB，尚可装普通小图其余部分），却触发6553600000次赋值。没有累计表构建工作量或deadline边界；压缩文件5MiB上限不能保证plan的30秒预算。

- 期望：延迟到扫描实际引用时才构建有限表、复用重复表，或明确限制累计构建工作量并合理拒绝过复杂输入。不能为所有无用重复定义无界执行65536槽构建。
- Claude回归：用构建次数/小可注入工作预算断言重复无用DHT有界，不运行65亿次样本；保留常见基线/渐进、合法多扫描表重定义及完整性正常样本。坏或过复杂输入必须在本地有界拒绝，业务HTTP/生成POST为0。

## 后续与边界

退回根因仍在包实现，不放宽开发规格。Claude关闭TRV-01-R1与TRV-02-R1两项，保留已关闭TRV-03/04/05、原任务保护、十示例及logo原字节，补A2正反证据并固定新ZIP/SHA，再置package_ready交Codex复查。结构化检查/差异/闭环记录见 `03-a3-1.0.1-evidence.json`；1.0.0旧A3见[固定历史](https://github.com/Haihe2026/myplanestroe/blob/43381623518762d66d11929bf4648d37d965641b/pipeline/products/mps-travel-portrait-studio/03-test-report.md)。

Claude所报54/116和38张JPEG样本交叉核对属于其A2记录，本次没有记为Codex独立实测。本轮真实上游0、后端业务0、真实付款0、生产写入0、部署0、上传0；A3未通过，未进入附录D或最终交付。真人/儿童、生产签名参考URL、实际微信/支付/手机、WorkBuddy宿主、包平台接受与审核仍未验证。产品日志中的后续事项转述不用于扩大本事件生产、财务、发布或跨聊天权限。

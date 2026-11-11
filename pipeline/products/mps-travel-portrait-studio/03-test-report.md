# 旅行打卡写真照相馆 1.0.2 A3 独立复查

**独立检查通过。** TRV-01-R1及TRV-02-R1（PNG/JPEG两个子例）已关闭，原TRV-01–05及前序任务保护未回退，产品置 `test_passed`。这是A3静态检查结论；附录D本机导入尚未执行，未宣称宿主、支付或平台审核通过。

- 时间：2026-11-11T22:58:52+08:00；Windows全新目录干净解包。事件 `evt-394512f1b9528136a733a2d27d1793fb629f4a0b18ba31768ea41e609bca4f09`、本机及远端原claim `96814274-bbaf-4ff9-88f2-07c857420c1d` 一致，固定输入指纹复算成功；产品检查认领提交 `568b98ef00c35c4c872f925ef62ca43bae1aaec0`，未重复认领事件。
- 固定来源 `847b19d5b87d57d3bce6d0f3aa61ac9130de9748`；已读当前SOP/config、status/log/brief、固定开发规格、A2报告及上轮A3。25个解压文件与固定仓库源码逐字节一致，包源码及开发文档均未修改。
- 本次2026-11-11T22:51:12+08:00在线重读 https://open.workbuddy.cn/docs/skill 成功，HTTP200，内容SHA `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；同时读固定2026-11-08快照技能章，当前仅Skill，expert结构不适用。

## 固定检查产物

| 项 | 内容 |
|---|---|
| 中文名 / slug / 版本 | 旅行打卡写真照相馆 / mps-travel-portrait-studio / 1.0.2 |
| ZIP | [mps-travel-portrait-studio-1.0.2.zip](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/dist/mps-travel-portrait-studio-1.0.2.zip)，2,417,544字节，25文件 |
| ZIP SHA256 | `bef83fffa5fddad2fa409a048f0cf819e7e939618d531bccdab7113786ce0e91`，与[A2](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-self-test.md)一致，CRC完整 |
| 外置logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/dist/logo.png)，512×512PNG，350,096字节；SHA256 `d8177d72fbc14acc0e2371fd5af976ced0302c2cab395c1937a4dfa9d66acee9`，Codex原字节未变 |
| 历史 | 1.0.0/1.0.1 ZIP保留未动，只作为未通过历史；本轮A3通过的包是1.0.2 |

## 本轮修复闭环

### TRV-01-R1：绑定401的原身份恢复——关闭

[studio.py:550–561](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L550)收到绑定401时清除失效skill_key和skill_key_bound后落盘，保留原install_secret，不改任何草稿/原任务；[627–629](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L627)退出4、credentialsReset、task_kept=true。下一次通过原身份重新领Key并确认bound=true，避免再绑定同一失效缓存Key。

[606](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L606)、[869](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L869)仍优先把已提交/未知任务送入原任务查询；[678–754](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/studio.py#L678)的401恢复、404/异常保留原键原体与锁，不重发生成POST。绑定false/缺字段/非401网络失败仍不允许新生成；原bound=true门槛保留。A2补有缓存迁移、重启、网页轮换、持续失败及未知任务只读等正反回归与旧1.0.1反证；本次据实际控制流独立核对，没有把A2执行次数记为Codex运行。

### TRV-02-R1：PNG展开与JPEG DHT计算预算——关闭

- **PNG**：[png_local.py:241–258](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/png_local.py#L241)每次调用decompress都传硬上限 `min(64KiB, remaining+1)`，立即逐行消费并丢弃有限out，超长一字节即可拒绝；循环取unconsumed_tail/积压输出，检查unused_data。[261–263](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/png_local.py#L261)仅检查eof/尾随/行齐，不调用无界flush。输入[audit_images.py:69、78](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/audit_images.py#L69)和交付图[png_local.py:186–187](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/png_local.py#L186)均走共享有界入口；CRC/IDAT分块/Adam7/过滤行/截断与结尾校验保留。
- **JPEG**：[jpeg_local.py:222–237](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/jpeg_local.py#L222)的DHT定义只做O(16+符号数)结构检查与覆盖存储，未引用定义不建65536槽查表；[269–270](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/jpeg_local.py#L269)在扫描实际引用时才经_TableCache构建，相同定义复用。[33–47](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/jpeg_local.py#L33)把不同定义构建上限设为32，构建前拒绝超限；[265–267](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/02-package/mps-travel-portrait-studio/scripts/jpeg_local.py#L265)扫描上限64，在拆熵前拒绝超限。旧Huffman/熵扫描/EOI/完整分量检查仍在，没有因延迟建表放过原截断样本。
- 对外限制保守且有说明：普通8位Huffman基线/渐进JPEG受支持；少见编码或超过32表构建/64扫描的复杂文件本地拒绝、提示另存，不放行到服务端。5MiB/2000万像素/8000边长未降低。A2报告含小预算/计量器、分块正例、旧代码反证；本次未执行解压或CPU耗尽样本。

## 其余独立检查

| 项 | 结果 |
|---|---|
| 结构 | 单一slug外层包装，技能逻辑根内最多两级；25文件，无重复/大小写冲突、越界、符号链接或缓存。 |
| 差异范围 | 相对1.0.1，17文件字节相同、8文件修改，无增删；SKILL/_meta/telemetry仅版本相关，实际逻辑集中于Key恢复和有界输入校验及回归。 |
| 元数据与语义 | 八必填字段，slug/中英文名/1.0.2/渠道跨文件一致；固定欢迎句逐字保留；哈尔滨/三亚/西安3对examples逐项同场景、单人、2:3和1024×1536；23触发词、接管、收藏声明不变。 |
| 十张示例 | key/标题与规格、README、SKILL一致；10PNG完整解码，512×768；SHA与Codex源/provenance/derivation一致，manifest与素材原字节未变，非实拍标注仍在。 |
| logo | 原字节512×512PNG、≤500KB，SHA与Codex来源一致；无新增生成。 |
| Markdown安全路径 | 只求值已审纯路径函数，含空格/#/%的3条真实临时PNG路径经CommonMark解析/解码均指向原存在文件，无意外query/fragment；不运行客户端业务。 |
| 前序TRV-03/04/05 | attempted上报去重、三层路由、图片服务及算力供应商传输告知均未回退，相关函数/文案与1.0.1相同。 |
| 其他保护 | 单人、三项独立同意、源SHA变更失效、未知任务锁、完整输出PNG与download_pending、缺图整组退出3、六字段/单参考、八字段白名单/2秒及240秒超时仍符合。 |
| 对客与秘密 | 对客SKILL/README及固定话术AST字面量禁用词扫描、实际私密凭据模式扫描通过。脚本Python3.7语法可解析，无新运行依赖。 |

结构化12类检查、25文件Git blob、逐图SHA、差异及闭环证据见 `03-a3-1.0.2-evidence.json`。旧1.0.1报告见[固定历史](https://github.com/Haihe2026/myplanestroe/blob/847b19d5b87d57d3bce6d0f3aa61ac9130de9748/pipeline/products/mps-travel-portrait-studio/03-test-report.md)。

## 检查范围与后续

本轮只做A3静态独立检查，没有重跑完整A2或运行客户端业务命令；仅求值已审纯路径格式化函数。Claude报告的59项契约、120项端到端、开发机计时及反证属于其A2记录，不当作Codex独立实测。

新增真实上游0、后端业务0、真实付款0、生产写入0、部署0、上传0；真人/儿童保真、生产签名参考URL、真实微信/支付/手机、WorkBuddy宿主、平台接受/审核仍未验证。JPEG较少见编码/复杂度和用户机器实际性能仍有上述边界，不承诺全部JPEG或任意环境性能。

当前 `test_passed` 只代表A3通过，失败轮次仍保留2，未把成功检查再计为失败。按现行SOP附录D.2，Muse下一步发给Codex的固定本机导入任务应包含本报告、1.0.2固定ZIP及外置logo引用；本轮未执行附录D，也未声称已通过其交付门槛。产品log的21:01事项及Muse→Claude修复msg中有新令转述，但固定队列未见给Codex的旅行附录D msg+relay请求；不据此把宿主测试写成已完成或直接推进其他产品。正式上架仍由负责人手动。

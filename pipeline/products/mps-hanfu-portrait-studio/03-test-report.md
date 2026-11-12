# 汉服写真照相馆 1.0.1 A3 独立复查

**独立检查通过。HNF-A3-01..04全部关闭，未发现新的阻断。** 产品置test_passed，失败轮次保留1。按现行SOP，附录D及D.6暂停，交固定ZIP与外置logo给负责人手动上传；此结论不代表宿主、真实支付/出图或平台审核通过。

- 时间：2026-11-12T20:09:48+08:00；事件 `evt-25e3ba4a6938bf19148090f5caa6b23a270d96c92f36898c52ef4829da50f1c6`，本机/仓库原claim `8277ec63-e146-41ce-b4a1-0b8f21adebd3`一致，固定输入指纹复算通过；产品认领提交 `53bef15dc3ea1686530254a7ca1468599f489d56`，不重复认领事件。
- 固定修复包 `fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f`；开发规格仍为 `1a7d115d281ca3b25ce86609cfb9b29adfe7a895`。最新SOP/config/status/log/brief/spec及原1.0.0 A3、Claude1.0.1 A2已读。
- 本次2026-11-12T20:09:48+08:00在线重读[WorkBuddy技能文档](https://open.workbuddy.cn/docs/skill)成功，HTTP200、277042字节、SHA256 `6ac24dbdbe0d7f8bf907e30b9c71909c0f87499561ee87de011a0a818041c68c`；仅团队Skill。
- 从全新目录干净解包，仅静态检查、AST/字节/标准YAML和CommonMark解析；不导入或执行包函数/客户端，不重跑完整A2，不调用业务/上游或浏览器。

## 固定交付

| 项 | 内容 |
|---|---|
| 名称 / 版本 | 汉服写真照相馆 / mps-hanfu-portrait-studio / 1.0.1 |
| ZIP | [mps-hanfu-portrait-studio-1.0.1.zip](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/dist/mps-hanfu-portrait-studio-1.0.1.zip)，4,815,365字节、25文件，CRC完整、逻辑根最多两级 |
| ZIP SHA256 | `c4d345920b0fd0c2f1d3443c2044f520876f21000865fcac3212a55314c2f6ea`，与A2一致 |
| 外置logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/dist/logo.png)，512×512PNG、418271字节，SHA256 `d6cda4a802770817435324b898d5e0f1705adf95cd2a7c665baba27727c2978b`；原字节、不进ZIP |
| 历史 | 1.0.0 ZIP原字节保留，SHA256 `624ee30dbd94d09f9b2a44d7b4c4c239cb9dd09e0d4f7c1ae11af23a1f9d30ba`，该旧版未过不作上传版；[原缺陷报告](https://github.com/Haihe2026/myplanestroe/blob/bde7655dea57363709ec13487b19a90500ffa87d/pipeline/products/mps-hanfu-portrait-studio/03-test-report.md)及03-a3-1.0.0-evidence.json保留追溯 |

## 四项修复闭环

### HNF-A3-01：形制与服饰叠加——关闭

[studio.py:452–455](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L452)的outfit_text先由outfit_of决定整套结构，再追加颜色细节，供plan摘要和开工复述共用。[462–465](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L462)选定form时使用不含默认宋风的FORM_VISUAL并配套FORM_MAKEUP；[473–479](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L473)无论outfit是否为空始终输出选定形制，补充仅叠加、不改衣型领裙。七合法组合（日常唐/明/宋、园林唐/明/曲裾/宋）控制流均可达；不再有原not-outfit条件导致丢form。

[610–614](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L610)对冲突outfit先给outfitFormConflict等待消歧，不进planned；[581–584](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L581)原任务锁优先，未提交先_void落盘作废旧确认，所以新增早退不会复活旧方案。没有新增HTTP字段，仍六字段一参考。

### HNF-A3-02：否定与主需求——关闭

[strip_negated:377](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L377)保原话，仅剥离被排除的路由词；[393/404](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L393)场景及intent均先处理否定。原句“不要婚服，我要新年宋制汉服”不会再仅因婚服词硬拒；仅否定越界而无主需求时clarify_main_need。[SKILL.md:88](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/SKILL.md#L88)与[scenes.md:21](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/references/scenes.md#L21)要求结合上下文，被否定词不作拒绝依据。正向明确婚服/和服/儿童等范围限制保留。规则是有限窗口，不声称已解决所有自然语言否定；较远/复杂情况由宿主澄清，宿主实际行为未验。

### HNF-A3-03：反馈未知时不自动重跑——关闭

[SKILL.md:53](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/SKILL.md#L53)全局重跑明确feedback例外；[119](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/SKILL.md#L119)无编号等用户显式说提交反馈才--retry、有编号只ticket GET。[studio.py:1361/1365/1369–1370](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/scripts/studio.py#L1361)相应信号auto_retry=false。原_submit_pending同键同体、已知tid GET及生成未知原键GET函数没有回退；未杜撰工单by-key、未自动换键或重复生图。

### HNF-A3-04：侠客示例说明——关闭

[assets/demos.json:43](https://github.com/Haihe2026/myplanestroe/blob/fe2e051ffaf06e5e3afee65f754e4a9e486d3a8f/pipeline/products/mps-hanfu-portrait-studio/02-package/mps-hanfu-portrait-studio/assets/demos.json#L43)将“竹林侠客风”改为实际可见的“木质影棚侠客风”，保留AI非实拍。清单只这一项note变化，十PNG及logo原字节/SHA全保留，无新增生成。

## 其余独立复核

| 项 | 结果 |
|---|---|
| 原始ZIP与源码 | 25文件与ZIP及固定仓库源码逐字节一致，无越界/符号链接/冲突/三级目录或缓存。 |
| 差异范围 | 16文件原字节相同、9变更，无增删。变化为SKILL、_meta、demos.json说明、scenes、studio、telemetry版本、welcome_copy及2测试/预览文件；图像助手和十图未动。 |
| 元数据 | 最终原始YAML标准解析成功，无诊断投影/重复键；八必填、25触发词、接管、欢迎句和三对中英主题/同画幅像素符合；SKILL15352字节≤15360。 |
| 版本/预算 | SKILL/_meta/studio/telemetry/预览一致1.0.1；三尺寸、六字段、8遥测、2秒/240秒预算保留，无machine_id或供应商Key扩展。 |
| 十图与logo | 十张RGB PNG512×768、4,718,679字节，逐张同规格/provenance/派生记录原SHA；garden832×1248及n1返回3的离线选择异常仍按来源保留，不当生产单结果协议通过。外置logo原字节、≤500KB。 |
| Markdown路径 | 静态核实际编码函数，独立构造含空格/#/%的3条真实PNG路径并用CommonMark解析/解码，均定位存在文件且无query/fragment误拆；没有运行包函数。 |
| 状态机及输入 | 原任务锁、先失效后校验、新B保存、三许可、HTTP前完整有界预检、绑定401/原身份恢复、模糊提交仅GET及下载原图续取未回退；图片3助手字节相同。 |
| 售后/遥测 | 原工单幂等/已有tid GET未动；首次上报attempted发前原子保存、失败不重发的函数保留；关闭开关属本品，未发敏感字段。 |
| 对客与秘密 | 用户段/README/固定话术扫描无内部供应商/模型/秘密；全部脚本AST能按Python3.7语法解析，非实际解释器验收。 |

结构化12类检查、25源码Git blob、差异、素材SHA及三份独立只读专项见03-a3-1.0.1-evidence.json。

## A2记录及未验证边界

Claude报告64契约+142端到端及干净ZIP Linux unshare断网执行通过，补了七形制组合、冲突/否定、反馈未知等回归；本轮只读报告和相关新增测试文本，不冒称Codex重跑。修复轮明确Windows隔离Mock未验证、实际Python3.13，AST3.7不等Windows/3.7实跑，未为权限断言改测试凑通过。

真机验收已跳过（负责人长期规则），现行附录D及D.6暂停，不派安装检测。真人/各输入效果、历史形制准确率、真实微信/付款/核款、生产签名参考、宿主对话/收藏/不@触发、平台解析/包体积接受/审核均未验证。

## 结论与交付

A3独立检查通过，HNF-A3-01..04关闭，open findings为空。stage=test_passed，rounds.test仍1；交上述固定1.0.1 ZIP、外置logo与SHA给负责人手动上传，不自动发布。G7只在A3交付后负责人未回复的条件下允许继续下一包，不扩大生产/财务/发布权限。

本轮真实上游/后端业务/付款/生产写入/部署/重启/上传均0；未执行包或完整A2，不新增worker、AI心跳、自检或周期监测。

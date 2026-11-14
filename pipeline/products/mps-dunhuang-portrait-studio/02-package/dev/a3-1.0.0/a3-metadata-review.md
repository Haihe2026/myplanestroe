# 敦煌 1.0.0 A3 元数据静态检查

结果：**PASS（本报告范围）**。总 A3 结论由主审汇总；本结果不覆盖 Core 已报告的认证错误话术缺陷。

- 固定包提交：2f28a226db29d033cf85cc310aa2efe0bc2ac56f
- ZIP SHA256：0803d919774b6705b5df0b6cee3036a09396737f89a1588b4d05114143b16c51
- ZIP：1,453,045 字节，30 个文件；低于 2,500,000 目标和 3,000,000 上限。
- 批准规格 SHA256：8b46131f7526839246300bdd217250451730e3726f5cc04de6a41df182d460f9
- SOP blob：20b07a7e97a8e78403e82e0a2c71cee6a0b6013e；配置发布开关为 false。
- 官方读取沿用本轮 A3 记录：2026-11-14T19:09:17+08:00，https://open.workbuddy.cn/docs/skill，HTTP 200。

| 检查 | 结果 |
|---|---|
| M01-fixed-basis | PASS |
| M02-zip-integrity-size | PASS |
| M03-path-structure | PASS |
| M04-clean-source-binding | PASS |
| M05-raw-frontmatter | PASS |
| M06-bilingual-semantics | PASS |
| M07-versions-public-metadata | PASS |
| M08-runtime-static-dependencies | PASS |
| M09-ten-approved-jpegs | PASS |
| M10-external-logo | PASS |
| M11-manifest-assets-disclosure | PASS |
| M12-independent-markdown-paths | PASS |

原始 frontmatter 未改写即由标准 PyYAML 严格解析，八必填字段与批准规格一致，拒重复键；SKILL.md 为15,285字节。三对示例依次为肩背后反弹琵琶、鸣沙山夕阳沙丘、月牙泉夜景月牙水面；中英文均为成年本人单人、保持原貌、竖版2:3、1024×1536。版本1.0.0与_meta、studio及telemetry一致，欢迎句保持认证格式。

十张 JPEG 均为512×768 RGB、完整解码通过，合计1,333,229字节，逐张 SHA/字节与批准素材完全相同。JSON只使用裸文件名。外置logo为PNG512×512、480,802字节，SHA为9fdf400c88896e8dccaf6852fb4f7bf5d95a48ac97bc3468c86b6caea69acfe7，与批准规格一致；未塞入ZIP。

包内所有运行脚本只作AST分析，Python3.7语法可解析，静态导入均为标准库或随包模块。没有导入或执行任何被审包脚本，没有重跑A2。空格/#/%三种独立构造路径经CommonMark解析后无query/fragment误拆，解码均定位同字节文件；另静态核路径编码映射，未调用包内路径函数。

**not-run-host**：真机行为验收已跳过（负责人长期规则，2026-11-07），未标为通过。未验真实宿主、OAuth、支付、上游、生产部署；Python3.7仅语法核对。结构/元数据通过不代表总A3通过，Core问题与状态/回执由主审处理。

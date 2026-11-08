# A3 独立检查 · 证件照换底助手 1.0.6

检查时间 2026-11-08T17:44:41+08:00。通知 `evt-b929ace7a16ddbfef6ece37b0d937a11b0d361ef2c4cdea82cf788430be69ff1`。固定输入 `6c944b4abb2e2964cb2ec17fe26727151505af26`。接手前核对的远端 main 为 `7e41a5ff00dda8ccba9d8ccaebd956f3d8d407de`，状态 blob `423bd0105ad7f8ff4237854da2f54f5647964208` 与固定输入一致。产品认领提交 `73a79b8e8739757ff49ec9ce8b10671d28d029e6`。第 5 轮依据产品内的负责人超轮次批准记录，见 [本轮交接说明](msg-from-muse-20261108-fix-a3-e03.md)。

2026-11-08 在线读取 [WorkBuddy 技能](https://open.workbuddy.cn/docs/skill)、[专家](https://open.workbuddy.cn/docs/expert)及[开放平台概述](https://open.workbuddy.cn/docs/what-is-open-platform)。

| 检查项 | 结果 |
|---|---|
| ZIP 完整性与目录 | 889982 字节，24 个文件。SHA-256 `1bf5b30d216bd12de31b91625fc892b8fcef3ac2198af45ac14eba344882ac23` 与 A2 记录一致，Git blob `11813372b8031531a7cdb1647776cee1e66b01e7` 与固定输入及远端认领提交一致。CRC、干净解压、单一包根、目录层级、重复路径、路径穿越、符号链接检查通过。 |
| Frontmatter | WorkBuddy 技能页八个必填字段非空，版本与 ZIP、元数据及两个脚本一致。中英文各三条，逐条对应白底一寸报名、蓝底二寸考试报名、简历照换白。 |
| 契约及规格 | 静态对照开发规格核查首次展示、两项同意、授权和充值、原任务续接、换底与本地另存、消费记录、工单、8 字段遥测及收藏入口。欢迎句与规格逐字相符。面向用户的说明、市场字段、固定话术、进度及示例说明的禁用词扫描与包内常见凭证特征扫描均无命中。与 1.0.5 ZIP 逐文件比对，运行实现只改版本常量和路径转义，其他差异在元数据及测试材料。 |
| 示例资源及链接 | 十个场景与规格逐项对应。demos.json 使用裸文件名，十张 PNG 存在且均不超过 300 KiB，指定像素示例为 295×413。用 ZIP 中提取的路径函数生成两列 Markdown 表格，Windows PowerShell 7.6.5 的 ConvertFrom-Markdown 解析。含空格、括号及百分号、含 `#`、以及同时含空格与 `#` 的三组合成目录，各 10/10 个链接在拆分 URI 后无片段及查询串，解码路径均指向实际文件。A3-E02 回归与 A3-E03 修复通过。 |
| WorkBuddy 真机与上传 | 本接收端缺少已验证的电脑操作和上传适配器。真机行为验收、零消耗浏览器验证和上传均为 blocked，未执行。宿主点击、平台解析、审核和上架均未验证。 |

**A3 独立检查通过。** 产品置 `test_passed`，轮次记为 5，按看板规则交负责人手动验收和上传。A2 的 27 项契约及 53 项模拟端到端来自 Claude 自测，本轮按 A3 规则执行静态检查及本地路径回归。真实付费生图、真实遥测、核款、生产变更和上传均为 0。

[固定输入的 1.0.6 ZIP](https://github.com/Haihe2026/myplanestroe/blob/6c944b4abb2e2964cb2ec17fe26727151505af26/pipeline/products/mps-id-photo-background/02-package/dist/mps-id-photo-background-1.0.6.zip) · [1.0.5 A3 历史报告](https://github.com/Haihe2026/myplanestroe/blob/6c944b4abb2e2964cb2ec17fe26727151505af26/pipeline/products/mps-id-photo-background/03-test-report.md)

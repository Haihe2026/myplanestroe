# A3 独立检查 · 证件照换底助手 1.0.5

检查时间 2026-11-08T13:47:39+08:00。通知 `evt-52e3c0758b5da2a064f3a41509080e89d5eefab98f482b83ca9ebf47da4a83f0`。固定输入 `0e49b2fdfc7fe63da8e3af21eb736559b4c64235`。接手前核对的远端 main 为 `e5e9fadfd96ad0bb0e21563f91f0d16240561300`，产品状态 blob 与固定输入一致，版本 1.0.5，`package_ready`，无产品认领人。产品认领提交 `a24b9ac35dc592cfa0d301eea325d49740f9e9c5`。

| 检查项 | 结果 |
|---|---|
| ZIP 完整性与目录 | 889405 字节，24 个文件。SHA256 `c51cd69baaa70fd56ba455c459dd1067ed5713ea38fdac21d38d1bda8fad7707` 与 A2 记录一致，Git blob `6ebd10fb7946e342f0b10350ba73c691c7428230` 与固定输入一致。CRC、干净解压、单一包根、目录层级、重复路径、路径穿越、符号链接检查通过。 |
| Frontmatter | WorkBuddy 技能页八个必填字段均存在且非空，1.0.5 与元数据和脚本版本一致。中英示例各三条，逐一对应白底一寸报名、蓝底二寸考试报名、简历照换白。 |
| 契约及规格 | 静态核对首次展示、方案与双重同意、授权和充值、原任务续接、换底和本地另存、消费记录、工单、8 字段遥测及收藏入口。欢迎句与规格一致。对客说明和静态话术的禁用词检查、包内常见凭证特征扫描均无命中。 |
| 示例资源及链接 | 十个场景与规格对应，`demos.json` 用裸文件名，十张 PNG 存在且各不超过 300 KiB，指定像素示例为 295×413。含空格、括号及百分号的合成目录可解析并定位到文件，A3-E02 已修复。含 `#` 的目录仍断链，见 A3-E03。 |
| 真机、浏览器及上传 | 本接收端缺少已验证的电脑操作和上传适配器。WorkBuddy 真机行为验收、零消耗浏览器验证和上传均为 blocked，未执行。A3 只做独立检查。平台导入、审核和上架状态未验证。 |

对照 [WorkBuddy 技能](https://open.workbuddy.cn/docs/skill)、[专家](https://open.workbuddy.cn/docs/expert)和[开放平台概述](https://open.workbuddy.cn/docs/what-is-open-platform)。A2 的 26 项契约和 53 项模拟端到端是 Claude 自测记录，本轮未重跑完整套件。真实付费生图、真实遥测、核款和生产变更均为 0。

## A3-E03 · 示例目录名含 `#` 时链接目标被截断

1. 在 Windows 干净解压最终 ZIP，从 `scripts/idphoto.py` 提取 `md_safe_path()` 和其字符映射。创建合成目录 `Synthetic#User/demos/`，复制包内 `white-one.png` 并确认存在。
2. 依 `SKILL.md` 的首轮模板将函数输出原样代入 `**[white-one](path)**`，用 PowerShell 7.6.5 的 `ConvertFrom-Markdown` 解析，提取 `href`。按文件 URI 拆分片段后对路径做百分号解码，再检查是否指向原文件。
3. 预期为链接路径指向已存在的 `Synthetic#User/demos/white-one.png`。实测 `href` 末段仍是 `Synthetic#User/demos/white-one.png`，URI 片段为 `User/demos/white-one.png`，文件路径截在 `Synthetic`，无法定位原文件。
4. 同一方法下，`Synthetic User (A) 50%` 转成 `Synthetic%20User%20%28A%29%2050%25` 后可定位文件。独立对照将 `Control#User` 中的 `#` 编成 `%23` 后，片段为空，解码路径指向实际文件。对照只替换测试输入。

## 关口结果

A3 独立检查未通过。`rounds.test` 从 3 增至 4，超过 `max_rounds=3`，按 SOP A.3 置 `blocked`（`TOO_MANY_ROUNDS`）。负责人审阅后协调修复并重新打包，确认可恢复时将修复版置回 `package_ready`。真机及上传能力阻断单独记录，产品拦停原因为 A3 缺陷及轮次上限。

[1.0.4 A3 历史报告](https://github.com/Haihe2026/myplanestroe/blob/e5e9fadfd96ad0bb0e21563f91f0d16240561300/pipeline/products/mps-id-photo-background/03-test-report.md)

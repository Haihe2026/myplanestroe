# A3 独立检查 · 婚纱写真照相馆 1.0.1

2026-11-09T13:57:30+08:00，Codex 在本聊天接续。固定包事件 `evt-7a5c65ff7b194588c4ba96c33704fa78a1d4a08bb5b0073c113c34bbf79f93d5`、包提交 `49a6b48548560beb6626a4fe23b7bed1821dc255`。Muse 续接事件 `evt-99cf44e0d7e31f558fb1a5fe5e5e31526ac9732072cc340dd21825635ee2a5a3`、固定交接提交 `82c56f67cc747b4de055e5fcfa4d7d41ad68d7b4`。两条事件的指纹、原认领和同一 ZIP 均已核对。

**独立检查通过。** 版本 1.0.1 为 WorkBuddy 团队版待上传包。上传及平台审核由负责人处理，平台未提交。

| 项目 | 结果 |
| --- | --- |
| ZIP | 921555 字节、24 个文件，CRC 全部通过。Git blob `0561229306779954aa7d73250e47b24e05499024`，SHA256 `b26ede2626c357dbb178ad10f41188aaaece2bc5e4f63d67bd1a8ff26cd03208`。固定包、Muse 交接和最新输入中的 ZIP 一致。 |
| 结构 | 单一包根，最多两级目录，干净解压。没有重复路径、路径穿越或符号链接。 |
| Frontmatter 与文案 | 8 个必填字段齐全且无重复键，版本、名称和 WorkBuddy 团队版渠道一致。中英文各 3 条且逐条与规格的场景、人数和画幅对齐。欢迎语与规格逐字一致。对客简介、README 和固定话术未命中本轮扫描的内部禁用词及上游名。 |
| 示例资产 | 10 张 PNG 与清单裸文件名对应，两张横版、八张竖版。包内 SHA256 与派生清单逐项一致，派生来源 SHA256 与 provenance 对齐，图片合计 867268 字节。 |
| 功能契约 | 10 个场景的系列、标题、默认画幅与规格一致。Python 可静态解析。参考图正文白名单、原键、确认及成品链接按下表复核。 |
| 范围 | Claude 契约 34/34、模拟端到端 56/56 属 A2 结果。本轮只做静态检查和隔离函数核对。真实上游调用、上报、支付和平台上传均为 0。真机及浏览器验证按现行 SOP 跳过。 |

## 1.0.0 三项退回的复查

| 项目 | 包内证据和复现 | 结果 |
| --- | --- | --- |
| WED-A3-01 离线示例零网络 | `scripts/studio.py:295–320`。将可能的网络、账户及遥测入口替换为触发即失败的探针。直接执行 `demo` 返回 10 张，单项 `garden` 返回 1 张，探针均未触发。静态核对 `first-turn` 仍调用首次对话上报。 | 通过 |
| WED-A3-02 换图废止原确认及原键 | `scripts/studio.py:353–394,447–481`。确认时核对照片 SHA256，构造请求使用已核对的同一份字节。用同路径合成图分别覆盖确认前、确认后的替换。返回 `photoChanged`，两项同意和原键均清空，提交探针未触发。旧流程无法续发，重新规划和确认后生成新键，请求体绑定新照片。 | 通过 |
| WED-A3-03 成品与画廊链接 | `scripts/studio.py:592–631`。用隔离回包调用包内交付函数，分别将文件写入含空格和含 `#` 的两个合成目录。Markdown 解析后四条链接均未拆出片段或查询，解码后逐个定位到原 PNG 和画廊文件。文件操作路径与编码后的对客目标分开。 | 通过 |

[1.0.0 的退回报告](https://github.com/Haihe2026/myplanestroe/blob/ce8d0a7628f5c0c5ad51195f2dbfe2aad12c99ee/pipeline/products/mps-wedding-portrait-studio/03-test-report.md) · [固定 1.0.1 ZIP](https://github.com/Haihe2026/myplanestroe/blob/49a6b48548560beb6626a4fe23b7bed1821dc255/pipeline/products/mps-wedding-portrait-studio/02-package/dist/mps-wedding-portrait-studio-1.0.1.zip)

状态置 `test_passed`，待负责人手动验收与上传。正式提交及审核结果以实际平台记录为准。

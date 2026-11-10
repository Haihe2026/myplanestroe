# 宠物主题照相馆 1.0.5 A3 独立复查

**独立检查通过。** 本轮 A3-PAY-01/02/03 已关闭，固定 ZIP 交负责人手动上传。

时间 2026-11-11T07:44:16+08:00，Windows 干净解压并用合成状态、Mock 检查退回场景。真实上游和付款调用为零。真机验收及浏览器验证按 SOP 7.5 长期豁免跳过。没有重跑 A2 全量测试。

固定事件 `evt-e54d0037afe15ac61946d850b6b4d97640fd6e998c59bfabe790cbc51df22935`，提交 `5d2f004e87b7e58badf02e0213e888d466674bb4`。ZIP 1028163 字节、24 个文件，SHA256 `2e5604a8d7be2eb48763189f1e7111a0f9bb1b14d8af3929de1dc9cc344b756e`，与 A2 一致。[固定 ZIP](https://github.com/Haihe2026/myplanestroe/blob/5d2f004e87b7e58badf02e0213e888d466674bb4/pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.5.zip) · [A2](https://github.com/Haihe2026/myplanestroe/blob/5d2f004e87b7e58badf02e0213e888d466674bb4/pipeline/products/mps-pet-portrait-studio/02-self-test.md)

| 项目 | 结果及证据 |
|---|---|
| 包完整性 | CRC 正常，两级路径，无同名、越界路径或符号链接。 |
| 元数据、简介与接管 | 八项必填、三组中英同场景同画幅、21 个触发词、固定欢迎句、首节接管和收藏 ID 一致，无隐藏注释。description 末句已包含本技能账户问题。SKILL.md 15314 字节。 |
| paid 入口 | 全新环境的 paid 与另外五个账户命令均使用已持久化安装标识调用一次 quick-entry，给出关联链接；不再无依据返回付款登记。 |
| 链接和故障 | expires_in=0 的链接不转述，允许沿同安装重取。正常有效期给链接，外部域被拒。状态 0 与 503 的话术区分网络和繁忙。 |
| 示例及遥测 | 十张 PNG 可读，来源与派生 SHA256 对应；独立 demo 在两个全新目录零网络、零凭证读取。首次对话仍按八字段和 2 秒预算，版本与渠道一致。 |
| 路径 | 空格与井号目录的实际示例 Markdown 链接均经解析，解码后命中现存文件。 |

产品置为 `test_passed`。保留该 ZIP 的 SHA256，由负责人手动上传。

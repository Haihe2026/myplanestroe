# 宠物主题照相馆 1.0.6 A3 独立检查

**独立检查通过。** 新主题 logo 与版本升级符合 Muse 固定交接，产品置 `test_passed`，交负责人手动上传 ZIP 并更换 logo。1.0.5 已提交平台待审的记录和旧包均保留。

检查时间：2026-11-11T09:51:57+08:00。事件 `evt-75e3269bd8910771b013a9311932156a5bef966868bac51636afb9a39152c066`，源提交 `79fc8a58c7912780cb8baa3245d27d0f3e9ffe8c`；原 claim `251a0223-577c-4a65-8e67-1ee6237030cc` 与本机一致，指纹复算通过，未重复认领通知。产品认领提交 `55779ac835db31e7b61d3628c1d83285229f423e`。现行 SOP blob `5cbe73634ad7aa9767ed6a9e0997300f52d79cea`、config 已读；本轮升级不修改开发规格，按 SOP 不要求重读官方页面，沿现有技能字段约定检查。

## 交付

| 项 | 固定交付 |
|---|---|
| 中文名 | 宠物主题照相馆 |
| slug | `mps-pet-portrait-studio` |
| 版本及 ZIP | [mps-pet-portrait-studio-1.0.6.zip](https://github.com/Haihe2026/myplanestroe/blob/79fc8a58c7912780cb8baa3245d27d0f3e9ffe8c/pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.6.zip)，1,028,163 字节，24 文件 |
| ZIP SHA256 | `3224973893da8623ae7e6bfc8e9bca578d1099c303fa7277f283d448572798c2`，与 [A2](https://github.com/Haihe2026/myplanestroe/blob/79fc8a58c7912780cb8baa3245d27d0f3e9ffe8c/pipeline/products/mps-pet-portrait-studio/02-self-test.md) 一致 |
| 新 logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/79fc8a58c7912780cb8baa3245d27d0f3e9ffe8c/pipeline/products/mps-pet-portrait-studio/02-package/dist/logo.png)，PNG，512×512，405,487 字节；外置附件，ZIP 内无 logo |
| logo SHA256 | `4945dcd1edaa03964e5837180c01fccc32415c84be997e8db56ea7ff8e538e9a`，与 Codex 来源、Muse 交接及 A2 一致 |

## 独立检查结果

| 项目 | 结果与证据 |
|---|---|
| 固定包与安全解压 | ZIP SHA/CRC 正确；干净目录解压，24 文件、最多两级，无重复/大小写冲突、越界、符号链接、点开头目录或反斜杠路径。 |
| 与 1.0.5 比较 | 旧 ZIP SHA `2e5604a8d7be2eb48763189f1e7111a0f9bb1b14d8af3929de1dc9cc344b756e` 未变。19 文件字节完全相同；仅 SKILL.md、_meta.json、studio.py、telemetry.py、first-turn-preview.md 各一行版本由1.0.5变1.0.6。无功能逻辑变化。逐行差异见 `03-a3-1.0.6-evidence.json`。 |
| 元数据和双语 | 八项必填且无重复 YAML 键；中文名/slug 不变；3 对示例逐项仍为皇家油画猫2:3、卡通狗1:1、海边猫3:2，原规格匹配；21触发词含名称充值，末句包含账户问题。SKILL.md 15,314 字节。 |
| 约定与历史修复 | 固定欢迎句逐字匹配；接管规则在执行说明首节，收藏 slug 正确；生成六字段、遥测八字段/200和2秒预算的定义未回退。PAY-01/02/03、PET-01/02/03、A3-E01–03、WED-A3-01–03 的功能实现与已通过A3的1.0.5逐字节相同，本轮未重跑完整测试。 |
| 十张示例 | key/标题与规格、SKILL.md、README一致；十个 PNG 全部可解码；派生尺寸/字节 SHA 与 derivation 一致，源 SHA 与固定 provenance 一致；demos.json 只含裸文件名。 |
| Markdown路径 | 从当前包提取纯函数 md_safe_path，在实际含空格及 # 的两个本地合成路径生成链接，经 markdown-it-py 3.0.0 CommonMark 解析、解码后均指向现存PNG，无意外fragment/query；未编码负例能检出。没有执行包的业务命令。 |
| 对客文案与秘密 | 对客说明、README和固定话术AST字符串扫描无规定禁用词；全包文本无实际密钥、Cookie/私密凭据及上游服务商/真实模型泄露；客户照片未使用。 |
| logo | 固定新图字节/SHA正确，PNG可读、512×512、≤500KB；按现行A3不做审美评判，也没有重新生图。来源与原1次生成审计仍有效。 |

完整结构化结果见同目录 `03-a3-1.0.6-evidence.json`。上一版A3见[固定历史报告](https://github.com/Haihe2026/myplanestroe/blob/79fc8a58c7912780cb8baa3245d27d0f3e9ffe8c/pipeline/products/mps-pet-portrait-studio/03-test-report.md)。Claude所报44项契约与95项端到端属于A2报告结果，本次Codex未将它们记为独立重跑。

真机验收及上架前浏览器验证已跳过（负责人长期规则，2026-11-07）；未宣称宿主行为或实际支付验证通过。本轮真实上游调用0、付款0、后端业务调用0、生产写入0；未上传或发布。平台最新审核/上架结果未查询，1.0.6由负责人手动上传时确认平台版本。

## 结论

1.0.6 独立检查通过，`test_passed` 为A3检查合格。负责人上传 ZIP 时同时替换外置 logo。名字、slug、通用计费、账户及原已提交1.0.5均不改动。

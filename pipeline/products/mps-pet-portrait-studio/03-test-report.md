# 宠物写真照相馆 1.0.0 A3 独立检查报告

**独立检查不通过。** 退回 Claude 修复后重打包。

- 时间 2026-11-09T19:09:37+08:00，环境 Windows，ZIP 干净解压后逐文件检查。定向回归使用合成状态和内存 Mock，覆盖失败边界。真实上游调用 0，客户照片、支付和生产凭证均未使用。
- 固定资料提交 `5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7`。ZIP 为 `02-package/dist/mps-pet-portrait-studio-1.0.0.zip`，1,021,859 字节，SHA256 `660889b11d3f03bf35d05b5006a18c9325e7d84f4d56e09b45a962c20f189ade`。与原 A3 通知固定提交和 Claude `02-self-test.md` 中的同一文件匹配。
- 2026-11-09 已重新在线读取 WorkBuddy 技能和专家文档，核对团队技能包格式。对照仓库 2026-11-08 官方文档快照。[技能](https://open.workbuddy.cn/docs/skill) · [专家](https://open.workbuddy.cn/docs/expert)
- 真机验收已跳过（负责人长期规则，2026-11-07）。按现行 A3 口径跳过浏览器验证及完整测试重跑。

## 检查结果

| 项目 | 结果 | 证据 |
|---|---|---|
| ZIP 完整性与结构 | 通过 | SHA256 一致，CRC 正常，24 个文件，无重复名称或符号链接，包根下最多一层子目录。 |
| Frontmatter 与对客文案 | 通过 | YAML 无重复键，八个必填字段齐备。中英三组分别对应猫皇家油画竖版、狗卡通头像方版、猫海边度假横版。固定欢迎语与规格一致，公开简介、展示正文及 README 未发现列明的禁用词或供应商名称。 |
| 场景、网关与遥测 | 部分通过 | 十个场景尺寸与规格相符，POST 正文六字段、首轮遥测八字段与 2 秒预算一致。同路径换图后两项确认和旧键作废，阻止发送替换后的图。原任务未知续接存在 A3-PET-01。 |
| 示例图 | 部分通过 | 包内十张 PNG 与来源及派生 SHA-256 逐一匹配，画幅正确，合计 966,477 字节。直接运行全部或单项 demo 时，网络和凭证探针均为零。单项资源缺失处理存在 A3-PET-03。 |
| Markdown 路径 | 通过 | 分别在带空格与带井号的合成目录中，用 ConvertFrom-Markdown 解析 demo、成品、画廊三类链接，六条均解码到现存原文件，未误拆为片段。 |
| 成品完整性 | 不通过 | 截断的 PNG 会被写入输出和画廊并宣布交付，见 A3-PET-02。 |

## 退回项

### A3-PET-01 原任务结果未知时可丢失任务键

- 复现一。对已确认草稿运行提交，在合成传输收到 POST 时模拟进程中断。检查提交前保存记录。
- 实际一。进入 POST 前无持久化提交意图或请求正文，草稿仍是 `confirmed`。下次 `run` 可再次走生成 POST。
- 复现二。把同一草稿置为 `submit_unknown`、保留旧键且不设 job_id，对同一 draft 执行 `plan` 再 `confirm`。另用独立 Mock 让提交返回 409。
- 实际二。重规划返回 `planReady` 并清空旧键，再确认产生新键。409 分支不查原任务，直接显示照片无法处理且没有扣次数。存在无法继续查询原任务及重复提交风险，未发生真实扣费。
- 期望。首发前在私有状态原子保存原键、固定正文及可续接状态。未确定前只查原键/任务 ID，保留原记录。改方案或重新生成不能覆盖未知任务。409 应查原任务或说明同键冲突，费用按服务记录判断。回归覆盖进程中断、同一草稿重新规划与 409。[规格](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/01-dev-spec.md#L100) · [重规划](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L320-L345) · [提交与续接](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L442-L535)

### A3-PET-02 截断 PNG 被宣告交付

- 复现。对一个 Mock 成功任务，让图片 GET 返回某正常 PNG 的前 33 字节，仅含签名与 IHDR。运行解压 ZIP 内的交付逻辑。
- 实际。返回 `delivered`，生成可点击文件和画廊条目，但图像校验无法读取该 33 字节文件。
- 期望。校验图片内容完整后再写入正式结果和画廊、宣布交付。截断或不可解码时保留原任务并进入只读补取流程。[规格](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/01-dev-spec.md#L102) · [图片读取](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L225-L249) · [成品交付](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L587-L627)

### A3-PET-03 缺一张示例时仍返回成功

- 复现。在隔离复制的 `assets/` 中保留清单，移去 `cartoon.png`，运行全量 demo。
- 实际。脚本返回退出码 0、信号 `demos` 和 9 项结果。
- 期望。请求范围内缺任何一张时报告资源缺失并退出 3，保持离线且不读凭证。新增「只缺一张」回归，用单项 demo 核对范围。[规格](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/01-dev-spec.md#L76) · [示例命令](https://github.com/Haihe2026/myplanestroe/blob/5cbe2ee3ce644459da5c04a75b376ff1fd57d5e7/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L292-L317)

按自动 SOP A.4 更新为 `test_failed`，测试轮次加一。后续由 Claude 修复并提交新 ZIP 和 A2 证据，再按固定新 ZIP 独立检查。

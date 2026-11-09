# 宠物写真照相馆 1.0.2 A3 独立复查报告

**独立检查通过。** A3-PET-01、A3-PET-02 复查通过，A3-PET-03 保持关闭。交付负责人手动上传。

- 时间 2026-11-09T22:56:34+08:00。Windows 干净解压检查，定向复现仅用合成数据和 Mock。真实上游调用 0。按现行 A3 口径跳过完整测试重跑和浏览器验证。真机验收已跳过（负责人长期规则，2026-11-07）。
- 固定资料提交 `ad91d885e327c5c2c5e00e9cffef79a90517d590`。ZIP 为 `02-package/dist/mps-pet-portrait-studio-1.0.2.zip`，1,024,840 字节，SHA256 `67799fb6236a42cbcec564f6e989e17b5bf7c6e8a4f9c81beb025eed9b23d4ab`。与原复查通知和 A2 记录指向同一 ZIP。[固定 ZIP](https://github.com/Haihe2026/myplanestroe/blob/ad91d885e327c5c2c5e00e9cffef79a90517d590/pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.2.zip) · [A2 记录](https://github.com/Haihe2026/myplanestroe/blob/ad91d885e327c5c2c5e00e9cffef79a90517d590/pipeline/products/mps-pet-portrait-studio/02-self-test.md)
- 2026-11-09 在线读取 WorkBuddy 技能文档，HTTPS 返回 200，核对团队技能基础结构、frontmatter 与资源目录。[WorkBuddy 技能文档](https://open.workbuddy.cn/docs/skill)
- 之前的 A3 记录保留在固定提交。[1.0.1 复查报告](https://github.com/Haihe2026/myplanestroe/blob/fa58f74efe4c550629831af4691bf79212dbc644/pipeline/products/mps-pet-portrait-studio/03-test-report.md) · [1.0.0 A3 报告](https://github.com/Haihe2026/myplanestroe/blob/aa95c62fc3d8f0bde74e7a014e2c4ec331bf8e08/pipeline/products/mps-pet-portrait-studio/03-test-report.md)

## 逐项复查

| 项目 | 结果 | 独立证据 |
|---|---|---|
| ZIP 完整性和目录 | 通过 | SHA256、字节数一致，CRC 正常，24 个文件，最多两级，无大小写重名、越界路径或符号链接。复查的 studio.py 和 png_local.py 与固定源码 Git blob 一致。 |
| Frontmatter 和对客文案 | 通过 | YAML 无重复键，八个必填字段齐全，版本与包元数据一致。中英三组分别是猫皇家油画竖版、狗卡通头像方版、猫海边度假横版。欢迎句与规格逐字一致，公开简介、正文和 README 未见列明的禁用词或供应商名称。 |
| 契约与任务状态 | 通过 | 十个场景的画幅、生成六字段、遥测八字段和 2 秒预算匹配规格。同路径替换照片会作废提交前的两项同意与旧键。模拟提交中断前已保存原键和固定正文，结果未定时重规划、重确认及重生成均保留原记录。 |
| A3-PET-01 普通 404 | 通过 | 同一未定草稿两次 resume、一次 run，均只读查询原键并返回进度未能确认。额外生成 POST 为 0，原键、正文和未定状态保留。 |
| A3-PET-01 失效凭证 401 | 通过 | 首次原键查询用旧 Skill 凭证返回 401，清理落盘后以原安装身份取得并绑定新凭证，再查到同一原任务。持续 401 的独立样本使用原安装身份回查一次后退出 4，保留原键、原正文和未定状态。两种情形的新增生成 POST 均为 0。 |
| A3-PET-02 损坏 PNG | 通过 | 前 33 字节、截半、无 IEND、Adam7 非法过滤字节、CRC 正确但 IDAT 压缩流损坏，共 5 种样本均进入 downloadPending，保留同一任务，没有写 PNG，已有画廊内容保持原样。用有效 Adam7 对照样本恢复时，仅 GET 原任务图片和余额，成功交付并更新画廊。 |
| A3-PET-03 及素材来源 | 通过 | 十张 PNG 的来源和派生 SHA256 逐项匹配，共 966,477 字节，画幅一致。全量和单项 demo 零网络、零凭证读取。隔离复制中只缺 cartoon.png 时，全量与该单项均报告缺失并退出 3，其余单项仍可用。 |
| Markdown 链接 | 通过 | 在带空格、井号的两个合成目录解析 demo、成品及画廊共 6 条链接，全部解码到现存文件。 |

产品置为 `test_passed`。本轮交付的 ZIP 保持上述 SHA256，由负责人手动上传。

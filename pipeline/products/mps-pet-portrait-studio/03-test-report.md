# 宠物写真照相馆 1.0.1 A3 独立复查报告

**独立检查不通过。** A3-PET-03 已修复，A3-PET-01 与 A3-PET-02 的部分边界仍需修复。

- 时间 2026-11-09T21:10:05+08:00。使用 Windows 干净解压目录、合成图片和内存 Mock，针对退回项复现。真实上游调用 0，真机验收已跳过（负责人长期规则，2026-11-07）。按 A3 口径跳过完整测试重跑及浏览器验证。
- 固定资料提交 `20f8a83721fc01a96ff4c28c72c6535b53a39bef`。复查 ZIP 为 `02-package/dist/mps-pet-portrait-studio-1.0.1.zip`，1,024,515 字节，SHA256 `26c3ad64f64a22e3515854e17e1c1a0f9893b67db8a36cbe77b064417b6597e0`。与旧复查通知固定提交及 A2 记录匹配。[固定 ZIP](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/02-package/dist/mps-pet-portrait-studio-1.0.1.zip) · [A2 报告](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/02-self-test.md)
- 2026-11-09 重新在线读取 WorkBuddy 技能文档，主机 HTTPS 请求返回 200，核对技能基础结构和 frontmatter。[WorkBuddy 技能文档](https://open.workbuddy.cn/docs/skill)
- 上一版 A3 证据保留在固定提交。[1.0.0 A3 报告](https://github.com/Haihe2026/myplanestroe/blob/aa95c62fc3d8f0bde74e7a014e2c4ec331bf8e08/pipeline/products/mps-pet-portrait-studio/03-test-report.md)

## 逐项复查

| 项目 | 结果 | 独立证据 |
|---|---|---|
| ZIP 完整性与结构 | 通过 | SHA256、字节数与 A2 一致，CRC 正常，24 个文件，两级路径，无同名或符号链接。检查的两个 Python 文件与固定源码 Git blob 一致。 |
| Frontmatter、欢迎句与公开文案 | 通过 | 八个必填字段齐全，三组中英示例分别为皇家油画竖版、卡通头像方版、海边度假横版。欢迎句逐字匹配，公开简介、展示正文及 README 未见列明的禁用词或供应商名称。 |
| 规格契约 | 部分通过 | 十个场景画幅、六字段生成正文和八字段遥测一致。首次发送前替换同路径文件会作废确认和旧键。提交状态已未知时，重规划、确认和重生成均锁定原任务。查回策略见 A3-PET-01。 |
| 十张素材及缺图处理 | 通过 | 10/10 来源与派生哈希匹配，PNG 可读，共 966,477 字节。demo 独立运行零网络、零凭证读取。单缺 cartoon.png 时，全量和该单项均退出 3 并报告缺失，其余单项可用。A3-PET-03 关闭。 |
| Markdown 路径 | 通过 | 分别在含空格、井号的目录解析示例、成品、画廊三类链接，六条均命中现存文件。 |
| 成品完整性 | 部分通过 | 33 字节截断、截半、去掉 IEND 都进入 downloadPending，未写结果。异常的隔行过滤字节和坏压缩流仍未正确处理，见 A3-PET-02。 |

## 仍需修复

### A3-PET-01 原任务查回的 404 与 401 边界

- 已确认修复。模拟 POST 期间进程中断，磁盘上已保存原键、固定六字段正文及 `submit_unknown`。原图随后换掉，锁仍有效，补发路径也仍取旧正文。409 查原键后提示以服务记录为准，保留原键。
- 复现一。针对该未定草稿执行 `resume`，让原键查询只返回普通 404，且无任何未扣或未受理的业务证据。实际请求序列为 GET by-key、POST skill-jobs、GET by-key（本次 Mock 让 POST 返回 409）。固定共享后端的 404 只表示当前未查到，并要求保留任务等待核查。预期保持查询态，保留原键和正文，只有明确未受理且未扣的可恢复状态才能同键续接。该复现只证明发出额外 POST，未发生真实生成或扣费。[规格](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/01-dev-spec.md#L100) · [后端查回](https://github.com/Haihe2026/myplanestroe/blob/3e570ea52ac3a566af2a39b4ad6aefbbcd7f4126/snapshot/opt/skill-platform/member-0.10.14/service/shared_platform.py#L442-L451) · [客户端续接](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L580-L603)
- 复现二。未定草稿的缓存 Skill 凭证已失效，让原键查询连续返回 401，两次 `resume` 均用同一过期凭证并返回 `jobPending`，没有清理凭证。预期保留原任务，从原安装身份恢复，继续原键查询并覆盖 401 回归。[凭证选择与查回](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L576-L603)

### A3-PET-02 部分不可解码 PNG 被交付或使脚本异常退出

- 复现一。构造 1×1 Adam7 RGB PNG，块长度与 CRC 正确，IDAT 解压数据为 `05 00 00 00`，过滤字节 5 无效。独立 PNG 解码拒绝该图片，但当前校验接受，并返回 `delivered`、生成文件及画廊条目。正常过滤字节 0 的对照样本通过。
- 复现二。构造块 CRC 正确、但 IDAT 内容为非法 zlib 流的 PNG。实际从交付函数抛出未处理的 `zlib.error`，没有返回 `downloadPending`。
- 预期。拒绝不可解码的 PNG，统一进入原任务只读补取分支。覆盖隔行模式的非法过滤字节与无效压缩流，且不生成结果文件或画廊条目。[规格](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/01-dev-spec.md#L102) · [PNG 校验](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/png_local.py#L143-L205) · [交付处理](https://github.com/Haihe2026/myplanestroe/blob/20f8a83721fc01a96ff4c28c72c6535b53a39bef/pipeline/products/mps-pet-portrait-studio/02-package/mps-pet-portrait-studio/scripts/studio.py#L656-L679)

按 SOP A.4 更新为 `test_failed`，测试轮次加一。Claude 修复这两项并提交新 ZIP 与 A2 证据后，再对固定新版复查。

# 全家福写真照相馆 1.0.1 A3 独立复查

**独立检查通过。** 上轮 A3-FAM-01/02/03 已关闭，产品置 `test_passed`；固定 ZIP 与外置 logo 交负责人手动上传。

- 时间：2026-11-11T11:51:39+08:00；Windows 全新目录解压，固定 ZIP 独立检查。
- 事件 `evt-3d131877e8ea70018a4c517601854dafd5da8b8b0464d41fcf474e16804ac90c`；原 claim `3157220e-d721-4c43-8708-97dee05b16fd` 与本机/远端一致，固定输入指纹复算通过，未重复认领通知。产品认领提交 `62272f87a49a0e0d4d824f6af376fef1e2561ce0`。
- 固定源 `4669fdb7622e8562c6ce09a9ea7c3d9f4494638d`。现行 SOP/config、当前 status/log/brief、MD/JSON规格、A2及上轮A3均已读。修复轮按SOP无需重读官方页面，沿用本日1.0.0 A3已在线核对skill/expert及2026-11-08快照记录；未修改规格。

## 交付

| 项 | 内容 |
|---|---|
| 中文名 | 全家福写真照相馆 |
| slug | `mps-family-portrait-studio` |
| 英文名与版本 | Family Portrait Studio，1.0.1 |
| ZIP | [mps-family-portrait-studio-1.0.1.zip](https://github.com/Haihe2026/myplanestroe/blob/4669fdb7622e8562c6ce09a9ea7c3d9f4494638d/pipeline/products/mps-family-portrait-studio/02-package/dist/mps-family-portrait-studio-1.0.1.zip)，2,740,120字节，24文件 |
| ZIP SHA256 | `1138fe6925145fc8c7a0013f661d32af48a521dd707ad9980fd3411b39194756`，与[A2](https://github.com/Haihe2026/myplanestroe/blob/4669fdb7622e8562c6ce09a9ea7c3d9f4494638d/pipeline/products/mps-family-portrait-studio/02-self-test.md)一致 |
| 外置 logo | [logo.png](https://github.com/Haihe2026/myplanestroe/blob/4669fdb7622e8562c6ce09a9ea7c3d9f4494638d/pipeline/products/mps-family-portrait-studio/02-package/dist/logo.png)，512×512 PNG，427,328字节；SHA256 `29f6d8428ef741af4554083b1149ef4d5c026032ae03086a457e881de2a119b2` |

上传 ZIP 时同时使用外置 logo。旧1.0.0为未通过包，仅保留历史，不交付上传；本次不处理前三款已提交产品。

## 三项修复复查

| 编号 | 当前实际代码与结论 |
|---|---|
| A3-FAM-01 | [studio.py:625](https://github.com/Haihe2026/myplanestroe/blob/4669fdb7622e8562c6ce09a9ea7c3d9f4494638d/pipeline/products/mps-family-portrait-studio/02-package/mps-family-portrait-studio/scripts/studio.py#L625) `_submit_unauthorized(d,a)` 只恢复一次凭证并GET原键；函数唯一网络方法为GET，无_submit调用、POST或重试参数。404/500/断网/非法ID返回进度未知，查到原任务才续原任务；再次401只重置凭证并保留任务。**关闭。** |
| A3-FAM-02 | 401恢复失败/查询异常不再写confirmed、清原键或摘要；`_keep_reset` 带task_kept=true。进入恢复前已由_submit原子保存submit_unknown，plan/confirm/regenerate的状态锁未变；后续run/resume按原键只读查询。**关闭。** |
| A3-FAM-03 | [studio.py:310–367](https://github.com/Haihe2026/myplanestroe/blob/4669fdb7622e8562c6ce09a9ea7c3d9f4494638d/pipeline/products/mps-family-portrait-studio/02-package/mps-family-portrait-studio/scripts/studio.py#L310) 新增十键清单校验、完整集合missing预检查；缺任一所需文件在输出/复制前退出3，无continue跳过分支。默认恰十项、单项仍检查选中资源。**关闭。** |

以上结论来自实际固定ZIP的静态控制流、AST与前后逐行差异检查。包内新增两项契约回归可见；Claude A2另报告对应Mock故障序列、重启恢复、缺图/清单异常正反例通过，并对旧代码反证检出。本轮Codex没有重跑完整A2或执行客户端业务命令，不将Claude的49/99项记为Codex独立运行。

## 其他独立检查

| 项目 | 结果 |
|---|---|
| 完整性和目录 | ZIP SHA/CRC正确；24文件、最多两级，无重复/大小写冲突、越界、符号链接、点开头目录或反斜杠路径。 |
| 逐文件差异 | 相比固定1.0.0，18文件字节相同；SKILL.md、_meta.json、telemetry.py、first-turn-preview.md各仅一行版本变化；实际逻辑改动限studio.py及契约测试，符合三项修复范围。 |
| 元数据和语义 | 八必填字段，名称/slug/版本/渠道一致；三组双语示例逐项同场景、同人数、同3:2画幅；23触发词、账户调用倾向句、固定欢迎及首节接管均保留。SKILL.md为15,357字节。 |
| 十张示例 | key/标题/清单与规格、README、SKILL相同；十PNG原字节SHA匹配provenance/derivation，768×512可完整解码；demos.json仅裸文件名。 |
| logo | PNG可读、512×512、≤500KB，原字节SHA与Codex来源一致；无重新生成。 |
| Markdown路径 | 从本包提取纯md_safe_path，在含空格和#的两个真实合成路径上经CommonMark解析、解码后指向现存PNG，无意外fragment/query；只求值此纯函数，不运行客户端业务。 |
| 契约及文案 | 三/四人、十场景默认横版；六字段生成、八字段遥测/2秒、外层240秒定义一致。对客说明、README及固定话术AST字符串扫描通过；无实际私密凭据。 |

结构化证据及逐文件差异：`03-a3-1.0.1-evidence.json`。旧退回报告见[固定历史A3](https://github.com/Haihe2026/myplanestroe/blob/4669fdb7622e8562c6ce09a9ea7c3d9f4494638d/pipeline/products/mps-family-portrait-studio/03-test-report.md)。

## 验收范围与结论

本轮真实上游调用0、后端业务调用0、真实付款0、生产写入0、部署0、上传0。真机验收及上架前浏览器验证已跳过（负责人长期规则），未宣称通过。真人合照保真、生产签名素材路由、实际支付、宿主实际行为及平台接受约2.7MB包/审核结果仍未验证；负责人手动上传前自行宿主测试。

`test_passed` 表示本次A3独立检查合格。交付1.0.1 ZIP、原外置logo及名称/slug，由负责人手动上传；不自动发布。

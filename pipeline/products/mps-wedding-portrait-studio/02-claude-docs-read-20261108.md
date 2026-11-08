# Claude 官方文档读取记录（婚纱写真照相馆 1.0.0 首次开发）

- 时间：2026-11-08T19:28:27+08:00（北京时间）。负责人在本会话里放行了网页读取（拦停记录见 02-claude-docs-blocked-evt-64bf6f1d….md），随后重新读取。
- 已读 WorkBuddy 官方文档（2026-11-08，读了 docs/skill、docs/expert、docs/what-is-open-platform 三页）。

| 页面 | 结果 | 与本单相关的要点 |
|---|---|---|
| https://open.workbuddy.cn/docs/skill | 已读取（HTTP 200） | 目录：SKILL.md 必须，references/、scripts/、templates/ 可选；frontmatter 必填 name、display_name、display_name_en、description、description_zh、description_en、version、author；可选 allowed-tools、examples_zh、examples_en。页面没写字段长度、ZIP、目录层级和文件大小规则 |
| https://open.workbuddy.cn/docs/expert | 已读取（HTTP 200） | 专家包结构；本单只做技能包，不适用 |
| https://open.workbuddy.cn/docs/what-is-open-platform | 已读取（HTTP 200） | 入驻和审核流程概览，没有包规则 |

官方页面没写的部分（examples 条数上限 3、目录最多两级、assets/ 目录）沿用 SOP 记录的平台实测规则（证件照换底 1.0.1–1.0.3 的上传回执），按最保守写法执行。与 SOP 没有冲突，不追加 sop-proposals。

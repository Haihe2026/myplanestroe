# Skill 开发 SOP

开发、重构或优化 Skill 时，按类型选一份 SOP 严格执行。各份 SOP 独立使用，内容自成一体。

| 文件 | 适用 |
| --- | --- |
| [sop-image-gen-skill.md](sop-image-gen-skill.md) | 生图类付费 Skill（扣 token，走 myplanestore.com 付费） |
| [sop-image-gen-skill-auto.md](sop-image-gen-skill-auto.md) | 生图类 Skill **全自动流水线**版：Muse 选品 → Codex 开发文档 → Claude Code 开发 → Codex 测试与上架，无人工确认；流水线目录见仓库 `pipeline/` |
| [sop-per-use-skill.md](sop-per-use-skill.md) | 频次类付费 Skill（按次或按结果计费，人民币钱包，走 myplanestore.com 付费） |
| [sop-aliyun-skill.md](sop-aliyun-skill.md) | 阿里 Skill（按阿里官方 Agent Skills 标准开发，通过支付宝 SkillPay 收费） |
| [aliyun-skill-standard.md](aliyun-skill-standard.md) | 阿里云 Agent Skill 官方开发标准整理，供阿里 Skill SOP 引用 |

所有 WorkBuddy 开发工作开工前，必须先读 WorkBuddy 官方开发文档（各 SOP 第〇章）。

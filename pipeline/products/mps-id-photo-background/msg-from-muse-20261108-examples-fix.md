# 给 Claude：1.0.2 又被平台拒收——examples 数量超限，重打包 1.0.3

## 先确认包类型（负责人亲口强调）

我们上传的是 **WorkBuddy 团队版技能包**（`workbuddy-skill` 渠道），不是专家包、不是 SkillHub 包、不是通用技能包。打包与校验一律按 WorkBuddy 团队版技能包的平台要求来，不要搞错。SOP 阶段 7 与 config `channels: [workbuddy-skill]` 已写明，只打这一个包。

之前你直接给负责人开发 skill 时上传从没出过这么多错，现在流水线里连续两次被平台解析拒收（先是目录三级，这次是 examples），说明校验口径没对上平台。请按下面把 frontmatter 与校验一次对齐。

## 问题

负责人手动上传 1.0.2 被平台拒收：
「解析失败：examples_zh 最多 3 个示例，当前 4 个；examples_zh 与 examples_en 数量必须一致：当前中文 4 个，英文 3 个」

当前 SKILL.md frontmatter：`examples_zh` 4 条，`examples_en` 3 条。平台要求：`examples_zh` 最多 3 条，且 `examples_zh` 与 `examples_en` 数量必须一致。

## 改动（版本升 1.0.3）

1. 删掉第 3 条中文示例「一寸蓝底，像素要295×413，报名系统卡这个」（它是唯一没有英文对应条的；其余三条中英按主题一一对应：白底报名／蓝底二寸／简历换白）。改后 `examples_zh` 与 `examples_en` 各 3 条，数量一致。`295×413` 仍在 description 触发词里，不丢信息。
2. 另加一项契约测试：解析 SKILL.md frontmatter，断言 `examples_zh` ≤ 3、`examples_en` ≤ 3、且两者数量相等；测出即返工，不得带病交付。
3. 打包前自查：按 WorkBuddy 团队版技能包的平台解析规则逐项核对 frontmatter（必填字段、examples 数量与中英一致、版本号），不要只依赖自测跑通就交。
4. 版本升 **1.0.3**（1.0.2 已交付负责人且 SHA 已记录，重打同版会混淆）。目录层级修复（示例图在 `assets/` 下、最深两级）与 Markdown 回归测试保留；授权链接不改。

## 交付

自测通过后置 `package_ready`（`02-package/dist/mps-id-photo-background-1.0.3.zip`）交 Codex 独立复测。复测通过后由 Muse 交付负责人手动上传。紧急：负责人明天报名要用，今晚务必出新版。

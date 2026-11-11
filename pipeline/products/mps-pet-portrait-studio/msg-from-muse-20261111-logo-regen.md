# 给 Codex：重做技能主题 logo（上游生成）

## 任务
给「宠物主题照相馆」（mps-pet-portrait-studio）重做一版主题 logo，用上游资源生成。负责人 2026-11-11 反馈：现 logo 虽与名字接近，但都是平面 ico、不够好；已把「主题 logo 由 Codex 上游生成」写进自动化 SOP（主题 logo 节，SOP 提交 e81a092）。

## 现状
- 现 logo：02-package/dist/logo.png（平面 ico 风格；新 logo 覆盖此文件）
- 新 logo 保存到：`pipeline/products/mps-pet-portrait-studio/02-package/dist/logo.png`（SOP 标准名）
- 只换这一张 logo，不动其他资产（不改 SKILL.md、不改脚本、不动示例图）。

## 要求
- 规格：PNG，512×512 像素，不超过 500KB。
- 质量：不得是平面 ico——要有纵深感、质感与辨识度，像一个成品应用图标；主题与技能名/内容直接相关（让人一眼看出是做什么的）。
- 方向：宠物写真主题：活泼、温暖、可爱；核心意象可用猫/狗的写真肖像（保留毛色与五官特征感）；配色温暖活泼；质感高级、有纵深。
- 配色可蹭相关领域热度，但不得直接复制商标图形/文字；白标：logo 里不得出现上游模型名、服务商名、域名、品牌；小尺寸下仍清晰可辨。
- 记 provenance 与 audit（生成方式、上游、时间），写进产品目录（`logo-provenance.md` 或 log.md 追加一行）。

## 授权
logo 生成属负责人长期授权的上游调用（SOP 主题 logo 节，与示例图同例），按规格数量直接生成，无需逐单授权。如本次运行仍被上游开关拦停，不要静默等待，经 relay 回 Muse 说明需要负责人在 Codex 窗口里直接说一声。

## 完成后
经 relay 回 Muse 一声（logo 已生成、文件位置、provenance），Muse 再发 Claude 重新打包（新版本号）。

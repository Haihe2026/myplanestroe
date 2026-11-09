# 给 Claude：宠物写真照相馆改名「宠物主题照相馆」，重打包 1.0.3

skill_id: mps-pet-portrait-studio
时间：2026-11-10 CST

## 负责人已定新名

中文名字：**宠物主题照相馆**（7 字）
slug 不变：**mps-pet-portrait-studio**
英文名：Pet Themed Portrait Studio（与新中文名对应）

## 背景

1.0.2 上传被 WorkBuddy 平台拒收：display_name「宠物写真照相馆」已被占用（同类型资产须唯一），须改名后重提。负责人已从三个候选里亲口选定「宠物主题照相馆」。

## 要做的事

1. **改名**：把包里所有出现旧名「宠物写真照相馆」的地方改成新名「宠物主题照相馆」，包括但不限于：
   - SKILL.md：frontmatter 的 display_name、display_name_en、description 开头、标题、中文名字段
   - 欢迎句（scripts/welcome_copy.py）：改成「欢迎使用WorkBuddy官方认证技能 宠物主题照相馆」
   - README.md、_meta.json、scripts/studio.py、scripts/telemetry.py、tests/test_skill_contract.py、tests/first-turn-preview.md 里出现的旧名
   - 01-dev-spec.md 里如有旧名，同步改掉（规格与实现保持一致）
   - 注意：description 里的触发词、功能描述不变，只换名字本身；「宠物写真」「宠物头像」等触发词保留。
2. **附 logo**：按负责人新立的交付标准，本次起每个包必须附 logo 文件。做一张 logo（放在产品目录下，与 ZIP 并列，文件名 `logo.png`），风格按 LI 此前的要求：蹭相关领域热度配色，但不得直接复制商标图形/文字。宠物主题可用暖色、亲和的配色。
3. **明确交付三样**：交付时明确写出中文名字「宠物主题照相馆」、slug「mps-pet-portrait-studio」、logo 文件路径，不要只藏在 SKILL.md 里。
4. **版本号升 1.0.3**：SKILL.md 的 version 与 _meta.json 同步改成 1.0.3，ZIP 文件名 mps-pet-portrait-studio-1.0.3.zip。
5. **A2 自检**：改名后跑完整 A2 自检（契约、端到端、干净解压），确认欢迎句、frontmatter、示例与新名一致，确认前两单历史缺陷未回退（示例中英文义对齐、示例图路径无空格无 #、demo 零网络、照片哈希绑定、Markdown 链接用安全路径、缺一张示例报失败退出 3）。自检证据写 02-self-test.md。
6. **stage 置 package_ready**：交 Codex A3 复查（只查 1.0.3 这个新包，重点复核改名是否改全、改名有没有破坏 PET-01/02/03 的修复）。

## 不要改的

- slug（mps-pet-portrait-studio）不变；10 个模板、功能逻辑、付费口径不变；不要动 PET-01/02/03 已修好的逻辑。

# 给 Claude：负责人（LI）新立的交付标准——以后每个技能包必须附 logo＋中文名字＋slug

skill_id: mps-pet-portrait-studio（本次传达，规则适用于以后所有单）
时间：2026-11-10 CST

## 负责人原话

以后再给我技能包，需要给我 logo＋中文名字＋slug。

## 规则

从现在起，每次交付技能包时，除了 ZIP 包本身，必须同时明确给出三样东西：

1. **logo**：技能的 logo 图片文件，随包一起交付（放在产品目录下，与 ZIP 并列，文件名注明是 logo，例如 `logo.png`）。不要只把 logo 藏在包里或只字不提，负责人要直接拿到文件去上传。
2. **中文名字**：技能的中文名（即 SKILL.md 里的 display_name），在交付时明确写出来，不要只藏在 SKILL.md 的 frontmatter 里。
3. **slug**：技能的 slug（即 SKILL.md 里的 name，如 mps-pet-portrait-studio），在交付时明确写出来。

## 背景（为什么现在立这条）

宠物写真照相馆 1.0.2 上传被平台拒收：display_name「宠物写真照相馆」已被占用，平台要求改名后重提。包里没有 logo 文件，中文名和 slug 也只在 SKILL.md 里，没有作为交付物明确给出，负责人上传时才发现名字撞了。

## 本次的直接影响

宠物馆 1.0.3 重打包时，按这条新标准交付：附 logo 文件，明确写出新的中文名字和 slug（slug 不变，仍为 mps-pet-portrait-studio；中文名字等负责人定新名后按新名交付）。

## 注意

- 中文名字由负责人定，Claude 不擅自改名；新名字确定后，SKILL.md 的 display_name、欢迎句、README、description 里出现的旧名字要同步改掉。
- logo 风格按 LI 此前的要求：蹭相关领域热度配色，但不得直接复制商标图形/文字。
- 这条是长期交付标准，记入以后的每个包，不是一次性的。

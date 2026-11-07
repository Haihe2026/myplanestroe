# 给 Claude：修复证件照换底助手 1.0.0 的示例图链接 bug，重打包为 1.0.1（紧急，负责人明天报名要用）

## Bug（负责人实测，2026-11-07 晚）

技能在 WorkBuddy 内展示示例图时，用户点示例链接，Windows 弹“找不到文件”：
`C:\Users\Administrator.mps-id-photo-background\demos\white-one.png`。
图片本身没问题（包内 `assets/demos/` 有 10 张，`cmd_demo` 也正确拷到了状态目录）。

## 根因（已核实）

状态目录名以点开头（`.mps-id-photo-background`）。`cmd_demo` 返回的绝对路径是
`C:\Users\Administrator\.mps-id-photo-background\demos\white-one.png`，
SKILL.md 按 SOP 把它放进 Markdown 链接 `[标题](路径)`。Markdown 把反斜杠+标点当转义，
`\.` 被解析成 `.`、丢了一个反斜杠，点开的路径变成
`C:\Users\Administrator.mps-id-photo-background\demos\white-one.png`（不存在的文件夹），
所以报文件找不到。只丢这一个符号，其余反斜杠（在字母前）都不受影响。

## 修复要求（版本升到 1.0.1）

1. 状态目录去掉前导点（`.mps-id-photo-background` → `mps-id-photo-background`），从根上消除 `\.` 组合；注意 `state_dir()` 全技能共用， drafts 与遥测状态随之迁移，本单刚上架、旧状态可弃。
2. `cmd_demo` 输出给用户的路径一律用正斜杠 `/`，不再输出反斜杠 Windows 路径（正斜杠不触发 Markdown 转义，Windows 也认）。
3. 自测必须加一项回归测试：把 demo 链接按 Markdown 解析一遍，确认解析后的路径仍指向存在的文件（复现本 bug 的用例：含点开头目录名的路径）。
4. 其余功能、规格、欢迎句、遥测、付费均不动。只修路径与打包，不改后端、不动生产。

## SOP 已同步

SOP（docs/sop/sop-image-gen-skill-auto.md）「示例预览」一节已加规则：示例链接路径必须 Markdown 安全（状态目录与资源目录名不得以点开头；输出路径一律正斜杠；自测与独立测试加 Markdown 解析后路径仍存在这一回归测试）。按 SOP 执行。

## 交付

重打包为 1.0.1（`02-package/dist/mps-id-photo-background-1.0.1.zip`），自测通过后置 `package_ready` 交 Codex 独立复测。复测通过后由 Muse 交付负责人手动上传。紧急：负责人明天报名要用，今晚务必出新版。

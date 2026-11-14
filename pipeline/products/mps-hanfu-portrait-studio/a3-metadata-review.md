# 汉服 1.0.2：A3 静态元数据与差分子审

2026-11-14。**本子审结果：PASS。冻结包元数据、资产与允许的差分范围未发现阻断。** 本报告不代表整体A3通过，A2环境/适配证据与最终交付由主审汇总。

| 固定对象 | 核对结果 |
|---|---|
| 1.0.2 ZIP | 2,649,840 B；SHA256 `462837b50688cc5d9d6561e379637f99e5fbb0aa54d0f05aeb9ccb9edaa25b9d`；25文件，CRC完整；≤3,000,000 B，余350,160 B。 |
| 1.0.1 原ZIP | SHA256 `c4d345920b0fd0c2f1d3443c2044f520876f21000865fcac3212a55314c2f6ea`，作为真实原字节比较源。 |
| 外置logo | PNG/RGB、512×512、418249 B；SHA256 `bf919e85511fe0ea2adbd8d43b1599314801357c5fcb7bec40445c9c6540bff5`；与原logo解码像素完全相同，不在Skill ZIP内。 |

## 元数据、示例和欢迎句

- 直接读取ZIP中原始 `SKILL.md`，用PyYAML安全解析并加入重复键拒绝；八必填均为非空字符串。name为原slug，version为1.0.2；SKILL总15352 B≤15360 B。不是执行随包解析器或诊断投影。
- `examples_zh/en`各恰3条。逐对对应唐制齐胸襦裙（chest-high/chest-tied）、宋制褙子及同套裙、明制马面裙；本人/成年人/单人、竖版2:3、1024×1536均中英一致。
- 五处版本同步为1.0.2：`SKILL.md:16`、`_meta.json:5`、`scripts/studio.py:32`、`scripts/telemetry.py:16`、`tests/first-turn-preview.md:7`。测试说明中的历史修复版本没有被全局替换。
- `welcome_copy.py:7`以常量相加构成欢迎句；只读AST字符串节点求值（没有执行模块），结果逐字为“欢迎使用WorkBuddy官方认证技能 汉服写真照相馆。”。欢迎话术文件本身与1.0.1字节相同。
- 用户段与README未见新增供应商、模型、上游、流水线角色等白标泄露；README、固定话术和参考资料字节未变。

## 十图、结构和差分

- 十份PNG都由归档字节完整读取，格式PNG、RGB、512×768；合计2,555,027 B。逐份实际SHA同时匹配派生记录，来源SHA匹配1.0.1 ZIP同名图。独立比较像素，每通道最大变化≤2；这支持色阶压缩记录，不据此替代肉眼质量判断。
- `assets/demos.json`原字节相同，恰十key/标题/说明、裸PNG文件名、无子目录/空格/#；AI非实拍说明与侠客“木质影棚”原话保留。无额外旧PNG、logo或拒绝的参考seed混入。
- ZIP单根、最多两级；未发现越界、绝对路径、盘符、反斜杠、符号链接或大小写冲突。`md_safe_path`及Markdown路径编码业务代码字节未改；本子审没有调用包函数。
- 无成员增删。仅十PNG与上述五个版本位置变化；其余十文件原字节相同。`SKILL.md`正文与其他frontmatter字段原字节相同。studio/telemetry仅版本常量变化；对所有业务脚本独立AST解析，规范化SKILL_VERSION后AST完全一致。未修改账户、收费、鉴权、重规划、反馈、提示词、固定话术或功能。

逐图SHA、源SHA、实际尺寸/字节、最大通道差和13类静态结果见 `a3-metadata-review.json`。

## 证据更正与未验边界

初读外围staging/compression记录曾把压缩实验容器SHA `294600ab…`混作来源/正式ZIP身份；已重新只读确认更正：source为c4d345…，实验容器单列，`final_zip`为2,649,840 B/462837…。此更正不改变冻结ZIP，问题已关闭。

本子审没有运行/导入Skill、随包测试、开发A2/A3脚本，没有业务、上游、浏览器、生产或远端写入。图片肉眼接受范围沿独立 `compression-visual-review.md`，不能称十图像素无损；logo像素无损经本次独立比对。Windows原生测试harness适配、POSIX权限/Windows ACL、A2最终证据、真实宿主、真实付款和平台上传均不在本子审通过范围；不得由本报告推定整体A3或Windows原包无适配全绿。

open package blockers：空。overall A3：交主审汇总，未在本报告判定。

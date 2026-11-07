# 给 Claude：1.0.1 平台拒收——目录层级超限，重打包 1.0.2

## 问题

负责人手动上传 1.0.1（`mps-id-photo-background-1.0.1.zip`，866.3KB）时平台解析失败：
「解析失败：目录层级超限 — Skill 包仅支持两级目录结构（根目录/二级目录/文件），请移除子目录嵌套」

根因：`assets/demos/` 是三级嵌套。ZIP 内 10 张示例图在 `mps-id-photo-background/assets/demos/*.png`（根/ assets / demos / 文件，共三级），超出平台两级上限。其他文件都在两级以内（`assets/demos.json`、`scripts/*`、`references/*`、`tests/*` 均为两级）。

## 改动（版本升 1.0.2）

1. 把 10 张示例图从 `assets/demos/` 平移到 `assets/`（与 `demos.json` 同级），删除空的 `assets/demos/` 目录。`demos.json` 本身不动（它只写裸文件名如 `white-one.png`）。
2. `scripts/idphoto.py` 的 `cmd_demo`（约 line 294）：`src = os.path.join(base, 'demos', d['file'])` 改成 `os.path.join(base, d['file'])`（直接读 `assets/`）。
3. `tests/test_skill_contract.py` 两处（`test_demos_consistent`、`test_demos_are_fictional_and_small`）：`os.path.join(ROOT, 'assets', 'demos', d['file'])` 改成 `os.path.join(ROOT, 'assets', d['file'])`。另 grep 全仓，凡引用 `assets/demos` 的一并改掉（`demos.json` 的裸文件名不用改）。
4. 另加一项回归测试：解压 ZIP 后断言所有文件路径的 `/` 数 ≤ 2（包根目录为第 0 级），即不得出现三级及以上嵌套；该测试在自测与独立测试中都要跑。
5. 版本升 **1.0.2**（1.0.1 已交付负责人且 SHA 已记录，重打同版会混淆）。其余不动：demo 链接修复（状态目录去前导点、正斜杠、Markdown 回归测试）保留；授权链接不改（ticket/entry 依据，见前一条 msg）。

## 交付

自测通过后置 `package_ready`（`02-package/dist/mps-id-photo-background-1.0.2.zip`）交 Codex 独立复测。复测通过后由 Muse 交付负责人手动上传。紧急：负责人明天报名要用，今晚务必出新版。

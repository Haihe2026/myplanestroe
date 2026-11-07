# 独立测试报告 · mps-id-photo-background 1.0.0

- 本机 Codex 独立接收方，2026-11-07（北京时间）。已在线阅读 WorkBuddy 官方[技能](https://open.workbuddy.cn/docs/skill)、[专家](https://open.workbuddy.cn/docs/expert)和[开放平台概述](https://open.workbuddy.cn/docs/what-is-open-platform)。技能定义与必填 frontmatter 由契约测试核对。
- 通知 `evt-4f281188904d774b5be3b21260f01e2668089aea888988bc6547b2af2f07670d`，固定输入 `49251d3f8622a74e5374abc954f8131901f31acb:pipeline/products/mps-id-photo-background/status.json`。认领前核对远端 `main` 的 `package_ready` 与固定输入状态 blob `1d4b45e89113800b0a4c36461b059ed8c0b5de1a` 一致。看板认领提交 `65937d5160c926e823a233cbb9b784a2621d00ce`。
- 上一轮 Windows 诊断及真机阻断证据保留在 `f70ab301a81078e5a61ca3a18cb88d9ead7fe8d9:pipeline/products/mps-id-photo-background/03-test-report.md`。

## 干净 ZIP 与独立复跑

- `02-package/dist/mps-id-photo-background-1.0.0.zip`，886247 字节，24 个文件，唯一根目录 `mps-id-photo-background/`。ZIP 路径、重复项、符号链接与 CRC 检查通过。Git blob `b312bed4cb45ddc13bd21d3e14f4db5d821f9d46`，SHA256 `f187e418b9470275464d40a1af81529eef38649855305dc2a996379696d53b80`，与自测报告一致。
- Ubuntu WSL 2 非 root，Python 3.12.3。两套测试各自使用一份全新解压目录，合成账户和进程内模拟后端。先验证临时文件系统能读回 `0600` 文件模式，且 `0500` 目录拒绝写入。
- 契约脚本、端到端脚本、模拟后端、示例派生清单和来源清单按 Git blob 校验。Windows 检出的文本在需要时还原为与 Git 对象一致的行尾。第一次运行的隔离目录未带入示例溯源夹具，导致该用例找不到清单。按仓库原有相对路径补齐原始夹具后整套重跑，原测试和断言均原样执行。
- 测试进程审计钩子拒绝网络、DNS 和外部进程调用，两套均记录 0 次拦截。真实付费生图、生产变更、核款、真实遥测和上传均为 0 次。

| 项目 | 复跑命令 | 结果 |
|---|---|---|
| 契约 | `python3 -m unittest discover -s tests -v` | 20/20，通过，退出 0 |
| 端到端 | `python3 dev/e2e_check.py --package <干净解压的技能目录> -v` | 50/50，通过，退出 0 |

端到端覆盖账号与计费 13/13、确认 4/4、首轮 4/4、本地图像 2/2、示例来源与尺寸 1/1、消费记录与工单 10/10、遥测 8/8、等待轮询 8/8。此前在 Windows 卡住的 `test_skill_key_expired_reset_exit4` 已通过，包括凭证文件权限与失效处理。开发测试脚本仍产生未关闭测试文件的 `ResourceWarning`，不影响本轮断言及退出码。

## 真机与上架

| 项目 | 实际状态 |
|---|---|
| WorkBuddy 真机行为验收、上架前浏览器零消耗验证 | 本单书面豁免。电脑操作能力为 blocked，本轮未在真实宿主执行，未产生逐场景截图或 `/pricing` 浏览器证据。见 [单次豁免记录](01-host-acceptance-waiver-20261107.md)。 |
| WorkBuddy 团队版上传 | blocked。接收端缺少已验证的上传适配器，等待负责人手动上传。无渠道 ID、提交审核或上架证据。 |

## 结论

按单次豁免口径，A3 契约和端到端通过，看板置为 `test_passed`。独立测试轮次仍为 0，发布版本仍为空。

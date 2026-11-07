# 独立测试报告 · mps-id-photo-background 1.0.0

- 本机 Codex 独立接收方，2026-11-07（北京时间）。已在线阅读 WorkBuddy 官方[技能](https://open.workbuddy.cn/docs/skill)、[专家](https://open.workbuddy.cn/docs/expert)和[开放平台操作指引](https://open.workbuddy.cn/docs/what-is-open-platform)。按技能页核对 ZIP 内的技能定义、必填 frontmatter 和资源目录。
- 事件 `evt-cc2abad85d457749812ad59e5808e08383b6d79935173ec2942e4c5bcddfadd4`。固定输入 `c7aa6190e20458c65ccc2db74b8891ede50c554a:pipeline/products/mps-id-photo-background/status.json`。
- 通过 GitHub 连接器核对远端 `main`（`d7dff309f43b4c13559e055aa55443e8f48a4f4e`）。固定输入和该远端提交的状态 blob 同为 `db7ace3aaa485df8fcb90b9b24d7a7c69d5cfb5f`，状态为 `package_ready`。条件更新认领提交 `32a2130d3bb8c6f632072210e9b5629ad8f52025` 已进入 `main`。
- 上一轮同版本号但不同 ZIP 的报告留在 `15d50e5f9f92376e9daf0784dcbb3f8f6e4dc5e7:pipeline/products/mps-id-photo-background/03-test-report.md`。

## ZIP 与独立离线复跑

`02-package/dist/mps-id-photo-background-1.0.0.zip` 为 886247 字节，24 个文件，唯一根目录为 `mps-id-photo-background/`。ZIP 路径与 CRC 检查通过。Git blob `b312bed4cb45ddc13bd21d3e14f4db5d821f9d46` 与固定提交一致。SHA256 `f187e418b9470275464d40a1af81529eef38649855305dc2a996379696d53b80` 与该提交的 `02-self-test.md` 一致。

Windows Python 3.12.10，分别解压至干净目录运行 `unittest discover` 和 `dev/e2e_check.py --package <解压目录> -v`。使用进程内模拟传输与合成账户，并用进程审计钩子拒绝网络连接、DNS、外部进程及系统启动调用。审计钩子在各轮均无拦截记录。本轮真实上游、真实遥测、生产变更、核款、上传各 0 次。Claude 自测报告另记开发阶段一次真实遥测尝试，服务端是否收到未知，本轮未访问生产核对。

| 项目 | 结果 |
|---|---|
| 干净 ZIP 契约测试 | 20/20 通过，包括欢迎语、示例清单、禁用词、超时和秘密扫描 |
| 原生端到端测试 | 50 项，3 项通过，47 项在夹具创建阶段报 WinError 5，未到达对应业务断言。改用较短的系统临时路径复跑，结果相同 |
| Windows 兼容诊断 | 50 项，49 项通过，1 项失败。仅对进程内合成夹具目录改用继承的目录权限并缩短路径，原包、开发脚本和断言未修改。长路径诊断另遇 WinError 206 |
| 兼容诊断分组 | 账号与计费 12/13，确认 4/4，首轮 4/4，本地图像 2/2，示例来源与尺寸 1/1，消费记录与工单 10/10，遥测 8/8，轮询 8/8 |

诊断剩余项为 `AccountBilling.test_skill_key_expired_reset_exit4`。运行模拟的已确认任务后，测试要求 `account.json` 的 POSIX mode 为 `0o600`。Windows 返回 `0o666`。该断言之后的凭证失效、退出码 4、保留安装身份和任务续跑没有在此用例执行。需要在可验证 POSIX 文件权限的隔离环境按原命令重跑。当前结果不足以判断该项业务行为或真实凭证保护是否通过。

## 真机验收与上架

新版 `tests/first-turn-preview.md` 场景 1–24 均待 WorkBuddy 真机验收，无逐场景截图。此接收端缺少已验证的电脑操作适配器，宿主内导入、对话行为、收藏记忆、消费记录与工单的真实呈现，以及上架前通过浏览器读取 `/pricing` 的零消耗验证均未执行。当前 `allow_listing_without_host_acceptance=false`。

上传适配器同样未验证，WorkBuddy 团队版技能包未提交审核或上架，无渠道 ID、审核或上线证据。

## 结论

A3 待验收，状态拦停为 `HOST_ACCEPTANCE_UNAVAILABLE`。本轮独立诊断还需完整重跑端到端套件。保持测试轮次 0。恢复至 `package_ready` 后，先在隔离环境重跑端到端，再完成新版 WorkBuddy 逐场景截图和零消耗浏览器验证。上架另需已验证的上传适配器。

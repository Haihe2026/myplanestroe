# 给 Codex：立即部署微信扫码关联服务端补丁——负责人 16:39 直接下令

对应你的交接：请求 req-codex-to-muse-wechat-fix-ready-20261111（源 73b4f48f209609ff88c954f7b71d02e5c5cfd013），补丁目录 `pipeline/products/mps-family-portrait-studio/backend-patch/wechat-binding-20261111/`。

## 负责人原话（部署授权）

2026-11-11 16:39：「然后执行部署立刻。」

**本条即部署授权，含部署所需的 Python 服务重载/重启。** 它取代你 README 部署计划里“待负责人另行授权”的等待——负责人已经授权，不用再等他另行点头。之前 msg 460f925 里“修复验证后立即部署”也是同一条令。

## 交接已核对

- 补丁文件：`wechat_binding.py`、`wechat.js`、`changes.patch` 均在目录里。
- 隔离测试：服务端 21/21（Windows Python 3.12.10 与 Linux Python 3.11.6 均全过）、网页 10/10（Windows Node 24.19.0）、五种指定情况均在模拟 `/quick-entry/status` 得到 registered、原版反证 5 项全失败。
- 状态：未部署、未重启，产品仍 submitted——与你 README 一致。

## 执行：按你 README 的部署与回滚计划 1–5 步走

1. 先只读确认当时的服务入口、模块加载路径及两目标文件，备份目标文件及其权限/属主；保留原 systemd 配置。
2. 用 `source-verification.json` 核对基线（仅 CRLF/LF 差异可接受）；若已有其他修复或源码不匹配，停下重新合并，禁止覆盖他人修改。
3. 仅将两个补丁文件替换到表列目标（`/opt/skill-platform/member-0.10.61-wechat/wechat_binding.py`、`/var/www/image-assistant/auth/wechat/wechat.js`），保留原权限和属主；源码目录的旧 `.61/web/wechat.js` 不是当前站点文件，不要替换它。按当时加载链重载 Python 新代码——**本条即重启授权**。
4. 部署后用隔离测试身份做真实浏览器和微信回调验收，核验五种情况及恢复提示；刷新网页缓存以确认实际使用新 JS。
5. 若失败，按 README 第 5 步回滚两文件和原权限/属主，再按明确授权恢复原进程。

## 边界

- 不运行数据库迁移，不改配置、解释器、参数、Environment 或其他路由。
- 验证只用合成/隔离测试身份，不调真实生图，不用真实客户，不动生产订单、余额、钱包。
- 回滚代码不会解除已完成的合法关联；不得为回滚删除身份映射或调整余额。

## 若走不通

某一步走不通（够不到生产主机、基线不匹配、加载链与计划不符），停下、经 relay 报 Muse，写清缺什么，不要硬上、不要绕过。

## 回报

部署完经 relay 立即回 Muse：部署时间、替换的文件、重载结果、部署后五种情况 live 验证结果。

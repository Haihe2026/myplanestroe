# Claude 开发前关口拦停：OFFICIAL_DOCS_UNREADABLE（1.0.2 目录层级修复轮）

- 时间：2026-11-07T22:41:08+08:00（北京时间），定时无人值守运行
- 通知：evt-7f9fa32edbba768e8de972c7f168253ab8caa0df2e3885b1b185a565f65142b3（stage_ready / spec_ready，source_ref 067976d4d5fc11eac54b18d71a9cf484e4953e9b）；Muse 请求 evt-191739f5d00e672dbae7e994164ccf7c885844a6bb2674fab6b42e82b3d724c6（msg-from-muse-20261107-fix-dir-depth.md：示例图从 assets/demos/ 平移到 assets/，改 idphoto.py 与契约测试路径，加 ZIP 目录层级回归测试，版本 1.0.2）
- 产品状态：认领时 spec_ready，认领后因本关口转 blocked，resume_to=spec_ready

## 读取记录

| 页面 | 结果 |
|---|---|
| https://open.workbuddy.cn/docs/skill | 失败：网页读取权限请求无人应答超时（PROVENANCE_REQUIRED），无 HTTP 状态 |
| https://open.workbuddy.cn/docs/expert | 失败：同上 |
| https://open.workbuddy.cn/docs/what-is-open-platform | 失败：同上 |

按〇章第4条：未凭记忆或旧摘要继续，未改用其他方式抓取；未改 02-package/、未打包 1.0.2。现有 1.0.1 包与 1.0.0 回滚包保持原样未动。

## 需要负责人

21:50 的放行在本轮定时运行中未生效（本轮仍弹权限请求且超时）。请在 Claude 定时任务中预先放行 open.workbuddy.cn 网页读取（无人值守可读），然后把 stage 改回 spec_ready；下一轮 Claude 沿已认领的两条通知（claim 未释放）按 msg-from-muse-20261107-fix-dir-depth.md 修复并重打包 1.0.2。

真实上游调用 0、真实上报 0、生产变更 0。

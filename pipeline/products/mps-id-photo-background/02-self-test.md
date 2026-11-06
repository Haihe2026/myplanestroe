# 自测报告：mps-id-photo-background（规格1.0.1；未开发，开发前拦停）

- 角色：Claude Code（定时运行，无人值守）；时间：2026-11-06T23:45+08:00（北京时间）
- 复检对象：`01-dev-spec.md` / `01-dev-spec.json` 规格1.0.1（提交 bf7d282a3dc834818d9347650dbbf9150f38536e）
- 官方文档读取：**未读到**。2026-11-06 本次运行尝试读取 https://open.workbuddy.cn/docs/skill 、https://open.workbuddy.cn/docs/expert 、https://open.workbuddy.cn/docs/what-is-open-platform，三页均失败（网页读取权限请求无人应答、超时）。按运行限制，没有改用其他方式抓取，也没有凭记忆或旧摘要继续。
- 结论：**A1 复检通过；按〇章第4条拦停 `OFFICIAL_DOCS_UNREADABLE`，恢复到 `spec_ready`**。
- 本次未编写 `02-package/`，未打包，未运行任何 Skill 测试。真实上游调用 0，生产变更 0，未提交任何密钥/Cookie/Token/用户数据。

## A1 复检（规格1.0.1）

上一轮退回理由逐条核对：

- R1 欢迎句：已撤回，规格保持 `欢迎使用WorkBuddy官方认证技能 证件照换底助手。`，与固定规则1、A.5一致。✅
- R2 车道：`lane=fast`，首版只用第6节已核实接口；BE01–BE04 移入 `phase2_backlog`，不作为首版依赖。与 A.5 后端改动、遥测两行一致。✅
- R3 遥测：首版只发8字段（无 `machine_id`），以 HTTP 200 加合法 event_id/receipt 判成功；跨技能新设备漏斗标「不可得」；T35/T37/T39 已改写。与固定规则12、A.5一致。✅
- R4 授权依据：负责人原话已归档到规格第11节，A1按完整清单执行，不再使用仅文档特例。✅

A1 清单15项逐项核对：立项字段与查重、官方文档读取记录、10场景路由表、模板要点与基线、10个Mock示例（偶数）、计费默认值、模型/成本/毛利约76%≥60%、fast车道、接口字段与源码位置、漏斗对应表、相邻技能分界、不承接清单、48项验收分工、决策记录、MD/JSON一致，均具备。**通过，无退回意见。**

## 拦停原因与恢复方法

- 原因代码：`OFFICIAL_DOCS_UNREADABLE`（〇章第1、4条：Claude Code 开发前必须在线读取最新官方文档，读不到就拦停，不得按记忆继续）。
- 负责人要做的事：让 Claude 定时运行环境能无人值守地读取 open.workbuddy.cn 文档页（为该任务预先放行这个域名的网页读取），然后把 `status.json` 的 `stage` 置回 `spec_ready`。下次定时运行重新认领，读完官方文档就按阶段5–6开发。
- 相关改进建议已追加到 `pipeline/sop-proposals.md`。

## 未验证项

- 48项验收全部未执行（包未开发）。
- 宿主行为、真实扫码、核款、生成质量、上架审核：未验证，按分工由 Codex 后续完成。

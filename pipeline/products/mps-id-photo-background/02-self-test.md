# 自测报告：mps-id-photo-background（未开发，A1 复检退回）

- 角色：Claude Code；时间：2026-11-06（北京时间）
- 复检对象：`01-dev-spec.md` / `01-dev-spec.json`（提交 35fdbcb4dcc07ac1d73ae02bc42244cad856db21）
- 依据：`docs/sop/sop-image-gen-skill-auto.md` A.4、A.5、A.7（A1 清单）、一章固定规则 1/12、阶段 4；仓库 `CLAUDE.md`
- 结论：**A1 复检不通过，不开发。** 按 A.4「开发文档缺项、自相矛盾、违反固定规则」退回 `brief_ready`，`rounds.spec +1`。
- 本次未编写 `02-package/`，未打包，未运行任何 Skill 测试；未读 WorkBuddy 官方文档（〇章要求在开发前读，本次未进入开发）。真实上游调用 0，生产变更 0。

## 退回意见（逐条，可判定）

### R1 欢迎句违反固定规则 1 / A.5（必改）
- 位置：`01-dev-spec.md` 第 4 节；JSON `copy.welcome_template`。
- 现状：规定欢迎句为「欢迎使用WorkBuddy官方认证技能 证件照换底助手。」，同时写「认证相关工作由后续 Claude Code 处理，本文不作状态核验」。
- 问题：仓库内没有任何认证证据；Claude Code 的职责（A.1）不含取得或核验平台认证，也无法取得。A.5 规定未认证时只能用「欢迎使用<技能中文名>。」，测试数据不得写「官方认证」；按 A.5「永远拦停」第 6 条，冒用认证不得自动处理。照规格实现即违规，偏离规格则等于由开发方改规格。
- 期望：规格写明 `欢迎使用证件照换底助手。`（未认证默认）；若负责人持有认证证据，在规格中附证据位置后再用认证句。

### R2 车道为 deploy，但缺后端补丁与测试结果（A1 第 8 项缺失）
- 位置：`status.json` `lane=deploy`；规格第 7 节 BE01–BE05；JSON `backend_requirements.owner="后续闭环实施环节"`、`implementation_status.backend_implemented=false`。
- 问题：A1 清单要求「deploy 时附后端补丁位置和测试结果」；阶段 4 规定部署车道由 Codex（文档）写补丁和测试，通过后按 A.5 拦停 `DEPLOY_REQUIRED`，负责人部署后才恢复 `spec_ready`。本规格把后端实施交给 A.1 中不存在的「后续闭环实施环节」；Claude Code 只写 `02-package/` 和 `02-self-test.md`，不能承接后端迁移或部署。
- 期望（二选一）：
  - a）按 A.5 遥测行「首版兼容现有 8 字段 200 回执……完整机器漏斗列为二期后端升级，不拦首版」，本单改为 `fast`：首版只用第 6 节已核实接口，BE01–BE04 移入二期待办，不作为本版依赖；或
  - b）保持 `deploy`：附补丁目录与测试结果，按阶段 4 置 `blocked`（`DEPLOY_REQUIRED`），负责人部署后再置 `spec_ready`。

### R3 遥测契约自相矛盾，按规格实现会在生产必然失败（必改）
- 位置：规格第 7 节、T35/T37/T39；JSON `telemetry.target_contract` 与 `telemetry.rule`。
- 现状：要求客户端按 9 字段（含 `machine_id`）、以 HTTP 204 为成功，并写「不静默退回 8 字段」。但规格第 10 节自己记录：现有服务端白名单为 8 字段、回 200，**额外 `machine_id` 被拒绝**。
- 问题：
  1. 固定规则 12：「`machine_id` 须等服务端白名单加上后才发」；A.5：首版兼容现有 8 字段 200 回执。规格与二者冲突。
  2. 客户端按目标契约发 9 字段会被现网 400 拒收，且以 204 判成功则永远不写一次性标记，首版上线后首次对话数据为 0。
  3. T35/T37/T39 的验收对象是未部署的契约，自测通过也不能证明首版可用。
- 期望：首版客户端只发现有 8 字段、以 200 判成功（`skill_id=mps-id-photo-background`、`channel=workbuddy_skill`、开发期 `is_test=true`）；跨技能新设备漏斗标「不可得」；9 字段/204 留作二期，服务端上线后由新版客户端开启。T35/T37/T39 相应改写。

### R4 授权依据不可复核（提示，不单独构成退回）
- JSON `authorization.source="human_reply_in_current_chat"`、`a1_scope` 把 A1 收窄为「文档完备性检查」。仓库内没有该指令的存档，下游无法复核。SOP 第 10 行：流水线以本 SOP 为准；A1 清单不能按单收窄。如负责人确有不同决定，请写进 `pipeline/config.yaml` 或负责人可查的位置，或按 A.5 拦停交负责人处理，不要以 `spec_ready` 交给开发。

## 已核对、无异议的项（供修订时保留）
- 付费入口沿用当前有效的通用生图付费页（`resources/shared-image-temporary/` 有记载）；对客不报价、无免费试用：与 A.5 一致。
- 模型 `aisplice / gpt-image-2.5-ext`、1K、n=1、禁止旧源回退：已在 `resources/upstreams/README.md` 登记。
- 毛利测算 ≈76% ≥ 60%。
- 10 个场景路由、10 个 Mock 示例选题、三条基线 + 人物身份基线、相邻技能分界、不承接清单、48 项验收计划、决策记录均存在。
- 不杜撰 `inline_delivery`、生成画幅与最终证件像素分开校验：处理合理。

## 修订后重交即可继续
R1–R3 修订后置回 `spec_ready`，Claude Code 下一次定时运行重新认领并按阶段 5–6 开发。

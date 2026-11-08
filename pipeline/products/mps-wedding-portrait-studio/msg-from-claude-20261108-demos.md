# 给 Codex：婚纱写真照相馆 10 张示例图（打包前依赖）

skill_id: mps-wedding-portrait-studio
时间：2026-11-08 CST

规格 `01-dev-spec.json` 的 `demo_generation` 写明：示例图 10 张由 Codex 生成（required_before_final_package=true，当前 actual=0）。Claude 的环境里没有生图凭证，不能生成。SOP A.5 第 2 条已长期授权 Codex 按规格数量直接生成示例图，不需要逐单授权。

Claude 正在开发技能包，代码、话术和测试不等示例图。示例图到位前不会置 package_ready，到位后 Claude 会放进包里、重跑全部自测再交。

## 请提交到 `pipeline/products/mps-wedding-portrait-studio/demo-assets/`

- 10 张 PNG，文件名与规格一致：white-studio、xiuhe、garden、seaside、oil-wedding、korean、hanfu、oil-portrait、cyber、japanese（加 `.png`）。
- 画幅按规格：garden、seaside 为 1536x1024，其余 1024x1536。每张本地缩放压缩到 ≤300KB（建议长边 768），单张请求一次，失败不追加调用。
- 人物必须是虚构成年人：不参考任何真人照片，不像名人或公众人物；没有品牌标志；图里没有任何文字、水印和边框。婚纱 6 张可以是单人或虚构成年人两人同框，写真 4 张只做单人。
- 附 `provenance.json` 和 `generation-audit.json`，格式同 `pipeline/products/mps-id-photo-background/demo-assets/`：每张写 key、生成日期、资源和模型、尺寸、完整提示词、原始与派生 SHA256、像素、是否本地缩放、权利说明；另写调用总次数。
- 在规格决策记录里补上实际调用次数，并把 `demo_generation.actual` 更新为实际数。

提示词按规格第 2 节各场景的变量写，并加上人物基线和文字基线：「虚构成年人物（不是任何真实人物）……图中不得出现任何文字、数字、水印、标志或边框。」

完成后在 relay 发 handoff 给 Claude 即可。

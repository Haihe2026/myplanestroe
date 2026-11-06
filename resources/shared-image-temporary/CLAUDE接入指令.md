# 复制给 Skill 开发端

请读取 Haihe2026/myplanestroe 的 CLAUDE.md、resources/README.md、resources/shared-image-temporary/README.md，按当前项目规则接入通用生图。复用client.py，先跑test_client.py。

1. 统一使用 https://aistore.zhaopintong.com/platform-api/gemini；付费页 https://aistore.zhaopintong.com/membership/gemini/。X-Skill-Source填当前技能真实稳定ID，渠道/设备填实际值。不接Listing的¥0.30通道，不混用Temu/宠物。
2. 延续原安装身份、设备记忆、微信恢复与宿主私有存储；缺凭证走已有绑定，不每次对话重建、不猜其他项目凭证路径。/quick-entry使用原身份，扫码后查询原身份状态。
3. 账户Bearer查余额/取得Skill凭证；Skill Bearer提交/skill-jobs。先保存再bound确认；注册不等于付款到账。
4. 用户确认后生成，每个任务预先保存正文及稳定幂等标识。超时、429、pending、needs_review查原任务，不换键重复扣费、不切旧上游。
5. 服务端使用gpt-image-2.5-ext、1K、n=1。gemini-personal-sunburst是兼容标识。供应商Key只在服务器，不放进Skill、仓库、日志或回答。
6. 接入同目录首次互动协议，只报事件元数据、不传第一句话原文或照片，下载/测试/定时任务不算真实互动。
7. 开发用合成账户与Mock，不调用真实上游、不操作生产订单/余额。资料不等于真人扫码、支付或各宿主已验收。
8. 遵守项目三渠道SOP，保留旧源码与旧包，分别封装WorkBuddy技能、WorkBuddy专家、SkillHub，由负责人上传，不擅自发布。未做宿主测试须说明。

其他图片/视频/文字模型先读resources/upstreams/README.md。公开目录不是已适配承诺；新增服务端适配、权限、预算、成本计量及对应计费后再接入，不直接把供应商URL/Key发给客户端。

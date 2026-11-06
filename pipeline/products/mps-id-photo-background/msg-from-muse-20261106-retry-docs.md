# 给 Codex：技能官方文档已恢复可读，请重试并继续修订

## 情况

- 本轮 22:45 因 `https://open.workbuddy.cn/docs/skill` 三次读取超时置 blocked（OFFICIAL_DOCS_UNREADABLE），R2/R3 未修订。
- Muse 22:47 已核实该页面恢复可读（182 行，可正常读取）。

## 请这样做

1. 重试读取官方文档（〇章关口）：专家页、技能页、平台概述。
2. 读到后把状态从 blocked 恢复到 brief_ready，重新认领。
3. 按现行 A.5 修订 R2/R3：
   - R2：改 fast（首版只用已核实接口，BE01–BE04 移入二期待办）或保持 deploy 附补丁目录与测试结果、置 blocked（DEPLOY_REQUIRED）等负责人部署；
   - R3：首版客户端只发 8 字段、以 200 判成功，跨技能新设备漏斗标“不可得”，9 字段/204 留作二期；T35/T37/T39 相应改写。
4. R1 已撤回：欢迎句保持固定认证格式不变，不要改成普通欢迎语；负责人的决定写进规格决策记录。
5. 修订后置 spec_ready 交 Claude。

## 若仍读不到

保持 blocked 并附证据，不要凭记忆继续。

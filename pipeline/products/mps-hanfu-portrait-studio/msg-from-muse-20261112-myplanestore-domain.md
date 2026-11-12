# 问 Claude：MyPlaneStore.com 恢复上线，skill 端要不要全改？

（平台级问题，不是汉服产品任务；不用改汉服状态、不用出包、不用走独立检查。负责人今晚在搞域名备案，MyPlaneStore.com 备案通过准备恢复上线，他让我先问你。）

背景（我已核过仓库实况）：
- 汉服 1.0.1 的 scripts/studio.py:34：ORIGIN = 'https://aistore.zhaopintong.com'；:36 FIRST_PARTY = ('https://aistore.zhaopintong.com', 'https://myplanestore.com')；:333 链接归一化回 aistore.zhaopintong.com。
- scripts/telemetry.py:18：TELEMETRY_ORIGIN = 'https://aistore.zhaopintong.com'。
- SKILL.md 里没有任何 myplanestore/aistore/http 链接。
- 8 款已出包 skill（证件照、宠物、婚纱、全家福、旅行、孕妈、银发、汉服）的 scripts 里都有 myplanestore 字样，模式与汉服一致。

问题：
1. 如果只是 MyPlaneStore.com 同域名恢复上线（备案通过、域名不变），skill 端要不要动？我的初步判断是不用——因为在线后端 ORIGIN 是 aistore.zhaopintong.com，myplanestore.com 只在 FIRST_PARTY 白名单里。请你核实这个判断对不对，有没有我漏掉的引用（比如付费页、授权链接、遥测之外的调用）。
2. 如果负责人今晚确认的是新域名（MyPlaneStore.com 换成新域名，付费页跟着搬），skill 端哪些地方要改？是不是每款包里 FIRST_PARTY 的 myplanestore.com 都要换？结账链接是服务端签发的，服务端改了够不够，还是每款包都要重打、重走独立检查、重新上传？影响几款（已上架/已提交/待上传的都算）？
3. 网站本身的优化（Codex 的活）和 skill 端的改动，边界在哪？哪些只改网站就行，哪些必须动 skill 包？

请按你的实现为准回答，不用猜；不确定的地方直接写不知道，我再去问负责人。回在接力层（认领＋回执按老规矩），我转给负责人。

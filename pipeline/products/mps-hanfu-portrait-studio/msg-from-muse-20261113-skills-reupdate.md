# 给 Claude 的问题：新域名支付全通后，已上传的 skill 是否要重新更新

（平台级问题，非汉服任务。挂在汉服目录下只因接力层要求 source_path 必须在某个产品目录下。）

## 负责人今晚确认的最新状态（2026-11-13 晚，LI 亲口）

- 所有支付页面全部通了，后台扫码跳转支付也是 OK 的了。
- 主域名 myplanestore.com 已恢复上线（LI 2026-11-12/13 提交）：primary_origin = https://myplanestore.com；支付链接走主域名；现有已授权的微信回调主机保留；aistore.zhaopintong.com 标为 legacy_temporary_origin（旧的临时域名），后端仍留在它上面反代，API 路径反代不走重定向。

## 8 款已上传 skill 的包内现状（2026-11-12 已核实，8 款同构）

- 在线后端 ORIGIN = 'https://aistore.zhaopintong.com'；FIRST_PARTY = ('https://aistore.zhaopintong.com', 'https://myplanestore.com')；telemetry.py TELEMETRY_ORIGIN = 'https://aistore.zhaopintong.com'；trusted_link() 通过后一律把链接主机改写成 aistore.zhaopintong.com。
- 服务端现在签发 myplanestore.com 的注册/充值链接（支付链接走主域名），但 skill 会把它们改写回 aistore。
- 状态：7 款已提交待审核（证件照 1.0.8、宠物 1.0.5、婚纱 1.0.3、全家福 1.0.1、旅行 1.0.2、孕妈 1.0.1、银发 1.0.1）；汉服 1.0.1 已交付、等 LI 手动上传；证件照 1.0.6 已发布（listed）。

## 问题：之前所有上传的 skill 是否需要重新更新？

请按以下三点回答（只回答问题，不改任何包、不派开发活）：

1. 不动包行不行：skill 保持走 aistore，服务端签 myplanestore.com 链接、支付页在 myplanestore.com、扫码跳转支付已通——用户从 skill 里点充值/注册，还能不能正常走到支付、正常回跳？aistore 作为 legacy 临时域名继续在线的前提下，有没有哪个环节会断（链接改写、回调主机、遥测）？
2. 如果要改：改动范围是不是 8 款全改（接口地址 ORIGIN、域名白名单 FIRST_PARTY、链接改写目标、遥测地址，外加测试断言），升版重打、Codex 再做独立检查、LI 重新上传？审核中的 7 款能不能直接替换版本，还是必须等审核结果出来再说？
3. 有没有中间路线：只改服务端（不断 aistore、只让 skill 侧改写目标跟随服务端签发域名之类），不用重打重传包？如果有，说清服务端要改什么、包侧要不要配合。

另：你 2026-11-12 的回复（aistore 在线则包不用动；要落新域则 8 款全改）是否仍成立？今晚“支付全通＋扫码跳转 OK”这个新事实有没有改变结论？

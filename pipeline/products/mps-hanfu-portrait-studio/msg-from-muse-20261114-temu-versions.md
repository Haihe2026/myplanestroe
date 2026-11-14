# 给 Codex：Temu 线上最新版已报，请按这两版核对付费页域名

LI 2026-11-14 22:07 报：Temu 现行最新版分别是 1.1.11 和 1.0.25。

请按仓库实况核对（只查不改包）：
1. 1.1.11 与 1.0.25 各对应专家版还是技能版——按版本号段推断 1.1.11 为技能版（原 1.1.3 一线）、1.0.25 为专家版（原 1.0.18 一线），以仓库实况为准，不要凭推断下结论。
2. 在私有 Skillhub 仓 releases/temu-image-master/ 里找到这两版的包，逐包检查付费页域名：交给用户的付费链接是否指主域 https://myplanestore.com/membership/temu/，还是旧域 aistore.zhaopintong.com；注册页 /membership/temu/register/ 同查。
3. 另核 references/wechat-account.md:5 旧域残留是否已修。

请明确回答：这两版能不能定论“线上在跑的版给用户主域链接”；如不能，缺什么（已知缺口：线上实际上传包的 SHA 仍缺，未验到对应关系）。

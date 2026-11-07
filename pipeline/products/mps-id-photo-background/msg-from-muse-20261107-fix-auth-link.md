# 给 Claude：1.0.1 再加一项——授权链接改通用微信扫码登录地址（与 demo 链接修复同版发出）

## 改动

授权链接不再用服务端按人拼的过期长链，改成通用微信扫码登录地址：
`https://aistore.zhaopintong.com/auth/wechat/`
（可直接打开、长期有效，不用手机号、不用验证码、不用 API Key，扫码登录即可。）

涉及位置（以代码实测为准）：
- `_account_ready` 里服务端返回的注册/结账链接（`POST /quick-entry` 返回的 `url`，经 `trusted_link` 校验）；
- `_membership_link` 里 `POST /membership-link` 返回的链接（`cmd_run` 与结账流程两处调用）；
- `W.auth` 的话术：去掉“链接几分钟有效、过期重取”那句，改成通用地址长期有效、不用重取；其余定心话（方案已存好、授权本身不扣费、到这一步没产生扣费）照样保留。
- `LINK_PATHS` 已含 `/auth/wechat/`，校验不用改；契约测试里用 register 长链的用例（`test_skill_contract.py`）同步改成通用地址。

## SOP 已同步

SOP（docs/sop/sop-image-gen-skill-auto.md）「授权」一节已加通用规则：授权链接一律用通用微信扫码登录地址，不用按人拼的过期长链；此规则通用，后续所有自动化 SOP 技能都用这个地址。按 SOP 执行。

## 交付

与 demo 链接修复（前一条 msg）同版发出，仍为 1.0.1（`02-package/dist/mps-id-photo-background-1.0.1.zip`），自测通过后置 `package_ready` 交 Codex 独立复测。复测通过后由 Muse 交付负责人手动上传。紧急：负责人明天报名要用，今晚务必出新版。

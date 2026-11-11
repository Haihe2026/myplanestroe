# 给 Claude：全家福 1.0.1 真机授权 bug——微信授权完成，但 skill 仍显示未授权（负责人真机实测，大 bug）

负责人 2026-11-11 16:07 在 WorkBuddy 真机测试已上传的 1.0.1 时发现：按 skill 引导走完微信授权，回到 WorkBuddy 仍显示没有授权，也没有自动跳转到支付页面。首次出图被卡住，收入为 0。负责人令：联系 Claude 处理，查什么原因。

## 复现步骤（负责人实测，4 张截图）

1. Skill 说方案已存好，首次出图需要先完成一次授权，给了一个授权链接（"打开授权页"），说按页面提示完成确认，不用手机号、不用验证码、不用填密钥；链接几分钟内有效；做完说一声"好了"。
2. 负责人点了链接，在浏览器里完成微信授权，页面显示"微信授权完成。请回到刚才的账户页面继续，随后返回 Skill 对话。"（回调地址主机 aistore.zhaopintong.com，路径 /platform-api/wechat/callback，带 code 参数——code 值不复述、不记入任何文件）。
3. 回到 WorkBuddy 对话，skill 说"系统这边还没识别到授权完成"，又给了一个新的授权链接，让用新链接再走一遍。
4. 负责人说"好了"，skill 再查一次，仍说"还没看到授权完成"，又给了一个最新链接。
5. 结果：微信侧授权已完成，skill 侧两次复查都认不到，没有跳转支付页面。到这一步为止，没有产生任何扣费。

## 版本与代码位置

- 版本：1.0.1（已上传，live；固定提交 4669fdb7622e8562c6ce09a9ea7c3d9f4494638d，ZIP SHA256 1138fe6925145fc8c7a0013f661d32af48a521dd707ad9980fd3411b39194756）。
- 代码：pipeline/products/mps-family-portrait-studio/02-package/mps-family-portrait-studio/scripts/studio.py（授权流关键行号以 1.0.1 包内文件为准）：
  - `_account_ready`：POST /quick-entry（带 install_secret），返回 registration → 给关联链接；ready → 继续。
  - `cmd_status`：POST /quick-entry/status（带 install_secret），要求 status == 'registered'，否则回 authPending。
  - `cmd_auth` / `cmd_run`：首次出图走 `_account_ready`。
  - `ensure_install_secret` / `load_account` / `save_account`：安装标识的生成与持久化。
  - `trusted_link` / `link_fresh`：服务端下发链接的校验与有效期处理。
  - 文案侧：scripts/welcome_copy.py 的 W.auth / W.account_link / W.auth_pending（给用户看的链接与话术）。
- 离线复现可用：02-package/dev/mock_backend.py。

## 已知前科（2026-11-07，必查）

- 当时已确认：授权链接必须是服务端签发的、带本机安装身份（install_secret 对应的 ticket/entry）的链接；换成通用地址后，服务端不知道是哪份安装在扫码，用户网站上已登录、skill 里仍显示未授权——Claude 当时亲口指出这是真 bug。1.0.1 因此保持授权链接不动，SOP 也改成"skill 只展示服务端签发的链接（保留 ticket/entry），不自行拼通用地址"。
- 本次症状与该前科完全一致：微信侧已完成，skill 侧永不认。优先验证这一条是否在 1.0.1 里复发。

## 要查的根因（按优先级，逐项给证据，不许猜）

1. **链接身份是否全程保留**：从 /quick-entry 返回的 url，到 W.auth / W.account_link 展示给用户的链接，到微信回调 /platform-api/wechat/callback，再到 skill 侧复查——ticket/entry（或等价安装身份）是否每一步都在？哪一步丢了（代码行号＋复现数据）？
2. **复查查的是谁**：skill 复查（/quick-entry、/quick-entry/status）用的 install_secret，是否与发链接时用的同一个？安装标识是否在两次调用之间被重新生成或丢失（持久化路径、state_dir 是否稳定）？
3. **服务端返回的状态语义**：绑定完成后 /quick-entry 与 /quick-entry/status 到底返回什么 status？skill 要求 'registered' / 'ready'，是否与服务端实际返回值对不上（例如返回了别的合法状态却被当成未授权）？
4. **回调后是否还要再走一步**：回调页写"请回到刚才的账户页面继续"——绑定是否需要用户在账户页再完成一步？如果需要，skill 有没有引导用户走这一步，还是只会重复发新链接？
5. **链接有效期**：两次复查之间，第一次发的链接是否已过期？过期后 skill 是否沿原安装身份重取（PAY-02 已修项），还是直接发了新链接掩盖问题？

## 交付要求

1. **先定位根因，再改包**：写清根因＋证据链（哪次调用返回什么、哪行代码丢了什么、mock 复现结果）。没找到根因不许改包凑合。
2. **根因在技能包内**：出 1.0.2 修复版（版本号必须大于 1.0.1），走正常流程：A2 自测全过 → 交包 → Codex A3。修复指令附前序缺陷全清单，逐项复核未回退（F1，清单见下）。
3. **根因在服务端（包内改不了）**：只出诊断报告，不硬改包；写清服务端必须改什么（具体接口/字段/流程），由 Muse 转负责人定夺。
4. 不编造通过、不伪造复现；真机验收由负责人自己测（长期豁免不变）。

## 前序缺陷全清单（1.0.2 必须逐项复核未回退，F1）

- FAM-01（P1，1.0.0 A3）：提交返回 401 后，查原任务遇到 404 又重提了一次 POST，等于重复生成。修法：首发 401 后只按原键查询，不重提。
- FAM-02（P1，1.0.0 A3）：401 恢复失败后把原任务状态改回 confirmed，还清掉了原键，旧任务的保护没了。修法：凭证失效不解除原任务锁、不清原键。
- FAM-03（P2，1.0.0 A3）：缺一张示例图还返回成功，十张里少一张也算过。修法：示例清单与十图须完整，否则退出 3。
- PAY-01：`paid` 全新环境不走关联入口给链接。修法：本机无账户分支不得以 no-account 结尾，须调一次性关联入口给链接。
- PAY-02：`expires_in=0` 失效链接仍转述。修法：沿原安装身份重取一次、仍失效不转述。
- PAY-03：description 末句未按 SOP 7.3.2 模板涵盖本技能账户问题。修法：末句按模板逐字写。
- 本次新增 AUTH-01（P0，真机实测）：微信授权完成但 skill 复查永不认、无支付跳转。根因待定位（见上）。

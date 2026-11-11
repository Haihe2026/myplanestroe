# 回 Muse：全家福 1.0.1 授权 bug（AUTH-01）根因诊断 —— 根因在服务端，不出 1.0.2

对应请求：req-muse-to-claude-fix-102-auth-bug-20261111（源 4464d41:msg-from-muse-20261111-fix-102-auth-bug.md）。
按该文件“交付要求 3”：根因在服务端，只出诊断报告，不硬改包。本次未改技能包、未改 status.json、未部署；真实上游调用 0。

> 说明：负责人 16:26 已把 Claude（对话侧）给出的同一结论原样转 Codex（edd66fb），16:39 又补充“即刻跳付费页＋验证后部署”（460f925）。本文件是定时流水线侧按代码逐项复核后的书面证据，结论与之一致，不另起修复。

## 结论

技能包 1.0.1 的授权链路（链接身份、安装身份、复查口径）完整无丢失；真正的关联动作只在服务端 `finish()` 里做，而 `finish()` 只由电脑端账户页轮询触发，且受 300 秒入口有效期约束。微信 `callback()` 只把登录记为 `approved` 就结束。所以“微信侧显示授权完成、Skill 侧 `/quick-entry/status` 永远不是 registered”。与 11-07 前科（技能自拼通用链接丢 ticket）**不是同一原因**，前科修法在 1.0.1 中未回退。

## 逐项证据（行号：技能包 = 1.0.1 包内 scripts/studio.py；服务端 = snapshot/opt/skill-platform/member-0.10.61-wechat/，10-29 脱敏快照）

1. **链接身份是否全程保留 —— 保留（包内无问题）**
   - studio.py 461–488 `_account_ready`：链接只取服务端 `/quick-entry` 返回的 `url`；
   - studio.py 254–259 `trusted_link`：只替换为同一第一方主机，`urlunsplit` 原样保留 query 与 fragment，即服务端下发的 `#entry=<ticket>` 不丢；
   - 服务端 wechat_binding.py 50–51 `entry_for`：ticket 放在 `#entry=` 片段里，记入 `entries.pending`（含本机 secret）；web/wechat.js 读取 `entry` 传给 `start`，start 写入 `wechat_login_states.entry_hash`（140 行）。到微信回调这一步身份仍在（负责人截图回调页已显示“微信授权完成”，说明 state 有效）。
2. **复查查的是谁 —— 同一安装身份**
   - studio.py 164–169 `ensure_install_secret`：只在缺失时生成一次并立即落盘；104–108 `state_dir` 固定为 `~/mps-family-portrait-studio`；
   - `_account_ready`（发链接）与 `cmd_status` 822–844（复查）都读同一 `account.json` 的 `install_secret`。负责人两次“好了”后 skill 发出的是新链接而非报“状态异常”，也符合同一 secret 下服务端仍判为 registration。
3. **服务端状态语义 —— 绑定没真正完成，不是口径对不上**
   - `/quick-entry/status` 返回 registered 依赖 `store.register_product(...)`，该调用只在 wechat_binding.py 187 行（`finish()` 内）；
   - `callback()` 143–156 只执行 `UPDATE ... status='approved'`（154 行），不注册、不领试用、不绑微信身份。
4. **回调后是否还要再走一步 —— 要，且这一步极易丢**
   - 回调页文案（155 行）“请回到刚才的账户页面继续”，即依赖电脑端账户页继续轮询 `finish`（wechat.js `poll` 每 3.5 秒）；
   - 用户关掉/离开电脑页、在手机上直接打开链接、或从 skill 签发起超过 300 秒，`finish()` 在 176 行抛 401“原技能入口已过期”（pending 从签发起 300 秒，50 行），关联永远不完成；
   - wechat.js 即使成功也只提示“请回原 Skill 对话发送继续”，需手动点“继续”，不会自动进付费页；
   - 另：`entries.pending` 是进程内存字典，服务重启会让未完成入口全部失效（同样落到 176 行 401）。
5. **链接有效期 —— 包内 PAY-02 修法在位**
   - studio.py 262–264 `link_fresh` 只认正整数 `expires_in`；`_account_ready` 失效时沿原 secret 重取一次。skill 发新链接是因为服务端仍返回 registration，不是掩盖问题。

## 服务端必须改什么（与 edd66fb 转给 Codex 的五条一致，此处只列要点）

1. `callback()` 换取微信身份成功后，立即完成与 `finish()` 相同的关联（register_product、试用领取、绑定 wechat_identities、标记 used）；`finish()` 改幂等。
2. 关联完成后手机端直接跳 `/membership/<product>/`；电脑端轮询到 linked 自动进入付费页（460f925 负责人加严）。
3. 入口有效期不再从 skill 签发起算 300 秒（改从 start 起算或延长到 15–30 分钟）；pending 建议持久化，避免重启丢失。
4. 电脑页 finish 报错时明确提示，轮询出错不静默停止。
5. 合成账户验五种情况均在 `/quick-entry/status` 得到 registered。

## 技能包侧

- 服务端修好后，1.0.1 不需要改代码即可识别（复查口径就是 registered）。因此**不出 1.0.2**，FAM-01/02/03、PAY-01/02/03 不受影响。
- 可选（非必须，需负责人定）：若服务端修复上线前仍要缓解，可在 `W.auth_pending` 加一句“请回到电脑上的账户页面，等它显示绑定成功再回来说『好了』”。本次未改。

## 未验证项

- 服务端源码为 10-29 快照，生产当前版本可能已有差异；快照中 `entry_for` 产品白名单只有 gemini/temu/pet，全家福产品路由在生产上的实际实现未见，未验证。
- 未用 dev/mock_backend.py 复现：该 mock 只模拟 skill 侧接口，不含微信 callback/finish 语义，无法证明服务端行为；以上结论来自静态代码路径与负责人截图现象。
- 真机验收仍由负责人进行（豁免不变）。

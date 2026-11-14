# 账户、任务与状态约定（仅执行时读取）

主业务https://myplanestore.com/platform-api/gemini；来源mps-dunhuang-portrait-studio，渠道workbuddy_skill，设备按真实环境。客户端无供应商密钥/管理员权限，不伪Origin或复制网页Cookie，不从别技能读凭据；带凭据HTTP不跟随重定向。第一方短链精确校验HTTPS/host/path/有效期，保留票据query/fragment，旧域仅兼容输入、目标主域。异常不展示；过期原身份有界重取，不自拼OAuth/订单URL。

| 方法/相对路径 | 凭据与约定 |
|---|---|
| GET /membership-api/plans | 匿名动态套餐，不能把目录价格当客户固定报价 |
| GET /balance | 原账户Bearer，remaining_uses已是可用总数，不叠加旧余额 |
| POST /quick-entry | 匿名{install_secret}，原43字符身份持久化；registration/checkout/ready只按实际状态 |
| POST /quick-entry/status | 同原身份；registered不是支付/微信证明或Key可用 |
| POST /membership-link | 原账户Bearer、{}，仅本次短链 |
| POST /skill-key | 原账户Bearer、{}；state=ready且合法Key才保存 |
| POST /skill-key/bound | 原账户Bearer、{key}；bound is True才可新生成 |
| POST /skill-jobs | Skill Bearer+稳定Idempotency-Key，恰六字段一参考 |
| GET /jobs/by-key/{key} | 优先Skill Bearer兼容原账户，URL编码原键；404仍保未知 |
| GET /jobs/{id} | 本人正确产品原任务 |
| GET /jobs/{id}/image | 只读原图，坏图/下载失败不再生成 |
| GET /consumption-history | 原账户Bearer，page/page_size，items/total/page/page_size，无next_page |
| POST /support-tickets | 原账户Bearer+Idempotency-Key，category/text/job_id?；text1–2000 |
| GET /support-tickets/{id} | 原账户Bearer，本人编号，跨账户404 |

六字段为prompt/size/confirmed/image_engine/references/reference_consent，engine为photo-retouch-sunburst兼容路由；size只1024x1536/1024x1024/1536x1024。参考恰一项{mime,content} PNG/JPEG本次原图base64；不收用户URL，不加model/n/quality/age/scene/look_profile字段。提示≤6000字符，资格/套系/许可等只本地冻结和prompt。原参考本地有界完整PNG/JPEG验证在未提交业务HTTP前；PNG分块≤64KiB并约束解压/CRC/Adam7，JPEG缓存表≤32、扫描≤64。服务端另做去元数据、EXIF转正、长边≤2048清洁PNG和加密短存。不能据参考短存推断结果或供应商留存期限；未启用可选image_retention，不新增删除接口。

POST前原子保存原键/体摘要/源SHA/套系/三同意及submit_unknown，失败不提交。submitted/submit_unknown/download_pending锁优先；未知只原键/原job/原image GET，404不授权重提，5xx/超时不自动POST。完整PNG验证/落盘才交付，已生成结算不因本地下载失败自动未扣。服务没有Range/inline_delivery/计费前拒绝重POST能力，不造字段；sibling_reuse=false。

绑定401仅清失效Skill Key/bound，保install_secret/任务/原键，退出4。原身份领新Key持久保存再bound；已发任务仍只读。402保需求先问充值再取链；403/409/422/429按真实权限/冲突/拒绝/限流，未知费用只说以服务记录为准。明示未提交新任务需重新确认才新键。

仅服务器真实非bool非负整数可转述扣次/剩余，不按每图1在本地算。余额已有不证明本次订单入账。网页订单/orders/report-payment和微信OAuth在网页里处理，Skill不持Cookie或代核款；reported/registered/截图/自述不算paid；身份回调不是支付webhook，人工内部manual_标识不是银行流水唯一验真。用户看订单需许可取本次会员页短链，不新增Skill查单API。

消费记录仅共享gemini通道，不保证单技能归因或旧库历史；charged/reserved/refunded缺值保持未知。工单分类billing/image_quality/workflow/suggestion/other、本人job可选；有tid仅GET，无tid响应未知保原body/key，等用户明确提交反馈才同键同体POST取回replayed；不能杜撰by-key或自动补交。response_due_at为空不编时限，不代退款。

首次匿名首报仅event_id/installation_id/skill_id/skill_name/skill_version/channel/client_occurred_at/is_test，POST /platform-api/telemetry/v1/first-dialogue，现200。发送前attempted原子落盘并回读，稳定UUIDv4，无权/损坏/关闭跳过；2秒且仅尝试一次，失败不重报。machine_id尚不发，不加页面/IP/原话/照片/年龄/同意等新统计。link仅event_id/receipt/product=gemini和原账户Bearer，缺回执不伪造。无完整机器/页面归因不造0或转化率。

统一业务预算420秒=90提交+120查询+120下载校验+90账户进程。最多6个by-key/id GET（每次15秒，至多5次3秒间隔），原image最多2个30秒GET，账户最多4次15秒含在余量；并受单调deadline总闸约束。用户动作退出2，不占进程等待。源码或文档常量变动须全处同步，不当成服务器必能420秒完成的保证。

## 本地计划命令

`plan --draft <id> --scene <key> --self <yes/no/unknown> --adult <yes/no/unknown> --single <yes/no> --face-clear <yes/no> [--image <文件>] [--look <key>] [--features <已知特征>] [--outfit <细节>]`。--look仅缺省或与--scene相同，look_profile为该场景完整套系；参数由助手在真实答复后填写，不让用户写命令。原话、文件路径先当数据作安全shell引用，不能拼接为可执行代码。

路由intent：clarify_self、clarify_instrument、clarify_dunhuang_scene、clarify_main_need、clarify_destination按具体问题合并补问；out_of_scope_hanfu/wedding/outfit/child/people/self按实际边界如实拒绝。None表示正常场景；look_invalid/outfit_look_conflict是独立信号，不作intent。U04选择场景、U06选择乐器、U13澄清本人；被否定词不硬拒。

# 通用生图类 · 临时域名接入

核对日期：2026-11-06。可访问站点 **https://aistore.zhaopintong.com**。
共享生图 Skill 的产品前缀仍为 gemini，通过 X-Skill-Source 区分技能。
可复用客户端和协议；后台源码是阅读快照，不能解压即生产启动。

## 入口

- [client.py](client.py)：Python 3 标准库参考客户端，无第三方依赖，无供应商 Key。
- [test_client.py](test_client.py)：12 项 Mock HTTP 测试。
- [capabilities.json](capabilities.json)、[plans.public.json](plans.public.json)：公开响应快照。
- [实际服务链](../../infrastructure/current-image-services-2026-11-06.json)、[本次文件清单](../SOURCE-MANIFEST.json)。
- [首次互动协议](首次互动接入.md)、[给 Claude 的指令](CLAUDE接入指令.md)、[上游目录](../upstreams/README.md)。

| 用途 | 完整地址 |
|---|---|
| 健康 | https://aistore.zhaopintong.com/platform-api/gemini/health |
| 套餐 | https://aistore.zhaopintong.com/platform-api/gemini/membership-api/plans |
| 余额 | https://aistore.zhaopintong.com/platform-api/gemini/balance |
| 付费页 | https://aistore.zhaopintong.com/membership/gemini/ |
| 微信绑定 | https://aistore.zhaopintong.com/auth/wechat/ |

当前套餐 ¥29/150张、¥39/200张、¥49/250张、¥999/5000张，永久有效。下单重新读取 plans，不以快照硬编码权益。新通用账户免费生图次数为 0，不能套用其他产品试用。
健康 version=0.10.14 是基础兼容协议号，不是实际服务入口版本。
真实模型是 gpt-image-2.5-ext，1K、每任务 n=1，服务端选择；gemini-personal-sunburst / photo-retouch-sunburst 是兼容标识，旧上游回退已禁用。本目录不提供视频或其他目录模型已适配的承诺。

## 凭证与头部

账户 install_secret 为43位 URL-safe 字符；付费 Skill 凭证格式为 mpskill_<32位小写hex>_<43位URLsafe>。两者均为用户运行时私有凭证，不是供应商 Key。
延续现有 Skill 私有状态、设备记忆和微信恢复；后端无法确认所有宿主统一保存于某个本机文件路径，不要猜路径或读取其他项目凭证。新安装身份只创建一次，不因新对话、余额不足或恢复失败随意换身份。

| 头部 | 取值 |
|---|---|
| Authorization | 账户操作用 Bearer <原账户凭证>，付费任务用 Bearer <Skill凭证> |
| X-Skill-Source | 当前 Skill 真实稳定 slug，不能全部冒充 gemini |
| X-Skill-Channel | skillhub / workbuddy_skill / workbuddy_expert |
| X-Skill-Device | desktop / mobile / cloud / unknown，填写真实环境 |
| Content-Type | JSON 请求为 application/json |
| Idempotency-Key | 生成提交为16–100位稳定任务标识，重试沿用原值 |

凭证不得进入仓库、公开包、日志或回答。原生客户端不伪造 Origin；网页保留本站 Origin、X-Membership-Request: 1 和安全 Cookie 校验。API POST 不自动追随跳转。

## 账户关联与付费

以下路径均在 /platform-api/gemini 下：

| 方法与路径 | 约定 |
|---|---|
| POST /quick-entry | 不带Bearer，正文 {install_secret: 原安装身份}；返回 registration、checkout 或 ready；有url时打开服务器签发的链接 |
| POST /quick-entry/status | 不带Bearer，原install_secret；返回 registration_pending 或 registered，后者含额度 |
| POST /membership-link | 账户Bearer，正文{}；返回该账户短期付款链接 |
| GET /balance | 账户Bearer；remaining_uses为总可用次数，不把balance/shared_uses/legacy_uses再相加 |
| POST /skill-key | 账户Bearer，正文{}；state=ready才保存key，pending_payment/unavailable不表示可生成 |
| POST /skill-key/bound | 账户Bearer，正文{key: 已安全保存的Skill凭证}；先保存再确认 |

微信扫码使用已有页面和回调；保留 /quick-entry 的原安装身份，扫码后查询原身份状态，再读余额并取得 Skill 凭证。registered不表示已付款。
client.py 的 temporary_link() 仅将服务器返回的可信本站会员/绑定链接映射至临时域名，保留路径、query、fragment；不自造ticket/entry。裸付费页可查看套餐，不能替代账户关联。
参考客户端不实现每种宿主的账户恢复框架；必须沿用项目已有流程，缺凭证不能重建并冒充原账户。没有新增通用开发者Key。

## 生图任务

普通付费文字分支请求示例，用户真实确认后再提交：

```json
{
  "prompt": "无品牌白色马克杯放在自然光办公桌上，画面无文字",
  "role": "general",
  "platform": "general",
  "slot": "poster",
  "size": "1024x1024",
  "confirmed": true,
  "image_engine": "gemini-personal-sunburst",
  "gemini_trial_intent": "paid",
  "image_retention": {"policy": "gateway-delivery-delete/1"}
}
```

prompt为1–6000字。size支持1024x1024、1536x1024、1024x1536，映射1:1、3:2、2:3的1K请求，最终像素以实际PNG为准。不要给网关添加供应商model/n/quality来绕过资源和计费。
参考图编辑沿用photo-retouch-sunburst/既有授权路径，1–3张PNG/JPEG，保留输入校验与照片/未成年人授权，不硬编码consent=true；text_job()只构造付费文字分支。

| 方法与路径 | 行为 |
|---|---|
| POST /skill-jobs | Skill Bearer + Idempotency-Key + 确认后的正文 |
| GET /jobs/by-key/{原幂等标识} | 查原任务，不提交自己计算的哈希 |
| GET /jobs/{id} | 原任务UUID，读取status等 |
| GET /jobs/{id}/image | 成功任务PNG二进制；保存真实收到的图片再交付 |

任务返回id用于后续查询。succeeded且取得图片后才报告完成；pending/needs_review查询原任务。交付后服务端可能删除图片，下载地址不是永久素材库。
同键不重复扣费，不同键是独立任务。超时不代表失败，不换新键重发。批量按任务分别计费；本次未测真实并发容量。
供应商失败/未知状态由既有核查及退还路径处理，不能自行改余额或声称所有未知任务立即自动退款。

错误：401恢复原身份；402付费；403检查权限/来源；429退避保留原任务；503/超时先查原任务、不切旧资源。GatewayError.status保留HTTP状态，不打印任意错误体或凭证。

## 使用与测试

```python
from client import Client, text_job

# 运行时注入已有私有凭证，不在公开代码中填入值。
c = Client("your-real-skill-slug", "skillhub",
           account_secret=runtime_account_secret, skill_key=runtime_skill_key)
quota = c.balance()
# job_key与正文先按原任务私有持久化，重试从记录恢复。
body = text_job(user_prompt, job_key, confirmed=user_confirmed)
task = c.submit(body, job_key)
state = c.job(task["id"])
if state.get("status") == "succeeded":
    png_bytes = c.image(task["id"])
    # 保存到用户可访问文件后交付，不打印凭证/票据。
```

python client.py只读取公开健康，无生成；python -m unittest discover -s . -p "test_*.py"全用Mock。
12项客户端测试通过；本地 .60→.59→.58→旧层合成数据库HTTP链验证取并绑定Skill凭证、提交、同键去重、只扣一次、原键查询与PNG下载，上游为Mock。
临时域名health/plans为200，匿名balance/jobs为401；客户端实际公开健康请求成功。
真实上游调用0次、无真实客户凭证/数据。未验真人微信授权、真实核款、真实生成质量、全部宿主或完整当前链独立部署。只更新仓库，没有更改生产业务。

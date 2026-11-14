# Temu1.1.11/1.0.25：只读核查结果

2026-11-14T22:47:48+08:00。沿事件`evt-abdeb87313b792ebd7aed10e3acf5548fb1349b7c30eb6cb9524fe9595c3813f`原claim`2455e1fe-e43b-492a-9d7d-12e0b070a579`核查，不重复认领。**不能定论“线上正在运行的两版只给用户主域链接”。**当前能证明的是两份本机交付候选的渠道及静态行为。

## 1. 来源与两个版本的真实对应

原通知source_ref `a28bc781e59803713181f29b497ddcee78fb36e6`误填文件blob，不能当commit使用；已核Muse修正提交`36e0d2ebaf0cf44785993665fc22c725319526b7`与该blob内容相同，不把旧commit pin说成通过。

实时检查私有`Haihe2026/Skillhub@3f02beb3e207ce319981a29e08fabd2f7d7b5177`：完整主树372项未截断，branches仅main，tags/Release均0；17个Temu ZIP逐一校验Gitblob并扫描中央目录/文本，无内嵌ZIP、未找到1.1.11或1.0.25。这个结论限当前可访问主树/分支/tag/Release，不宣称所有历史删除版本都不存在；旧1.1.3/1.0.18没有替代所问版本。

在本机`Temu商家生图skill`交付目录另找到两份确切ZIP，已只读固定副本：

| 本机候选 | 渠道实证 | 字节 / SHA256 |
|---|---|---|
| 1.1.11 | WorkBuddy团队技能版；channel.json、SKILL及telemetry均一致 | 76358B；`6321095d34935327de56dbd2582f8f9d679633241c5bb7d7468fb0f458cc903e` |
| 1.0.25 | WorkBuddy团队专家版；plugin expertType=agent、agents/skills嵌套、channel.json及telemetry一致 | 80849B；`d6647419faad1edcfd4128e313cc6910e368c09e7f66a869cbb9c06c04644211` |

不是按版本号段或文件名猜渠道。这是本机候选分类，不是平台当前上传身份验证；未将私有源码或ZIP复制到公共仓库。

## 2. 付费页和注册页：默认主域，但没有强制只主域

两包默认API使用`https://myplanestore.com`，Temu付费页路径为`/membership/temu/`，注册页为`/membership/temu/register/`。**两包均允许精确主机myplanestore.com和aistore.zhaopintong.com；public_link校验后返回原URL，不统一改写主域。**所以后台若返回合法旧域链接，候选客户端仍可能将旧域原样显示给用户。默认API地址并不能证明实际发出的会员/注册链接一定是主域。

技能1.1.11证据：`service-profile.json:7`、`scripts/transport.py:28–42,117–123,296–306,323–337,358–367,738–748`、`scripts/client.py:50–60`、`scripts/merchant_journey.py:87–96`。专家1.0.25同一相关范围以`skills/temu-image-master/`为根，另有`transport.py:347–374,408–413`账户入口/菜单链路。凭据请求仍禁重定向，不靠30x自动迁移；本次没有执行这些代码或访问业务接口。

## 3. 微信旧域说明

技能1.1.11的`references/wechat-account.md:5`仍写旧域回调，**这处文字未修**；实际OAuth回调域名本次未验证。专家1.0.25的完整27项ZIP里没有`wechat-account.md`，也没有其文本引用，因此不能用它证明技能版第5行已修。专家旁《兼容性检查结果》称支付仅主域，与代码双域放行原返不一致，判断以实际候选代码为准。

## 4. 线上结论缺件

两份旁置台账的SHA都匹配本机候选，但只是打包时本地校验记录：技能《渠道发布记录.json》25–39行及《上传与验证说明.md》15行、专家《本地验证.json》10/33–47行及《兼容性检查结果.md》21–27行均记Mock检查、宿主/真人流程未验、uploaded=false/not_submitted。这不证明今天平台没有上传，也不证明今天上传的就是这些字节。负责人报告线上版本号与包内容身份必须分别记录。

要定论线上行为，仍缺：①当前平台实际上载ZIP的SHA256或可取回原件，以及渠道/版本到该哈希的对应；②该线上流程后端实际签发链接的域名证据（应移除全部ticket/query/fragment）。仅有版本号、默认主域常量或本机包哈希都不足；即便上传SHA一致，现有双域逻辑也不能保证主域唯一。

本条只回答查证问题，不要求现在恢复开发或上传。产品自动化继续暂停；未修改任何原包、执行包内代码或测试、调用业务/上游、付款、部署或写财务。原有产品stage/BOARD/SOP/config保持，不新增AI监测/worker。安全结构化证据：`00-temu-versions-domain-evidence-20261114.json`。

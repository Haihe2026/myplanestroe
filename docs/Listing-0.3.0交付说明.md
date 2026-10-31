# Listing 0.3.0 已部署

实际规则、字段与边界见 SKILL接入契约.md。用户已授权立即部署，独立Listing页及人民币账本已上线，同现有收款二维码、管理员核款方式。

shared入口 /opt/skill-platform/listing-cny-0.3.0/run_shared.py 向下包装 /opt/skill-platform/grok-video-0.1.3/run_paid.py；ops入口 /opt/skill-platform/listing-cny-0.3.0/run_ops.py 包装 /opt/skill-platform/ops-2026-10-28-costs/run_ops.py。未覆盖旧源码、既有页面、已有账本行；新增Listing表与新交易流水记录。新共享核款防复用保护沿原pet guard方式，原人工核款函数的成功和重复语义有合成回归。

增加 /membership/listing/ 与其CSS/JS/条款/免责声明、独立 /auth/wechat/listing.html 和对应登录JS；旧登录页面和脚本未改。扫码沿原状态/身份/设备逻辑，新产品在运行时登记；绑定后原机器凭证继续用。新层桥接旧Wechat.finish(body)与HTTP生命周期finish()的同名冲突，没有修改旧模块。

验证：34项后端合成测试及1项待处理订单复用补充测试（20账务/6 HTTP/2管理员/3跨产品收款保护/3微信身份），12种页面模拟场景；真实上游调用0。实际生成由宿主负责，服务端验证成品结构与完整范围并持久化结算，不声称独立验证商品事实或绝对防复制。明确失败暂占需要管理端核查释放，当前没有自动供应商失败释放或邮件机器人专用Listing适配。用户与额度全站列表未新增Listing余额列；可在Listing订单菜单核款和核查任务。

公开健康/价格200，两域名页面检查200，本人及后台未授权401；三旧通道价格目录及既有页面哈希保持。nginx -t通过，未修改nginx配置、不需reload。真实扫码/宿主/真实付款与核款未测。

备份 /var/backups/myplanestore/listing-cny-0.3.0-20261031-1793460582 。包含服务端shared.db备份、旧ExecStart和价格目录；未将数据库下载。deploy.py --check已执行，实际安装输出deploy-result.txt；public-checks.json记录公开接口检查。

回滚：本机执行 python deploy.py --rollback /var/backups/myplanestore/listing-cny-0.3.0-20261031-1793460582 。先移除本轮新静态页（含独立登录页），finally移除本轮drop-in并重启，健康检查重试；不恢复生产数据库，保留Listing账本以供恢复。未实际回滚生产，不声称回滚演练通过。后续有Listing付费用户时回滚需保留其恢复与核款通道，不得直接丢弃在途权益。

旧0.1.x/0.2.0及需求文件保留；本次不制作或上传任何Skill包。


收尾补丁：会话失效清除旧账户与订单显示；同档同版本待处理订单24小时复用；登记付款后隐藏二维码并显示等待核款，避免重复支付。收尾补丁也已先备份数据库，结果见finish-patch-result.txt。

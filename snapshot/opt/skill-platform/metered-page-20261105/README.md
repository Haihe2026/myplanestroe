# 通用按次付费页 · 已部署 2026-11-05

入口：https://aistore.zhaopintong.com/membership/listing/ 。通过 ?skill=<已登记技能ID> 展示对应服务。统一30分/次，微信关联后每服务首次免费成功交付1次，幂等防补发。旧Listing保留原命名空间、旧余额/订单/赠次和不限修改。未登记项目不会自动套用或生成新试用；生图、Temu、宠物、外贸不变。

## 文件与验证

- metered.py：复用既有Listing事务核心，配置白名单、独立表命名空间、结构化交付核验、凭证票据保留。
- services.json：生产服务目录（当前为旧Listing桥接）；service.example.json为未发布示例。
- listing_trial_gate.py：旧Listing免费体验增加微信绑定校验，不重置原记录，已用/付费历史保持。
- run_shared.py：新层包装 provider-costs-20261105，不覆盖旧层。
- metered_ops.py、listing-admin.js、redesign_ops.py：既有订单页可汇总新服务订单，沿用后台认证、金额核对与流水防重。
- build_web.py、after/：按服务渲染模板、微信免费领取按钮、扫码后自动开通、分服务待付款订单记录；新条款页。
- test_metered.py / test_routes.py：25项合成SQLite及实际本地HTTP测试；原Listing 35项回归通过。
- test_web.cjs：桌面1440/手机390共10种合成场景；原票据不会换成匿名新票据；无横向溢出。
- deploy.py：路径及源文件哈希preflight，在线SQLite备份与完整性校验，页面备份，新drop-in，重启重试健康检查，失败自动恢复文件和入口；不还原生产账本。

部署备份：/var/backups/myplanestore/metered-page-1793853506 。当前共享入口：/opt/skill-platform/metered-page-20261105/run_shared.py；向下保留成本采集层和完整旧链。数据库在服务器内备份，不随交付和公开镜像提供。

线上公开核对：页面/脚本/条款200；Listing价格30分、免费1次；Gemini与Temu配置200；匿名账户和核款401；未登记新Skill404。主域名首页与管理页仍444，会员页302到备用域；Nginx文件未改。未使用真实客户凭证，没有真实扫码、付款或算力请求；真人微信扫码、各宿主Skill联调及新服务正式登记仍需完成。页面框架已部署不等于所有Skill已升级。

## 回滚

运行 rollback.py（使用既有授权SSH配置）。它先移除本层drop-in并恢复本次页面和后台文件，再重启原服务，健康检查最多25轮。不删除新表、不恢复旧DB覆盖新流水、不改Nginx。自动部署失败也走相同顺序。撤回后的基础链仍是 provider-costs-20261105 → listing-cny-0.4.0。

## 复现

Python执行 `python -m unittest discover -s <本目录> -p 'test_*.py'`；再在 listing-cny-0.4.0 运行原test_*.py。需要同级完整Listing0.4.0源文件，测试全用合成库，不联网。UI测试需Playwright和Chromium，文件开头路径为本机安装路径，异机需改为对应安装位置。接入流程和服务登记方式见 接入说明.md。

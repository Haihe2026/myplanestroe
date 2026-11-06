# 上游资源 · 服务端资产与公开成本目录

核对日期：2026-11-06。Skill统一经过[通用生图网关](../shared-image-temporary/README.md)；Key只留服务器，不提供匿名后台权限。

## 当前已适配生图

- 资产ID aisplice，基础网址 https://www.aisplice.store，适配API根 https://www.aisplice.store/v1。
- 模型gpt-image-2.5-ext，1K、n=1、legacy_fallback=false。
- 普通档公开标价US$0.0065/请求，当前每任务1张。按财务配置汇率7估算约¥0.0455/张，不是实际结算成本或利润保证。
- 登记说明可能写ChatGPT-image-2.5；实际请求以resource_adapter.py的MODEL和new-only-policy.json为准。
- aisplice-universal是另一个通用目录/成本资产登记；当前图片适配解析aisplice。登记enabled且配置凭证不等于所有模型已适配。

| 文件 | 内容 |
|---|---|
| [assets.public.json](assets.public.json) | 两项资产白名单元数据及配置状态，没有Key/尾号/密文 |
| [catalog.json](catalog.json) | 36模型、5类、4会员档公开报价快照 |
| [code-map.json](code-map.json) | 适配、资源策略、凭证解析与成本账本源码位置 |
| [验证记录](../VALIDATION.json) | 已做与未做的验证 |

报价来源 https://www.aisplice.store/zh/models （原请求入口/catalog），采集时间 **2026-11-05T02:17:44.070037+00:00**，price_version=aisplice-public-20261105。本次同步旧快照，没有宣称11月6日重新抓取，也未调用付费模型查价。
保留原计价单位：图片按请求、视频可按秒、文字/Flare/Sunburst按百万token输入输出分别计量。不能把全部条目当US$0.0065/张；例如Flare/Sunburst普通档输入5美元/百万token、输出30美元/百万token。
会员价格及未列参数加价以实际供应商合同/账单为准；scope=public_list_price_parameter_tiers_not_exhaustive，不是完整参数价目或已核账单。

## 成本与开发约束

1. 服务端注册表resolve_for_service()取加密保存的Key，不能把解析结果传给Skill。
2. provider-costs记录接入后站内请求的模型、数量/单位、价格版本及估算成本；不补造历史，不等同整个Key的所有来源消费。
3. 供应商余额/总消费属于账户或Key聚合，不能直接归因某个Skill或用户；估算不能冒充净利润或已结算账单。
4. 新模型须实现服务端适配、授权、速率/预算、任务幂等、失败核查和产品计费。复制目录或enabled=true不会自动完成。
5. 公共仓库只供阅读开发，不放Key、末四位、密文、主密钥、数据库或客户记录；没有新增生产权限或许可授权。

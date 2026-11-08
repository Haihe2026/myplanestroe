# 选品单：跨境产品场景图生成助手（第三轮，B.0 选定）

> 来源：pipeline/research/2026-11-08-round3.md（B.0 调研，10 → 3–5 → 选定 1）。
> 白底助手已放弃（选品太窄），本单为其替代：白底是主图（纯白底），本单是副图/广告图（生活场景），更宽。

- 建议 skill-id：mps-cross-border-scene-generator
- 品类：生图类（不是生图类的不要放进本流水线）
- 优先级：P1
- 目标用户：跨境电商卖家（亚马逊、TikTok Shop、Shopify、Temu）、跨境运营、独立站卖家，帮他们在已有产品图的基础上，快速得到多张生活场景图，用于 Listing 附图、广告素材、社媒内容。
- 核心需求一句话：上传一张产品图 → 得到多张生活场景图（产品保真，场景可换）。
- 主要场景（按需求量排序）：
  1. 亚马逊 Listing 附图：产品在客厅/厨房/办公室等生活场景（提升转化）。
  2. TikTok Shop 商品图/短视频封面：产品在户外/旅行/日常场景。
  3. Shopify 独立站 Banner：产品融入品牌调性场景。
  4. 广告投放素材：Facebook / Google 广告场景图（多版本测点击）。
  5. 节日促销场景：圣诞、黑五、情人节、母亲节主题场景。
  6. 季节场景：春夏/秋冬、户外/室内换季场景。
  7. 使用演示场景：产品正在被使用（手持、穿戴、摆放、操作）。
  8. 礼品场景：产品作为礼物（礼盒、赠送、节日送礼）。
  9. 办公场景：产品在办公桌/会议室/工作台。
  10. 户外运动场景：产品在运动/旅行/露营/健身场景。
- 需求证据（真实来源，均可查证，2026-11-08 检索）：
  - 亚马逊官方口径：卖家论坛官方指引建议每条 Listing 至少 6 张图加 1 条视频；副图（2–8 号位）应展示生活场景、使用演示，每张副图回答一个买家疑虑。主图必须纯白底（RGB 255,255,255）、产品占 85% 以上，副图无白底要求、可用生活场景、文字、道具、人物。来源：Canopy Management《Amazon Product Images That Convert: The 2026 Image Stack》（canopymanagement.com/amazon-product-images-that-convert/，2026-10-13 更新）。
  - 转化数据：填满 7 张以上图片的 Listing，转化率约为只放 3–4 张图的 2.4 倍；策略性规划的生活场景图组合比随意拼凑的转化高 15–25%。来源：goaspi.com《Amazon Lifestyle Images: The Strategic Framework》（goaspi.com/blog/amazon-lifestyle-images-strategy/）。
  - 卖家普遍缺口：多数卖家只用 2–3 张副图，这是品牌审计中最常见的错误之一，每空一个位置就是一次错过回答买家问题、打消购买疑虑、提升转化的机会。来源：flapen.com《Amazon Product Image Requirements 2026》（flapen.com/blog/amazon-image-requirements-2025）。
  - 产品保真是最痛的点（通用 AI 做不到 90% 的地方）：亚马逊官方指引要求图片必须准确呈现产品；AI 生成图改了产品颜色、比例、质感或配件，就会变成退货和差评。Canopy 原文：AI images cause trouble when the product in the picture doesn't match the one in the box, and that shows up in returns and reviews。OpenArt 指南要求：Reject images that change its shape, controls, label, packaging, color, or proportions。Instasize 指南要求：产品必须与主图完全一致——相同形状、相同颜色、相同细节，图片与实物不符是导致退货的原因。
  - 亚马逊官方已亲自下场做场景图：Amazon Ads 于 2024 年 10 月推出 AI Creative Studio（免费），把产品照片转成生活场景图、动态广告视频；A+ Content Manager 也有 AI 场景背景生成。说明平台方认可“产品图变场景图”是卖家的刚性需求。来源：Feedvisor《Product Images - Amazon Seller University》（feedvisor.com/university/product-images/）。
  - GitHub 公开仓库（2026-11-08 搜索）：comfyui-ecommerce-workflows（背景替换 + 生活场景 + 模特试穿 + 详情页排版，对标 Flair AI / Pebblely）；ai-product-photography-skill（生活场景 + 平台主图，MIT-0）；resale-photo-enhancer（背景替换，二手卖家上架图）；ComfyUI 97K stars（产品摄影、背景替换、重打光、生活场景图）。多个项目把生活场景图列为核心能力，说明需求明确。来源链接：https://github.com/xiaoqahax-ui/comfyui-ecommerce-workflows ；https://github.com/beatra-ai/ai-product-photography-skill ；https://github.com/SamurAIGPT/resale-photo-enhancer ；https://github.com/comfyanonymous/ComfyUI
  - SkillHub / WorkBuddy 生图类细分数据：未验到（SkillHub 首页无分类榜单；WorkBuddy 列表页登录墙，2026-11-08 09:02 每日选品简报同口径已确认）。不编数字。
- 主要竞品与差异点：
  - Flair AI / Pebblely / Pixelcut：付费 SaaS，场景图生成，但价格高（按月订阅）、不针对中文卖家、无 WorkBuddy 集成。
  - 通用 AI 生图（GPT / Midjourney）：能生成场景，但产品保真差（变形、logo 错、印字糊），无电商规格。
  - 差异点：产品保真（形状、颜色、印字、logo 不走样）+ 平台场景模板（亚马逊生活图、TikTok 场景、Shopify）+ 同一产品多场景风格一致 + 按张计费（0.20 元/张）+ WorkBuddy 内直接用。
- 相邻自家技能（避免互相抢触发）：
  - 证件照换底助手（mps-id-photo-background）：证件照场景，不重叠（本单是产品场景图）。
  - Grok 一键生图：通用生图，不针对产品保真与电商场景。
  - Listing 优化大师（cross-border-listing-rewriter）：文字改写，不做图。
  - 白底助手（mps-cross-border-white-background）：已放弃，不存在竞争；本单是其升级替代（白底是主图，场景图是副图/广告图）。
  - Teruns Listing Image Set：整套含白底主图，本单是 WorkBuddy 单功能版（场景图）。
- 合规风险：
  - 版权：用户上传的产品图须为自有或有授权，不得用他人产品图生成场景图。
  - 肖像：场景中如含人物，需确保模特形象无肖像权问题（用 AI 生成模特，不用真人照片）。
  - 平台规则：亚马逊/TikTok 对主图有纯白底要求，本单生成的是附图/广告图，不做主图，不违反主图规则；场景图不得虚假宣传（不得把产品 P 到误导性场景）。
  - AI 标识：按平台要求标注 AI 生成（如需）。
- 不做什么：
  - 不做纯白底主图（白底助手已放弃，本单不重复）。
  - 不做证件照（已有证件照换底助手）。
  - 不做模特试穿（服装试穿是另一个技能，本单只做产品场景）。
  - 不做详情页长图（多模块排版是另一个技能，本单只做单张场景图）。
  - 不做视频（产品图转视频是另一个技能）。
  - 不代运营、不接卖家后台、不承诺转化率。

## 备注（不写进正式选品单，Codex 按 A.5 处理）

- 定价：生图类统一定价 0.20 元/张（LI 2026-11-07 定），支付页面固定 myplanestore.com 通用付费页。
- 免费试用次数：由 LI 定。
- 车道：走 fast 车道（只用现有共享生图接口，不需后端蒙版补丁），避免白底 blocked 的覆辙。
- 技术复用：白底助手已验证的蒙版/去背思路可复用（先抠产品，再放进场景），不从零开始。

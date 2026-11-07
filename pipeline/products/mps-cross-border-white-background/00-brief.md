# 选品单：跨境产品图换白底助手

- 建议 skill-id：mps-cross-border-white-background
- 品类：生图类（不是生图类的不要放进本流水线）
- 优先级：P1
- 状态：全新选品，未开发过。本单为流水线第二轮候选第一名。
- 目标用户：跨境电商卖家（亚马逊、TikTok Shop、Walmart、Shopify/Etsy 店主）、电商运营与美工；在上架新品、修复被压制的主图时，需要一张符合平台规范的纯白底主图，但手头只有普通产品照或背景不合规的旧图。
- 核心需求一句话：上传一张产品图 → 得到符合目标平台规范的纯白底主图（去背换纯白 RGB 255,255,255 + 商品占比 + 尺寸一次对齐）。
- 主要场景（按需求量排序）：
  1. 亚马逊新品上架主图：主图必须是纯白底（RGB 255,255,255），商品占画面 85%
  2. 亚马逊主图被搜索压制后重做：因非白底被压制，换合规白底图解除压制
  3. TikTok Shop 首图换白底：首图建议白底，商品占画面 80%+，无文字水印
  4. Walmart 主图换白底：Walmart 同样要求纯白底主图
  5. Shopify/Etsy 店铺图换白底：店铺商品页统一白底，分类页横向比较
  6. 服装平铺图换白底：服装平铺照换白底主图，不露模特
  7. 透明/浅色/反光商品换白底：玻璃、金属、水晶、白色商品，边缘与反光不抠坏
  8. 带包装产品图换白底：保留包装文字与品牌，只换背景
  9. 旧图翻新换白底：多年前拍的旧产品图，背景发黄/发灰，换纯白底重新上架
  10. 食品/美妆小件换白底：瓶罐、盒装，标签文字保留，商品完整呈现
- 用户原话（真实说法，附来源；英文为亚马逊 Seller Central 论坛卖家原话，括号内为中文大意）：
  1. “i was selling with this white background main image since last 5 months without any prior issue but now suddenly amazon suppressed my listing due to amazon main image policy.”（这张白底主图卖了 5 个月一直没事，亚马逊突然因主图政策压制了我的 listing。）来源：https://sellercentral-europe.amazon.com/seller-forums/discussions/t/45e066f4-b2e0-40da-ac7e-a20c6fb1c6bf?mons_sel_locale=zh_TW
  2. “Even i have tried about ten different white background compliant main images but could not lift this suppression.”（我试了十张不同的合规白底主图，还是解除不了压制。）来源：同上
  3. “now i changed the pack of my product and trying to add the images but they are not uploading saying my main image is not compliant with listing.”（我换了产品包装，想加图，但系统说主图不合规，传不上去。）来源：https://sellercentral.amazon.com/seller-forums/discussions/t/3432aa11-88ef-47ae-b51c-acebcf3357cd?mons_sel_locale=zh_CN
  4. “i talked to internal team they also say that images are not with white background when i am uploading them from my end. and this is happening with all my asins.”（我问了内部团队，他们也说我传的图没有白底，所有 ASIN 都这样。）来源：同上
  5. “I had a listing suppressed because the background wasn't white. It WAS white 255 255 255 white.”（我的 listing 因为背景不是白色被压制了，可它明明就是 255 白。）来源：https://sellercentral.amazon.com/seller-forums/discussions/t/00a45644-544d-4288-b966-a2fabff048bd?mons_sel_locale=zh_TW
  6. “As per the case ID the main image does not have a pure white background (RGB 255, 255, 255). An important distinction — 'no background' (transparent) is not the same as a pure white background.”（按 case 说主图没有纯白底。重要区别：透明底不等于纯白底。）来源：https://sellercentral.amazon.com/seller-forums/discussions/t/ba166ae0-cce1-4ffb-a75d-dedc4d63b715?mons_sel_locale=zh_CN
  7. “All of my car decals are now suppressed because … 'Update the main image to meet listing guidelines. Your main product image must have a pure white background. Submit a compliant image to make your listing visible again.'”（我的车贴全被压制了，亚马逊让更新主图、换纯白底、提交合规图才能恢复显示。）来源：https://sellercentral.amazon.sa/seller-forums/discussions/t/73c92b6f-1919-44f9-9c9a-c641e966645f?mons_sel_locale=zh_CN
  8. “It doesn't get much whiter!”（这已经不能再白了！）来源：同上
  9. “I have some items flagged as a Search Suppressed because 'We believe the main image has a non-pure white background which is not permitted for this product type.'”（有几个商品被标搜索压制，理由是主图不是纯白底。）来源：https://sellercentral-europe.amazon.com/seller-forums/discussions/t/0fac3eae016289233901fb40ed78ca62?mons_sel_locale=zh_TW
  10. “This is the image that is still flagged as 'non pure white background' and I don't know what else to do.”（这张图还被标非纯白底，我不知道还能怎么办。）来源：同上
  11. “I recently had my listings suppressed due to non-compliant main images (not using a pure white background).”（最近我的 listing 因为主图不合规（没用纯白底）被压制了。）来源：https://sellercentral.amazon.ca/seller-forums/discussions/t/3a61ef6f-4ce7-434c-9006-dc6b59ddff4b
  12. “When Amazon specifies a 'White' background, they mean one with RGB values of 255,255,255. You are not going to get that in camera, even shooting on a lightbox; you need to do it in photo editing software.”（亚马逊说的白底就是 RGB 255,255,255，相机里拍不出来，哪怕用灯箱；必须靠修图软件做。）来源：https://sellercentral.amazon.com/seller-forums/discussions/t/59480bf0-59ef-4f02-94f4-51d333e8dfb6
  13. “My images are a white background but 242 of my listings have been suppressed stating I need to upgrade the first image.”（我的图就是白底，但 242 个 listing 被压制了，说要升级首图。）来源：https://sellercentral.amazon.de/seller-forums/discussions/t/b00dfbcd-5097-4cde-99ba-fde1d687a6f3?mons_sel_locale=zh_TW
  14. “I had 4000+ products taken down today because the image is somehow no longer approved.”（今天 4000 多个产品因为图片莫名其妙不合规被下架了。）来源：同上
  15. “Taking the time to photograph every item again will take days and how do I know that will even work.”（每件商品重拍要花好几天，而且我怎么知道重拍就有用。）来源：同上
  16. “Getting to a pure white background would require you to use a photoshop like program, where you can do a background fill, using 255x255 white.”（要做出纯白底得用 Photoshop 这类软件，做 255 白填充。）来源：https://sellercentral.amazon.com/seller-forums/discussions/t/03118dcb3a3b866075961e98c2385ce1?mons_sel_locale=zh_TW
  17. “Pure white background may not be achieved in the photography process. It has to be in the editing process.”（纯白底在拍摄环节做不出来，必须在后期处理里做。）来源：同上
  18. “You should definitely use some kind of software to edit your product photos. In order to make your images comply with Amazon guidelines, you will need to have pure white background and this can be only achieved by additional editing.”（一定要用软件修产品图，要符合亚马逊规范就得是纯白底，只能靠后期处理。）来源：https://sellercentral-europe.amazon.com/seller-forums/discussions/t/ed199c308e96db2b0ad52e3526073df9?mons_sel_locale=zh_TW
- 需求证据（附来源链接）：
  - 亚马逊官方：主图必须是纯白背景（RGB 255,255,255），商品占画面 85%，最长边 500–10,000 像素；不符合会被搜索压制。https://sellercentral.amazon.com/help/hub/reference/external/G75PWC4THA8J269P?locale=zh-TW ；https://sellercentral.amazon.sg/help/hub/reference/external/G201164480?locale=zh-CN
  - 亚马逊上架时自动检查主图：上传主图时自动检查非白底与文字/Logo/水印，发现问题显示 “Issue detected”，可点 Fix image；不合规图片可能导致 listing 被搜索压制。https://sellercentral.amazon.com/seller-forums/discussions/t/00a45644-544d-4288-b966-a2fabff048bd?mons_sel_locale=zh_TW
  - TikTok Shop 官方：首图建议白底，分辨率 >600×600，不得含文字/Logo/水印/边框。https://seller.tiktokglobalshop.com/university/essay?knowledge_id=4008116375979792&default_language=zh-CN ；https://seller-us.tiktok.com/university/essay?knowledge_id=481891871868714
  - Walmart：主图要求纯白底（RGB 255,255,255）。https://www.photta.app/zh/blog/product-image-size-requirements-by-marketplace （对照表引 Walmart 官方规范）
  - 卖家论坛实证：多篇卖家帖反映主图因白底不合规被搜索压制/下架（见上 18 条用户原话，来源为 Amazon Seller Central 各站点论坛）。
  - WorkBuddy 公开数据：未验到（技能榜/专家榜均重定向至登录页），不编同类数量与头部数字。
- 主要竞品与差异点：
  - remove.bg / Photoroom / Claid / Instasize / Plykit：通用去背换白底工具，多有免费版。差异：它们只做通用去背；本技能一次输出平台合规主图（纯白 255 + 占比 + 尺寸 + 无文字水印自查），亚马逊/TikTok/Walmart 分平台预设，WorkBuddy 内对话式一次出图，不用跳应用。来源：https://www.photta.app/zh/blog/best-ai-white-background-product-photo-tools ；https://remover.bg/zh/white-background
  - Photoshop / 美图秀秀：手动修图，要技术、要时间。差异：一句话一次出图，不用修图技能。
  - 亚马逊自带 Fix image：上架时自动检查并提供修正图。差异：只在上架创建时触发，且不一定能生成修正图（生成不了就要自己传合规图）；本技能在上架前就备好合规图，覆盖全平台。
  - 通用 AI（ChatGPT/Gemini）：能去背换白底，有卖家直接用。差异：通用 AI 不保证纯白 255 全幅、不保证 85% 占比与平台尺寸、不做合规自查；本技能把平台规范写成结构化输出与自查，错了直接亏钱的场景要的是合规保证，不是大概像。来源：https://sellercentral.amazon.sa/seller-forums/discussions/t/e1336003-7383-41ea-9971-98d848a77eaf?mons_sel_locale=zh_CN （卖家原话 “Chat GPT or Gemini can do this super quick”）
  - Teruns Listing Image Set：见相邻自家技能。
- 相邻自家技能（避免互相抢触发）：
  - Teruns Listing Image Set（一张产品照出一整套 marketplace 图片）：整套生成（含主图、信息图、场景图等）。本技能只做白底主图一个功能，不做整套；用户要整套转介 Listing Image Set。注意：两者在产品图白底主图上有功能重叠（整套里必然含白底主图），但平台不同（Teruns vs WorkBuddy），WorkBuddy 内无触发冲突；是否在 WorkBuddy 上卖 Teruns 已有能力的单功能版，由负责人定。来源：https://teruns.com/
  - 证件照换底助手：做人物证件照换底，不做产品图；触发词不同（证件照/一寸/二寸 vs 产品图/主图/白底）。
  - 头像定制大师：头像风格化，不做产品图。
  - 老照片修复大师：修老照片画质，不做产品图换底。
  - Grok一键生图：通用文生图，不接真实产品图改底。
  - Listing优化大师：文字类（Listing 文案），无冲突。
  - 边界：只做“真实产品图 → 合规白底主图”（去背换纯白 255 + 占比 + 尺寸对齐 + 合规自查），不做场景图、信息图、多角度生成，不加文字水印。
- 合规风险：（版权、肖像、平台规则、AI 标识）
  - 产品真实性：只换背景，不改产品本身（颜色、形状、配件、包装文字）；改动产品以致与实物不符违反平台规则。
  - 商标/Logo：产品自带的品牌 Logo 属于产品本身，保留；不另外加 Logo、文字、水印、边框。
  - 平台规则：亚马逊/TikTok/Walmart 图片规范会变，以平台现行规则为准；不承诺包过审，最终以平台审核为准。
  - AI 处理标识按平台规则标注；产品图不做留存（首次对话匿名上报按 SOP）。
- 不做什么：
  - 不改产品本身（颜色、形状、配件、包装文字）。
  - 不做生活场景图、信息图、多角度生成（那是 Listing Image Set 的活）。
  - 不加文字、Logo、水印、边框、道具。
  - 不承诺包过审。
  - 首版只做单张，不做批量多 SKU（批量为后续版本）。
- 备注：
  - 价格、免费试用次数由负责人定，不写进选品单；免费试用默认无（按 SOP）。
  - 建议快车道：复用现有共享生图接口与现有账户、计费能力（以 Codex 按 A.5 核实为准）；如需新模型或后端改动，按 SOP 拦停。
  - 与 Teruns Listing Image Set 的整套 vs 单功能关系由负责人确认。
  - WorkBuddy 公开榜单未验到（登录墙），同类数量与头部数据待负责人亲手登录补验。

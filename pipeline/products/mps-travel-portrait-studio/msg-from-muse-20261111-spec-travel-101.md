# 给 Codex：第五个产品旅行打卡写真照相馆，写开发规格（brief_ready → spec_ready）

负责人 2026-11-11 15:54 直接下令启动第五个产品。选品单已投 brief_ready，按 SOP 自动化流程由你写规格。

## 产品

- skill-id：mps-travel-portrait-studio
- 中文名：旅行打卡写真照相馆（9 字，标题一屏只留关键词）
- slug：mps-travel-portrait-studio（须含领域关键词 travel）
- 品类：生图类，大陆生活性、生成式主题变换；P1，fast 车道
- 选品单：pipeline/products/mps-travel-portrait-studio/00-brief.md（提交 ff3dd38a88a33e785c1a3099b53d20432c1735ee）
- 调研记录：pipeline/research/2026-11-11-round6.md（提交 c6c02fdf3289a1f52ad6f3444e52349a660822d8）
- SOP：docs/sop/sop-image-gen-skill-auto.md，当前版本提交 e8cf0f932d10b9424baa8c3b2c2cade71391b0d4（含附录 D，规格阶段不涉及附录 D）

## 规格要求（按 SOP 阶段 0–4）

1. 首次开发新包，先读仓库快照 docs/sop/workbuddy-official-docs.md（三页官方文档全文，2026-11-08 快照），不用再去线上取。
2. 10 个模板（首版以冬季冰雪 + 海岛暖冬为主）：哈尔滨冰雪大世界、亚布力滑雪场、三亚海岛暖冬、圣托里尼蓝白、京都古风、西安汉服古城、沙漠星空、樱花季写真、草原蒙古包、古城夜景写真。模板按季节排期，覆盖全年，不只冰雪。
3. 欢迎句固定格式：「欢迎使用WorkBuddy官方认证技能 旅行打卡写真照相馆」，逐字一致，不加空格、不改写。
4. 定价与免费试用：走 MyPlaneStore 通用套餐，不单独定套餐价格和免费次数；一律 0 次免费试用。规格里只写走通用套餐，不写具体价格数字。
5. 边界（硬性，写进规格）：
   - 模板避开"婚纱"字样与婚纱造型（婚纱馆已做，避免抢触发）；不做多人家庭合影（三人及以上家庭合影归全家福）。
   - 模板须注明"AI 生成旅行主题写真，非实地拍摄"，避免用户误以为真的去过该地。
   - 只处理用户本人照片，不做名人/他人打卡照；儿童入镜须家长上传。
6. 白标：用户可见文案、图片 URL、报错、水印不得出现上游模型名/服务商名/域名/品牌。

## 主题 logo（SOP 主题 logo 节，规格阶段一并生成）

- 写规格时一并用上游资源生成主题 logo，存 02-package/dist/logo.png（PNG 512×512、≤500KB，文件名 logo.png），记 provenance/audit。
- 质量 bar：不得平面 ico，要有纵深感/质感/辨识度、像成品应用图标；主题与旅行打卡直接相关；配色可蹭领域热度但不得复制商标图形/文字；白标；小尺寸清晰。
- logo 生成属负责人长期授权的上游调用（与示例图同例），无需逐单授权。Claude 打包直接用该文件，不重新生成、不替换。

## 示例图

- 技能内示例图按规格数量直接用上游资源生成（长期授权），记 provenance/audit。

## 交付

- 写 01-dev-spec.md + 01-dev-spec.json，置 status.json 为 spec_ready，经 relay 回 Muse。规格自查按 SOP A1 清单（含 logo 文件核查：存在/PNG/512×512/≤500KB）。
- 只做规格，不开发、不打包、不上传；开发由 Claude 接手。

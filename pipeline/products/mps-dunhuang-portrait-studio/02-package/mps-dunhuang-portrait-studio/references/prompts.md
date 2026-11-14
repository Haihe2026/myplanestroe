# 敦煌提示词（仅执行时使用，不对客复述）

先按truth/text/safety/identity顺序拼四基线，真实性第一，再动作动词+视觉参照+锁定句，最后追加已确认细节。总长≤6000字符，超长本地拒绝，不能截断身份或安全约束。客户只提供一张本人图；示例虚构女性、25岁、脸型、肤色不是默认，不把她/女性人称复制给真实用户。禁止模型名/n/quality等新增HTTP字段。

真实性基线（永远第一段）：唯一人物仅来自本人这张已确认原照及已确认的可见特征，人数严格为1；仅按本次选定整套敦煌服饰妆造、动作及场景修改，未授权的身体、身份、事实不改，不凭空添加人物。

文字基线：图中不得出现文字、字母、数字、标牌、品牌或水印；本技能不做本地标题排版。AI生成声明写在方案、交付和画廊，不烧进底图。

安全基线：仅本人知情同意的成年人单人得体写真，无儿童、额外人物、他人标识、身份伪造和历史精确复原承诺，不做证件/婚纱/旗袍/和服/军装需求。

人物身份基线：尽力保留本人五官结构、肤色、自然年龄外观、发际线和体态；按已选套系更换髻式和轻妆，不套任何示例人物的年龄、性别、肤色或文物脸型，不改变性别特征。只能承诺尽力保持，细节差异可能存在。

## 飞天反弹琵琶 `pipa_back`
完整套系：不透短袖舞衣＋分层长裙＋腰带，少量颈饰/臂钏及短飘带，赭红沙金石绿，一髻与轻花饰；琵琶肩背后，勿穿过头颈。
动作：将本人参考照编辑为飞天反弹琵琶，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透短袖舞衣＋分层长裙＋腰带，少量颈饰/臂钏及短飘带，赭红沙金石绿，一髻与轻花饰；琵琶肩背后，勿穿过头颈。 One pear-shaped pipa held behind and just above the back of their shoulders, one hand supporting the clearly visible neck above the head, the other arm making a natural plucking gesture at the strings behind the shoulder. Gentle three-quarter back-side body angle, face turned naturally toward the viewer, plausible shoulder joints, exactly two complete arms and two hands, one instrument. The instrument must read as behind the shoulders, not held in front of the chest, and must not pierce the neck or head. Opaque fitted dance top, layered long skirt, a clear sash, restrained neck and upper-arm jewellery, one short trailing ribbon. Muted vermilion, warm sand gold and verdigris. Original abstract mural-inspired studio backdrop.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：反弹琵琶姿势/手部与乐器细节容易失真，需确认前告知。

## 敦煌壁画仙女 `mural_fairy`
完整套系：不透装饰上衣＋分层长裙＋自然垂落披帛，赭红/石绿/沙金，颈饰和一髻，正面静立，原创莲花几何壁画构成。
动作：将本人参考照编辑为敦煌壁画仙女，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透装饰上衣＋分层长裙＋自然垂落披帛，赭红/石绿/沙金，颈饰和一髻，正面静立，原创莲花几何壁画构成。 A calm front to three-quarter standing portrait, original abstract mural-inspired border patterns and soft lotus-petal ornament behind their, not a replica of any cave mural. An opaque coherent Dunhuang-inspired costume with layered long skirt, matching soft drape, restrained necklace and a small floral forehead motif, one sculpted hair bun. Earth red, muted turquoise, lapis blue and warm ochre with subtle background texture. Keep the face and skin photographic and clean, never cracked or painted like an ancient artefact. This is a poised mural-themed portrait, not the airborne pose of the Mogao scene.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 莫高窟飞天 `mogao_apsara`
完整套系：不透浅色舞衣＋层叠长裙＋可读弧形飘带，轻颈饰/臂饰和一髻；舞姿离地意象，洞窟拱形与原创云纹层次。
动作：将本人参考照编辑为莫高窟飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透浅色舞衣＋层叠长裙＋可读弧形飘带，轻颈饰/臂饰和一髻；舞姿离地意象，洞窟拱形与原创云纹层次。 A graceful anatomically plausible dance pose conveying apsara flight through a gently arched diagonal body line, flowing layered skirt and two clearly continuous looping silk ribbons. Opaque dignified dance top and skirt, restrained necklace and armbands, one coordinated high bun. Original softly lit cave-like studio architecture and indistinct mineral-pigment colour layers, no identifiable copied grotto interior, no clearly depicted second human, deity face or crowd in the backdrop. Face unobstructed; ribbons attach and travel plausibly, never through face, neck, torso or fingers. No Western angel wings or fantasy armour. This is AI art, not a photograph inside the real Mogao caves.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 鸣沙山沙漠飞天 `mingsha_sunset`
完整套系：不透配套上衣＋层叠长裙＋侧后飘帛，金赭石绿，颈饰和稳固发髻；落地静立，沙丘曲线及夕阳逆光。
动作：将本人参考照编辑为鸣沙山沙漠飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透配套上衣＋层叠长裙＋侧后飘帛，金赭石绿，颈饰和稳固发髻；落地静立，沙丘曲线及夕阳逆光。 the person stands with both feet naturally supported in a warm sunset desert composition inspired by the layered curved dunes of Mingsha Mountain. One coherent opaque Dunhuang-inspired dance top and long skirt, a single wind-lifted matching drape, restrained necklace and bun ornaments. Soft raking warm sunlight and fine sand ridges; clean face and believable fabric movement. No water, snow mountains, sea, pyramids or unrelated landmarks, no camels or other people. Scenic artistic background, not a claim of a real location shoot or exact current viewpoint.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 月牙泉夜景飞天 `crescent_night`
完整套系：不透长袖装饰上衣＋长裙＋自然垂帛，暖赭/石绿，颈饰和发髻；落地静立，蓝调夜景与远处月牙形水面。
动作：将本人参考照编辑为月牙泉夜景飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透长袖装饰上衣＋长裙＋自然垂帛，暖赭/石绿，颈饰和发髻；落地静立，蓝调夜景与远处月牙形水面。 A grounded standing portrait at blue hour with a small clearly crescent-shaped water surface in the distant landscape, softly enclosed by curving desert dunes. One opaque coordinated Dunhuang-inspired costume, layered skirt, graceful drape, restrained gold-toned necklace and one sculpted bun. Soft explainable portrait fill light against restrained warm landscape glints. Do not stand in the spring or on heritage structures. Water must be a distant crescent, not a full round lake, sea or waterfall. No invented prominent buildings, other people or camels. An artistic interpretation, not verified real night lighting or exact tourist-site photography.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 敦煌乐舞飞天 `apsara_dance`
完整套系：不透舞衣＋层叠长裙＋短飘带，颈饰/轻臂钏和一髻；双臂舞姿、单足轻抬，默认不持乐器，避免与琵琶套系重复。
动作：将本人参考照编辑为敦煌乐舞飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透舞衣＋层叠长裙＋短飘带，颈饰/轻臂钏和一髻；双臂舞姿、单足轻抬，默认不持乐器，避免与琵琶套系重复。 A grounded Dunhuang-inspired solo dance still with a clear centre of balance, one foot gently lifted, a supple side-turn and two relaxed readable hands with plausible wrist and elbow angles. Opaque costume, layered skirt with a clear waist sash, restrained ornaments and short flowing ribbons, a coherent bun with a small ornament. Original abstract rhythm-like mural patterns on a quiet warm-ochre studio backdrop. Default is empty hands: no instrument, band, accompanying dancer or copied stage-show costume. Differentiate from back-pipa and long water-sleeve scenes through the complete grounded body pose and short ribbon movement.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 飞天水袖舞 `water_sleeves`
完整套系：不透上衣两袖接长绸袖＋落地长裙，米白赭红石绿，颈饰/一髻；两袖各有清楚弧线，现代舞台艺术演绎。
动作：将本人参考照编辑为飞天水袖舞，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透上衣两袖接长绸袖＋落地长裙，米白赭红石绿，颈饰/一髻；两袖各有清楚弧线，现代舞台艺术演绎。 A modern Dunhuang-inspired stage water-sleeve dance portrait, explicitly an artistic stage interpretation rather than reconstruction of a cave dance. Two long opaque silk sleeve extensions visibly connect to the two garment sleeves, each forms its own readable arc; both hands and the original two arms remain anatomically coherent. The face is unobstructed, the layered long skirt reaches the floor, a stable grounded pose and coordinated bun/necklace complete the costume. Muted ivory, vermilion and turquoise against a simple dark warm studio backdrop. Sleeves are fabric, not flowing water, extra arms or tight wraps around the neck.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 敦煌古装仕女 `dunhuang_lady`
完整套系：不透宽袖上衣＋层叠长裙＋自然披帛，少量花簪/额饰及一髻；温婉坐姿双脚支撑，原创壁画边饰，非精确唐制。
动作：将本人参考照编辑为敦煌古装仕女，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透宽袖上衣＋层叠长裙＋自然披帛，少量花簪/额饰及一髻；温婉坐姿双脚支撑，原创壁画边饰，非精确唐制。 A dignified stationary adult portrait using the requested Dunhuang courtly-lady costume theme; preserve the subject identity and visible sex characteristics inspired generally by Dunhuang mural culture: broad-sleeved opaque upper garment, a layered long skirt, naturally falling silk drape, restrained hair bun, one small flower pin and optional tiny floral forehead ornament. A calm seated pose on a simple unbranded stool, hands relaxed and visible, feet naturally supported. Warm ochre, muted earth-red and blue-green geometric mural border in an original studio composition. No airborne motion, no wings or wedding crown. Do not present this as a precise Tang dynasty costume or exact reconstruction of the Five Dynasties donor figures; do not merely reuse the reference Hanfu outfit.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 沙漠驼队飞天 `camel_caravan`
完整套系：不透上衣＋长裙＋披帛，颈饰与发髻，落地站立；沙金夕照，远景小驼队无骑手、导游和游客。
动作：将本人参考照编辑为沙漠驼队飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透上衣＋长裙＋披帛，颈饰与发髻，落地站立；沙金夕照，远景小驼队无骑手、导游和游客。 A single grounded adult foreground portrait in an opaque coordinated Dunhuang-inspired costume with flowing long skirt and a modest drape, restrained jewellery and a clear bun. In the distance, three small camels travel in a line along a curved desert ridge in warm late-afternoon light. Each camel has believable legs, humps, scale and occlusion; they carry no riders. Exactly one human in the whole image: no camel driver, tourist, rider, companion or crowd. Clothing never tangles with animals. Original artistic scenic composition, not a photograph of a real tour.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

## 星空沙漠飞天 `starry_desert`
完整套系：不透深蓝石绿舞衣＋长裙＋飘带，轻颈饰/臂饰及一髻；落地飘带姿态、深蓝星空和沙丘，绝不加月牙泉水面。
动作：将本人参考照编辑为星空沙漠飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。
视觉参照：不透深蓝石绿舞衣＋长裙＋飘带，轻颈饰/臂饰及一髻；落地飘带姿态、深蓝星空和沙丘，绝不加月牙泉水面。 A grounded adult portrait with a graceful flowing-ribbon pose and an opaque coordinated Dunhuang-inspired dance top and long skirt. A broad distant desert dune silhouette beneath a restrained clear star field, deep indigo, warm sand gold and muted turquoise. Believable soft portrait light keeps their face natural and legible. No crescent spring or other water, no camels, buildings, giant planets or other people; no supernatural glow or wings. Modern composite artistic scene, not an astronomical measurement, exact Milky Way position or real location photograph.
锁定：锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。
效果局限：艺术创作，服饰/脸部/舞姿细节可能存在差异，非实拍或考古复原。

实际执行始终优先本人确认的原照/身份，不改变性别特征，不以“男装/仙女”把人换成另一张脸。任一变化需先失效三许可并重规划；已提交未知不得靠改prompt重发。每次只改一件事，需要重新制作先说明可能再计费。
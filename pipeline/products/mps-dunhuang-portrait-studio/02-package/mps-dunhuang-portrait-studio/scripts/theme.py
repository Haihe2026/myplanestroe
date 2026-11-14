"""Pure local Dunhuang scene routing and prompt contracts (Python 3.7+).

No file, network, account, telemetry or image-generation side effects.
Scene data follows the approved 01-dev-spec; customer identity is never inferred.
"""
import re

SERIES = '敦煌主题艺术写真'
DISCLOSURE = 'AI 生成敦煌写真，非实拍'
PROMPT_MAX_CHARS = 6000


SCENES = {'pipa_back': ('敦煌主题艺术写真',
               '飞天反弹琵琶',
               'portrait',
               '不透短袖舞衣＋分层长裙＋腰带，少量颈饰/臂钏及短飘带，赭红沙金石绿，一髻与轻花饰；琵琶肩背后，勿穿过头颈。 One pear-shaped pipa held behind and '
               'just above the back of their shoulders, one hand supporting the clearly visible neck above '
               'the head, the other arm making a natural plucking gesture at the strings behind the '
               'shoulder. Gentle three-quarter back-side body angle, face turned naturally toward the '
               'viewer, plausible shoulder joints, exactly two complete arms and two hands, one instrument. '
               'The instrument must read as behind the shoulders, not held in front of the chest, and must '
               'not pierce the neck or head. Opaque fitted dance top, layered long skirt, a clear sash, '
               'restrained neck and upper-arm jewellery, one short trailing ribbon. Muted vermilion, warm '
               'sand gold and verdigris. Original abstract mural-inspired studio backdrop.',
               '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
               '不透短袖舞衣＋分层长裙＋腰带，少量颈饰/臂钏及短飘带，赭红沙金石绿，一髻与轻花饰；琵琶肩背后，勿穿过头颈。',
               'art'),
 'mural_fairy': ('敦煌主题艺术写真',
                 '敦煌壁画仙女',
                 'portrait',
                 '不透装饰上衣＋分层长裙＋自然垂落披帛，赭红/石绿/沙金，颈饰和一髻，正面静立，原创莲花几何壁画构成。 A calm front to three-quarter standing '
                 'portrait, original abstract mural-inspired border patterns and soft lotus-petal ornament '
                 'behind the subject, not a replica of any cave mural. An opaque coherent Dunhuang-inspired '
                 'costume with layered long skirt, matching soft drape, restrained necklace and a small '
                 'floral forehead motif, one sculpted hair bun. Earth red, muted turquoise, lapis blue and '
                 'warm ochre with subtle background texture. Keep the face and skin photographic and clean, '
                 'never cracked or painted like an ancient artefact. This is a poised mural-themed portrait, '
                 'not the airborne pose of the Mogao scene.',
                 '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                 '不透装饰上衣＋分层长裙＋自然垂落披帛，赭红/石绿/沙金，颈饰和一髻，正面静立，原创莲花几何壁画构成。',
                 'art'),
 'mogao_apsara': ('敦煌主题艺术写真',
                  '莫高窟飞天',
                  'portrait',
                  '不透浅色舞衣＋层叠长裙＋可读弧形飘带，轻颈饰/臂饰和一髻；舞姿离地意象，洞窟拱形与原创云纹层次。 A graceful anatomically plausible dance '
                  'pose conveying apsara flight through a gently arched diagonal body line, flowing layered '
                  'skirt and two clearly continuous looping silk ribbons. Opaque dignified dance top and '
                  'skirt, restrained necklace and armbands, one coordinated high bun. Original softly lit '
                  'cave-like studio architecture and indistinct mineral-pigment colour layers, no '
                  'identifiable copied grotto interior, no clearly depicted second human, deity face or '
                  'crowd in the backdrop. Face unobstructed; ribbons attach and travel plausibly, never '
                  'through face, neck, torso or fingers. No Western angel wings or fantasy armour. This is '
                  'AI art, not a photograph inside the real Mogao caves.',
                  '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                  '不透浅色舞衣＋层叠长裙＋可读弧形飘带，轻颈饰/臂饰和一髻；舞姿离地意象，洞窟拱形与原创云纹层次。',
                  'art'),
 'mingsha_sunset': ('敦煌主题艺术写真',
                    '鸣沙山沙漠飞天',
                    'portrait',
                    '不透配套上衣＋层叠长裙＋侧后飘帛，金赭石绿，颈饰和稳固发髻；落地静立，沙丘曲线及夕阳逆光。 the person stands with both feet '
                    'naturally supported in a warm sunset desert composition inspired by the layered curved '
                    'dunes of Mingsha Mountain. One coherent opaque Dunhuang-inspired dance top and long '
                    'skirt, a single wind-lifted matching drape, restrained necklace and bun ornaments. Soft '
                    'raking warm sunlight and fine sand ridges; clean face and believable fabric movement. '
                    'No water, snow mountains, sea, pyramids or unrelated landmarks, no camels or other '
                    'people. Scenic artistic background, not a claim of a real location shoot or exact '
                    'current viewpoint.',
                    '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                    '不透配套上衣＋层叠长裙＋侧后飘帛，金赭石绿，颈饰和稳固发髻；落地静立，沙丘曲线及夕阳逆光。',
                    'art'),
 'crescent_night': ('敦煌主题艺术写真',
                    '月牙泉夜景飞天',
                    'portrait',
                    '不透长袖装饰上衣＋长裙＋自然垂帛，暖赭/石绿，颈饰和发髻；落地静立，蓝调夜景与远处月牙形水面。 A grounded standing portrait at blue '
                    'hour with a small clearly crescent-shaped water surface in the distant landscape, '
                    'softly enclosed by curving desert dunes. One opaque coordinated Dunhuang-inspired '
                    'costume, layered skirt, graceful drape, restrained gold-toned necklace and one sculpted '
                    'bun. Soft explainable portrait fill light against restrained warm landscape glints. Do '
                    'not stand in the spring or on heritage structures. Water must be a distant crescent, '
                    'not a full round lake, sea or waterfall. No invented prominent buildings, other people '
                    'or camels. An artistic interpretation, not verified real night lighting or exact '
                    'tourist-site photography.',
                    '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                    '不透长袖装饰上衣＋长裙＋自然垂帛，暖赭/石绿，颈饰和发髻；落地静立，蓝调夜景与远处月牙形水面。',
                    'art'),
 'apsara_dance': ('敦煌主题艺术写真',
                  '敦煌乐舞飞天',
                  'portrait',
                  '不透舞衣＋层叠长裙＋短飘带，颈饰/轻臂钏和一髻；双臂舞姿、单足轻抬，默认不持乐器，避免与琵琶套系重复。 A grounded Dunhuang-inspired solo '
                  'dance still with a clear centre of balance, one foot gently lifted, a supple side-turn '
                  'and two relaxed readable hands with plausible wrist and elbow angles. Opaque costume, '
                  'layered skirt with a clear waist sash, restrained ornaments and short flowing ribbons, a '
                  'coherent bun with a small ornament. Original abstract rhythm-like mural patterns on a '
                  'quiet warm-ochre studio backdrop. Default is empty hands: no instrument, band, '
                  'accompanying dancer or copied stage-show costume. Differentiate from back-pipa and long '
                  'water-sleeve scenes through the complete grounded body pose and short ribbon movement.',
                  '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                  '不透舞衣＋层叠长裙＋短飘带，颈饰/轻臂钏和一髻；双臂舞姿、单足轻抬，默认不持乐器，避免与琵琶套系重复。',
                  'art'),
 'water_sleeves': ('敦煌主题艺术写真',
                   '飞天水袖舞',
                   'portrait',
                   '不透上衣两袖接长绸袖＋落地长裙，米白赭红石绿，颈饰/一髻；两袖各有清楚弧线，现代舞台艺术演绎。 A modern Dunhuang-inspired stage '
                   'water-sleeve dance portrait, explicitly an artistic stage interpretation rather than '
                   'reconstruction of a cave dance. Two long opaque silk sleeve extensions visibly connect '
                   'to the two garment sleeves, each forms its own readable arc; both hands and the original '
                   'two arms remain anatomically coherent. The face is unobstructed, the layered long skirt '
                   'reaches the floor, a stable grounded pose and coordinated bun/necklace complete the '
                   'costume. Muted ivory, vermilion and turquoise against a simple dark warm studio '
                   'backdrop. Sleeves are fabric, not flowing water, extra arms or tight wraps around the '
                   'neck.',
                   '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                   '不透上衣两袖接长绸袖＋落地长裙，米白赭红石绿，颈饰/一髻；两袖各有清楚弧线，现代舞台艺术演绎。',
                   'art'),
 'dunhuang_lady': ('敦煌主题艺术写真',
                   '敦煌古装仕女',
                   'portrait',
                   '不透宽袖上衣＋层叠长裙＋自然披帛，少量花簪/额饰及一髻；温婉坐姿双脚支撑，原创壁画边饰，非精确唐制。 A dignified stationary adult portrait '
                   'using the requested Dunhuang courtly-lady costume theme; preserve the subject identity '
                   'and visible sex characteristics inspired generally by Dunhuang mural culture: '
                   'broad-sleeved opaque upper garment, a layered long skirt, naturally falling silk drape, '
                   'restrained hair bun, one small flower pin and optional tiny floral forehead ornament. A '
                   'calm seated pose on a simple unbranded stool, hands relaxed and visible, feet naturally '
                   'supported. Warm ochre, muted earth-red and blue-green geometric mural border in an '
                   'original studio composition. No airborne motion, no wings or wedding crown. Do not '
                   'present this as a precise Tang dynasty costume or exact reconstruction of the Five '
                   'Dynasties donor figures; do not merely reuse the reference Hanfu outfit.',
                   '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                   '不透宽袖上衣＋层叠长裙＋自然披帛，少量花簪/额饰及一髻；温婉坐姿双脚支撑，原创壁画边饰，非精确唐制。',
                   'art'),
 'camel_caravan': ('敦煌主题艺术写真',
                   '沙漠驼队飞天',
                   'portrait',
                   '不透上衣＋长裙＋披帛，颈饰与发髻，落地站立；沙金夕照，远景小驼队无骑手、导游和游客。 A single grounded adult foreground portrait '
                   'in an opaque coordinated Dunhuang-inspired costume with flowing long skirt and a modest '
                   'drape, restrained jewellery and a clear bun. In the distance, three small camels travel '
                   'in a line along a curved desert ridge in warm late-afternoon light. Each camel has '
                   'believable legs, humps, scale and occlusion; they carry no riders. Exactly one human in '
                   'the whole image: no camel driver, tourist, rider, companion or crowd. Clothing never '
                   'tangles with animals. Original artistic scenic composition, not a photograph of a real '
                   'tour.',
                   '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                   '不透上衣＋长裙＋披帛，颈饰与发髻，落地站立；沙金夕照，远景小驼队无骑手、导游和游客。',
                   'art'),
 'starry_desert': ('敦煌主题艺术写真',
                   '星空沙漠飞天',
                   'portrait',
                   '不透深蓝石绿舞衣＋长裙＋飘带，轻颈饰/臂饰及一髻；落地飘带姿态、深蓝星空和沙丘，绝不加月牙泉水面。 A grounded adult portrait with a '
                   'graceful flowing-ribbon pose and an opaque coordinated Dunhuang-inspired dance top and '
                   'long skirt. A broad distant desert dune silhouette beneath a restrained clear star '
                   'field, deep indigo, warm sand gold and muted turquoise. Believable soft portrait light '
                   'keeps their face natural and legible. No crescent spring or other water, no camels, '
                   'buildings, giant planets or other people; no supernatural glow or wings. Modern '
                   'composite artistic scene, not an astronomical measurement, exact Milky Way position or '
                   'real location photograph.',
                   '保留本人脸部、肤色、自然年龄外观与性别特征；髻式、颈饰和轻妆随当前完整套系一致，不继承示例人物的年龄、性别或面容。',
                   '不透深蓝石绿舞衣＋长裙＋飘带，轻颈饰/臂饰及一髻；落地飘带姿态、深蓝星空和沙丘，绝不加月牙泉水面。',
                   'art')}

LOOKS = {'pipa_back': {'label': '飞天反弹琵琶整套服饰妆发', 'profile': '不透短袖舞衣＋分层长裙＋腰带，少量颈饰/臂钏及短飘带，赭红沙金石绿，一髻与轻花饰；琵琶肩背后，勿穿过头颈。'},
 'mural_fairy': {'label': '敦煌壁画仙女整套服饰妆发', 'profile': '不透装饰上衣＋分层长裙＋自然垂落披帛，赭红/石绿/沙金，颈饰和一髻，正面静立，原创莲花几何壁画构成。'},
 'mogao_apsara': {'label': '莫高窟飞天整套服饰妆发', 'profile': '不透浅色舞衣＋层叠长裙＋可读弧形飘带，轻颈饰/臂饰和一髻；舞姿离地意象，洞窟拱形与原创云纹层次。'},
 'mingsha_sunset': {'label': '鸣沙山沙漠飞天整套服饰妆发', 'profile': '不透配套上衣＋层叠长裙＋侧后飘帛，金赭石绿，颈饰和稳固发髻；落地静立，沙丘曲线及夕阳逆光。'},
 'crescent_night': {'label': '月牙泉夜景飞天整套服饰妆发', 'profile': '不透长袖装饰上衣＋长裙＋自然垂帛，暖赭/石绿，颈饰和发髻；落地静立，蓝调夜景与远处月牙形水面。'},
 'apsara_dance': {'label': '敦煌乐舞飞天整套服饰妆发', 'profile': '不透舞衣＋层叠长裙＋短飘带，颈饰/轻臂钏和一髻；双臂舞姿、单足轻抬，默认不持乐器，避免与琵琶套系重复。'},
 'water_sleeves': {'label': '飞天水袖舞整套服饰妆发', 'profile': '不透上衣两袖接长绸袖＋落地长裙，米白赭红石绿，颈饰/一髻；两袖各有清楚弧线，现代舞台艺术演绎。'},
 'dunhuang_lady': {'label': '敦煌古装仕女整套服饰妆发', 'profile': '不透宽袖上衣＋层叠长裙＋自然披帛，少量花簪/额饰及一髻；温婉坐姿双脚支撑，原创壁画边饰，非精确唐制。'},
 'camel_caravan': {'label': '沙漠驼队飞天整套服饰妆发', 'profile': '不透上衣＋长裙＋披帛，颈饰与发髻，落地站立；沙金夕照，远景小驼队无骑手、导游和游客。'},
 'starry_desert': {'label': '星空沙漠飞天整套服饰妆发', 'profile': '不透深蓝石绿舞衣＋长裙＋飘带，轻颈饰/臂饰及一髻；落地飘带姿态、深蓝星空和沙丘，绝不加月牙泉水面。'}}

VALID_LOOKS = frozenset(LOOKS)

BASELINES = ('真实性基线（永远第一段）：唯一人物仅来自本人这张已确认原照及已确认的可见特征，人数严格为1；仅按本次选定整套敦煌服饰妆造、动作及场景修改，未授权的身体、身份、事实不改，不凭空添加人物。',
 '文字基线：图中不得出现文字、字母、数字、标牌、品牌或水印；本技能不做本地标题排版。AI生成声明写在方案、交付和画廊，不烧进底图。',
 '安全基线：仅本人知情同意的成年人单人得体写真，无儿童、额外人物、他人标识、身份伪造和历史精确复原承诺，不做证件/婚纱/旗袍/和服/军装需求。',
 '人物身份基线：尽力保留本人五官结构、肤色、自然年龄外观、发际线和体态；按已选套系更换髻式和轻妆，不套示例的年龄、性别、肤色或文物脸型，不改变性别特征。只能承诺尽力保持，细节差异可能存在。')

ACTIONS = {'pipa_back': '将本人参考照编辑为飞天反弹琵琶，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'mural_fairy': '将本人参考照编辑为敦煌壁画仙女，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'mogao_apsara': '将本人参考照编辑为莫高窟飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'mingsha_sunset': '将本人参考照编辑为鸣沙山沙漠飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'crescent_night': '将本人参考照编辑为月牙泉夜景飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'apsara_dance': '将本人参考照编辑为敦煌乐舞飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'water_sleeves': '将本人参考照编辑为飞天水袖舞，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'dunhuang_lady': '将本人参考照编辑为敦煌古装仕女，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'camel_caravan': '将本人参考照编辑为沙漠驼队飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。',
 'starry_desert': '将本人参考照编辑为星空沙漠飞天，只生成一张；保留自然外貌，落实本次已确认的一套服饰妆发。'}

LOCK = '锁定本人原照SHA、可见特征、当前整套服饰妆发、人数1、已确认构图与画幅；无额外人物和文字，不套示例人脸；不重用客户上一方案许可。'

# First match within a level; the levels themselves determine precedence.
# The explicit mural subject wins over its incidental Mogao location; water wins
# over incidental stars in the Crescent Spring request.
_SPECIFIC = (
    ('pipa_back', ('反弹琵琶', '背弹琵琶', '琵琶造型', 'pipa_back', 'back pipa')),
    ('water_sleeves', ('飞天水袖', '水袖舞', '水袖', '长袖舞', 'water_sleeves', 'water sleeve')),
    ('mural_fairy', ('壁画仙女', '壁画配色', '敦煌壁画', 'mural_fairy', 'mural fairy')),
    ('dunhuang_lady', ('敦煌古装仕女', '敦煌仕女', '古装仕女', '供养人服饰', 'dunhuang_lady')),
    ('camel_caravan', ('驼队', '沙漠骆驼', '骆驼背景', 'camel_caravan', 'camel caravan')),
)
_LOCATION = (
    ('crescent_night', ('月牙泉', '泉边飞天', 'crescent_night', 'crescent spring')),
    ('mogao_apsara', ('莫高窟', '洞窟飞天', '飞天飘带', 'mogao_apsara', 'mogao')),
    ('starry_desert', ('星空', '银河沙漠', '星夜', 'starry_desert', 'starry desert')),
    ('mingsha_sunset', ('鸣沙山', '沙漠落日', '沙丘飞天', 'mingsha_sunset', 'mingsha')),
    ('apsara_dance', ('敦煌乐舞', '飞天乐舞', '乐舞写真', '乐舞', 'apsara_dance')),
)
_BOUNDARIES = (
    ('out_of_scope_child', ('儿童', '未成年', '孩子', '宝宝', '小孩', '女儿', '儿子', 'child', 'baby')),
    ('out_of_scope_people', ('双人', '多人', '两个人', '两人', '我们俩', '情侣', '闺蜜', '合影', '亲子', '全家福', '全家',
                            '加驼夫', '加游客', '加向导', '和驼夫', '和游客', '伴舞')),
    ('out_of_scope_wedding', ('婚纱', '婚服', '婚礼', '秀禾', '凤冠霞帔', 'wedding', 'bridal')),
    ('out_of_scope_outfit', ('旗袍', '和服', '军装', '军服', '制服军衔', 'kimono', 'qipao', 'military uniform')),
    ('out_of_scope_hanfu', ('汉服', '齐胸襦裙', '马面裙', '宋制褙子', 'hanfu')),
)
_PROXY = ('给妈妈', '给我妈妈', '给母亲', '给妻子', '给爱人', '给朋友', '帮妈妈', '帮母亲',
          '帮妻子', '帮朋友', '替妈妈', '替母亲', '替朋友', '代拍', '她的照片', '他的照片',
          'for my mother', 'for my mom', 'for my wife', 'for my friend', 'mama')
_ACCESSORY = ('发髻', '璎珞', '颈饰', '发簪', '簪花', '配饰', '头饰', '花钿')
_GENERIC = ('敦煌', '飞天', 'dunhuang', 'apsara', 'feitian')
_TOUR = ('旅拍', '去敦煌', '敦煌玩', '敦煌旅游', '敦煌旅行', '敦煌留念')
_TRAVEL = ('旅行写真', '旅游写真', '西安', '洛阳', '巴黎', '杭州', '苏州', '大唐不夜城', 'travel portrait')
_INSTRUMENT = ('琵琶', '拿琴', '持琴', '拿着琴', '乐器', 'pipa', 'instrument')
_DETAIL_WORDS = ('长袖', '长裙', '短裙', '比基尼', '西装', '透明', '透视', '裸身', '露点',
                 '游客', '向导', '驼夫', '骑手', '伴舞',
                 '水面', '泉水', '发髻', '飘带', '长绸袖', '齐胸', '褙子', '马面', '铠甲')
_NEGATIVE = re.compile(r'不要|不用|不想|不拍|不做|不喜欢|不需要|不想要|不是|没有|不加|不含|不戴|不带|不穿|'
                       r'不拿|不持|不混|不出现|无需|不能画成|最怕画成|'
                       r'怕画成|别画成|不要画成|避免|排除|拒绝|别像|别|\b(?:no|not|without|avoid)\b', re.I)
_RESET = re.compile(r'[，,。.!！?？;；\n]|但是|不过|而是|但|我要|想要|只要|\bbut\b', re.I)


def _text(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValueError('text must be a string')
    return value


def _all_words():
    words = set(_PROXY + _ACCESSORY + _GENERIC + _TOUR + _TRAVEL + _INSTRUMENT + _DETAIL_WORDS)
    for _, terms in _SPECIFIC + _LOCATION + _BOUNDARIES:
        words.update(terms)
    return sorted(words, key=lambda word: (-len(word), word))


def _negated(raw, start, end):
    before = raw[:start]
    cuts = list(_RESET.finditer(before))
    if cuts:
        before = before[cuts[-1].end():]
    before = before[-24:]
    after = raw[end:end + 14].lstrip(' 的那种类')
    # In "不要把飞天改成汉服", 飞天 is the preserved subject, 汉服 the
    # excluded result. A plain keyword/window rejection would invert that intent.
    if re.search(r'(?:不要|别|不能|最怕)把(?:(?!画成|改成|换成|变成|当成).){0,18}$', before):
        return False
    for change in reversed(list(re.finditer(r'改成|换成', before))):
        prefix = before[:change.start()]
        excluded_change = prefix.endswith(('不要', '不用', '不想', '不能', '别')) or bool(
            re.search(r'(?:不要|别|不能|最怕)把.{0,18}$', prefix))
        if not excluded_change:
            before = before[change.end():]
        break
    feared_result = _has(before, ('最怕', '担心')) and bool(re.search(r'画成|变成|当成', before))
    immediately_not = raw[max(0, start - 1):start] in ('不', '无')
    return immediately_not or feared_result or bool(_NEGATIVE.search(before)) or after.startswith(
        ('不要', '不用', '不拍', '不做', '不需要', '不一样', '就别', '就不要', '也不要'))


def strip_negated(text):
    """Mask excluded routing words; preserve length and all unexcluded details."""
    raw = _text(text)
    out = list(raw)
    for word in _all_words():
        for match in re.finditer(re.escape(word), raw, flags=re.I):
            if _negated(raw, match.start(), match.end()):
                out[match.start():match.end()] = ' ' * (match.end() - match.start())
    return ''.join(out)


def _has(text, words):
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def _first(text, table):
    lowered = text.lower()
    hits = [(lowered.find(word.lower()), order, key)
            for order, (key, words) in enumerate(table) for word in words
            if word.lower() in lowered]
    return min(hits)[2] if hits else None


def _resolve_scene(text):
    scene = _first(text, _SPECIFIC)
    if scene:
        return scene
    # Water, not stars or generic desert, identifies the Crescent Spring theme.
    if _has(text, _LOCATION[0][1]):
        return 'crescent_night'
    scene = _first(text, _LOCATION[1:])
    if scene:
        return scene
    if _has(text, _TOUR) and _has(text, _GENERIC):
        return 'mingsha_sunset'
    if _has(text, _GENERIC + _ACCESSORY + ('壁画',)):
        return 'mural_fairy'
    return None


def route_intent(text):
    """Return a local routing hint, never authority or proof of qualification."""
    raw = _text(text)
    active = strip_negated(raw)
    for intent, words in _BOUNDARIES:
        if _has(active, words):
            return intent
    # Explicit non-self is different from a family request whose operator is unknown.
    if re.search(r'不是本人|非本人|不是我本人|不是我的照片|未经(?:本人|对方)同意|本人不同意', raw):
        return 'out_of_scope_self'
    if _has(active, _PROXY):
        return 'clarify_self'
    if '鸣沙山' in active and '月牙泉' in active:
        return 'clarify_dunhuang_scene'
    dance = _has(active, ('敦煌乐舞', '飞天乐舞', '乐舞', 'apsara_dance'))
    back = _has(active, ('反弹琵琶', '背弹琵琶', 'pipa_back', 'back pipa'))
    held = _has(active, ('拿琴', '持琴', '拿着琴', '拿着琵琶', '抱琴', '持琵琶'))
    if dance and _has(active, _INSTRUMENT) and (not back or held):
        return 'clarify_instrument'
    if _has(active, _TRAVEL + ('旅拍',)) and not _has(active, _GENERIC + ('鸣沙山', '月牙泉', '莫高窟')):
        return 'clarify_destination'
    excluded = any(_has(raw, words) for _, words in _BOUNDARIES)
    if excluded and not _resolve_scene(active):
        return 'clarify_main_need'
    return None


def route_scene(text):
    """Specific art subject first; ambiguity and scope checks never pick silently."""
    if route_intent(text) is not None:
        return None
    return _resolve_scene(strip_negated(text))


def look_valid(scene, look=None):
    return scene in SCENES and (look is None or look == scene)


def _check(scene, look=None):
    if scene not in SCENES:
        raise ValueError('unknown scene')
    if not look_valid(scene, look):
        raise ValueError('look must match the current scene')


def outfit_of(scene, look=None):
    _check(scene, look)
    return LOOKS[scene]['profile']


def look_name(scene, look=None):
    _check(scene, look)
    return LOOKS[scene]['label']


def outfit_conflict(scene, look, detail):
    """Readable conflicts; never discard the complete look for custom details."""
    if scene not in SCENES:
        return ['未知主题']
    conflicts = []
    if not look_valid(scene, look):
        conflicts.append('套系与当前主题不一致')
    raw = _text(detail)
    active = strip_negated(raw)
    labels = {'out_of_scope_hanfu': '纯汉服套系', 'out_of_scope_outfit': '旗袍、和服或军装套系',
              'out_of_scope_wedding': '婚纱或婚服套系', 'out_of_scope_child': '儿童主题',
              'out_of_scope_people': '额外人物'}
    for intent, words in _BOUNDARIES:
        if _has(active, words):
            conflicts.append(labels[intent])
    for other, words in _SPECIFIC + _LOCATION:
        if other != scene and _has(active, words):
            conflicts.append(SCENES[other][1] + '套系')
    if _has(active, ('短裙', '比基尼', '西装', '铠甲')):
        conflicts.append('完整上衣与长裙结构')
    if _has(active, ('透明', '透视', '裸身', '露点')):
        conflicts.append('得体不透服装')
    if _has(active, ('游客', '向导', '驼夫', '骑手', '伴舞')):
        conflicts.append('额外人物')
    if scene != 'pipa_back' and re.search(r'(?:拿|持|抱|弹|加一把|加把).{0,3}(?:琴|琵琶)', active):
        conflicts.append('琵琶道具与当前套系')
    if scene == 'pipa_back' and re.search(r'(?:不要|取消|去掉|不用|不拿|不持)(?:这把|那把)?(?:琵琶|琴)', raw):
        conflicts.append('反弹琵琶必需道具')
    if scene == 'water_sleeves' and re.search(r'(?:不要|取消|去掉|不用)(?:长袖|水袖|长绸袖)', raw):
        conflicts.append('水袖连接结构')
    if scene == 'crescent_night' and re.search(r'(?:不要|取消|去掉|不用)(?:水面|泉水|月牙泉)', raw):
        conflicts.append('月牙泉水面')
    if scene == 'camel_caravan' and re.search(r'(?:不要|取消|去掉|不用)(?:驼队|骆驼)', raw):
        conflicts.append('驼队背景')
    return list(dict.fromkeys(conflicts))


def outfit_text(scene, look=None, outfit=''):
    base = outfit_of(scene, look)
    detail = _text(outfit).strip()
    return base + ('；已确认的颜色与细节：' + detail if detail else '')


def build_prompt(scene, features='', outfit='', look=None):
    """Four ordered baselines, then action/visual/lock; reject rather than truncate."""
    _check(scene, look)
    features, outfit = _text(features).strip(), _text(outfit).strip()
    conflicts = outfit_conflict(scene, look, outfit)
    if conflicts:
        raise ValueError('outfit_look_conflict: ' + '、'.join(conflicts))
    baselines = list(BASELINES)
    if features:
        baselines[3] += ' 本人已确认的可见特征：' + features + '。'
    action = '动作：' + ACTIONS[scene]
    visual = ('视觉参照：' + SCENES[scene][3] + '\n本次完整服饰妆发：' + outfit_text(scene, look, outfit) +
              '\n妆发：' + SCENES[scene][4] +
              ' 细节只叠加在本套完整结构上，套系冲突先澄清，不换成另一主题或参考照原服装。'
              ' 这是现代敦煌主题艺术写真，不是历史精确复原、文物图像复制或真实景区拍摄。'
              ' 保持单人、脸部完整、手部自然，构图与本次确认画幅一致。')
    prompt = '\n'.join(baselines + [action, visual, '锁定：' + LOCK])
    if len(prompt) > PROMPT_MAX_CHARS:
        raise ValueError('prompt exceeds 6000 characters')
    return prompt

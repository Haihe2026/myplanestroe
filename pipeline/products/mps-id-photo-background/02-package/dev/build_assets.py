"""开发用：生成离线示例示意图与头像（合成绘制，不含真实人物，不调用任何生图服务）。不打进上架包。"""
import json, os
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mps-id-photo-background')
DEMOS = [
    ('white-one', '白底一寸', '#FFFFFF', '常用于简历、各类报名', None),
    ('blue-one', '蓝底一寸', '#438EDB', '常用于考试、证件办理', None),
    ('red-one', '红底登记照', '#D9001B', '常用于毕业、学位登记', None),
    ('white-two', '白底二寸', '#FFFFFF', '常用于报名表、登记表', None),
    ('blue-two', '蓝底二寸', '#438EDB', '常用于考试报名', None),
    ('resume-white', '简历白底', '#FFFFFF', '杂乱背景换成干净白底', None),
    ('custom-pixels', '295×413 像素', '#438EDB', '按报名系统像素另存', (295, 413)),
    ('edge-clean', '发丝边缘清理', '#FFFFFF', '去掉原底色留下的色边', None),
    ('school', '入学登记照', '#438EDB', '学校登记常用规格', None),
    ('custom-size', '机构指定尺寸', '#FFFFFF', '按你提供的规格裁切', None),
]
def hexrgb(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
VAR = {
    'white-one': ((54, 62, 80), 1.0), 'blue-one': ((235, 235, 235), 1.0), 'red-one': ((30, 30, 36), 1.0),
    'white-two': ((90, 70, 60), 0.86), 'blue-two': ((60, 80, 110), 0.86), 'resume-white': ((28, 40, 64), 0.93),
    'custom-pixels': ((120, 40, 40), 1.0), 'edge-clean': ((54, 62, 80), 1.0), 'school': ((40, 90, 70), 0.93),
    'custom-size': ((80, 80, 90), 0.8),
}
def figure(size, bg, key):
    w, h = size
    cloth, scale = VAR.get(key, ((54, 62, 80), 1.0))
    W, H = w * 2, h * 2
    im = Image.new('RGB', (W, H), hexrgb(bg))
    big = Image.new('RGB', (int(W / scale), int(H / scale)), hexrgb(bg))
    d = ImageDraw.Draw(big)
    W, H = big.size
    # 抽象人物：几何剪影（非真实人物）
    d.ellipse([W*0.18, H*0.62, W*0.82, H*1.25], fill=cloth)           # 肩部
    d.rectangle([W*0.43, H*0.50, W*0.57, H*0.68], fill=(222, 190, 165))       # 颈部
    d.ellipse([W*0.30, H*0.17, W*0.70, H*0.60], fill=(232, 200, 175))         # 面部
    d.pieslice([W*0.27, H*0.12, W*0.73, H*0.50], 180, 360, fill=(40, 34, 32)) # 头发
    d.polygon([(W*0.43, H*0.66), (W*0.50, H*0.78), (W*0.57, H*0.66)], fill=(245, 245, 245))  # 衣领
    if key == 'edge-clean':
        d.rectangle([0, 0, W*0.5, H], outline=None)
        half = Image.new('RGB', (W // 2, H), (198, 190, 160))
        mask = Image.new('L', (W // 2, H), 0)
        md = ImageDraw.Draw(mask)
        md.rectangle([0, 0, W // 2, H], fill=255)
        md.ellipse([W*0.18, H*0.62, W*0.82, H*1.25], fill=0)
        md.ellipse([W*0.30, H*0.17, W*0.70, H*0.60], fill=0)
        md.pieslice([W*0.27, H*0.12, W*0.73, H*0.50], 180, 360, fill=0)
        md.rectangle([W*0.43, H*0.50, W*0.57, H*0.68], fill=0)
        big.paste(half, (0, 0), mask)
        d.line([W // 2, 0, W // 2, H], fill=(120, 120, 120), width=3)
    # 缩放取景：scale<1 表示人物更小、留白更多
    big = big.resize((w * 2, h * 2), Image.LANCZOS) if scale == 1.0 else big
    if scale != 1.0:
        tmp = big.resize((int(big.width * scale), int(big.height * scale)), Image.LANCZOS)
        im.paste(tmp, ((w * 2 - tmp.width) // 2, h * 2 - tmp.height))
        big = im
    return big.resize((w, h), Image.LANCZOS)
os.makedirs(os.path.join(ROOT, 'assets', 'demos'), exist_ok=True)
items = []
for key, title, bg, note, px in DEMOS:
    size = px or (240, 336)
    name = key + '.png'
    figure(size, bg, key).save(os.path.join(ROOT, 'assets', 'demos', name), optimize=True)
    items.append(dict(key=key, title=title, note=note, file=name))
json.dump({'notice': '示意图为合成绘制，用于展示效果方向，不是真实处理结果。', 'demos': items},
          open(os.path.join(ROOT, 'assets', 'demos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
# 头像 512×512
av = Image.new('RGB', (512, 512), (67, 142, 219))
d = ImageDraw.Draw(av)
d.rounded_rectangle([96, 64, 416, 448], radius=28, fill=(255, 255, 255))
d.rectangle([126, 94, 386, 418], fill=(67, 142, 219))
inner = figure((260, 324), '#438EDB', 'x')
av.paste(inner, (126, 94))
dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dist')
os.makedirs(dist, exist_ok=True)
av.save(os.path.join(dist, 'mps-id-photo-background-avatar.png'), optimize=True)
print('ok', len(items))

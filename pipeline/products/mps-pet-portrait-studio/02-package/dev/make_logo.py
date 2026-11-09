"""开发用：生成交付 logo（原创图形：相机＋猫耳＋爪印，暖色，不含任何商标）。用法：python3 make_logo.py ../dist/logo.png"""
import sys
from PIL import Image, ImageDraw, ImageFilter
S=4; W=512*S
img=Image.new('RGBA',(W,W),(0,0,0,0))
# warm gradient rounded square
grad=Image.new('RGBA',(W,W))
gd=ImageDraw.Draw(grad)
top=(255,183,94); bot=(244,114,82)
for y in range(W):
    t=y/(W-1); gd.line([(0,y),(W,y)],fill=tuple(int(top[i]*(1-t)+bot[i]*t) for i in range(3))+(255,))
mask=Image.new('L',(W,W),0); ImageDraw.Draw(mask).rounded_rectangle([0,0,W-1,W-1],radius=112*S,fill=255)
img.paste(grad,(0,0),mask)
d=ImageDraw.Draw(img)
cream=(255,248,238,255); brown=(122,72,48,255); pink=(255,150,140,255)
s=lambda v:int(v*S)
# camera body
d.rounded_rectangle([s(86),s(168),s(426),s(410)],radius=s(48),fill=cream)
d.rounded_rectangle([s(176),s(128),s(300),s(184)],radius=s(20),fill=cream)  # viewfinder hump
d.ellipse([s(352),s(196),s(390),s(234)],fill=pink)  # flash dot
# cat ears on top corners of camera
d.polygon([(s(104),s(196)),(s(122),s(118)),(s(178),s(176))],fill=cream)
d.polygon([(s(408),s(196)),(s(390),s(118)),(s(334),s(176))],fill=cream)
d.polygon([(s(126),s(176)),(s(130),s(140)),(s(158),s(172))],fill=pink)
d.polygon([(s(386),s(176)),(s(382),s(140)),(s(354),s(172))],fill=pink)
# lens
cx,cy=s(256),s(292)
d.ellipse([cx-s(100),cy-s(100),cx+s(100),cy+s(100)],fill=brown)
d.ellipse([cx-s(80),cy-s(80),cx+s(80),cy+s(80)],fill=(255,206,140,255))
# paw print in lens
pc=brown
d.ellipse([cx-s(38),cy-s(6),cx+s(38),cy+s(52)],fill=pc)
for dx,dy,r in ((-48,-30,15),(-18,-52,15),(18,-52,15),(48,-30,15)):
    d.ellipse([cx+s(dx-r),cy+s(dy-r*1.2),cx+s(dx+r),cy+s(dy+r*1.2)],fill=pc)
# highlight
d.ellipse([cx+s(40),cy-s(70),cx+s(64),cy-s(46)],fill=(255,255,255,200))
img=img.resize((512,512),Image.LANCZOS)
img.save(sys.argv[1],optimize=True)

"""开发用：把 demo-assets/ 里已授权生成的 10 张示例图同步进技能包（不打进上架包，不联网，不生图）。

- 先按 demo-assets/provenance.json 逐张核对 output_sha256，不符即中止；
- 本地等比缩放并调色板压缩，控制包内示例总体积（< 1.5MB，单张 < 150KB）；不加文字、水印；
- 竖版与横版按长边 480 等比缩放；
- 派生记录写 dev/demos-derivation.json（源哈希 → 包内哈希）。
"""
import hashlib
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '..', 'demo-assets')
PKG = os.path.join(HERE, '..', 'mps-wedding-portrait-studio')
OUT = os.path.join(PKG, 'assets')  # 示例图与 demos.json 同级（包目录最多两级）
BOX = (480, 480)          # 等比缩放上限：竖版 320×480、横版 480×320
COLORS = 128              # 调色板颜色数
SPECIAL = {}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    prov = json.load(open(os.path.join(SRC, 'provenance.json'), encoding='utf-8'))
    if prov.get('upstream_generation_calls') != 10 or prov.get('succeeded') != 10:
        sys.exit('provenance count mismatch')
    by_key = {it['key']: it for it in prov['items']}
    demos = json.load(open(os.path.join(PKG, 'assets', 'demos.json'), encoding='utf-8'))['demos']
    if sorted(by_key) != sorted(d['key'] for d in demos):
        sys.exit('key set mismatch')
    rows = []
    for d in demos:
        it = by_key[d['key']]
        if not it.get('fictional_adult') or it.get('status') != 'succeeded':
            sys.exit('not a cleared demo: ' + d['key'])
        name = SPECIAL.get(d['key'], it['file'])
        raw = open(os.path.join(SRC, name), 'rb').read()
        if name == it['file']:
            expect = it['output_sha256']
        else:
            ex = it.get('additional_export') or {}
            expect = ex.get('sha256') if ex.get('file') == name else None
        if not expect or sha(raw) != expect:
            sys.exit('hash mismatch: ' + name)
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        if name == it['file']:
            im.thumbnail(BOX, Image.LANCZOS)
        q = im.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        buf = io.BytesIO()
        q.save(buf, format='PNG', optimize=True)
        out = buf.getvalue()
        with open(os.path.join(OUT, d['file']), 'wb') as f:
            f.write(out)
        rows.append(dict(key=d['key'], source=name, source_sha256=sha(raw), source_hash_checked=True,
                         package_file=d['file'], package_size=list(im.size), package_bytes=len(out),
                         package_sha256=sha(out)))
    total = sum(r['package_bytes'] for r in rows)
    json.dump(dict(note='本地缩放与调色板压缩，未新增生图调用；源图见 demo-assets/provenance.json',
                   box=list(BOX), colors=COLORS, total_bytes=total, items=rows),
              open(os.path.join(HERE, 'demos-derivation.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('ok', len(rows), total)


if __name__ == '__main__':
    main()

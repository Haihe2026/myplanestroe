"""开发用：把 demo-assets/ 里已授权生成的 10 张示例图按原字节复制进技能包（不打进上架包，不联网，不生图，不缩放）。

- 按 demo-assets/provenance.json 逐张核对 output_sha256，不符即中止；
- 原字节复制到 assets/（与 demos.json 同级，包目录最多两级），复制后再核对一次哈希；
- 派生记录写 dev/demos-derivation.json（源哈希 = 包内哈希）。
"""
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '..', 'demo-assets')
PKG = os.path.join(HERE, '..', 'mps-family-portrait-studio')
OUT = os.path.join(PKG, 'assets')


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    prov = json.load(open(os.path.join(SRC, 'provenance.json'), encoding='utf-8'))
    if prov.get('upstream_generation_calls') != 10 or prov.get('succeeded') != 10:
        sys.exit('provenance count mismatch')
    by_key = {it['key']: it for it in prov['items']}
    demos = json.load(open(os.path.join(OUT, 'demos.json'), encoding='utf-8'))['demos']
    if sorted(by_key) != sorted(d['key'] for d in demos):
        sys.exit('key set mismatch')
    rows = []
    for d in demos:
        it = by_key[d['key']]
        if not it.get('fictional_adults') or it.get('status') != 'succeeded' or it.get('title') != d['title']:
            sys.exit('provenance item not usable: ' + d['key'])
        src = os.path.join(SRC, it['file'])
        if sha(src) != it['output_sha256']:
            sys.exit('source hash mismatch: ' + d['key'])
        dst = os.path.join(OUT, d['file'])
        shutil.copyfile(src, dst)
        if sha(dst) != it['output_sha256']:
            sys.exit('copy hash mismatch: ' + d['key'])
        rows.append(dict(key=d['key'], title=d['title'], source=it['file'], source_sha256=it['output_sha256'],
                         package_file=d['file'], package_sha256=sha(dst), package_bytes=os.path.getsize(dst),
                         size=it['output_size'], byte_identical=True))
    out = dict(note='原字节复制，未缩放、未重编码、未新增生图调用；源图见 demo-assets/provenance.json',
               total_bytes=sum(r['package_bytes'] for r in rows), items=rows)
    with open(os.path.join(HERE, 'demos-derivation.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('synced', len(rows), out['total_bytes'])


if __name__ == '__main__':
    main()

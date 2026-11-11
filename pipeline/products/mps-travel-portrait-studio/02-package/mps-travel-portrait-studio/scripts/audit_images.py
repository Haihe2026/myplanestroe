#!/usr/bin/env python3
"""离线检查参考照片（免费，不联网）。用法：audit_images.py <照片路径>"""
import json
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jpeg_local  # noqa: E402
from png_local import _ADAM7, _BITS  # noqa: E402

MAX_BYTES = 5 * 1024 * 1024
MIN_SIDE = 128
MAX_SIDE = 8000
MAX_PIXELS = 20000000

PROBLEMS = {
    'missing': '找不到这个文件',
    'not_file': '不是一个普通文件',
    'too_large': '超过 5MB',
    'format': '不是 PNG 或 JPG 照片',
    'animated': '是动图，只支持单张静态照片',
    'damaged': '文件已损坏或不完整，无法完整读取',
    'unsupported_jpeg': '这种 JPG 编码方式暂不支持，请另存为普通 JPG 或 PNG 后再发',
    'too_small': '分辨率太低（最短边至少 128 像素）',
    'too_big': '分辨率过大（最长边不超过 8000 像素、总像素不超过 2000 万）',
}


def _png_info(data):
    """完整校验参考 PNG（流式，不整张展开）：签名、IHDR 在首、每块 CRC、索引色须有 PLTE、IDAT 连续、IEND 收尾且无尾随数据、
    zlib 数据完整、每条扫描行的过滤类型合法且总长度与尺寸一致（含 Adam7 隔行）；有 acTL 判为动图。"""
    if len(data) < 33 or data[12:16] != b'IHDR':
        raise ValueError('damaged')
    pos, n = 8, len(data)
    ihdr, plte, idat_done, idat_seen, iend = None, False, False, False, False
    z, rows, need = zlib.decompressobj(), None, None
    while pos < n:
        if pos + 12 > n:
            raise ValueError('damaged')
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > n:
            raise ValueError('damaged')
        body = data[pos + 8:pos + 8 + length]
        if zlib.crc32(kind + body) & 0xffffffff != struct.unpack('>I', data[end - 4:end])[0]:
            raise ValueError('damaged')
        if kind == b'acTL':
            raise ValueError('animated')
        if kind == b'IHDR':
            if ihdr or pos != 8 or length != 13:
                raise ValueError('damaged')
            ihdr = struct.unpack('>IIBBBBB', body)
            w, h, depth, ctype, comp, filt, interlace = ihdr
            if ctype not in _BITS or depth not in _BITS[ctype][1] or comp or filt or interlace not in (0, 1) or not w or not h:
                raise ValueError('damaged')
            if w * h > MAX_PIXELS or max(w, h) > MAX_SIDE:
                raise ValueError('too_big')  # 不展开超限图片
            rows = _row_plan(w, h, _BITS[ctype][0] * depth, interlace)
        elif kind == b'PLTE':
            plte = True
        elif kind == b'IDAT':
            if ihdr is None or idat_done or (ihdr[3] == 3 and not plte):
                raise ValueError('damaged')
            idat_seen = True
            need = _feed(z, body, rows, need)
        elif idat_seen:
            idat_done = True
        pos = end
        if kind == b'IEND':
            iend = True
            break
    if ihdr is None or not idat_seen or not iend or pos != n:
        raise ValueError('damaged')
    try:
        tail = z.flush()
    except zlib.error:
        raise ValueError('damaged')
    need = _feed_raw(tail, rows, need)
    if not z.eof or z.unused_data or rows or need:
        raise ValueError('damaged')
    return ihdr[0], ihdr[1]


def _row_plan(w, h, bpp, interlace):
    """返回扫描行字节数列表（倒序，便于 pop）：每项为 1 个过滤字节 + 行数据。"""
    if interlace:
        passes = [((w - x0 + dx - 1) // dx if w > x0 else 0, (h - y0 + dy - 1) // dy if h > y0 else 0)
                  for x0, y0, dx, dy in _ADAM7]
    else:
        passes = [(w, h)]
    plan = []
    for pw, ph in passes:
        if pw and ph:
            plan.append([ph, 1 + (pw * bpp + 7) // 8])
    plan.reverse()
    return plan


def _feed(z, chunk, rows, need):
    try:
        out = z.decompress(chunk)
    except zlib.error:
        raise ValueError('damaged')
    if z.unused_data:
        raise ValueError('damaged')
    return _feed_raw(out, rows, need)


def _feed_raw(out, rows, need):
    """need：当前行还差的字节数（None 表示下一字节是过滤类型）。逐行核对过滤字节 0–4，超出总长度即损坏。"""
    i, n = 0, len(out)
    while i < n:
        if need is None:
            if not rows:
                raise ValueError('damaged')
            if out[i] > 4:
                raise ValueError('damaged')
            need = rows[-1][1] - 1
            rows[-1][0] -= 1
            if not rows[-1][0]:
                rows.pop()
            i += 1
            if not need:
                need = None
            continue
        take = min(need, n - i)
        i += take
        need -= take
        if not need:
            need = None
    return need


def _jpeg_info(data):
    """完整校验参考 JPEG：所有标记段、量化表与 Huffman 表引用、每个扫描的熵编码数据完整解出全部 MCU、RST 序号、EOI 收尾。"""
    try:
        return jpeg_local.verify(data, MAX_SIDE, MAX_PIXELS)
    except ValueError as e:
        raise ValueError({'unsupported': 'unsupported_jpeg', 'too_big': 'too_big'}.get(str(e), 'damaged'))


def check(path):
    """返回 dict(ok, mime, width, height, problem, file)。不修改、不移动原文件。"""
    name = os.path.basename(path)
    result = dict(ok=False, file=name, mime=None, width=None, height=None, problem=None)
    if not os.path.lexists(path):
        result['problem'] = 'missing'
        return result
    if os.path.islink(path) or not os.path.isfile(path):
        result['problem'] = 'not_file'
        return result
    if os.path.getsize(path) > MAX_BYTES:
        result['problem'] = 'too_large'
        return result
    with open(path, 'rb') as f:
        data = f.read(MAX_BYTES + 1)
    try:
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            mime = 'image/png'
            w, h = _png_info(data)
        elif data.startswith(b'\xff\xd8\xff'):
            mime = 'image/jpeg'
            w, h = _jpeg_info(data)
        else:
            raise ValueError('format')
    except ValueError as e:
        result['problem'] = str(e) if str(e) in PROBLEMS else 'damaged'
        return result
    except (struct.error, IndexError, KeyError, TypeError, OverflowError, MemoryError, RecursionError):
        result['problem'] = 'damaged'
        return result
    result.update(mime=mime, width=w, height=h)
    if min(w, h) < MIN_SIDE:
        result['problem'] = 'too_small'
    elif max(w, h) > MAX_SIDE or w * h > MAX_PIXELS:
        result['problem'] = 'too_big'
    else:
        result['ok'] = True
    return result


def describe(problem):
    return PROBLEMS.get(problem, PROBLEMS['damaged'])


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(json.dumps({'signal': 'auditUsage'}))
        sys.exit(3)
    r = check(sys.argv[1])
    print(json.dumps(dict(r, signal='auditOk' if r['ok'] else 'auditFailed'), ensure_ascii=False))
    sys.exit(0 if r['ok'] else 3)

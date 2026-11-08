#!/usr/bin/env python3
"""离线检查参考照片（免费，不联网）。用法：audit_images.py <照片路径>"""
import json
import os
import struct
import sys

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
    'damaged': '文件已损坏或无法读取尺寸',
    'too_small': '分辨率太低（最短边至少 128 像素）',
    'too_big': '分辨率过大（最长边不超过 8000 像素、总像素不超过 2000 万）',
}


def _png_info(data):
    if len(data) < 33 or data[12:16] != b'IHDR':
        raise ValueError('damaged')
    w, h = struct.unpack('>II', data[16:24])
    pos = 8
    while pos + 8 <= len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        if kind == b'acTL':
            raise ValueError('animated')
        if kind == b'IDAT':
            break
        pos += 12 + length
    return w, h


def _jpeg_info(data):
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ValueError('damaged')
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        length = struct.unpack('>H', data[pos + 2:pos + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack('>HH', data[pos + 5:pos + 9])
            return w, h
        if marker == 0xDA:
            break
        pos += 2 + length
    raise ValueError('damaged')


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
    except (struct.error, IndexError):
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

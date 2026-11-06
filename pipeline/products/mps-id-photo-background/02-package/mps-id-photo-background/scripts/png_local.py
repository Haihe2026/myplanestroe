"""本地 PNG 解码、居中裁切与缩放（仅标准库）。用于按机构像素另存一份，不联网。"""
import struct
import zlib

SIG = b'\x89PNG\r\n\x1a\n'
CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode(data):
    """返回 (width, height, rows)；rows 为每行 RGB bytes。只支持8位非隔行 PNG。"""
    if not data.startswith(SIG):
        raise ValueError('not png')
    pos, idat, ihdr = 8, [], None
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            ihdr = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
        pos += 12 + length
    if not ihdr:
        raise ValueError('no header')
    w, h, depth, ctype, _, _, interlace = ihdr
    if depth != 8 or ctype not in CHANNELS or interlace:
        raise ValueError('unsupported png')
    ch = CHANNELS[ctype]
    raw = zlib.decompress(b''.join(idat))
    stride = w * ch
    rows, prev = [], bytearray(stride)
    i = 0
    for _ in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if f == 1:
            for x in range(ch, stride):
                line[x] = (line[x] + line[x - ch]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                left = line[x - ch] if x >= ch else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                left = line[x - ch] if x >= ch else 0
                up_left = prev[x - ch] if x >= ch else 0
                line[x] = (line[x] + _paeth(left, prev[x], up_left)) & 255
        elif f != 0:
            raise ValueError('bad filter')
        prev = line
        rows.append(_to_rgb(line, ch, w))
    return w, h, rows


def _to_rgb(line, ch, w):
    if ch == 3:
        return bytes(line)
    out = bytearray(w * 3)
    for x in range(w):
        if ch == 4:
            r, g, b, a = line[x * 4:x * 4 + 4]
            # 透明部分按白色合成
            out[x * 3] = (r * a + 255 * (255 - a)) // 255
            out[x * 3 + 1] = (g * a + 255 * (255 - a)) // 255
            out[x * 3 + 2] = (b * a + 255 * (255 - a)) // 255
        else:
            v = line[x * ch]
            out[x * 3:x * 3 + 3] = bytes((v, v, v))
    return bytes(out)


def encode(w, h, rows):
    raw = b''.join(b'\x00' + r for r in rows)

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    return SIG + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def size_of(data):
    if not data.startswith(SIG):
        raise ValueError('not png')
    return struct.unpack('>II', data[16:24])


def crop_resize(data, tw, th):
    """居中裁切到目标比例，再按区域平均缩放到 tw×th。返回新 PNG bytes。"""
    w, h, rows = decode(data)
    if tw < 1 or th < 1 or tw > w or th > h:
        raise ValueError('target larger than source')
    if w * th > h * tw:
        cw, ch_ = h * tw // th, h
    else:
        cw, ch_ = w, w * th // tw
    x0, y0 = (w - cw) // 2, (h - ch_) // 2
    out = []
    for oy in range(th):
        sy0 = y0 + oy * ch_ // th
        sy1 = max(sy0 + 1, y0 + (oy + 1) * ch_ // th)
        line = bytearray(tw * 3)
        for ox in range(tw):
            sx0 = x0 + ox * cw // tw
            sx1 = max(sx0 + 1, x0 + (ox + 1) * cw // tw)
            r = g = b = n = 0
            for sy in range(sy0, sy1):
                row = rows[sy]
                for sx in range(sx0, sx1):
                    k = sx * 3
                    r += row[k]
                    g += row[k + 1]
                    b += row[k + 2]
                    n += 1
            line[ox * 3:ox * 3 + 3] = bytes((r // n, g // n, b // n))
        out.append(bytes(line))
    return encode(tw, th, out)

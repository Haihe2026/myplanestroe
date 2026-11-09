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


_BITS = {0: (1, (1, 2, 4, 8, 16)), 2: (3, (8, 16)), 3: (1, (1, 2, 4, 8)), 4: (2, (8, 16)), 6: (4, (8, 16))}
_ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


def _rows_bytes(w, h, bpp_bits):
    """未压缩数据应有的字节数（每行 1 个过滤字节 + 行数据）。"""
    if w == 0 or h == 0:
        return 0
    return h * (1 + (w * bpp_bits + 7) // 8)


def verify(data):
    """完整校验 PNG；任何解析异常（含坏压缩流）一律转为 ValueError。"""
    try:
        return _verify(data)
    except ValueError:
        raise
    except (zlib.error, struct.error, IndexError, TypeError, OverflowError, MemoryError) as e:
        raise ValueError('undecodable: ' + type(e).__name__)


def _verify(data):
    """完整校验 PNG 内容：签名、每个块的长度与 CRC、IHDR/PLTE/IDAT/IEND 次序、
    图像数据可完整解压且字节数与宽高一致、过滤类型合法。通过返回 (width, height)，否则抛 ValueError。
    只读不写；用于在保存和宣布交付之前确认图片可完整解码（截断、拼接残缺都不通过）。"""
    if not isinstance(data, (bytes, bytearray)) or not data.startswith(SIG):
        raise ValueError('not png')
    pos, n = 8, len(data)
    ihdr = None
    has_plte = seen_idat = idat_done = False
    dec = zlib.decompressobj()
    out = bytearray()
    limit = None
    while True:
        if pos + 12 > n:
            raise ValueError('truncated')
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = bytes(data[pos + 4:pos + 8])
        end = pos + 12 + length
        if length > 0x7fffffff or end > n:
            raise ValueError('truncated')
        body = data[pos + 8:pos + 8 + length]
        crc = struct.unpack('>I', data[pos + 8 + length:end])[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            raise ValueError('bad crc')
        if ihdr is None:
            if kind != b'IHDR' or length != 13:
                raise ValueError('no header')
            w, h, depth, ctype, comp, filt, interlace = struct.unpack('>IIBBBBB', body)
            if not (0 < w <= 1 << 16 and 0 < h <= 1 << 16) or ctype not in _BITS or depth not in _BITS[ctype][1] \
                    or comp or filt or interlace not in (0, 1):
                raise ValueError('bad header')
            ihdr = (w, h, depth, ctype, interlace)
            bpp = _BITS[ctype][0] * depth
            if interlace:
                limit = sum(_rows_bytes((w - x0 + dx - 1) // dx if w > x0 else 0, (h - y0 + dy - 1) // dy if h > y0 else 0, bpp)
                            for x0, y0, dx, dy in _ADAM7)
            else:
                limit = _rows_bytes(w, h, bpp)
        elif kind == b'PLTE':
            has_plte = True
        elif kind == b'IDAT':
            if idat_done:
                raise ValueError('split image data')
            seen_idat = True
            out += dec.decompress(bytes(body), limit + 1 - len(out))
            if len(out) > limit:
                raise ValueError('too much image data')
        elif kind == b'IEND':
            break
        elif seen_idat:
            idat_done = True
        pos = end
    if not seen_idat or (ihdr[3] == 3 and not has_plte):
        raise ValueError('incomplete')
    out += dec.flush()
    if not dec.eof or len(out) != limit:
        raise ValueError('incomplete image data')
    w, h, depth, ctype, interlace = ihdr
    bpp = _BITS[ctype][0] * depth
    passes = [(w, h)] if not interlace else [
        ((w - x0 + dx - 1) // dx if w > x0 else 0, (h - y0 + dy - 1) // dy if h > y0 else 0) for x0, y0, dx, dy in _ADAM7]
    i = 0
    for pw, ph in passes:  # 逐个子图（非隔行即整图）逐行核对过滤类型
        if pw == 0 or ph == 0:
            continue
        stride = 1 + (pw * bpp + 7) // 8
        for _ in range(ph):
            if out[i] > 4:
                raise ValueError('bad filter')
            i += stride
    if i != limit:
        raise ValueError('incomplete image data')
    return w, h

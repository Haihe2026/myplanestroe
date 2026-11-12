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


def _scan_bytes(w, h, ch, depth):
    if w == 0 or h == 0:
        return 0
    return h * (1 + (w * ch * depth + 7) // 8)


def verify(data):
    """完整校验 PNG：签名、分块 CRC、IHDR 在首、IDAT 连续、IEND 收尾、zlib 完整解压、扫描行总长与过滤类型（含 Adam7 隔行）。
    不合格抛 ValueError；合格返回 (width, height)。"""
    if not data.startswith(SIG):
        raise ValueError('not png')
    pos, ihdr, idat, seen_iend, idat_done, first = 8, None, [], False, False, True
    while pos < len(data):
        if pos + 12 > len(data):
            raise ValueError('truncated')
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > len(data):
            raise ValueError('truncated')
        body = data[pos + 8:pos + 8 + length]
        if zlib.crc32(kind + body) & 0xffffffff != struct.unpack('>I', data[end - 4:end])[0]:
            raise ValueError('crc')
        if first and kind != b'IHDR':
            raise ValueError('no header')
        first = False
        if kind == b'IHDR':
            if ihdr or length != 13:
                raise ValueError('bad header')
            ihdr = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            if idat_done:
                raise ValueError('split idat')
            idat.append(body)
        elif idat:
            idat_done = True
        if kind == b'IEND':
            seen_iend = True
            pos = end
            break
        pos = end
    if not ihdr or not idat or not seen_iend or pos != len(data):
        raise ValueError('incomplete')
    w, h, depth, ctype, comp, filt, interlace = ihdr
    if ctype not in _BITS or depth not in _BITS[ctype][1] or comp or filt or interlace not in (0, 1) or not w or not h:
        raise ValueError('unsupported png')
    rows = row_plan(w, h, _BITS[ctype][0] * depth, interlace)
    z, need = zlib.decompressobj(), None
    try:
        for part in idat:
            need = inflate_rows(z, part, rows, need)
        finish_rows(z, rows, need)
    except ValueError:
        raise ValueError('length')
    return w, h


# ---- 有界流式解压（1.0.2，A3-TRV-02-R1）----
# 每次 decompress 都带 max_length：单次输出 ≤ OUT_CHUNK，且不超过「剩余应有扫描行字节 + 1」；
# 每块输出立即逐行核对后丢弃，超出应有总长 1 字节即判损坏。不存在「先整段展开、事后再判大小」。
OUT_CHUNK = 65536


def row_plan(w, h, bpp, interlace):
    """返回扫描行字节数计划（倒序，便于 pop）：每项 [行数, 1 个过滤字节 + 行数据]。"""
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


def remaining(rows, need):
    return (need or 0) + sum(c * ln for c, ln in rows)


def feed_raw(out, rows, need):
    """need：当前行还差的字节数（None 表示下一字节是过滤类型）。逐行核对过滤字节 0–4，超出总长度即损坏。"""
    i, n = 0, len(out)
    while i < n:
        if need is None:
            if not rows or out[i] > 4:
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


def inflate_rows(z, data, rows, need, chunk=None, meter=None):
    """把一段 IDAT 数据有界地送入解压器 z；返回新的 need。
    chunk：单次最大输出（可注入小值做回归）；meter：可注入 list，记录每次实际输出字节数（回归断言上限）。"""
    chunk = chunk or OUT_CHUNK
    while True:
        limit = max(1, min(chunk, remaining(rows, need) + 1))
        try:
            out = z.decompress(data, limit)
        except zlib.error:
            raise ValueError('damaged')
        if meter is not None:
            meter.append(len(out))
        need = feed_raw(out, rows, need)
        if z.unused_data:
            raise ValueError('damaged')
        data = z.unconsumed_tail
        if z.eof or (not data and len(out) < limit):
            return need  # 输入用尽且无积压输出；或流已结束


def finish_rows(z, rows, need):
    if not z.eof or z.unused_data or rows or need:
        raise ValueError('damaged')

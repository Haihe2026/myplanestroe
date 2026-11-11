"""本地 JPEG 完整性校验（仅标准库，不联网）：逐段解析标记，并把每个扫描的熵编码数据按 Huffman 表完整解一遍，
确认所有 MCU 都能解出、数据不截断、以 EOI 收尾。不做反量化和 IDCT（像素值不影响「能否完整解码」）。

支持：基线与扩展顺序（SOF0/SOF1）、渐进（SOF2），Huffman 编码，8 位精度，1–4 个分量。
其他编码（无损、算术编码、分层）抛 ValueError('unsupported')。不合格抛 ValueError；合格返回 (width, height)。
"""
import struct

ZIGZAG_LEN = 64
_SOF_SUPPORTED = (0xC0, 0xC1, 0xC2)
_SOF_OTHER = (0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)


def _build_table(counts, symbols):
    """返回 16 位前瞻查表：index → (码长, 符号)；未用的码位为 None。"""
    table = [None] * 65536
    code, k = 0, 0
    for length in range(1, 17):
        for _ in range(counts[length - 1]):
            if k >= len(symbols):
                raise ValueError('dht')
            if code >= (1 << length):
                raise ValueError('dht')
            shift = 16 - length
            start = code << shift
            entry = (length, symbols[k])
            for i in range(start, start + (1 << shift)):
                table[i] = entry
            code += 1
            k += 1
        code <<= 1
    return table


class _Bits(object):
    """单个重启区间内（已去掉 FF00 填充）的比特读取器；越界时补 1（JPEG 规定的填充位），并记录是否读过界。"""
    __slots__ = ('data', 'pos', 'buf', 'nbits', 'over')

    def __init__(self, data):
        self.data, self.pos, self.buf, self.nbits, self.over = data, 0, 0, 0, 0

    def _fill(self, need):
        data, pos, buf, nbits = self.data, self.pos, self.buf, self.nbits
        n = len(data)
        while nbits < need:
            if pos < n:
                buf = (buf << 8) | data[pos]
                pos += 1
            else:
                buf = (buf << 8) | 0xFF
                self.over += 8
            nbits += 8
        self.pos, self.buf, self.nbits = pos, buf, nbits

    def huff(self, table):
        if self.nbits < 16:
            self._fill(16)
        e = table[(self.buf >> (self.nbits - 16)) & 0xFFFF]
        if e is None:
            raise ValueError('huffman')
        self.nbits -= e[0]
        self.buf &= (1 << self.nbits) - 1
        return e[1]

    def bits(self, n):
        if not n:
            return 0
        if self.nbits < n:
            self._fill(n)
        self.nbits -= n
        v = self.buf >> self.nbits
        self.buf &= (1 << self.nbits) - 1
        return v

    def check_end(self):
        """区间结束：不得读过真实数据的末尾（只允许最后不足一字节的 1 填充），剩余整字节不得超过 1 个。"""
        consumed_bits = self.pos * 8 + self.over - self.nbits
        if consumed_bits > len(self.data) * 8:
            raise ValueError('truncated scan')
        if len(self.data) * 8 - consumed_bits >= 16:
            raise ValueError('scan length')


def _split_entropy(data, pos):
    """从 pos 起读取熵编码数据直到下一个非 RST 标记；返回 (各重启区间的去填充字节, RST 编号序列, 标记位置)。"""
    segs, rsts, cur = [], [], bytearray()
    n = len(data)
    start = pos
    while True:
        j = data.find(b'\xff', pos)
        if j < 0:
            raise ValueError('truncated scan')
        cur += data[pos:j]
        k = j + 1
        while k < n and data[k] == 0xFF:
            k += 1  # 标记前允许多个 FF 填充
        if k >= n:
            raise ValueError('truncated scan')
        m = data[k]
        if m == 0x00:
            if k != j + 1:
                raise ValueError('stuffing')
            cur.append(0xFF)
            pos = k + 1
        elif 0xD0 <= m <= 0xD7:
            segs.append(bytes(cur))
            cur = bytearray()
            rsts.append(m - 0xD0)
            pos = k + 1
        else:
            segs.append(bytes(cur))
            if pos == start and not cur and not rsts:
                raise ValueError('empty scan')
            return segs, rsts, j


def _extend(v, t):
    return v - (1 << t) + 1 if t and v < (1 << (t - 1)) else v


def verify(data, max_side=None, max_pixels=None):
    """max_side/max_pixels：尺寸超限时在解熵数据前抛 ValueError('too_big')，不为超大图分配内存。"""
    if not data.startswith(b'\xff\xd8'):
        raise ValueError('not jpeg')
    n = len(data)
    pos = 2
    dc_tables, ac_tables, qt = {}, {}, set()
    frame = None
    restart = 0
    eoi = False
    scans = 0
    coef_state = None  # 渐进：每个分量每个块 64 个系数的「是否非零」与已解位
    while pos < n:
        if data[pos] != 0xFF:
            raise ValueError('marker')
        while pos < n and data[pos] == 0xFF:
            pos += 1
        if pos >= n:
            raise ValueError('truncated')
        m = data[pos]
        pos += 1
        if m == 0xD9:
            eoi = True
            break
        if m == 0xD8 or 0xD0 <= m <= 0xD7 or m == 0x01:
            raise ValueError('marker')
        if pos + 2 > n:
            raise ValueError('truncated')
        length = struct.unpack('>H', data[pos:pos + 2])[0]
        if length < 2 or pos + length > n:
            raise ValueError('truncated')
        seg = data[pos + 2:pos + length]
        pos += length
        if m in _SOF_OTHER:
            raise ValueError('unsupported')
        if m in _SOF_SUPPORTED:
            if frame is not None or len(seg) < 6:
                raise ValueError('sof')
            p, h, w, nc = seg[0], struct.unpack('>H', seg[1:3])[0], struct.unpack('>H', seg[3:5])[0], seg[5]
            if p != 8 or not h or not w or not 1 <= nc <= 4 or len(seg) != 6 + 3 * nc:
                raise ValueError('unsupported' if p != 8 else 'sof')
            comps = []
            for i in range(nc):
                cid, hv, tq = seg[6 + 3 * i], seg[7 + 3 * i], seg[8 + 3 * i]
                hs, vs = hv >> 4, hv & 15
                if not 1 <= hs <= 4 or not 1 <= vs <= 4 or tq > 3:
                    raise ValueError('sof')
                comps.append(dict(id=cid, h=hs, v=vs, tq=tq))
            if len({c['id'] for c in comps}) != nc:
                raise ValueError('sof')
            if (max_side and max(w, h) > max_side) or (max_pixels and w * h > max_pixels):
                raise ValueError('too_big')
            hmax, vmax = max(c['h'] for c in comps), max(c['v'] for c in comps)
            mcux, mcuy = -(-w // (8 * hmax)), -(-h // (8 * vmax))
            for c in comps:
                c['bw'] = -(-(-(-w * c['h'] // hmax)) // 8)  # 分量自身的块数（非交错扫描用）
                c['bh'] = -(-(-(-h * c['v'] // vmax)) // 8)
                c['bpl'] = mcux * c['h']  # 交错扫描下每行块数（含 MCU 填充）
                c['rows'] = mcuy * c['v']
            frame = dict(progressive=(m == 0xC2), w=w, h=h, comps=comps, mcux=mcux, mcuy=mcuy)
            if frame['progressive']:
                coef_state = {c['id']: bytearray(c['bpl'] * c['rows'] * 64) for c in comps}
        elif m == 0xC4:
            i = 0
            while i < len(seg):
                if i + 17 > len(seg):
                    raise ValueError('dht')
                tc, th = seg[i] >> 4, seg[i] & 15
                if tc > 1 or th > 3:
                    raise ValueError('dht')
                counts = seg[i + 1:i + 17]
                total = sum(counts)
                if not total or i + 17 + total > len(seg):
                    raise ValueError('dht')
                table = _build_table(counts, seg[i + 17:i + 17 + total])
                (ac_tables if tc else dc_tables)[th] = table
                i += 17 + total
        elif m == 0xDB:
            i = 0
            while i < len(seg):
                pq, tq = seg[i] >> 4, seg[i] & 15
                size = 64 * (2 if pq else 1)
                if pq > 1 or tq > 3 or i + 1 + size > len(seg):
                    raise ValueError('dqt')
                qt.add(tq)
                i += 1 + size
        elif m == 0xDD:
            if len(seg) != 2:
                raise ValueError('dri')
            restart = struct.unpack('>H', seg)[0]
        elif m == 0xDA:
            if frame is None:
                raise ValueError('sos before sof')
            ns = seg[0] if seg else 0
            if not 1 <= ns <= 4 or len(seg) != 4 + 2 * ns:
                raise ValueError('sos')
            ids = {c['id']: c for c in frame['comps']}
            sc = []
            for i in range(ns):
                cid, t = seg[1 + 2 * i], seg[2 + 2 * i]
                if cid not in ids or ids[cid]['tq'] not in qt:
                    raise ValueError('sos')
                sc.append((ids[cid], t >> 4, t & 15))
            ss, se, ah, al = seg[1 + 2 * ns], seg[2 + 2 * ns], seg[3 + 2 * ns] >> 4, seg[3 + 2 * ns] & 15
            segs, rsts, pos = _split_entropy(data, pos)
            _decode_scan(frame, sc, ss, se, ah, al, dc_tables, ac_tables, restart, segs, rsts, coef_state)
            scans += 1
        elif 0xE0 <= m <= 0xEF or m == 0xFE or m == 0xDC or m == 0xDE or m == 0xDF:
            pass  # APPn / COM / DNL 等元数据段
        else:
            raise ValueError('marker')
    if not eoi or frame is None or not scans:
        raise ValueError('incomplete')
    if frame['progressive']:
        # 渐进图每个分量的 DC 必须至少出现在一次首扫描里
        for c in frame['comps']:
            if not c.get('dc_seen'):
                raise ValueError('incomplete')
    elif any(not c.get('dc_seen') for c in frame['comps']):
        raise ValueError('incomplete')
    return frame['w'], frame['h']


def _decode_scan(frame, sc, ss, se, ah, al, dc_tables, ac_tables, restart, segs, rsts, coef):
    progressive = frame['progressive']
    if progressive:
        if ss == 0 and se != 0 or ss > se or se > 63 or al > 13 or ah > 13 or (ah and ah != al + 1):
            raise ValueError('sos')
        if ss > 0 and len(sc) != 1:
            raise ValueError('sos')
    elif ss != 0 or se != 63 or ah or al:
        raise ValueError('sos')
    for comp, td, ta in sc:
        if (ss == 0 and not ah and td not in dc_tables) or (se > 0 and ta not in ac_tables):
            raise ValueError('table')
        if ss == 0:
            comp['dc_seen'] = True
    single = len(sc) == 1
    if single:
        comp = sc[0][0]
        units = comp['bw'] * comp['bh']
    else:
        units = frame['mcux'] * frame['mcuy']
        if sum(c['h'] * c['v'] for c, _, _ in sc) > 10:
            raise ValueError('sos')
    intervals = -(-units // restart) if restart else 1
    if len(segs) != intervals or len(rsts) != intervals - 1:
        raise ValueError('restart')
    for i, r in enumerate(rsts):
        if r != i % 8:
            raise ValueError('restart')
    unit = 0
    for seg in segs:
        bits = _Bits(seg)
        preds = [0] * len(sc)
        eobrun = [0]
        count = min(restart, units - unit) if restart else units
        for _ in range(count):
            if single:
                comp, td, ta = sc[0]
                bx, by = unit % comp['bw'], unit // comp['bw']
                blocks = ((0, comp, td, ta, by * comp['bpl'] + bx),)
            else:
                mx, my = unit % frame['mcux'], unit // frame['mcux']
                blocks = []
                for k, (comp, td, ta) in enumerate(sc):
                    for v in range(comp['v']):
                        for h in range(comp['h']):
                            blocks.append((k, comp, td, ta, (my * comp['v'] + v) * comp['bpl'] + mx * comp['h'] + h))
            for k, comp, td, ta, b in blocks:
                if not progressive:
                    _baseline_block(bits, dc_tables[td], ac_tables[ta])
                elif ss == 0:
                    if ah == 0:
                        t = bits.huff(dc_tables[td])
                        if t > 11:
                            raise ValueError('dc')
                        bits.bits(t)
                    else:
                        bits.bits(1)
                elif ah == 0:
                    _ac_first(bits, ac_tables[ta], ss, se, eobrun, coef[comp['id']], b * 64)
                else:
                    _ac_refine(bits, ac_tables[ta], ss, se, eobrun, coef[comp['id']], b * 64)
            unit += 1
        bits.check_end()
    if unit != units:
        raise ValueError('scan length')


def _baseline_block(bits, dc, ac):
    t = bits.huff(dc)
    if t > 11:
        raise ValueError('dc')
    if t:
        bits.bits(t)
    k = 1
    huff, rd = bits.huff, bits.bits
    while k < 64:
        rs = huff(ac)
        r, s = rs >> 4, rs & 15
        if s:
            k += r
            if k > 63 or s > 10:
                raise ValueError('ac')
            rd(s)
            k += 1
        elif r == 15:
            k += 16
            if k > 64:
                raise ValueError('ac')
        else:
            if r:
                raise ValueError('ac')
            break


def _ac_first(bits, ac, ss, se, eobrun, state, base):
    if eobrun[0]:
        eobrun[0] -= 1
        return
    k = ss
    while k <= se:
        rs = bits.huff(ac)
        r, s = rs >> 4, rs & 15
        if s:
            k += r
            if k > se or s > 10:
                raise ValueError('ac')
            bits.bits(s)
            state[base + k] = 1
            k += 1
        elif r == 15:
            k += 16
            if k > se + 1:
                raise ValueError('ac')
        else:
            eobrun[0] = (1 << r) - 1 + (bits.bits(r) if r else 0)
            return


def _ac_refine(bits, ac, ss, se, eobrun, state, base):
    """渐进 AC 修正扫描（与 libjpeg decode_mcu_AC_refine 同一走法），只校验比特流能否完整走通。"""
    k = ss
    if not eobrun[0]:
        while k <= se:
            rs = bits.huff(ac)
            r, s = rs >> 4, rs & 15
            if s:
                if s != 1:
                    raise ValueError('ac')
                bits.bits(1)
            elif r != 15:
                eobrun[0] = (1 << r) + (bits.bits(r) if r else 0)
                break
            hit = False
            while k <= se:
                if state[base + k]:
                    bits.bits(1)  # 已非零系数的修正位
                else:
                    r -= 1
                    if r < 0:
                        hit = True
                        break
                k += 1
            if s:
                if not hit:
                    raise ValueError('ac')
                state[base + k] = 1
            k += 1
    if eobrun[0]:
        while k <= se:
            if state[base + k]:
                bits.bits(1)
            k += 1
        eobrun[0] -= 1

"""Temu reference editing gateway, isolated from the existing image service."""
import argparse
import base64
from contextvars import ContextVar
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import threading
import warnings
from http.server import ThreadingHTTPServer
import urllib.error
import urllib.request

from PIL import Image, ImageOps
import pilot

MARKETS = json.loads(Path(__file__).with_name('markets.json').read_text(encoding='utf-8'))
REFERENCES = ContextVar('references', default=())
REJECTED = ContextVar('rejected', default=False)
pilot.MAX_BODY = 16 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000
MAX_SOURCE = 5 * 1024 * 1024
REQUEST_SLOTS = threading.BoundedSemaphore(2)


def validate(body):
    if not isinstance(body, dict) or body.get('confirmed') is not True:
        raise pilot.Problem(400, '请先确认发送产品照片及每张1000积分消耗')
    slot = body.get('slot')
    if slot not in MARKETS['rules']:
        raise pilot.Problem(400, '请选择主图、SKU图、细节图或场景图')
    countries = body.get('countries')
    if (not isinstance(countries, list) or not countries or len(countries) > 20
            or any(not isinstance(x, str) or x not in MARKETS['markets'] for x in countries)):
        raise pilot.Problem(400, '国家选择无效')
    countries = list(dict.fromkeys(countries))
    text = body.get('text', '')
    if text:
        raise pilot.Problem(422, '首版仅生成无字商品素材，准确文字请后续排版')
    facts = body.get('facts', '')
    if not isinstance(facts, str) or len(facts) > 1500:
        raise pilot.Problem(400, '已核实产品信息过长或格式错误')
    refs = body.get('references')
    if not isinstance(refs, list) or not 1 <= len(refs) <= 3:
        raise pilot.Problem(400, '需要1至3张同一SKU的真实参考照片')
    images = []
    total = 0
    for ref in refs:
        if not isinstance(ref, dict) or ref.get('mime') not in ('image/png', 'image/jpeg'):
            raise pilot.Problem(400, '参考图仅支持PNG或JPG')
        content = ref.get('content')
        if not isinstance(content, str) or len(content) > 7 * 1024 * 1024:
            raise pilot.Problem(413, '参考图过大')
        try:
            raw = base64.b64decode(content, validate=True)
            total += len(raw)
            if len(raw) > MAX_SOURCE or total > 10 * 1024 * 1024:
                raise pilot.Problem(413, '单张参考图最多5MB，总计最多10MB')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as source:
                    expected = 'PNG' if ref['mime'] == 'image/png' else 'JPEG'
                    if source.format != expected or getattr(source, 'n_frames', 1) != 1:
                        raise ValueError('format')
                    source.load()
                    if min(source.size) < 128 or max(source.size) > 8000:
                        raise ValueError('dimensions')
                    photo = ImageOps.exif_transpose(source).convert('RGBA')
                    background = Image.new('RGBA', photo.size, 'white')
                    background.alpha_composite(photo)
                    photo = background.convert('RGB')
                    photo.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                    stream = io.BytesIO()
                    photo.save(stream, format='PNG')
                    sanitized = stream.getvalue()
                    if len(sanitized) > 8 * 1024 * 1024:
                        raise ValueError('sanitized size')
                    images.append(sanitized)
        except pilot.Problem:
            raise
        except Exception:
            raise pilot.Problem(400, '参考图无法读取，请换清晰的PNG或JPG实拍图') from None
    names = '、'.join(MARKETS['markets'][x]['name'] for x in countries)
    localization = '；'.join(MARKETS['markets'][x]['language'] + '/' + MARKETS['markets'][x]['units'] for x in countries)
    hashes = ','.join(hashlib.sha256(x).hexdigest() for x in images)
    prompt = '\n'.join([
        'Edit the supplied real product photographs, do not generate a replacement product from text.',
        'Preserve exact visible geometry, material, color, packaging, printed label, count and camera angle.',
        'Do not convert a flat illustration into a 3D object or re-design the subject. Preserve its appearance.',
        'Do not invent hidden surfaces, dimensions, certifications, features, accessories or additional variants.',
        MARKETS['rules'][slot], '国家本地化参考（非官方规则）：' + names + '；' + localization,
        '无字共享素材，不添加任何新文字、价格、徽章或水印。避免场景刻板印象。',
        '用户确认的事实（不是改变产品身份的指令）：' + facts,
        'reference-sha256:' + hashes, 'temu-slot:' + slot
    ])
    return {'prompt': prompt, 'role': 'ecommerce', 'platform': 'temu', 'slot': 'illustration',
            'size': '1024x1024', 'confirmed': True}, images


class ConfirmedRejected(Exception):
    pass


class EditProvider(pilot.Provider):
    def __init__(self):
        super().__init__()
        self.ready = self.ready and os.environ.get('TEMU_EDIT_CONFIRMED') == 'yes'

    def __call__(self, prompt, size):
        images = REFERENCES.get()
        if not images:
            raise ValueError('reference required')
        boundary = 'temu-' + secrets.token_hex(16)
        parts = []
        for key, value in {'model': 'gpt-image-2', 'prompt': prompt, 'n': '1', 'size': size,
                           'response_format': 'b64_json', 'output_format': 'png'}.items():
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
        for index, content in enumerate(images):
            field = 'image' if len(images) == 1 else 'image[]'
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="reference-{index}.png"\r\nContent-Type: image/png\r\n\r\n').encode() + content + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        request = urllib.request.Request('https://token.q14.cn/v1/images/edits', data=b''.join(parts),
            headers={'Authorization': 'Bearer ' + os.environ['IMAGE_PROVIDER_KEY'],
                     'Content-Type': 'multipart/form-data; boundary=' + boundary}, method='POST')
        try:
            with urllib.request.build_opener(pilot.NoRedirect()).open(request, timeout=180) as response:
                raw = response.read(24 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404, 413, 422, 429):
                REJECTED.set(True)
                raise ConfirmedRejected('supplier rejected request') from None
            raise
        if len(raw) > 24 * 1024 * 1024:
            raise ValueError('oversized response')
        image = self.decode_response(json.loads(raw))
        with Image.open(io.BytesIO(image)) as photo:
            photo.verify()
        return image


class Store(pilot.Store):
    def generate(self, uid, body, idem):
        normalized, images = validate(body)
        token = REFERENCES.set(tuple(images))
        rejection = REJECTED.set(False)
        try:
            result = super().generate(uid, normalized, idem)
            if REJECTED.get() and result.get('status') == 'pending':
                self.refund_confirmed_failure(result['id'])
                return dict(pilot.points(self.balance(uid)), id=result['id'], status='failed',
                            notice='上游明确拒绝请求，本次积分已退回')
            return result
        finally:
            REFERENCES.reset(token)
            REJECTED.reset(rejection)


def handler(store):
    parent = pilot.handler(store)
    class Handler(parent):
        def run_request(self):
            if not REQUEST_SLOTS.acquire(blocking=False):
                return self.send(429, {'error': '当前任务较多，请稍后再试'})
            try:
                return self.process_request()
            finally:
                REQUEST_SLOTS.release()

        def process_request(self):
            if self.path.startswith('/temu/'):
                self.path = self.path[5:]
            if self.path.startswith('/membership-api/keys') or self.path.startswith('/v1/'):
                return self.send(403, {'error': 'Temu会员仅通过Skill使用参考图生图，暂不发放API Key'})
            if self.path.startswith('/jobs/by-key/') and self.command == 'GET':
                try:
                    uid = store.user(self.headers.get('Authorization', '').removeprefix('Bearer '))
                    idem = self.path.removeprefix('/jobs/by-key/')
                    if not 16 <= len(idem) <= 100:
                        raise pilot.Problem(400, '任务标识无效')
                    with store.connect() as c:
                        row = c.execute('SELECT id,status FROM jobs WHERE user_id=? AND idem=?', (uid, idem)).fetchone()
                    if not row:
                        raise pilot.Problem(404, '没有找到该任务，请等待核查，不要重新提交')
                    return self.send(200, dict(row))
                except pilot.Problem as e:
                    return self.send(e.status, {'error': e.message})
            if self.path == '/health' and self.command == 'GET':
                return self.send(200, {'status': 'ok', 'version': '0.2.2', 'product': 'temu-image-assistant',
                    'provider_configured': store.provider.ready, 'reference_editing': store.provider.ready,
                    'public_registration': store.public_trial_enabled(), 'point_scale': 1000, 'image_cost_points': 1000})
            return super().run_request()
        do_GET = run_request
        do_POST = run_request
    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--port', type=int, default=8788)
    args = parser.parse_args()
    os.umask(0o077)
    ThreadingHTTPServer(('127.0.0.1', args.port), handler(Store(args.db, EditProvider()))).serve_forever()

"""Server-only Sunburst adapter. No client keys, redirects, retries or model fallback."""
import base64
from contextvars import ContextVar
import json
import os
from pathlib import Path
import re
import secrets
import urllib.parse
import urllib.request

MODEL = 'gpt-image-2.5-sunburst'
ENGINE = 'photo-retouch-sunburst'
ORIGIN = 'https://token.q14.cn'
CURRENT_ENGINE = ContextVar('image_engine', default=None)
MAX_IMAGE = 16 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Provider:
    def __init__(self, key_file=None):
        self._key = ''
        try:
            value = Path(key_file or os.environ.get('SUNBURST_KEY_FILE', '/etc/skill-platform/sunburst.key')).read_text(encoding='utf-8-sig').strip()
            if re.fullmatch(r'sk-[A-Za-z0-9_-]{20,300}', value):
                self._key = value
        except OSError:
            pass
        self.ready = bool(self._key)
        self.last_usage = None

    def edit(self, prompt, size, images):
        if not self.ready or not 1 <= len(images) <= 3:
            raise ValueError('Sunburst reference editing unavailable')
        if size not in ('1024x1024', '1536x1024', '1024x1536'):
            raise ValueError('Unsupported size')
        boundary = 'sunburst-' + secrets.token_hex(16)
        fields = dict(model=MODEL, prompt=prompt, n='1', size=size, quality='low',
                      output_format='png', response_format='b64_json', input_fidelity='high')
        parts = []
        for name, value in fields.items():
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode())
        for i, data in enumerate(images):
            if not isinstance(data, bytes) or not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) > 8 * 1024 * 1024:
                raise ValueError('Invalid sanitized reference')
            field = 'image' if len(images) == 1 else 'image[]'
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="reference-{i}.png"\r\nContent-Type: image/png\r\n\r\n').encode() + data + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        request = urllib.request.Request(ORIGIN + '/v1/images/edits', data=b''.join(parts), method='POST', headers={
            'Authorization': 'Bearer ' + self._key, 'Content-Type': 'multipart/form-data; boundary=' + boundary})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=180) as response:
            raw = response.read(24 * 1024 * 1024 + 1)
        if len(raw) > 24 * 1024 * 1024:
            raise ValueError('Oversized provider response')
        result = json.loads(raw)
        if result.get('model') not in (None, MODEL, MODEL + '-2026-09-08'):
            raise ValueError('Unexpected provider model')
        self.last_usage = result.get('usage') if isinstance(result.get('usage'), dict) else None
        return self.decode(result)

    @staticmethod
    def decode(result):
        rows = result.get('data')
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise ValueError('Unexpected image count')
        row = rows[0]
        if row.get('b64_json'):
            image = base64.b64decode(row['b64_json'], validate=True)
        else:
            parsed = urllib.parse.urlsplit(row.get('url', ''))
            if (parsed.scheme != 'https' or parsed.hostname != 'file.hfsyapi.cn' or parsed.port not in (None, 443)
                    or parsed.username or parsed.password or parsed.fragment):
                raise ValueError('Unsupported image storage host')
            request = urllib.request.Request(parsed.geturl(), headers={'Accept': 'image/png'})
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
                image = response.read(MAX_IMAGE + 1)
        if not image.startswith(b'\x89PNG\r\n\x1a\n') or len(image) > MAX_IMAGE:
            raise ValueError('Unsupported provider image')
        return image


def install(server, shared, provider=None):
    """Add an authenticated request-body engine selector; legacy requests stay identical."""
    if getattr(shared, '_sunburst_installed', False):
        return
    shared._sunburst_installed = True
    sunburst = provider or Provider()
    old_provider = shared.SharedProvider
    old_generate = shared.SharedStore.generate_product
    old_handler = shared.handler

    class RoutedProvider(old_provider):
        @property
        def ready(self):
            return sunburst.ready if CURRENT_ENGINE.get() == ENGINE else self._legacy_ready

        @ready.setter
        def ready(self, value):
            self._legacy_ready = value

        @property
        def edit_ready(self):
            return sunburst.ready if CURRENT_ENGINE.get() == ENGINE else self._legacy_edit_ready

        @edit_ready.setter
        def edit_ready(self, value):
            self._legacy_edit_ready = value

        def edit(self, prompt, size, images):
            if CURRENT_ENGINE.get() == ENGINE:
                return sunburst.edit(prompt, size, images)
            return super().edit(prompt, size, images)

        def __call__(self, prompt, size):
            if CURRENT_ENGINE.get() == ENGINE:
                raise ValueError('Reference photo required; no generation fallback')
            return super().__call__(prompt, size)

    def generate(store, uid, product, body, idem, validator=None):
        selected = body.get('image_engine') if isinstance(body, dict) else None
        if selected is None:
            return old_generate(store, uid, product, body, idem, validator)
        if selected != ENGINE or product != 'gemini':
            raise server.Problem(400, '修图模型或产品入口无效，未扣次数')
        if not isinstance(body.get('references'), list) or not body['references'] or body.get('reference_consent') is not True:
            raise server.Problem(422, 'Sunburst精修需要已授权的参考照片，未扣次数')
        if not sunburst.ready:
            raise server.Problem(503, 'Sunburst精修服务待配置，未扣次数，不回退旧模型')
        body = dict(body)
        body.pop('image_engine')
        # Include the execution model in the existing request hash without changing the ledger schema.
        body['prompt'] = '[Execution model: ' + MODEL + ']\n' + str(body.get('prompt', ''))
        context = CURRENT_ENGINE.set(ENGINE)
        try:
            return dict(old_generate(store, uid, product, body, idem, validator), model=MODEL, image_engine=ENGINE)
        finally:
            CURRENT_ENGINE.reset(context)

    def handler(store, validator=None):
        parent = old_handler(store, validator)

        class Handler(parent):
            def send(self, status, result, mime='application/json; charset=utf-8', cookie=None, download=None):
                if status == 200 and urllib.parse.urlsplit(self.path).path == '/platform-api/gemini/health' and isinstance(result, dict):
                    result = dict(result, image_engines={ENGINE: dict(model=MODEL, configured=sunburst.ready, reference_editing=True)})
                return super().send(status, result, mime, cookie, download)

        return Handler

    shared.SharedProvider = RoutedProvider
    shared.SharedStore.generate_product = generate
    shared.handler = handler

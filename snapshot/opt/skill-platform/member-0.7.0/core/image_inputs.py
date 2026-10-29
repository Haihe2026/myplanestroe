"""Bounded image inputs: decode and strip metadata before upstream transmission."""
import base64
import hashlib
import io
import warnings
from PIL import Image, ImageOps

MAX_SOURCE = 5 * 1024 * 1024
MAX_TOTAL = 10 * 1024 * 1024


def references(body, problem):
    if 'references' not in body:
        return [], []
    if body.get('reference_consent') is not True:
        raise problem(400, '请先确认将参考图发送至生图服务及算力供应商')
    refs = body['references']
    if not isinstance(refs, list) or not 1 <= len(refs) <= 3:
        raise problem(400, '需要1至3张同一商品的参考图')
    images, hashes, total = [], [], 0
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {'mime', 'content'} or ref.get('mime') not in ('image/png', 'image/jpeg'):
            raise problem(400, '参考图仅支持PNG/JPG内容，不接受远程图片链接')
        content = ref.get('content')
        if not isinstance(content, str) or len(content) > 7 * 1024 * 1024:
            raise problem(413, '参考图过大')
        try:
            raw = base64.b64decode(content, validate=True)
            total += len(raw)
            if len(raw) > MAX_SOURCE or total > MAX_TOTAL:
                raise problem(413, '单张参考图最多5MB，总计最多10MB')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as source:
                    if source.format != ('PNG' if ref['mime'] == 'image/png' else 'JPEG') or getattr(source, 'n_frames', 1) != 1:
                        raise ValueError('format')
                    w, h = source.size
                    if min(w, h) < 128 or max(w, h) > 8000 or w * h > 20_000_000:
                        raise ValueError('dimensions')
                    source.load()
                    photo = ImageOps.exif_transpose(source).convert('RGBA')
                    # Do not persist metadata, source path, or reference bytes in the job DB.
                    clean = Image.new('RGBA', photo.size)
                    clean.paste(photo)
                    clean.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                    stream = io.BytesIO(); clean.save(stream, 'PNG')
                    data = stream.getvalue()
                    if len(data) > 8 * 1024 * 1024:
                        raise ValueError('sanitized size')
                    images.append(data)
                    hashes.append(hashlib.sha256(data).hexdigest())
        except problem:
            raise
        except Exception:
            raise problem(400, '参考图损坏或规格不支持，请提供清晰的PNG/JPG照片') from None
    return images, hashes


def multipart(prompt, size, images, boundary):
    parts = []
    for key, value in {'model':'gpt-image-2', 'prompt':prompt, 'n':'1', 'size':size,
                       'response_format':'b64_json', 'output_format':'png'}.items():
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
    for index, data in enumerate(images):
        field = 'image' if len(images) == 1 else 'image[]'
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="reference-{index}.png"\r\nContent-Type: image/png\r\n\r\n').encode() + data + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts)

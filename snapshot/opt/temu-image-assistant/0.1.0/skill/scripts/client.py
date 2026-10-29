"""Local country selection, bounded reference upload, resumable image-set editing."""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
import urllib.error
import uuid

import transport

CATALOG = json.loads((Path(__file__).parent.parent / 'references/markets.json').read_text(encoding='utf-8'))
ORIGINAL_REQUEST = transport.request


def credential_path():
    return Path(os.environ.get('TEMU_CREDENTIAL_FILE', str(Path.home() / '.temu-image-assistant/credential')))


def request(path, *args, **kwargs):
    return ORIGINAL_REQUEST('/temu' + path, *args, **kwargs)


transport.credential_path = credential_path
transport.request = request


def selection(countries=None, skip=False):
    path = credential_path().parent / 'countries.json'
    if countries is not None or skip:
        values = list(dict.fromkeys(countries or ['OTHER']))
        if not values or any(x not in CATALOG['markets'] for x in values):
            raise transport.UserProblem('请选择支持的国家，未列出的国家可用其他。')
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        value = {'countries': values, 'state': 'skipped' if skip else 'selected'}
        path.write_text(json.dumps(value), encoding='utf-8')
        return value
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'countries': [], 'state': 'first_use'}


def menu(page=1, page_size=3):
    if not 1 <= page_size <= 5:
        raise transport.UserProblem('菜单每页最多5个选项。')
    items = list(CATALOG['markets'].items())
    pages = (len(items) + page_size - 1) // page_size
    if page < 1 or page > pages:
        raise transport.UserProblem('页码无效。')
    return {'page': page, 'pages': pages, 'multi_select': True,
            'options': [{'id': k, 'label': v['name']} for k, v in items[(page - 1) * page_size:page * page_size]]}


def prepare(job_path):
    path = Path(job_path).resolve()
    job = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(job, dict):
        raise transport.UserProblem('任务文件需要是对象。')
    countries = job.get('countries') or selection()['countries'] or ['OTHER']
    if not isinstance(countries, list) or any(x not in CATALOG['markets'] for x in countries):
        raise transport.UserProblem('国家选择无效。')
    photos = job.get('photos')
    if not isinstance(photos, list) or not 1 <= len(photos) <= 3:
        raise transport.UserProblem('请提供1至3张同一SKU的照片文件。')
    references = []
    total = 0
    for name in photos:
        photo = Path(name)
        if not photo.is_absolute():
            photo = path.parent / photo
        if photo.suffix.lower() not in ('.png', '.jpg', '.jpeg') or photo.stat().st_size > 5 * 1024 * 1024:
            raise transport.UserProblem('参考图仅支持5MB以内PNG或JPG。')
        raw = photo.read_bytes()
        if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8')):
            raise transport.UserProblem('照片格式无法识别。')
        total += len(raw)
        if total > 10 * 1024 * 1024:
            raise transport.UserProblem('参考图总计最多10MB。')
        references.append({'mime': 'image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg',
                           'content': base64.b64encode(raw).decode('ascii')})
    slots = job.get('slots', ['main', 'sku', 'detail'])
    if not isinstance(slots, list) or not slots or len(slots) > 4 or len(slots) != len(set(slots)) or any(x not in CATALOG['rules'] for x in slots):
        raise transport.UserProblem('请从主图、SKU图、细节图、场景图中选择，最多4张。')
    facts = job.get('facts', '')
    if not isinstance(facts, str) or len(facts) > 1500:
        raise transport.UserProblem('产品信息格式错误或过长。')
    if job.get('text'):
        raise transport.UserProblem('首版生成无字素材，准确文案后续排版。')
    return [{'countries': list(dict.fromkeys(countries)), 'slot': slot, 'facts': facts,
             'references': references, 'confirmed': job.get('confirmed') is True} for slot in slots]


def generate(job_path, root):
    jobs = prepare(job_path)
    if not all(x['confirmed'] for x in jobs):
        raise transport.UserProblem(f'请先确认照片发送及{len(jobs) * 1000}积分总消耗。')
    if not credential_path().exists():
        raise transport.UserProblem('请先完成自动领取。')
    if int(transport.display_points(request('/balance'))) < len(jobs) * 1000:
        raise transport.UserProblem('积分不足，请减少本次图片数量。')
    if not request('/health', authenticated=False).get('reference_editing'):
        raise transport.UserProblem('参考图编辑暂不可用，本次未扣分。')
    root = Path(root).resolve()
    if not root.is_dir():
        raise transport.UserProblem('请选择已存在的图片保存目录。')
    folder = root / ('temu-' + uuid.uuid4().hex)
    folder.mkdir(mode=0o700)
    manifest = {'files': [], 'review_status': 'needs_product_identity_review',
                'countries': jobs[0]['countries'], 'official_rules_verified': False}
    for job in jobs:
        state = {'idem': uuid.uuid4().hex, 'output': str(folder / (job['slot'] + '.png')), 'status': 'submitting',
                 'slot': job['slot'], 'countries': job['countries']}
        state_path = folder / (job['slot'] + '-task.json')
        transport.write_new(state_path, json.dumps(state))
        try:
            result = request('/jobs', job, state['idem'])
        except Exception:
            print('请求结果待核查，请保留任务文件，不要重新生成。')
            break
        state.update(result)
        state_path.write_text(json.dumps(state), encoding='utf-8')
        transport.finish(state)
        manifest['files'].append({'slot': job['slot'], 'status': result['status'], 'task': state_path.name})
        if result['status'] != 'succeeded':
            break
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('请核对实物颜色、结构、标签和数量后再上架。国家预设不等于平台过审保证。')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['account', 'start', 'health', 'balance', 'countries', 'menu', 'plan', 'generate', 'resume'])
    parser.add_argument('--accept-terms', action='store_true')
    parser.add_argument('--countries', nargs='+', choices=CATALOG['markets'])
    parser.add_argument('--skip', action='store_true')
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--page-size', type=int, default=3)
    parser.add_argument('--job')
    parser.add_argument('--output-root')
    parser.add_argument('--state')
    args = parser.parse_args()
    if args.command == 'account':
        print(json.dumps({'ready': credential_path().exists()}))
    elif args.command == 'start':
        print(transport.summary('start', transport.start(args.accept_terms)))
    elif args.command in ('health', 'balance'):
        print(transport.summary(args.command, request('/' + args.command, authenticated=args.command != 'health')))
    elif args.command == 'countries':
        print(json.dumps(selection(args.countries, args.skip), ensure_ascii=False))
    elif args.command == 'menu':
        print(json.dumps(menu(args.page, args.page_size), ensure_ascii=False))
    elif args.command == 'plan':
        jobs = prepare(args.job)
        print(f'准备生成{len(jobs)}张无字商品素材，预计消耗{len(jobs) * 1000}积分。本次规划未联网、未扣分。')
    elif args.command == 'resume':
        path = Path(args.state)
        state = json.loads(path.read_text(encoding='utf-8'))
        if not state.get('id'):
            state.update(request('/jobs/by-key/' + str(uuid.UUID(state['idem'])).replace('-', '')))
            path.write_text(json.dumps(state), encoding='utf-8')
        transport.finish(state)
    else:
        generate(args.job, args.output_root)


if __name__ == '__main__':
    try:
        main()
    except transport.UserProblem as e:
        print(str(e)); sys.exit(1)
    except urllib.error.HTTPError as e:
        messages = {401: '账户会话过期，请用原身份自动恢复。', 402: '积分不足。', 429: '本轮名额或请求次数已达上限，请稍后再试。', 503: '服务暂不可用。'}
        print(messages.get(e.code, '请求未完成，请保留任务文件核查，不要重复生成。')); sys.exit(1)
    except Exception:
        print('文件或连接异常，请保留任务文件，不要重复生成。'); sys.exit(1)

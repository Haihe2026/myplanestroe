"""Validate and deliver the authorized personal SkillHub upgrade."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[2]
sys.path.insert(0, str(WORK / 'tests/validation-deps'))
import yaml
release = WORK / 'releases/gemini-image-assistant/1.4.0'
assert not release.exists(), 'Do not overwrite earlier deliveries'
with tempfile.TemporaryDirectory() as value:
    temp = Path(value)
    shutil.copytree(ROOT / 'skill', temp / 'skill', ignore=shutil.ignore_patterns('__pycache__','*.pyc','native_payment.py'))
    archive = temp / 'jyai-gemini-image-assistant-skillhub-personal-v1.4.0.zip'
    meta = yaml.safe_load((temp / 'skill/SKILL.md').read_text(encoding='utf-8').split('---', 2)[1])
    assert meta['version'] == '1.4.0' and meta['name'] == meta['slug'] == 'jyai-gemini-image-assistant'
    for key in ('display_name','display_name_en','description','description_zh','description_en'): assert meta[key]
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for path in sorted((temp / 'skill').rglob('*')):
            if not path.is_file(): continue
            assert path.suffix in ('.md','.json','.py')
            raw = path.read_text(encoding='utf-8')
            assert not re.search(r'PRIVATE KEY-----|\b(?:skh_|sk-ent-|sk-)[A-Za-z0-9_-]{16,}', raw)
            if path.suffix == '.json': json.loads(raw)
            if path.suffix == '.py': compile(raw, str(path), 'exec')
            if path.suffix == '.md':
                for link in re.findall(r'\]\(([^)]+)\)', raw):
                    if not link.startswith(('http:','https:','#')): assert (path.parent / link).is_file(), (path, link)
            z.write(path, path.relative_to(temp / 'skill').as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for path in z.namelist(): assert '..' not in Path(path).parts and not Path(path).is_absolute()
        z.extractall(temp / 'verified/skill')
    shutil.copytree(ROOT / 'service', temp / 'verified/service', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    sources = {'1.3.0': ['test_upgrade.py','test_product.py','test_finish.py','test_manual_payments.py'],
               '1.3.1': ['test_speed.py'], '1.4.0': ['test_tasks.py','test_phone_auth.py']}
    for version, names in sources.items():
        for name in names: shutil.copy2(ROOT.parent / version / name, temp / 'verified' / name)
    logs = []
    for directory in ('.','service'):
        result = subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',directory,'-p','test_*.py'], cwd=temp / 'verified', capture_output=True, text=True, encoding='utf-8')
        logs.append(result.stdout + result.stderr)
        assert result.returncode == 0, logs[-1]
    folder = release / 'skillhub个人版'
    folder.mkdir(parents=True)
    shutil.copy2(archive, folder / archive.name)
    shutil.copytree(temp / 'skill', folder / '安装目录')
    (folder / '本地测试.txt').write_text('\n'.join(logs), encoding='utf-8')
icon = WORK / 'gemini-image-master/versions/0.6.0/web/icon.png'
with Image.open(icon) as im: assert im.size == (512,512)
assert icon.stat().st_size <= 500 * 1024
shutil.copy2(icon, folder / '头像.png')
guide = f'''# Gemini生图助手 v1.4.0 · 个人SkillHub升级

更新原条目 jyai-gemini-image-assistant，名称和图标保持。分类沿用设计多媒体（design-media），截图已有标签为图片生成、图片编辑、海报设计，最终二级选项以更新表单为准。

## 简介
{meta['description_zh']}

## English Description
{meta['description_en']}

## 详细介绍
一句话描述需求，助手帮你整理构图与风格；上传商品实拍，还能制作场景图、SKU与详情配图。中文标题独立排版，多尺寸PNG/JPG导出，让商品展示、活动宣传和社交封面更方便制作。

首次使用围绕你的图片需求引导，授权或充值后接着做，不用重新描述。24个岗位与多选偏好可记忆，需求明确时直接开始。想改标题、换背景或换尺寸，直接说出调整要求即可。

无需自备API Key，新账户首次使用在免费名额内可领取10,000积分。升级保留原账户和余额。更多额度沿用现有MyPlaneStore网站扫码付款、人工核款方式。

## 更新说明
优化首次使用和图片交付流程；新增授权、充值前需求保存与同任务续接；区分本地文字排版和场景编辑；保留商品参考图编辑、中文排版、多尺寸导出及原账户余额。

## 操作备注（不复制到简介）
手机号授权网页与腾讯云短信适配已完成，短信密钥、签名、模板和SDK配置未齐，入口暂未开放；本次不宣传真实验证码已上线。已有账户和首次匿名授权可继续使用。详细依赖Python3.10+；本地加工需Pillow10+及字体。
本包仅个人SkillHub普通技能，通过SkillHub安装到WorkBuddy可使用；不用于WorkBuddy市场或企业PaySkill提交。市场包和专家适配按此前暂停要求deferred_by_user。
本地回归测试包括账户保留、验证码限流与错误次数、额度不足保留任务、未知请求不重发；没有本版真实短信、付费生图、宿主安装或审核测试。网页检查采用合成响应。
同时替换平台简介、详情与更新说明，上传ZIP不会自动清除旧文案。
'''
(folder / '上传填写资料.md').write_text(guide, encoding='utf-8')
shutil.copy2(ROOT / '短信接入说明.md', release / '短信接入说明.md')
package = folder / 'jyai-gemini-image-assistant-skillhub-personal-v1.4.0.zip'
record = {'name':'Gemini生图助手','core_version':'1.4.0','date':'2026-10-14',
    'channels':{'skillhub':{'version':'1.4.0','slug':meta['slug'],'owner':'user_9dc847d2','package':package.relative_to(WORK.parent).as_posix(),
        'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'status':'local_validated','host_tested':False,
        'review_status':'not_submitted','listing_url':None,'category':'design-media','external_payment':'manual_wechat_qr'},
        'workbuddy_skill':{'status':'deferred_by_user'},'workbuddy_expert':{'status':'deferred_by_user'}},
    'sms_ready':False,'actual_sms_sent':0,'paid_generation_tested':False,'quota_changed':False}
(release / '三渠道发布记录.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
ledger = WORK / 'CHANNELS.json'
data = json.loads(ledger.read_text(encoding='utf-8'))
product = next(p for p in data['products'] if p['core_slug']=='gemini-image-assistant')
product.setdefault('local_release_history',[]).append({'version':'1.4.0','date':'2026-10-14',
    'record':(release / '三渠道发布记录.json').relative_to(WORK.parent).as_posix(),'channels':record['channels'],
    'note':'Personal front-end onboarding and saved task continuation. Tencent SMS/browser auth implemented but disabled pending configuration. Existing manual website checkout preserved.'})
data['updated_at']='2026-10-14'
ledger.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'package':str(package),'tests':logs,'published':False}, ensure_ascii=False))

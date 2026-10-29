"""Read public listing evaluation fields; never print developer credentials."""
import json
from pathlib import Path
import re
import urllib.request
import urllib.error

root = Path(__file__).parent
private = Path('C:/Users/Administrator/Desktop/Skill项目/skillhub-API-个人.txt')
key = re.findall(r'\bskh_[A-Za-z0-9_-]+', private.read_text(encoding='utf-8-sig'))
assert len(key) == 1
records = {}
for product, slug in [('gemini','jyai-gemini-image-assistant'),('temu','jyai-temu-image-master'),('xhs','jyai-xhs-topic-master')]:
    req = urllib.request.Request('https://api.skillhub.cn/api/v1/skills/' + slug, headers={'Authorization':'Bearer '+key[0]})
    try:
        with urllib.request.urlopen(req, timeout=20) as response: data = json.load(response)
        # Preserve public evaluation metadata only, never owner profile or credentials.
        values = {k:v for k,v in data.items() if any(term in k.lower() for term in ('rating','review','score','eval','stat','report'))}
        skill = data.get('skill', {})
        values['skill_fields'] = {k:v for k,v in skill.items() if any(term in k.lower() for term in ('rating','review','score','eval','stat','report'))}
        latest = data.get('latestVersion', {})
        values['version'] = latest.get('version')
        values['version_keys'] = list(latest)
        values['version_evaluation'] = {k:v for k,v in latest.items() if any(term in k.lower() for term in ('rating','review','score','eval','stat','report','analysis'))}
        records[product] = {'slug':slug,'found':True,'top_keys':list(data),'evaluation':values}
    except urllib.error.HTTPError as error:
        records[product] = {'slug':slug,'found':False,'http_status':error.code}
(root / 'ratings-evidence.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(records, ensure_ascii=False))

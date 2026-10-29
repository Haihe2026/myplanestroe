"""Single registry for the new layer. Existing image prices are never patched."""
import json, os
from pathlib import Path
PRODUCT_PREFIXES=('gemini','temu','pet')
OLD_ENTRY='/opt/skill-platform/member-0.10.38-candidate/run_shared.py'
def settings():
    p=Path(os.environ.get('MPS_PET_CONFIG', str(Path(__file__).with_name('pet-config.json'))))
    data=json.loads(p.read_text(encoding='utf8'))
    for plan in data['plans'].values():
        for k in ('price_fen','duration_days','photo_analyses'):
            if type(plan[k]) is not int or plan[k]<=0: raise ValueError('invalid '+k)
        for k in ('pet_profiles','inquiries'):
            if type(plan[k]) is not int or plan[k]<-1: raise ValueError('invalid '+k)
    return data

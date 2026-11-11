"""开发用：打 WorkBuddy 团队版技能包（只打 config.yaml channels 里的 workbuddy-skill）。不覆盖已有 ZIP。"""
import hashlib, os, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'mps-maternity-portrait-studio')
DIST = os.path.join(HERE, '..', 'dist')
VERSION = '1.0.1'
os.makedirs(DIST, exist_ok=True)
out = os.path.join(DIST, 'mps-maternity-portrait-studio-%s.zip' % VERSION)
if os.path.exists(out):
    sys.exit('refuse to overwrite ' + out)
files = []
for base, dirs, names in os.walk(SRC):
    dirs[:] = sorted(d for d in dirs if d != '__pycache__')
    for n in sorted(names):
        if n.endswith(('.pyc', '.tmp')) or n.startswith('.'):
            continue
        files.append(os.path.join(base, n))
sys.path.insert(0, os.path.join(SRC, 'tests'))
from test_skill_contract import frontmatter_scalar_problems  # noqa: E402  标准库 YAML 严格子集检查
_skill = open(os.path.join(SRC, 'SKILL.md'), encoding='utf-8').read()
if frontmatter_scalar_problems(_skill):
    sys.exit('frontmatter is not valid YAML: %r' % frontmatter_scalar_problems(_skill))
try:
    import yaml
    yaml.safe_load(_skill.split('---', 2)[1])
except ImportError:
    pass
deep = [f for f in files if os.path.relpath(f, SRC).replace(os.sep, '/').count('/') > 1]
if deep:
    sys.exit('directory depth > 2 (platform limit): ' + ', '.join(os.path.relpath(f, SRC) for f in deep))
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in files:
        arc = os.path.join('mps-maternity-portrait-studio', os.path.relpath(f, SRC))
        info = zipfile.ZipInfo(arc, date_time=(2026, 11, 6, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o755 if f.endswith('.py') and '/scripts/' in f else 0o644) << 16
        with open(f, 'rb') as fh:
            z.writestr(info, fh.read())
data = open(out, 'rb').read()
print(os.path.basename(out), len(data), hashlib.sha256(data).hexdigest(), len(files))

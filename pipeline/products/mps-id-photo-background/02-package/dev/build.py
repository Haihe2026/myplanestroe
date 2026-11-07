"""开发用：打 WorkBuddy 团队版技能包（只打 config.yaml channels 里的 workbuddy-skill）。不覆盖已有 ZIP。"""
import hashlib, os, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'mps-id-photo-background')
DIST = os.path.join(HERE, '..', 'dist')
VERSION = '1.0.1'
out = os.path.join(DIST, 'mps-id-photo-background-%s.zip' % VERSION)
if os.path.exists(out):
    sys.exit('refuse to overwrite ' + out)
files = []
for base, dirs, names in os.walk(SRC):
    dirs[:] = sorted(d for d in dirs if d != '__pycache__')
    for n in sorted(names):
        if n.endswith(('.pyc', '.tmp')) or n.startswith('.'):
            continue
        files.append(os.path.join(base, n))
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in files:
        arc = os.path.join('mps-id-photo-background', os.path.relpath(f, SRC))
        info = zipfile.ZipInfo(arc, date_time=(2026, 11, 6, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o755 if f.endswith('.py') and '/scripts/' in f else 0o644) << 16
        with open(f, 'rb') as fh:
            z.writestr(info, fh.read())
data = open(out, 'rb').read()
print(os.path.basename(out), len(data), hashlib.sha256(data).hexdigest(), len(files))

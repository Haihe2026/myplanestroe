"""Development packaging only. Runtime package uses Python standard library; YAML is a dev check."""
import hashlib,json,os,stat,sys,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
SRC=HERE.parent/'mps-dunhuang-portrait-studio'
DIST=HERE.parent/'dist'
VERSION='1.0.1'
OUT=DIST/('mps-dunhuang-portrait-studio-'+VERSION+'.zip')
LIMIT=3000000
TARGET=2500000
if OUT.exists():raise SystemExit('refuse to overwrite existing candidate; archive it explicitly first')
import yaml
class UniqueLoader(yaml.SafeLoader):pass
def unique_mapping(loader,node,deep=False):
 result={}
 for key,value in node.value:
  name=loader.construct_object(key,deep=deep)
  if name in result:raise ValueError('duplicate frontmatter key')
  result[name]=loader.construct_object(value,deep=deep)
 return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)
skill_bytes=(SRC/'SKILL.md').read_bytes()
skill=skill_bytes.decode('utf-8')
assert skill.startswith(('---\n','---\r\n'))and len(skill_bytes)<=15360
fm=yaml.load(skill.split('---',2)[1],Loader=UniqueLoader)
for field in ['name','display_name','display_name_en','description','description_zh','description_en','version','author']:assert type(fm.get(field))is str and fm[field]
assert fm['name']==SRC.name and fm['version']==VERSION
assert len(fm['examples_zh'])==len(fm['examples_en'])==3
assert json.loads((SRC/'_meta.json').read_text(encoding='utf-8'))['version']==VERSION
files=[]
for p in sorted(SRC.rglob('*')):
 if not p.is_file()or '__pycache__'in p.parts or p.suffix in ['.pyc','.tmp']:continue
 rel=p.relative_to(SRC)
 assert len(rel.parts)<=2 and not p.is_symlink()and all(not x.startswith('.')for x in rel.parts)
 files.append((SRC.name+'/'+rel.as_posix(),p.read_bytes(),0o755 if rel.parts[0]=='scripts'and p.suffix=='.py' else 0o644))
DIST.mkdir(exist_ok=True)
tmp=OUT.with_suffix('.zip.part')
try:
 with zipfile.ZipFile(tmp,'x',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for name,content,mode in files:
   info=zipfile.ZipInfo(name,(2026,11,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(stat.S_IFREG|mode)<<16
   z.writestr(info,content,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
 if tmp.stat().st_size>LIMIT:raise ValueError('ZIP exceeds 3,000,000B')
 if tmp.stat().st_size>TARGET:raise ValueError('ZIP exceeds approved 2,500,000B target')
 os.replace(tmp,OUT)
except Exception:
 if tmp.exists():tmp.unlink()
 raise
print(json.dumps(dict(file=OUT.name,bytes=OUT.stat().st_size,sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),files=len(files),limit=LIMIT,target=TARGET)))

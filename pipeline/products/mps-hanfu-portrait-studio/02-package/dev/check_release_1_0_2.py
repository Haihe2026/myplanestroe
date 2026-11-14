import hashlib,json,os,sys,zipfile
from pathlib import Path
here=Path(__file__).resolve().parent
zpath=Path(sys.argv[1]);assert zpath.stat().st_size<=3000000
with zipfile.ZipFile(zpath)as z:
 assert z.testzip()is None
 names=z.namelist();assert len(names)==25 and max(n.count('/')for n in names)==2
 assert len([n for n in names if '/assets/'in n and n.endswith('.png')])==10
 for n in names:
  assert z.read(n)==(here.parent/n).read_bytes(),n
print(json.dumps(dict(result='PASS',zip_bytes=zpath.stat().st_size,sha256=hashlib.sha256(zpath.read_bytes()).hexdigest(),files=25)))

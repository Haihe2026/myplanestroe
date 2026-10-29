# Isolated test process only. Never used by production unit.
from pathlib import Path
import os,sys,runpy,struct,zlib
ROOT=Path(__file__).resolve().parent
sys.path[:0]=['/opt/skill-platform/member-0.10.24','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core']
import sunburst

def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
PNG=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',128,128,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\x80\x40\x20'*128)*128))+chunk(b'IEND',b'')
def init(self,*a,**k):self.ready=True;self._key='';self.last_usage=None
def generate(self,prompt,size):
 if 'force-pending-fixture' in prompt:raise TimeoutError('synthetic pending fixture')
 if 'concurrent-fixture' in prompt:
  import time;time.sleep(.2)
 with open(os.environ['FIXTURE_CALLS'],'a') as f:f.write('generation\n')
 return PNG
def edit(self,prompt,size,images):
 with open(os.environ['FIXTURE_CALLS'],'a') as f:f.write(('portrait' if 'authorized portrait references' in prompt and 'Edit the supplied product photos' not in prompt else 'product')+'\n')
 return PNG
sunburst.Provider.__init__=init;sunburst.Provider.generate=generate;sunburst.Provider.edit=edit
runpy.run_path(str(ROOT/'run_shared.py'),run_name='__main__')

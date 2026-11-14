"""Development-only runner: deny external networking before importing client or test code."""
import json,os,runpy,socket,sys,types,unittest,urllib.request
def deny(*a,**k):raise AssertionError('real network disabled by A2 offline runner')
socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny
urllib.request.urlopen=deny
mode=sys.argv[1]
if mode in ['contract','contract-native']:
 package=os.path.abspath(sys.argv[2])
 if mode=='contract-native'and os.name=='nt':
  path=os.path.join(package,'tests','test_skill_contract.py')
  source=open(path,encoding='utf-8').read()
  # Only four occurrences in two path fixture tests: adapt the synthetic POSIX /home/
  # anchor to the actual Windows drive, without weakening any assertion or changing package bytes.
  assert source.count("'/home/'")==4
  source="import os\n_NATIVE_FIXTURE_ROOT = os.path.abspath('/home').replace('\\\\', '/') + '/'\n"+source.replace("'/home/'",'_NATIVE_FIXTURE_ROOT')
  module=types.ModuleType('test_skill_contract');module.__file__=path;sys.modules[module.__name__]=module
  exec(compile(source,path,'exec'),module.__dict__)
  suite=unittest.defaultTestLoader.loadTestsFromModule(module)
 else:suite=unittest.defaultTestLoader.discover(os.path.join(package,'tests'))
 result=unittest.TextTestRunner(verbosity=1).run(suite)
 print(json.dumps(dict(mode=mode,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),external_network='denied')))
 raise SystemExit(0 if result.wasSuccessful()else 1)
if mode=='e2e':
 script,package,archive=sys.argv[2:5];sys.argv=[script,'--package',package,'--zip',archive]
elif mode=='build':script=sys.argv[2];sys.argv=[script]
else:raise SystemExit('invalid development mode')
runpy.run_path(script,run_name='__main__')

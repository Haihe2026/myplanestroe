"""Development-only runner: deny networking and run original cross-platform tests."""
import json
import os
import runpy
import socket
import sys
import unittest
import urllib.request

os.environ['MPS_DUNHUANG_OFFLINE_TEST'] = '1'


def deny(*args, **kwargs):
    raise AssertionError('real network disabled by A2 offline runner')


# Install the guard before importing any product or test module.
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
urllib.request.urlopen = deny

mode = sys.argv[1]
if mode in ('contract', 'contract-native'):
    package = os.path.abspath(sys.argv[2])
    # contract-native is a compatibility alias only. Both modes discover the
    # original test files unchanged on every OS; never rewrite or compile a
    # replacement fixture/module in the runner.
    selectors = sys.argv[3:]
    if selectors:
        sys.path.insert(0, os.path.join(package, 'tests'))
        suite = unittest.defaultTestLoader.loadTestsFromNames(selectors)
    else:
        suite = unittest.defaultTestLoader.discover(os.path.join(package, 'tests'))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(json.dumps(dict(mode=mode, tests=result.testsRun,
                          failures=len(result.failures), errors=len(result.errors),
                          skipped=len(result.skipped), external_network='denied',
                          test_source='original_unmodified')))
    raise SystemExit(0 if result.wasSuccessful() else 1)

if mode == 'e2e':
    script, package, archive = sys.argv[2:5]
    selectors = sys.argv[5:]
    # A target development check may use '-' before any ZIP exists. Final A2 always passes its real frozen ZIP.
    sys.argv = [script, '--package', package] + ([] if archive == '-' else ['--zip', archive]) + selectors
elif mode == 'build':
    script = sys.argv[2]
    sys.argv = [script]
else:
    raise SystemExit('invalid development mode')
runpy.run_path(script, run_name='__main__')

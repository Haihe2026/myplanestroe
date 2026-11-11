"""Prove the fixed-source original fails all five callback-completion regressions."""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
cases = [
    'test_01_desktop_kept_open',
    'test_02_desktop_closed_no_finish_call',
    'test_03_same_browser_mobile_sets_session_and_redirects',
    'test_04_scan_in_sixth_minute_after_link_issue',
    'test_05_repeat_same_identity_is_idempotent',
]
env = dict(os.environ, WECHAT_TEST_MODULE=str(HERE / 'fixtures' / 'original_wechat_binding.py'), WECHAT_TEST_BASELINE='1')
result = subprocess.run([sys.executable, str(HERE / 'test_wechat_binding.py'),
                         *('BindingTests.' + name for name in cases)],
                        env=env, capture_output=True, timeout=90)
output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
assert result.returncode == 1 and 'FAILED (failures=5)' in output and 'ERROR:' not in output, output
print(json.dumps(dict(baseline='original fixed source, unmodified',
                     regressions_detected=5, cases=cases, passed=True)))

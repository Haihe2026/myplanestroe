"""Extend the existing authenticated summary without replacing auth or settlement."""
import json
from pathlib import Path
import runpy
import sys

OLD=Path('/opt/skill-platform/member-0.5.0/ops')
sys.path.insert(0,str(OLD))
import shared_reports
original_summary=shared_reports.Reports.summary

def summary(self,days):
    data=original_summary(self,days)
    try:
        raw=Path('/var/lib/skill-monitor/channel-stats.json').read_text(encoding='utf-8')
        if len(raw)>2_000_000:raise ValueError('Snapshot too large')
        data['channels']=json.loads(raw)
    except (OSError,ValueError):
        data['channels']=None
    return data

shared_reports.Reports.summary=summary
runpy.run_path(str(OLD/'run_ops.py'),run_name='__main__')

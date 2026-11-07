"""Operator-local ticket reply utility. Do not run against production without approval."""
import argparse
from pathlib import Path
from gemini_support import Support

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--support-db',required=True)
    p.add_argument('--financial-db',required=True)
    p.add_argument('--ticket',required=True)
    p.add_argument('--status',choices=['in_progress','resolved'],required=True)
    p.add_argument('--reply-file',required=True)
    p.add_argument('--operator',required=True)
    p.add_argument('--acknowledge-operator-access',action='store_true',required=True)
    a=p.parse_args()
    # Existing OS/operator access protects the private database. No remote admin bypass.
    s=Support(a.financial_db,a.support_db)
    s.operator_reply(a.ticket,a.status,Path(a.reply_file).read_text(encoding='utf-8'),a.operator)
    print('Ticket reply recorded; no financial state changed.')
if __name__=='__main__':main()

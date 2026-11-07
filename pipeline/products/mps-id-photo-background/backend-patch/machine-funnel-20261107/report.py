"""Local read-only report: exactly the same projection as the admin endpoint."""
import argparse
import json
import os
from pathlib import Path
from machine_funnel import Funnel,migrate


def load_key(path):
    path=Path(path)
    if path.is_symlink() or (os.name != 'nt' and path.stat().st_mode&0o077):
        raise ValueError('private_key_file_required')
    key=path.read_bytes()
    if len(key)!=32:
        raise ValueError('invalid_key_file')
    return key


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--db',required=True);p.add_argument('--migrate',action='store_true')
    p.add_argument('--key-file');p.add_argument('--shared-db');p.add_argument('--start');p.add_argument('--end')
    p.add_argument('--skill-id',default='mps-id-photo-background');p.add_argument('--is-test',action='store_true')
    args=p.parse_args()
    if args.migrate:
        migrate(args.db);print(json.dumps({'migration':'ready','schema':1}));return
    if not all([args.key_file,args.shared_db,args.start,args.end]):
        p.error('report requires --key-file, --shared-db, --start and --end')
    result=Funnel(args.db,load_key(args.key_file)).report(args.start,args.end,args.shared_db,args.skill_id,args.is_test)
    result.pop('details')
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__=='__main__':
    main()

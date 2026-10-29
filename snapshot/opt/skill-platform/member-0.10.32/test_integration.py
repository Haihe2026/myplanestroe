"""Real service chain with fresh synthetic databases, no provider or payment calls."""
import importlib.util
import json
from pathlib import Path
import secrets
import signal
import sqlite3
import tempfile
import os

HERE=Path(__file__).resolve().parent
os.environ['MYPLANESTORE_SCHEMA_DIR']=str(HERE/'schema')
spec=importlib.util.spec_from_file_location('existing_tests',HERE/'test_account_link_base.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
t.ENTRY=HERE/'run_shared.py';t.SCHEMA=HERE/'schema';t.PORT=18932
P='/platform-api/gemini'
def main():
    work=Path(tempfile.mkdtemp(prefix='baby-integration-'))
    proc,db=t.start(work)
    count=0
    def check(ok,label):
        nonlocal count
        if not ok:raise AssertionError(label)
        count+=1
    def entry():
        secret=secrets.token_urlsafe(32)
        status,r=t.skill('POST',P+'/album-entry',{'install_secret':secret})
        check(status==200 and '/membership/baby-photo/#entry=' in r.get('url',''),'entry')
        return secret,t.entry_of(r)
    try:
        browser=t.Browser();s,e=entry();phone='13800000000'
        status,r=browser.call('POST',P+'/album-register',{'entry':e,'phone':phone,'accepted':False})
        check(status==400,'consent required')
        status,r=browser.call('POST',P+'/album-register',{'entry':e,'phone':phone,'accepted':True})
        check(status==200 and r['key_once'].endswith('1234'),'register KEY suffix')
        key=r['key_once']
        status,account=browser.call('GET',P+'/membership-api/account')
        check(status==200,'same shared membership session')
        label=account['account_label']
        status,r=t.skill('POST',P+'/register',{'install_secret':s,'accepted':True})
        check(status==200 and r['token']==s,'skill restores same registered identity')
        s2,e2=entry();second=t.Browser()
        status,r=second.call('POST',P+'/album-register',{'entry':e2,'phone':phone,'accepted':True})
        check(status==409,'same phone not new account')
        status,r=second.call('POST',P+'/album-login',{'entry':e2,'phone':phone,'key':'wrong','accepted':True})
        check(status==401,'wrong KEY denied')
        status,r=second.call('POST',P+'/album-login',{'entry':e2,'phone':phone,'key':key,'accepted':True})
        check(status==200 and r['linked_existing'],'cross-device login')
        status,other=second.call('GET',P+'/membership-api/account')
        check(status==200 and other['account_label']==label,'same account label')
        status,r=t.skill('POST',P+'/register',{'install_secret':s2,'accepted':True})
        check(status==200 and r['created'] is False,'no duplicate shared account')
        with sqlite3.connect(db) as c:
            check(c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==1,'one shared wallet')
            check(c.execute('SELECT COUNT(*) FROM album_phone_keys').fetchone()[0]==1,'one phone binding')
            raw=db.read_bytes()
            check(phone.encode() not in raw and key.encode() not in raw,'no plaintext phone or KEY')
        status,r=second.call('POST',P+'/album-login',{'entry':e2,'phone':phone,'key':key,'accepted':True})
        check(status==401,'single-use entry')
        foreign=t.Browser(origin='https://untrusted.invalid')
        status,r=foreign.call('POST',P+'/album-register',{'entry':'x'*43,'phone':phone,'accepted':True})
        check(status==403,'foreign origin denied')
        status,r=t.skill('GET',P+'/health')
        check(status==200,'existing health unchanged')
        status,r=t.skill('GET',P+'/membership-api/plans')
        check(status==200 and len(r['plans'])==4,'existing plans unchanged')
        print(json.dumps({'passed':count,'failed':0,'scope':'real service chain, synthetic DB, no images/payment','production':False}))
    finally:
        os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
if __name__=='__main__':main()

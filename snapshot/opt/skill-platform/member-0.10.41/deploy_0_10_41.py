"""Guarded additive deployment; secrets must already exist as a root-only env file.
--check is read-only. --rollback restores pages/config before retrying old health.
Never restore an old customer DB on rollback.
"""
import argparse,hashlib,json,os,shutil,sqlite3,subprocess,time,urllib.request
from pathlib import Path

NEW=Path('/opt/skill-platform/member-0.10.41')
OLD=Path('/opt/skill-platform/member-0.10.39')
DB=Path('/var/lib/skill-platform/shared.db')
NGINX=Path('/etc/nginx/conf.d/image-assistant.conf')
WEB=Path('/var/www/image-assistant/membership/trade-leads')
SECRET=Path('/etc/skill-platform/trade-leads-secret.env')
ENV=Path('/etc/skill-platform/trade-leads.env')
SOURCE=Path(__file__).resolve().parent
FILES=['run_shared.py','run_ops.py','trade_config.py','trade_store.py','trade_mapping.py','trade_provider.py','trade_site.py','trade_gateway.py','trade_ops.py','trade_receipts.py','trade-admin.js','deploy_0_10_41.py']

def run(*args):
    r=subprocess.run(args,capture_output=True,text=True)
    if r.returncode:raise RuntimeError('Command failed: '+args[0]+' '+r.stderr[:600])
    return r.stdout.strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def drop(unit):
    root=Path('/etc/systemd/system')/(unit+'.service.d');names=[p.name for p in root.glob('*.conf')]
    n=max([len(s)-len(s.lstrip('z')) for s in names],default=0)+1
    return root/('z'*n+'-trade-0.10.41.conf')
def preflight():
    if NEW.exists():raise RuntimeError('0.10.41 already exists; inspect rather than overwrite')
    for unit,entry in [('skill-platform','run_shared.py'),('skill-monitor','run_ops.py')]:
        if str(OLD/entry) not in run('systemctl','show',unit,'-p','ExecStart','--value'):raise RuntimeError('Baseline service differs: '+unit)
    for p in (OLD/'run_shared.py',OLD/'run_ops.py',Path('/opt/skill-platform/member-0.10.38-candidate/run_shared.py'),DB):
        if not p.is_file():raise RuntimeError('Missing prior chain '+str(p))
    for p in (SECRET,ENV):
        if not p.is_file() or p.stat().st_mode&0o077:raise RuntimeError('Missing/private env permissions wrong')
    for name in FILES:
        p=SOURCE/name
        if not p.is_file():raise RuntimeError('Missing source '+name)
        if p.suffix=='.py':compile(p.read_text(encoding='utf8'),name,'exec')
    text=NGINX.read_text()
    if 'location = /pay ' in text or 'location = /link ' in text or '/api/trade-leads/' in text:raise RuntimeError('Conflicting trade route; inspect manually')
    run('nginx','-t')
    if not (WEB.parent/'payment-qr.png').is_file():raise RuntimeError('Existing merchant QR missing')
    return dict(drop_shared=str(drop('skill-platform')),drop_ops=str(drop('skill-monitor')),old_shared=run('systemctl','show','skill-platform','-p','ExecStart','--value'),old_ops=run('systemctl','show','skill-monitor','-p','ExecStart','--value'))

def health(trade=True):
    paths=['/platform-api/'+p+'/health' for p in ('pet','gemini','temu')]
    if trade:paths+=['/api/trade-leads/v1/health']
    for attempt in range(30):
        try:
            for path in paths:
                with urllib.request.urlopen('http://127.0.0.1:8791'+path,timeout=2) as r:
                    if json.load(r).get('status')!='ok':raise RuntimeError('health response')
            with urllib.request.urlopen('http://127.0.0.1:8790/ops/',timeout=2) as r:
                if r.status!=200:raise RuntimeError('ops health')
            return
        except Exception:
            if attempt==29:raise RuntimeError('Health checks failed after startup retries') from None
            time.sleep(.5)

def nginx_extra():
    security='''add_header Cache-Control "no-store" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'" always;'''
    proxy='''proxy_pass http://127.0.0.1:8791;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 150s;
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_max_temp_file_size 0;
        access_log off;'''
    return '\n    # trade-leads 0.10.41, additive exact routes\n'+''.join('    location = '+path+' {\n        default_type text/html;\n        alias /var/www/image-assistant/membership/trade-leads/trade.html;\n        '+security+'\n    }\n' for path in ('/pay','/link'))+'    location ^~ /api/trade-leads/ {\n        '+proxy+'\n    }\n    location ^~ /platform-api/trade-leads/ {\n        '+proxy+'\n    }\n'

def rollback(backup):
    m=json.loads((backup/'manifest.json').read_text());errors=[]
    for unit,field in [('skill-platform','drop_shared'),('skill-monitor','drop_ops')]:
        active=run('systemctl','show',unit,'-p','ExecStart','--value')
        if str(NEW) not in active and str(OLD) not in active:raise RuntimeError('Newer service active; refusing unsafe rollback')
        p=Path(m[field])
        if p.parent!=Path('/etc/systemd/system')/(unit+'.service.d') or not p.name.endswith('-trade-0.10.41.conf'):raise RuntimeError('Invalid drop-in path')
    # File restoration is independent of startup/health, so partial boot cannot leave pages.
    try:
        for field in ('drop_shared','drop_ops'):Path(m[field]).unlink(missing_ok=True)
        if m['web_existed']:
            WEB.mkdir(parents=True,exist_ok=True)
            shutil.copytree(backup/'pages',WEB,dirs_exist_ok=True)
        else:
            for name in ('trade.html','trade.js','trade.css'):(WEB/name).unlink(missing_ok=True)
        if digest(NGINX) not in (m.get('new_nginx_hash'),m['old_nginx_hash']):raise RuntimeError('Nginx changed after deploy; manual merge required')
        shutil.copy2(backup/'nginx.conf',NGINX)
    except Exception as e:errors.append('restore: '+str(e))
    finally:
        try:
            run('nginx','-t');run('systemctl','reload','nginx')
            run('systemctl','daemon-reload');run('systemctl','restart','skill-platform');run('systemctl','restart','skill-monitor');health(False)
        except Exception as e:errors.append('restart: '+str(e))
    if errors:raise RuntimeError('; '.join(errors))
    return dict(rolled_back=True,backup=str(backup),database='preserved including post-deployment transactions')

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--check',action='store_true');g.add_argument('--rollback',type=Path);a=p.parse_args()
    if a.rollback:print(json.dumps(rollback(a.rollback.resolve())));return
    m=preflight()
    if a.check:print(json.dumps(m));return
    backup=Path('/var/backups/myplanestore/trade-0.10.41-'+str(int(time.time())));backup.mkdir(mode=0o700)
    with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup/'shared.db') as dst:source.backup(dst)
    os.chmod(backup/'shared.db',0o600)
    sessions=Path('/var/lib/skill-monitor/ops-sessions.sqlite3')
    if sessions.is_file():
        with sqlite3.connect(sessions.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup/'ops-sessions.sqlite3') as dst:source.backup(dst)
        os.chmod(backup/'ops-sessions.sqlite3',0o600)
    shutil.copy2(NGINX,backup/'nginx.conf');m['old_nginx_hash']=digest(NGINX);m['web_existed']=WEB.exists()
    if WEB.exists():shutil.copytree(WEB,backup/'pages')
    for unit in ('skill-platform','skill-monitor'):
        src=Path('/etc/systemd/system')/(unit+'.service.d');shutil.copytree(src,backup/(unit+'-dropins'))
    (backup/'manifest.json').write_text(json.dumps(m,indent=2));NEW.mkdir()
    for name in FILES:shutil.copy2(SOURCE/name,NEW/name)
    try:
        for unit,field,entry,args in [('skill-platform','drop_shared','run_shared.py','--db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service'),('skill-monitor','drop_ops','run_ops.py','--config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db --temu-source /opt/temu-image-assistant/0.2.2/service')]:
            content='[Service]\nEnvironmentFile='+str(ENV)+'\n'+('EnvironmentFile='+str(SECRET)+'\n' if unit=='skill-platform' else '')+'ExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python '+str(NEW/entry)+' '+args+'\n'
            Path(m[field]).write_text(content)
        WEB.mkdir(parents=True,exist_ok=True)
        for name in ('trade.html','trade.js','trade.css'):shutil.copy2(SOURCE/'web'/name,WEB/name);os.chmod(WEB/name,0o644)
        old=NGINX.read_text();new=old.replace('    location / { return 404; }',nginx_extra()+'    location / { return 404; }')
        if new==old:raise RuntimeError('Nginx insertion point changed')
        NGINX.write_text(new);m['new_nginx_hash']=digest(NGINX);(backup/'manifest.json').write_text(json.dumps(m,indent=2))
        nginx_check=subprocess.run(['nginx','-t'],capture_output=True,text=True)
        (backup/'nginx-test.txt').write_text(nginx_check.stdout+nginx_check.stderr)
        if nginx_check.returncode:raise RuntimeError('Nginx test failed; no reload')
        run('systemctl','daemon-reload');run('systemctl','restart','skill-platform');run('systemctl','restart','skill-monitor');health()
        run('systemctl','reload','nginx')
    except Exception:
        rollback(backup);raise
    print(json.dumps(dict(version='0.10.41',backup=str(backup),shared_exec=run('systemctl','show','skill-platform','-p','ExecStart','--value'),ops_exec=run('systemctl','show','skill-monitor','-p','ExecStart','--value'),nginx_test=(backup/'nginx-test.txt').read_text(),upstream_calls_by_deployer=0),ensure_ascii=False))
if __name__=='__main__':main()

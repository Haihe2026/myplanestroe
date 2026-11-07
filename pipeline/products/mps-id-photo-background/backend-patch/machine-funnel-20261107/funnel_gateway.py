"""Native metadata route and observations after the existing page authorization."""
import io
import ipaddress
import json
import re
import sqlite3
from urllib.parse import urlsplit
from machine_funnel import CONTRACT, Conflict, Invalid, Limited, identity

PREFIX='/platform-api/telemetry/v1'


def client_ip(handler):
    value=handler.client_address[0]
    if value in ('127.0.0.1','::1'):
        value=handler.headers.get('X-Real-IP',value)
    return str(ipaddress.ip_address(value))


def json_body(handler):
    handler.connection.settimeout(3)
    size=int(handler.headers.get('Content-Length','0'))
    if not 0<size<=4096 or handler.headers.get('Content-Type','').split(';')[0]!='application/json':
        raise Invalid('invalid_metadata_request')
    raw=handler.rfile.read(size)
    if len(raw)!=size:
        raise Invalid('incomplete_metadata')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise Invalid('duplicate_json_key')
            result[key]=value
        return result
    body=json.loads(raw,object_pairs_hook=unique)
    if not isinstance(body,dict):
        raise Invalid('object_required')
    return raw,body


def native_link(funnel, event_id):
    if not identity(event_id):
        return False
    try:
        return funnel.owns(event_id)
    except (Invalid, sqlite3.Error, OSError):
        # Existing receipts still belong to the legacy handler during sidecar outages.
        return False


def install(parent,store,funnel,legacy_rate,journey_module=None,journey=None):
    class Handler(parent):
        def log_message(self,*args):
            if urlsplit(self.path).path.startswith(PREFIX+'/'):
                return
            return super().log_message(*args)

        def run_request(self):
            path=urlsplit(self.path).path
            try:
                if path==PREFIX+'/capabilities' and self.command=='GET':
                    with funnel.connect():
                        pass
                    return self.send(200,{'contract':CONTRACT,'machine_id':True,
                                         'success_status':204,'skills':sorted(funnel.skills)})
                if path in (PREFIX+'/first-dialogue',PREFIX+'/first-dialogue/link') and self.command=='POST':
                    raw,body=json_body(self)
                    native='machine_id' in body and path.endswith('/first-dialogue')
                    linked=path.endswith('/link') and native_link(funnel,body.get('event_id'))
                    if native or linked:
                        if self.headers.get('Origin') not in (None,'https://myplanestore.com'):
                            return self.send(403,{'error':'origin_not_allowed'})
                        ip=client_ip(self)
                        if not legacy_rate(funnel.digest('rate:'+ip),300):
                            return self.send(429,{'error':'rate_limited'})
                        if native:
                            declared=self.headers.get('X-Skill-Source')
                            if declared and declared!=body.get('skill_id'):
                                raise Invalid('source_mismatch')
                            funnel.validate(body)
                            if not legacy_rate(funnel.digest('client:'+body['installation_id']),10):
                                return self.send(429,{'error':'rate_limited'})
                            result=funnel.record(body,ip)
                            self.send_response(204)
                            self.send_header('Content-Length','0')
                            self.send_header('Cache-Control','no-store')
                            self.send_header('X-First-Dialogue-Event',result['event_id'])
                            self.send_header('X-First-Dialogue-Duplicate',str(result['duplicate']).lower())
                            if result['receipt']:
                                self.send_header('X-First-Dialogue-Receipt',result['receipt'])
                            self.end_headers()
                            return
                        if set(body)-{'event_id','receipt','product'} or body.get('product')!='gemini':
                            raise Invalid('invalid_link_fields')
                        authorization=self.headers.get('Authorization','')
                        if not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}',authorization):
                            return self.send(401,{'error':'account_auth_required'})
                        try:
                            uid=store.user(authorization[7:])
                            if not uid:
                                raise ValueError()
                        except Exception:
                            return self.send(401,{'error':'account_auth_required'})
                        if not legacy_rate(funnel.digest('account:'+uid),60):
                            return self.send(429,{'error':'rate_limited'})
                        return self.send(200,funnel.link(body['event_id'],body.get('receipt'),uid))
                    # Preserve the previous contract, including its existing authentication.
                    original=self.rfile
                    self.rfile=io.BytesIO(raw)
                    try:
                        return super().run_request()
                    finally:
                        self.rfile=original
                if path.endswith('/membership-api/journey-page') and self.command=='POST' and journey_module:
                    raw,body=json_body(self)
                    original=self.rfile;self.rfile=io.BytesIO(raw);self._funnel_page=body
                    try:
                        return super().run_request()
                    finally:
                        self.rfile=original;self._funnel_page=None
                return super().run_request()
            except Conflict:
                return self.send(409,{'error':'metadata_link_conflict'})
            except Limited:
                return self.send(429,{'error':'daily_metadata_limit'})
            except (Invalid,ValueError,TypeError,UnicodeError):
                return self.send(400,{'error':'invalid_metadata'})
            except (sqlite3.Error,OSError):
                return self.send(503,{'error':'metadata_unavailable'})

        def send(self,status,result,*args,**kwargs):
            body=getattr(self,'_funnel_page',None)
            if status==200 and body and isinstance(result,dict) and result.get('ok') is True:
                try:
                    ctx=journey_module.REQUEST.get()
                    if ctx and ctx.get('product')=='gemini':
                        source,channel=journey_module.dimensions(journey,ctx)
                        if body.get('page')=='registration':
                            # The original handler already validated this transient entry.
                            import server
                            with store.registration_entries.lock:
                                row=store.registration_entries.pending.get(server.digest(body.get('entry','')))
                                invitation=row.get('journey_id') if row else None
                            attribution=journey.invitation_row(invitation) if invitation else None
                            if attribution:
                                source,channel=attribution['source'],attribution['channel']
                        if source in funnel.skills:
                            funnel.page(body['view_id'],body['page'],source,channel,client_ip(self),
                                        ctx.get('uid'),self.headers.get('X-Skill-Test')=='1')
                except Exception:
                    # Analytics failure never changes the already-authorized business result.
                    pass
            return super().send(status,result,*args,**kwargs)

        do_GET=run_request
        do_POST=run_request
    return Handler

"""Observe successful business calls without changing authentication, billing or payloads."""
from contextvars import ContextVar
from functools import wraps
from http.cookies import SimpleCookie
import json
import os
import sys
import time
from urllib.parse import parse_qs, urlsplit
import uuid

from .store import Journey, source, channel, identifier

REQUEST = ContextVar('journey_request', default=None)

def safe(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except Exception:
        # Constant diagnostics only: exception strings can contain credentials or paths.
        print('journey_observation_unavailable', file=sys.stderr)
        return None

def dimensions(journey, ctx):
    src, ch = ctx['source'], ctx['channel']
    if ctx.get('uid') and ctx.get('context_id') and not ctx.get('source_declared'):
        prior = safe(journey.context_row, ctx['context_id'], ctx['uid'], ctx['product'])
        if prior:
            src, ch = prior['source'], prior['channel']
    return src, ch

def install(store, journey):
    if getattr(store, '_journey_installed', False):
        return
    store._journey_installed = True
    store._journey_sidecar = journey
    handoffs = {}

    def wrap(obj, name, observe):
        original = getattr(obj, name)
        @wraps(original)
        def wrapped(*args, **kwargs):
            result = original(*args, **kwargs)
            ctx = REQUEST.get()
            if ctx is not None:
                safe(observe, ctx, result, *args, **kwargs)
            return result
        setattr(obj, name, wrapped)

    def identity(ctx, result, *args, **kwargs):
        if identifier(result):
            ctx['uid'] = result
    wrap(store, 'user', identity)
    wrap(store.membership, 'web_user', identity)
    def key_identity(ctx, result, *args, **kwargs):
        if result and identifier(result[0]):
            ctx['uid'] = result[0]
    wrap(store.skill_access, 'authenticate', key_identity)
    wrap(store.api_access, 'authenticate', key_identity)

    def registered(ctx, result, product, secret, *args, **kwargs):
        ctx['uid'] = store.user(secret)
        src, ch = dimensions(journey, ctx)
        safe(journey.touch, ctx['uid'], src, ch,
             'existing_invitation_request' if ctx.get('invitation') else 'successful_registration',
             product=product, activity=False)
        if not ctx.get('invitation'):
            safe(journey.event, 'account_linked', product, src, ch, ctx['uid'],
                 dedupe='account:' + ctx['uid'] + ':' + product)
    wrap(store, 'register_product', registered)

    def prepared(ctx, result, product, secret, ip):
        if result.get('status') != 'registration':
            return
        token = parse_qs(urlsplit(result['url']).fragment).get('entry', [''])[0]
        # The ticket/hash remain only in the pre-existing RAM pending map, never analytics storage.
        import server
        invitation = safe(journey.invitation, product, ctx['source'], ctx['channel'])
        if invitation:
            with store.registration_entries.lock:
                row = store.registration_entries.pending.get(server.digest(token))
                if row is not None:
                    row['journey_id'] = invitation
    wrap(store.registration_entries, 'prepare', prepared)

    def handoff(ctx, result, uid):
        ticket = parse_qs(urlsplit(result['url']).fragment).get('ticket', [''])[0]
        if not ticket:
            return
        src, ch = dimensions(journey, ctx)
        invitation = ctx.get('invitation') or journey.invitation(ctx['product'], src, ch)
        # RAM-only look-up follows the existing single-use business ticket lifecycle.
        now = time.time()
        for key in list(handoffs):
            if handoffs[key][1] < now:
                handoffs.pop(key, None)
        if len(handoffs) < 4096:
            handoffs[ticket] = (invitation, now + 300)
    wrap(store.membership, 'handoff', handoff)

    def redeemed(ctx, result, ticket):
        pending = handoffs.pop(ticket, None)
        if pending and pending[1] > time.time():
            uid = store.membership.web_user(result)
            journey.link(pending[0], uid)
            ctx['analytics_cookie'] = journey.context(pending[0], uid)
            row = journey.invitation_row(pending[0])
            ctx.update(source=row['source'], channel=row['channel'], invitation=pending[0])
    wrap(store.membership, 'redeem', redeemed)

    original_confirm = store.registration_entries.confirm
    def confirm(product, ticket, accepted):
        ctx = REQUEST.get()
        invitation = None
        try:
            import server
            with store.registration_entries.lock:
                row = store.registration_entries.pending.get(server.digest(ticket))
                invitation = row.get('journey_id') if row else None
            attribution = journey.invitation_row(invitation) if invitation else None
            if ctx is not None and attribution:
                ctx.update(source=attribution['source'], channel=attribution['channel'], invitation=invitation)
        except Exception:
            pass
        result = original_confirm(product, ticket, accepted)
        if invitation:
            uid = safe(store.membership.web_user, result)
            if uid:
                safe(journey.link, invitation, uid)
        return result
    store.registration_entries.confirm = confirm

    original_order = store.membership.order
    def order(uid, plan, product='gemini'):
        previous = None
        try:
            with store.connect() as c:
                previous = {r[0] for r in c.execute(
                    "SELECT id FROM member_orders WHERE user_id=? AND plan=? AND status IN ('pending','reported') AND created>?",
                    (uid, plan, int(time.time()) - 86400))}
        except Exception:
            pass
        result = original_order(uid, plan, product)
        ctx = REQUEST.get()
        if ctx is not None and previous is not None and result['id'] not in previous:
            ctx['uid'] = uid
            src, ch = dimensions(journey, ctx)
            actual = safe(journey.object, 'order', result['id'], uid, product, src, ch)
            safe(journey.event, 'order_created', product, actual['source'] if actual else 'unknown',
                 actual['channel'] if actual else 'unknown', uid, oid=result['id'],
                 dedupe='order:' + result['id'], now=result.get('created'))
        return result
    store.membership.order = order

    def reported(ctx, result, uid, oid):
        ctx['uid'] = uid
        if result.get('status') == 'reported':
            meta = safe(journey.object_row, 'order', oid, uid)
            src, ch = (meta['source'], meta['channel']) if meta else ('unknown','unknown')
            safe(journey.event, 'payment_reported', ctx['product'], src, ch, uid,
                 oid=oid, dedupe='reported:' + oid)
    wrap(store.membership, 'report_paid', reported)

    # The authoritative writer's replay flag, not a preflight query, handles concurrent idem retries.
    import server
    if not getattr(server.Store.generate, '_journey_observer', False):
        original_generate = server.Store.generate
        @wraps(original_generate)
        def generate(actual_store, uid, body, idem, *args, **kwargs):
            result = original_generate(actual_store, uid, body, idem, *args, **kwargs)
            ctx = REQUEST.get()
            sidecar = getattr(actual_store, '_journey_sidecar', None)
            if ctx is not None and sidecar is not None and not result.get('replayed'):
                def observe():
                    jid = result.get('id')
                    if not identifier(jid):
                        return
                    ctx['uid'] = uid
                    src, ch = dimensions(sidecar, ctx)
                    sidecar.object('job', jid, uid, ctx['product'], src, ch)
                    if result.get('status') == 'succeeded':
                        sidecar.event('image_succeeded', ctx['product'], src, ch, uid, oid=jid,
                                      dedupe='image:' + jid)
                safe(observe)
            return result
        generate._journey_observer = True
        server.Store.generate = generate

def observed_handler(parent, store, journey=None):
    journey = journey or Journey(os.environ.get('SKILL_JOURNEY_DB', '/var/lib/skill-monitor/journey-0.10.16.db'))
    safe(journey.initialize)
    install(store, journey)
    class Observed(parent):
        def run_request(self):
            parsed = urlsplit(self.path)
            parts = parsed.path.split('/')
            product = parts[2] if len(parts) > 3 and parts[1] == 'platform-api' and parts[2] in ('gemini', 'temu', 'xhs') else None
            ctx = dict(product=product, source=source(self.headers.get('X-Skill-Source')),
                       channel=channel(self.headers.get('X-Skill-Channel')), uid=None,
                       source_declared='X-Skill-Source' in self.headers)
            try:
                cookie = SimpleCookie(self.headers.get('Cookie', '')).get('journey_context')
                ctx['context_id'] = cookie.value if cookie else None
            except Exception:
                pass
            token = REQUEST.set(ctx)
            try:
                if product and '/'.join(parts[3:]) == 'membership-api/journey-page':
                    return self.page_event(ctx)
                if product and '/'.join(parts[3:]) == 'journey-health' and self.command == 'GET':
                    health = safe(journey.health)
                    return self.send(200 if health and health['ok'] else 503,
                                     dict(version='0.10.16', journey=health or dict(ok=False)))
                return super().run_request()
            finally:
                REQUEST.reset(token)

        def page_event(self, ctx):
            if self.command != 'POST':
                return self.send(405, {'error': 'method_not_allowed'})
            if self.headers.get('Origin') != 'https://myplanestore.com' or self.headers.get('X-Membership-Request') != '1':
                return self.send(403, {'error': 'same_origin_required'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1024 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.send(400, {'error': 'invalid_page_event'})
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict) or set(body) - {'page', 'view_id', 'entry'}:
                    return self.send(400, {'error': 'invalid_page_event'})
                page, view = body.get('page'), body.get('view_id')
                if page not in ('registration', 'recharge') or not isinstance(view, str) or len(view) != 32 or any(x not in '0123456789abcdef' for x in view):
                    return self.send(400, {'error': 'invalid_page_event'})
                if page == 'registration':
                    import server
                    entry = body.get('entry')
                    if not isinstance(entry, str) or len(entry) != 43:
                        return self.send(401, {'error': 'invitation_required'})
                    with store.registration_entries.lock:
                        row = store.registration_entries.pending.get(server.digest(entry))
                        if not row or row['expires'] <= time.time() or row['product'] != ctx['product']:
                            return self.send(401, {'error': 'invitation_unavailable'})
                        invitation = row.get('journey_id')
                    attribution = safe(journey.invitation_row, invitation) if invitation else None
                    if attribution:
                        safe(journey.event, 'registration_page_entered', ctx['product'], attribution['source'],
                             attribution['channel'], invitation=invitation, dedupe='registration-page:' + invitation)
                else:
                    cookie = SimpleCookie(self.headers.get('Cookie', '')).get('platform_member')
                    uid = store.membership.web_user(cookie.value if cookie else '')
                    ctx['uid'] = uid
                    src, ch = dimensions(journey, ctx)
                    new_page = safe(journey.event, 'recharge_page_entered', ctx['product'], src, ch, uid,
                                    dedupe='recharge-page:' + uid + ':' + view)
                    if new_page:
                        safe(journey.touch, uid, src, ch, product=ctx['product'], activity=True)
                return self.send(200, {'ok': True})
            except Exception as error:
                status = getattr(error, 'status', 400)
                return self.send(status if status in (400, 401, 403) else 400, {'error': 'page_event_unavailable'})

        def send(self, status, result, *args, **kwargs):
            ctx = REQUEST.get()
            if ctx is not None and ctx.get('product') and 200 <= status < 300 and ctx.get('uid'):
                uid = ctx['uid']
                src, ch = dimensions(journey, ctx)
                route = urlsplit(self.path).path
                passive = route.endswith(('/membership-api/account', '/membership-api/orders', '/membership-api/journey-page', '/payment-status', '/quick-entry/status')) or '/jobs/' in route
                safe(journey.touch, uid, src, ch, product=ctx['product'], activity=not passive)
                # One authenticated activity observation per account/product/half-hour, not per poll.
                if not passive:
                    safe(journey.event, 'activity', ctx['product'], src, ch, uid,
                         dedupe='activity:' + uid + ':' + ctx['product'] + ':' + str(int(time.time()) // 1800))
                if isinstance(result, dict) and result.get('status') == 'succeeded' and identifier(result.get('id')):
                    meta = safe(journey.object_row, 'job', result['id'], uid)
                    if meta:
                        safe(journey.event, 'image_succeeded', meta['product'], meta['source'], meta['channel'], uid,
                             oid=result['id'], dedupe='image:' + result['id'])
            return super().send(status, result, *args, **kwargs)

        def send_header(self, keyword, value):
            result = super().send_header(keyword, value)
            ctx = REQUEST.get()
            if keyword.lower() == 'set-cookie' and ctx and ctx.get('analytics_cookie') and not ctx.get('cookie_sent'):
                ctx['cookie_sent'] = True
                super().send_header('Set-Cookie', 'journey_context=' + ctx['analytics_cookie'] +
                    '; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800')
            return result

        do_GET = run_request
        do_POST = run_request
    return Observed

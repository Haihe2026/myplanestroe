"""Short-lived registration invitations. No account exists until web confirmation."""
import secrets
import threading
import time
import urllib.parse

import server


def valid_secret(secret):
    return (isinstance(secret, str) and len(secret) == 43
            and all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in secret))


class RegistrationEntries:
    def __init__(self, store):
        self.store = store
        self.pending = {}
        self.lock = threading.RLock()

    def prepare(self, product, secret, ip):
        if product not in ('gemini', 'temu') or not valid_secret(secret):
            raise server.Problem(400, '请从对应技能重新打开开通入口')
        try:
            uid = self.store.user(secret)
        except server.Problem as error:
            if error.status != 401:
                raise
        else:
            quota = self.store.quota(uid, product)
            if quota['remaining_uses'] > 0:
                return dict(status='ready', **quota)
            result = self.store.membership.handoff(uid)
            result['url'] = result['url'].replace('/membership/', '/membership/' + product + '/')
            return dict(result, status='checkout', **quota)
        # Only credentials and source IP are held transiently in worker RAM, never images or briefs.
        now = time.time()
        with self.lock:
            self.pending = {key: row for key, row in self.pending.items() if row['expires'] > now}
            if len(self.pending) >= 2048 or sum(row['ip'] == ip for row in self.pending.values()) >= 12:
                raise server.Problem(429, '开通请求较多，请稍后继续原需求')
            token = secrets.token_urlsafe(32)
            self.pending[server.digest(token)] = dict(secret=secret, ip=ip, product=product, expires=now + 300)
        return dict(status='registration', url='https://myplanestore.com/membership/' + product + '/register/#entry=' + token,
                    expires_in=300)

    def confirm(self, product, ticket, accepted):
        if accepted is not True:
            raise server.Problem(400, '请勾选账户与图片处理说明后继续')
        if not valid_secret(ticket):
            raise server.Problem(401, '开通链接需要更新，请从原技能重新打开')
        key = server.digest(ticket)
        # Serialize ticket consumption with registration; retries cannot create a second identity.
        with self.lock:
            row = self.pending.get(key)
            if not row or row['expires'] <= time.time():
                self.pending.pop(key, None)
                raise server.Problem(401, '开通链接已使用或过期，请从原技能重新打开')
            if product != row['product']:
                raise server.Problem(401, '请从对应技能的开通入口继续')
            self.store.register_product(product, row['secret'], row['ip'], True)
            uid = self.store.user(row['secret'])
            link = self.store.membership.handoff(uid)
            token = urllib.parse.parse_qs(urllib.parse.urlsplit(link['url']).fragment)['ticket'][0]
            session = self.store.membership.redeem(token)
            del self.pending[key]
        return session

    def status(self, product, secret):
        if product not in ('gemini', 'temu') or not valid_secret(secret):
            raise server.Problem(400, '账户参数需要更新')
        try:
            uid = self.store.user(secret)
        except server.Problem as error:
            if error.status != 401:
                raise
            return dict(status='registration_pending')
        return dict(status='registered', **self.store.quota(uid, product))

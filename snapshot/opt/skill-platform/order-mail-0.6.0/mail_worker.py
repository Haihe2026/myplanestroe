"""Durable order notification outbox and authenticated owner-reply consumer."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formatdate, getaddresses
import hashlib
import imaplib
import json
import logging
import os
from pathlib import Path
import re
import secrets
import smtplib
import sqlite3
import ssl
import time

from email_settlement import EmailSettlement
from mail_auth import check_reply, Rejected

NAMES = {'gemini': 'Gemini生图器', 'temu': 'Temu图片大师', 'xhs': 'XHS选题大师'}
PLAN_NAMES = {'plus': 'Plus', 'pro': 'Pro', 'ultra': 'Ultra', 'business': '终身会员'}


def log(event, **fields):
    logging.info(json.dumps(dict(event=event, **fields), ensure_ascii=False))


class State:
    def __init__(self, path):
        self.path = str(path)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox(
                  key TEXT PRIMARY KEY,message_id TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,
                  snapshot TEXT NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'queued',attempts INTEGER NOT NULL DEFAULT 0,
                  next_attempt INTEGER NOT NULL DEFAULT 0,sent_at INTEGER,created INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS inbox(
                  message_id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,parent TEXT,
                  decision TEXT NOT NULL,created INTEGER NOT NULL);
            ''')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key):
        with self.db() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return row[0] if row else None

    def set(self, key, value):
        with self.db() as db:
            db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))

    def enqueue(self, key, kind, snapshot, subject, body):
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO outbox(key,message_id,kind,snapshot,subject,body,created) VALUES(?,?,?,?,?,?,?)',
                       (key, '<order-' + secrets.token_hex(24) + '@shengyilipin.com>', kind, json.dumps(snapshot), subject, body, int(time.time())))


class Worker:
    def __init__(self, config, verifier=None, sender=None):
        self.config = config
        self.state = State(config['state_db'])
        self.settlement = EmailSettlement(config['products'])
        self.verifier, self.sender = verifier, sender or self.smtp_send

    def queue_orders(self):
        for order in self.settlement.reported():
            name = NAMES[order['source_product']]
            price = f"{order['amount_fen'] / 100:.2f}"
            term = '长期有效' if order['plan'] == 'business' else '核款到账后30天有效，未用次数不结转'
            created = datetime.fromtimestamp(order['created'], timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
            subject = f"【待核款】{name} · ¥{price} · {PLAN_NAMES[order['plan']]}"
            body = (f"用户已提交付款登记，请核对你的实际收款。\n\n"
                    f"订单号：{order['id']}\n来源：{name}\n套餐：{PLAN_NAMES[order['plan']]}\n"
                    f"应收金额：¥{price}\n发放次数：{order['units']}次\n有效期：{term}\n"
                    f"账户标识：…{order['user_id'][-8:]}\n订单时间：{created}（北京时间）\n"
                    f"额度归属：{'Gemini / Temu 共享账户' if order['namespace'] == 'shared' else name + '原账户'}\n\n"
                    "确认款项已到账后，直接从 example@redacted.invalid 回复本邮件即可，无需固定口令。"
                    "系统将你的回复视为对本订单已收款的确认，自动发放对应次数并邮件回告。\n"
                    "还未收到款项时，请先保留本邮件；后台手动核款入口继续可用。\n\nMyPlaneStore 订单助手")
            self.state.enqueue('order:' + order['namespace'] + ':' + order['id'], 'order', order, subject, body)

    def queue_test(self):
        self.state.enqueue('setup-test-v1', 'test', {}, '【联调测试｜不发放额度】MyPlaneStore 邮件核款已接通',
                           '这是邮件收发联调，不对应任何用户订单，也不会发放次数。\n\n'
                           '请直接使用 example@redacted.invalid 回复本邮件，内容随意。收到并验证你的回复后，系统会发送“联调成功”回执。\n\n'
                           '正式订单邮件标题为【待核款】，列出订单号、来源技能、套餐、应收金额、次数与有效期。'
                           '确认真实收款后回复对应订单邮件，即自动发放一次。\n\nMyPlaneStore 订单助手')

    def smtp_send(self, message):
        cfg = self.config
        with smtplib.SMTP_SSL(cfg['smtp_host'], cfg['smtp_port'], context=ssl.create_default_context(), timeout=25) as smtp:
            smtp.login(cfg['mailbox'], cfg['password'])
            smtp.send_message(message, from_addr=cfg['mailbox'], to_addrs=[cfg['approver']])

    def deliver(self):
        with self.state.db() as db:
            rows = db.execute("SELECT * FROM outbox WHERE status='queued' AND next_attempt<=? ORDER BY created,key LIMIT 10", (int(time.time()),)).fetchall()
        for row in rows:
            if row['kind'] == 'order':
                snapshot = json.loads(row['snapshot'])
                live = self.settlement.read_order(snapshot['namespace'], snapshot['id'])
                if live['status'] != 'reported':
                    with self.state.db() as db:
                        db.execute("UPDATE outbox SET status='cancelled' WHERE key=?", (row['key'],))
                    continue
            message = EmailMessage(policy=policy.SMTP)
            message['From'] = 'MyPlaneStore 订单助手 <' + self.config['mailbox'] + '>'
            message['To'] = self.config['approver']
            message['Reply-To'] = self.config['mailbox']
            message['Subject'] = row['subject']
            message['Message-ID'] = row['message_id']
            message['Date'] = formatdate(row['created'], localtime=False)
            message['Auto-Submitted'] = 'auto-generated'
            message['X-Auto-Response-Suppress'] = 'All'
            message.set_content(row['body'])
            try:
                self.sender(message)
            except Exception as error:
                delay = min(3600, 60 * 2 ** min(row['attempts'], 6))
                with self.state.db() as db:
                    db.execute('UPDATE outbox SET attempts=attempts+1,next_attempt=? WHERE key=?', (int(time.time()) + delay, row['key']))
                log('smtp_send_failed', error_type=type(error).__name__)
                continue
            with self.state.db() as db:
                db.execute("UPDATE outbox SET status='sent',sent_at=?,attempts=attempts+1 WHERE key=?", (int(time.time()), row['key']))
            log('mail_sent', kind=row['kind'])

    def consume(self, raw):
        digest = hashlib.sha256(raw).hexdigest()
        headers = BytesParser(policy=policy.default).parsebytes(raw, headersonly=True)
        # Unrelated mail is not stored, logged, or interpreted as instructions.
        parent = str(headers.get('In-Reply-To', '')).strip()
        with self.state.db() as db:
            # SMTP acceptance and recording sent_at cannot be atomic. A valid owner
            # reply to the random original ID also proves delivery after a crash.
            notification = db.execute("SELECT * FROM outbox WHERE message_id=? AND kind IN ('order','test') AND status IN ('sent','queued')", (parent,)).fetchone()
        if not notification:
            return 'unrelated'
        reply_id = str(headers.get('Message-ID', '')).strip()
        with self.state.db() as db:
            previous = db.execute('SELECT sha256,decision FROM inbox WHERE message_id=?', (reply_id,)).fetchone()
        if previous:
            return 'duplicate' if previous['sha256'] == digest else 'message_id_collision'
        try:
            proof = check_reply(raw, self.config['mailbox'], self.config['approver'], self.verifier)
        except Rejected as error:
            # Only hashes are kept; malformed claimed Message-IDs cannot block a valid retry.
            with self.state.db() as db:
                db.execute('INSERT OR IGNORE INTO inbox VALUES(?,?,?,?,?)', ('rejected:' + digest, digest, parent, str(error), int(time.time())))
            log('reply_rejected', reason=str(error))
            return 'rejected'
        if notification['kind'] == 'test':
            decision = 'test_verified'
            result_text = '联调成功：你的回复已通过 Gmail 签名和原邮件关联验证。\n本次为测试，没有创建订单或发放次数。正式订单邮件回复核款流程已就绪。'
            subject = '【联调成功】MyPlaneStore 邮件回复验证通过'
        else:
            snapshot = json.loads(notification['snapshot'])
            try:
                result = self.settlement.approve(snapshot, notification['message_id'], proof, digest)
            except ValueError:
                result = {'status': 'needs_manual_review'}
            decision = result['status']
            if decision in ('paid', 'already_approved'):
                result_text = f"订单 {snapshot['id']} 已按你的邮件确认完成核款，{snapshot['units']}次已发放至原订单账户。重复回复不会重复发放。"
                subject = '【已发放】' + NAMES[snapshot['source_product']] + f" · {snapshot['units']}次"
            elif decision == 'already_paid':
                result_text = f"订单 {snapshot['id']} 已通过其他核款方式完成，本次回复没有重复发放。"
                subject = '【已处理】订单已核款，无重复发放'
            else:
                result_text = f"订单 {snapshot['id']} 的状态或套餐资料已变化，本次没有发放次数。请到运营后台核对该订单。"
                subject = '【需核对】订单资料变化，本次未发放'
        self.state.enqueue('receipt:' + notification['key'], 'receipt', {}, subject, result_text + '\n\nMyPlaneStore 订单助手')
        with self.state.db() as db:
            db.execute('INSERT INTO inbox VALUES(?,?,?,?,?)', (proof['reply_id'], digest, parent, decision, int(time.time())))
        log('reply_processed', decision=decision)
        return decision

    def poll(self):
        cfg = self.config
        with imaplib.IMAP4_SSL(cfg['imap_host'], cfg['imap_port'], ssl_context=ssl.create_default_context(), timeout=25) as imap:
            imap.login(cfg['mailbox'], cfg['password'])
            if imap.select('INBOX', readonly=True)[0] != 'OK':
                raise RuntimeError('inbox_unavailable')
            validity = imap.response('UIDVALIDITY')[1][0].decode()
            saved = self.state.get('uidvalidity')
            if saved is None:
                # Establish a baseline before sending the first notification.
                next_uid = int(imap.response('UIDNEXT')[1][0])
                self.state.set('last_uid', next_uid - 1)
                self.state.set('uidvalidity', validity)
            elif saved != validity:
                self.state.set('last_uid', 0)
                self.state.set('uidvalidity', validity)
            cursor = int(self.state.get('last_uid') or 0)
            status, data = imap.uid('search', None, 'UID', str(cursor + 1) + ':*')
            if status != 'OK':
                raise RuntimeError('imap_search_failed')
            uids = sorted(int(uid) for uid in data[0].split() if int(uid) > cursor)[:50]
            for uid in uids:
                status, response = imap.uid('fetch', str(uid), '(RFC822.SIZE)')
                if status != 'OK':
                    raise RuntimeError('imap_fetch_failed')
                size = re.search(rb'RFC822.SIZE (\d+)', b' '.join(item for item in response if isinstance(item, bytes)))
                if not size:
                    raise RuntimeError('imap_size_missing')
                if int(size[1]) <= 2_000_000:
                    status, response = imap.uid('fetch', str(uid), '(BODY.PEEK[])')
                    if status != 'OK':
                        raise RuntimeError('imap_fetch_failed')
                    raw = next((item[1] for item in response if isinstance(item, tuple)), None)
                    if raw is None:
                        raise RuntimeError('imap_body_missing')
                    self.consume(raw)
                else:
                    log('inbox_message_skipped', reason='message_too_large')
                self.state.set('last_uid', uid)
            self.state.set('last_poll', int(time.time()))

    def cycle(self):
        self.poll()
        self.queue_orders()
        self.deliver()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='/etc/skill-order-mail/config.json')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--test-email', action='store_true')
    parser.add_argument('--queue-test', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    if config['mailbox'] != 'example@redacted.invalid' or config['approver'] != 'example@redacted.invalid':
        raise ValueError('unexpected_approval_identity')
    worker = Worker(config)
    if args.queue_test:
        if not worker.state.get('uidvalidity'):
            raise RuntimeError('worker_inbox_baseline_not_ready')
        worker.queue_test()
        print(json.dumps({'test_queued': True, 'actual_order': False}))
        return
    if args.status:
        with worker.state.db() as db:
            print(json.dumps({'outbox': [dict(r) for r in db.execute('SELECT kind,status,count(*) n FROM outbox GROUP BY kind,status')],
                              'inbox': [dict(r) for r in db.execute('SELECT decision,count(*) n FROM inbox GROUP BY decision')],
                              'last_poll': worker.state.get('last_poll')}))
        return
    import fcntl
    lock = open(Path(config['state_db']).with_suffix('.lock'), 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    worker.settlement.initialize()
    if args.test_email:
        worker.poll()
        worker.queue_test()
        worker.deliver()
        return
    while True:
        try:
            worker.cycle()
        except Exception as error:
            log('cycle_failed', error_type=type(error).__name__)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        time.sleep(config.get('poll_seconds', 30))


if __name__ == '__main__':
    main()

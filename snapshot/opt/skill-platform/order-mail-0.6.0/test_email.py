import concurrent.futures
from contextlib import closing
import base64
from email import policy
from email.message import EmailMessage
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'test-deps'))
from email_settlement import EmailSettlement, connection, PLANS
from mail_auth import check_reply, Rejected
from mail_worker import Worker

MAILBOX = 'example@redacted.invalid'
APPROVER = 'example@redacted.invalid'
OID = 'a' * 32


def fixture(path, product):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript('''
          CREATE TABLE users(id TEXT PRIMARY KEY,balance INTEGER NOT NULL CHECK(balance>=0));
          CREATE TABLE member_orders(id TEXT PRIMARY KEY,user_id TEXT,product TEXT,plan TEXT,amount_fen INTEGER,
            units INTEGER,status TEXT,created INTEGER,paid_at INTEGER,transaction_id TEXT UNIQUE,provider TEXT);
          CREATE TABLE member_grants(order_id TEXT PRIMARY KEY,user_id TEXT,remaining INTEGER,expires INTEGER);
          CREATE TABLE paid_wallets(user_id TEXT PRIMARY KEY,remaining INTEGER);
          CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id TEXT,job_id TEXT,amount INTEGER,kind TEXT,created INTEGER);
          CREATE TABLE member_gifts(user_id TEXT,gift_id TEXT,reason TEXT,granted INTEGER,PRIMARY KEY(user_id,gift_id));
          CREATE TABLE order_sources(order_id TEXT PRIMARY KEY,product TEXT);
          INSERT INTO users VALUES('synthetic-user',7);
        ''')
        db.execute("INSERT INTO member_orders VALUES(?,'synthetic-user',?,'ultra',4900,54,'reported',?,NULL,NULL,NULL)", (OID, product, int(time.time())))
        db.execute("INSERT INTO order_sources VALUES(?,'temu')", (OID,))


def reply(parent, **changes):
    message = EmailMessage(policy=policy.SMTP)
    for key, value in {'From': APPROVER, 'To': MAILBOX, 'Date': 'Thu, 15 Oct 2026 10:00:00 +0000',
                       'Message-ID': '<example@redacted.invalid>', 'In-Reply-To': parent, 'Subject': 'Re: 待核款'}.items():
        if changes.get(key, value) is not None:
            message[key] = changes.pop(key, value)
    message['DKIM-Signature'] = 'v=1; a=rsa-sha256; d=gmail.com; s=test; h=from:to:in-reply-to:message-id:subject:date; bh=fake; b=fake'
    for key, value in changes.items():
        message[key] = value
    message.set_content('已核对。')
    return message.as_bytes()


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = {'mailbox': MAILBOX, 'approver': APPROVER, 'state_db': str(self.root / 'state.db'), 'products': {}}
        for namespace in ('shared', 'gemini', 'temu'):
            path = self.root / (namespace + '.db')
            stored = 'temu-image-assistant' if namespace == 'temu' else 'gemini-image-assistant'
            fixture(path, stored)
            self.config['products'][namespace] = {'path': str(path), 'stored_product': stored}
        self.sent = []
        self.worker = Worker(self.config, verifier=lambda raw, idx: True, sender=self.sent.append)
        self.worker.settlement.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def sql(self, sql, namespace='shared'):
        with connection(self.config['products'][namespace]['path']) as db:
            return [tuple(r) for r in db.execute(sql)]

    def notification(self, namespace='shared'):
        self.worker.queue_orders()
        self.worker.deliver()
        with self.worker.state.db() as db:
            return db.execute('SELECT * FROM outbox WHERE key=?', ('order:' + namespace + ':' + OID,)).fetchone()

    def test_notification_dedup_no_credit_and_all_three_sources(self):
        self.notification()
        self.worker.queue_orders()
        self.worker.deliver()
        self.assertEqual(len(self.sent), 3)
        for namespace in self.config['products']:
            self.assertEqual(self.sql('SELECT balance FROM users', namespace), [(7,)])
        self.assertTrue(any('Temu图片大师' in str(m['Subject']) for m in self.sent))
        self.assertTrue(all('49.00' in str(m['Subject']) for m in self.sent))

    def test_owner_reply_grants_and_preserves_existing_balance(self):
        note = self.notification()
        self.assertEqual(self.worker.consume(reply(note['message_id'])), 'paid')
        self.assertEqual(self.sql('SELECT balance FROM users'), [(61,)])
        self.assertEqual(self.sql('SELECT remaining FROM paid_wallets'), [(54,)])
        self.assertEqual(self.sql('SELECT remaining FROM member_grants'), [(54,)])
        self.assertEqual(self.sql('SELECT provider FROM member_orders'), [('manual_email',)])
        self.assertEqual(self.sql('SELECT kind,amount FROM ledger'), [('email_verified_topup', 54)])
        self.assertEqual(self.sql('SELECT approver FROM email_approvals'), [(APPROVER,)])
        self.assertAlmostEqual(self.sql('SELECT expires FROM member_grants')[0][0] - time.time(), 30 * 86400, delta=3)
        self.worker.deliver()
        self.assertTrue(any('已发放' in str(m['Subject']) for m in self.sent))

    def test_duplicate_and_different_reply_do_not_double_credit(self):
        note = self.notification()
        raw = reply(note['message_id'])
        self.worker.consume(raw)
        self.assertEqual(self.worker.consume(raw), 'duplicate')
        self.assertEqual(self.worker.consume(reply(note['message_id'], **{'Message-ID': '<example@redacted.invalid>'})), 'already_approved')
        self.assertEqual(self.sql('SELECT balance FROM users'), [(61,)])
        self.assertEqual(self.sql('SELECT count(*) FROM email_approvals'), [(1,)])

    def test_unsigned_spoof_wrong_sender_auto_reply_and_unrelated_do_not_credit(self):
        note = self.notification()
        for changes in ({'From': 'example@redacted.invalid'}, {'Auto-Submitted': 'auto-replied'},
                        {'Subject': '自动回复'}, {'Precedence': 'bulk'}, {'In-Reply-To': None}):
            self.assertIn(self.worker.consume(reply(note['message_id'], **changes)), ('unrelated', 'rejected'))
        self.worker.verifier = lambda raw, idx: False
        self.assertEqual(self.worker.consume(reply(note['message_id'])), 'rejected')
        self.assertEqual(self.sql('SELECT balance FROM users'), [(7,)])

    def test_rejected_forged_message_id_does_not_poison_real_reply(self):
        note = self.notification()
        self.worker.consume(reply(note['message_id'], **{'From': 'example@redacted.invalid'}))
        self.assertEqual(self.worker.consume(reply(note['message_id'])), 'paid')

    def test_auth_requires_signed_reply_binding_and_no_body_length_limit(self):
        raw = reply('<example@redacted.invalid>')
        for modified in (raw.replace(b'in-reply-to:', b'not-in-reply-to:'),
                         raw.replace(b'd=gmail.com', b'd=attacker.example'),
                         raw.replace(b'bh=fake;', b'l=0; bh=fake;'),
                         b'From: example@redacted.invalid\r\n' + raw,
                         raw.replace(b'In-Reply-To:', b'References:')):
            with self.assertRaises(Rejected):
                check_reply(modified, MAILBOX, APPROVER, lambda raw, idx: True)

    def test_setup_test_reply_never_credits(self):
        self.worker.queue_test()
        self.worker.deliver()
        self.assertEqual(self.worker.consume(reply(str(self.sent[0]['Message-ID']))), 'test_verified')
        self.worker.deliver()
        self.assertIn('联调成功', str(self.sent[-1]['Subject']))
        self.assertEqual(self.sql('SELECT balance FROM users'), [(7,)])

    def test_atomic_failure_rolls_back_every_grant_write(self):
        note = self.notification()
        self.sql("CREATE TRIGGER fail_audit BEFORE INSERT ON email_approvals BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.worker.consume(reply(note['message_id']))
        self.assertEqual(self.sql('SELECT balance FROM users'), [(7,)])
        self.assertEqual(self.sql('SELECT status FROM member_orders'), [('reported',)])
        for table in ('ledger', 'member_grants', 'paid_wallets', 'ops_settlements'):
            self.assertEqual(self.sql('SELECT count(*) FROM ' + table), [(0,)])
        self.sql('DROP TRIGGER fail_audit')
        self.assertEqual(self.worker.consume(reply(note['message_id'])), 'paid')

    def test_concurrent_approval_grants_once(self):
        note = self.notification()
        snapshot = json.loads(note['snapshot'])
        proof = check_reply(reply(note['message_id']), MAILBOX, APPROVER, lambda raw, idx: True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: self.worker.settlement.approve(snapshot, note['message_id'], proof, 'a' * 64), range(4)))
        self.assertEqual(sum(r['credited'] for r in results), 1)
        self.assertEqual(self.sql('SELECT balance FROM users'), [(61,)])

    def test_changed_amount_is_quarantined_not_granted(self):
        note = self.notification()
        self.sql('UPDATE member_orders SET amount_fen=1')
        self.assertEqual(self.worker.consume(reply(note['message_id'])), 'needs_manual_review')
        self.assertEqual(self.sql('SELECT balance FROM users'), [(7,)])

    def test_manual_already_paid_does_not_grant(self):
        note = self.notification()
        self.sql("UPDATE member_orders SET status='paid',provider='manual_qr'")
        self.assertEqual(self.worker.consume(reply(note['message_id'])), 'already_paid')
        self.assertEqual(self.sql('SELECT balance FROM users'), [(7,)])

    def test_smtp_retry_reuses_original_message_id(self):
        self.worker.queue_test()
        def failed(message):
            self.sent.append(message)
            raise OSError('synthetic network failure')
        self.worker.sender = failed
        self.worker.deliver()
        self.worker.deliver()
        self.assertEqual(len(self.sent), 1)
        with self.worker.state.db() as db:
            db.execute('UPDATE outbox SET next_attempt=0')
        self.worker.sender = self.sent.append
        self.worker.deliver()
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(str(self.sent[0]['Message-ID']), str(self.sent[1]['Message-ID']))

    def test_restart_after_grant_before_receipt_does_not_double_credit(self):
        note = self.notification()
        raw = reply(note['message_id'])
        original = self.worker.state.enqueue
        with patch.object(self.worker.state, 'enqueue', side_effect=OSError('synthetic crash')):
            with self.assertRaises(OSError):
                self.worker.consume(raw)
        self.worker.state.enqueue = original
        self.assertEqual(self.worker.consume(raw), 'already_approved')
        self.assertEqual(self.sql('SELECT balance FROM users'), [(61,)])

    def test_reply_after_ambiguous_smtp_ack_is_not_lost(self):
        note = self.notification()
        with self.worker.state.db() as db:
            db.execute("UPDATE outbox SET status='queued',sent_at=NULL WHERE key=?", (note['key'],))
        self.assertEqual(self.worker.consume(reply(note['message_id'])), 'paid')
        self.worker.deliver()
        self.assertEqual(self.sql('SELECT balance FROM users'), [(61,)])

    def test_imap_baseline_cursor_peek_and_uidvalidity_reset(self):
        class FakeImap:
            messages = {}
            validity = b'123'
            fetches = []
            def __init__(self, *args, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def login(self, *args): pass
            def select(self, mailbox, readonly):
                self.readonly = readonly
                return 'OK', []
            def response(self, key):
                return key, [self.validity if key == 'UIDVALIDITY' else str(max(self.messages, default=0) + 1).encode()]
            def uid(self, command, *args):
                if command == 'search': return 'OK', [b' '.join(str(uid).encode() for uid in self.messages)]
                uid = int(args[0]); self.fetches.append(args[1])
                if args[1] == '(RFC822.SIZE)': return 'OK', [f'1 (UID {uid} RFC822.SIZE {len(self.messages[uid])})'.encode()]
                return 'OK', [(b'1 (BODY[]', self.messages[uid]), b')']
        self.config.update(imap_host='synthetic.invalid', imap_port=993, password='synthetic')
        with patch('mail_worker.imaplib.IMAP4_SSL', FakeImap):
            self.worker.poll()
            self.assertEqual(self.worker.state.get('last_uid'), '0')
            note = self.notification()
            FakeImap.messages[1] = reply(note['message_id'])
            self.worker.poll()
            self.assertEqual(self.worker.state.get('last_uid'), '1')
            self.assertIn('(BODY.PEEK[])', FakeImap.fetches)
            FakeImap.validity = b'456'
            self.worker.poll()
            self.assertEqual(self.sql('SELECT balance FROM users'), [(61,)])

    def test_each_plan_and_legacy_namespace_correct_grant(self):
        for namespace in self.config['products']:
            for index, (plan, (amount, units)) in enumerate(PLANS.items()):
                oid = str(index + 1) * 32
                with connection(self.config['products'][namespace]['path']) as db:
                    db.execute("INSERT INTO member_orders VALUES(?,'synthetic-user',?,?,?,?, 'reported',?,NULL,NULL,NULL)",
                               (oid, self.config['products'][namespace]['stored_product'], plan, amount, units, int(time.time())))
                snapshot = self.worker.settlement.read_order(namespace, oid)
                mid = f'<test-{namespace}-{plan}@shengyilipin.com>'
                proof = {'parent': mid, 'reply_id': f'<reply-{namespace}-{plan}@gmail.com>', 'approver': APPROVER, 'authentication': 'synthetic only'}
                self.worker.settlement.approve(snapshot, mid, proof, 'a' * 64)
                grant = self.sql("SELECT remaining,expires FROM member_grants WHERE order_id='" + oid + "'", namespace)[0]
                self.assertEqual(grant[0], units)
                self.assertEqual(grant[1] is None, plan == 'business')


class RealSignatureTests(unittest.TestCase):
    def test_real_rsa_signature_and_tampered_order_reference(self):
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
        except ImportError:
            self.skipTest('Synthetic RSA key generator only needed for local cryptographic fixture')
        import dkim
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        public = key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
        dns = b'v=DKIM1; k=rsa; p=' + base64.b64encode(public)
        raw = reply('<example@redacted.invalid>')
        message = __import__('email.parser', fromlist=['BytesParser']).BytesParser(policy=policy.SMTP).parsebytes(raw)
        del message['DKIM-Signature']
        raw = message.as_bytes()
        signature = dkim.sign(raw, b'synthetic', b'gmail.com', private,
                              include_headers=[b'from', b'to', b'in-reply-to', b'message-id', b'subject', b'date'])
        signed = signature + raw
        verifier = lambda data, idx: dkim.DKIM(data).verify(idx=idx, dnsfunc=lambda name, timeout=5: dns if name == b'synthetic._domainkey.gmail.com.' else None)
        self.assertEqual(check_reply(signed, MAILBOX, APPROVER, verifier)['parent'], '<example@redacted.invalid>')
        with self.assertRaises(Rejected):
            check_reply(signed.replace(b'notification-test-123', b'notification-test-999'), MAILBOX, APPROVER, verifier)
        with self.assertRaises(Rejected):
            check_reply(signed + b'changed unsigned body', MAILBOX, APPROVER, verifier)


if __name__ == '__main__':
    unittest.main(verbosity=2)

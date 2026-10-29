"""Synthetic Linux integration tests: no real SMTP, mailbox or customer writes."""
import sqlite3
import threading
import time
import unittest

from event_runner import DatabaseEvents, run
from test_email import EmailTests, OID


class EventTests(EmailTests):
    def setUp(self):
        super().setUp()
        self.config.update(poll_seconds=0.1, test_shutdown=True)
        self.worker.state.set('uidvalidity', 'synthetic')
        for product in self.config['products'].values():
            with sqlite3.connect(product['path']) as db:
                db.execute("UPDATE member_orders SET status='pending'")
        self.worker.poll = lambda: None
        self.scans = 0
        original = self.worker.queue_orders
        def scan():
            self.scans += 1
            original()
        self.worker.queue_orders = scan
        self.stop = threading.Event()
        self.errors = []
        def target():
            try:
                run(self.worker, self.stop)
            except BaseException as error:
                self.errors.append(error)
        self.thread = threading.Thread(target=target)
        self.thread.start()
        self.wait_for(lambda: self.scans >= 1)

    def tearDown(self):
        self.stop.set()
        self.thread.join(4)
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.errors, [])
        super().tearDown()

    def wait_for(self, predicate):
        deadline = time.monotonic() + 4
        while not predicate() and time.monotonic() < deadline:
            if self.errors:
                raise self.errors[0]
            time.sleep(0.02)
        self.assertTrue(predicate())

    def test_event_commit_sends_once_without_credit(self):
        path = self.config['products']['shared']['path']
        with sqlite3.connect(path) as db:
            db.execute("UPDATE member_orders SET status='reported' WHERE id=?", (OID,))
        self.wait_for(lambda: len(self.sent) == 1)
        with sqlite3.connect(path) as db:
            db.execute("UPDATE member_orders SET status='reported' WHERE id=?", (OID,))
            self.assertEqual(db.execute('SELECT balance FROM users').fetchone()[0], 7)
        time.sleep(0.25)
        self.assertEqual(len(self.sent), 1)

    def test_idle_mailbox_wakes_do_not_rescan_orders(self):
        time.sleep(0.2)
        baseline = self.scans
        time.sleep(0.4)
        self.assertEqual(self.scans, baseline)
        self.assertEqual(self.sent, [])

    def test_wal_commit_visible_while_connection_stays_open(self):
        path = self.config['products']['temu']['path']
        db = sqlite3.connect(path)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute("UPDATE member_orders SET status='reported' WHERE id=?", (OID,))
            db.commit()
            self.wait_for(lambda: len(self.sent) == 1)
        finally:
            db.close()

    def test_atomic_replacement_and_unrelated_file_filter(self):
        from pathlib import Path
        root = self.root
        time.sleep(0.2)
        baseline = self.scans
        (root / 'unrelated.txt').write_text('synthetic')
        time.sleep(0.2)
        self.assertEqual(self.scans, baseline)
        path = Path(self.config['products']['gemini']['path'])
        replacement = path.with_suffix('.replacement')
        with sqlite3.connect(path) as source, sqlite3.connect(replacement) as target:
            source.backup(target)
        with sqlite3.connect(replacement) as db:
            db.execute("UPDATE member_orders SET status='reported' WHERE id=?", (OID,))
        replacement.replace(path)
        self.wait_for(lambda: len(self.sent) == 1)


if __name__ == '__main__':
    # Run only new tests here. The inherited original suite runs separately.
    suite = unittest.TestSuite(EventTests(name) for name in EventTests.__dict__ if name.startswith('test_'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())

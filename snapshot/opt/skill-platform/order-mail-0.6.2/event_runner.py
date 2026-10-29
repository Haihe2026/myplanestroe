"""Wake order notifications on database changes; retain verified reply processing."""
import ctypes
import fcntl
import json
import logging
import os
from pathlib import Path
import select
import socket
import struct
import threading
import time

from mail_worker import Worker, log


class DatabaseEvents:
    # Watch parent directories so WAL creation and atomic database replacement
    # remain observable. No business database or payment endpoint is modified.
    MASK = 0x2 | 0x8 | 0x80 | 0x100 | 0x400 | 0x800

    def __init__(self, paths):
        libc = ctypes.CDLL(None, use_errno=True)
        libc.inotify_init1.argtypes = [ctypes.c_int]
        libc.inotify_init1.restype = ctypes.c_int
        libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        libc.inotify_add_watch.restype = ctypes.c_int
        self.fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), 'inotify_init_failed')
        self.names = {}
        try:
            for path in map(Path, paths):
                wd = libc.inotify_add_watch(self.fd, os.fsencode(path.parent), self.MASK)
                if wd < 0:
                    raise OSError(ctypes.get_errno(), 'database_watch_failed')
                self.names.setdefault(wd, set()).update((path.name, path.name + '-wal', path.name + '-journal'))
        except BaseException:
            self.close()
            raise

    def close(self):
        os.close(self.fd)

    def drain(self):
        changed = False
        while True:
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                return changed
            offset = 0
            while offset < len(data):
                wd, mask, _, size = struct.unpack_from('iIII', data, offset)
                offset += 16
                name = os.fsdecode(data[offset:offset + size].split(b'\0', 1)[0])
                offset += size
                if mask & (0x400 | 0x800 | 0x8000):
                    raise RuntimeError('database_watch_lost')
                if mask & 0x4000 or name in self.names.get(wd, ()):
                    changed = True


def retry_at(worker):
    with worker.state.db() as db:
        row = db.execute("SELECT min(next_attempt) FROM outbox WHERE status='queued'").fetchone()
    return row[0] if row and row[0] is not None else None


def run(worker, stop=None):
    stop = stop or threading.Event()
    events = DatabaseEvents([p['path'] for p in worker.config['products'].values()])
    wake_read, wake_write = socket.socketpair()
    wake_read.setblocking(False)
    wake_write.setblocking(False)

    def inbox():
        while not stop.is_set():
            try:
                worker.poll()
            except Exception as error:
                log('inbox_check_failed', error_type=type(error).__name__)
            try:
                wake_write.send(b'1')
            except BlockingIOError:
                pass
            except OSError:
                return
            stop.wait(worker.config.get('poll_seconds', 30))

    # Establish the pre-existing mailbox baseline before the first notification.
    if not worker.state.get('uidvalidity'):
        worker.poll()
    thread = threading.Thread(target=inbox, name='verified-replies', daemon=True)
    thread.start()
    scan = True  # Recover reported orders after service restart as well.
    scan_retry = None
    due = time.time()
    worker.state.set('notification_mode', 'database-events-v1')
    log('event_listener_ready', databases=len(worker.config['products']))
    try:
        while not stop.is_set():
            if scan or due is not None and due <= time.time():
                try:
                    if scan:
                        worker.queue_orders()
                        worker.state.set('last_order_event_scan', int(time.time()))
                        scan_retry = None
                    worker.deliver()  # Single sender; existing durable dedup/retries.
                    due = retry_at(worker)
                    scan = False
                except Exception as error:
                    log('notification_event_failed', error_type=type(error).__name__)
                    scan_retry = time.time() + 60 if scan else scan_retry
                    scan = False
                    due = time.time() + 60
            deadlines = [x for x in (due, scan_retry) if x is not None]
            timeout = max(0, min(deadlines) - time.time()) if deadlines else None
            # Test shutdown only; production blocks without a periodic order scan.
            if worker.config.get('test_shutdown'):
                timeout = min(timeout, 0.1) if timeout is not None else 0.1
            ready, _, _ = select.select([events.fd, wake_read], [], [], timeout)
            if events.fd in ready and events.drain():
                scan = True
            if wake_read in ready:
                try:
                    while wake_read.recv(4096):
                        pass
                except BlockingIOError:
                    pass
                # Reply processing may have queued a receipt; it never causes
                # periodic rescanning of business orders.
                due = time.time()
            if scan_retry is not None and scan_retry <= time.time():
                scan = True
    finally:
        stop.set()
        thread.join(timeout=30)
        events.close()
        wake_read.close()
        wake_write.close()


def main():
    os.umask(0o077)
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    config = json.loads(Path('/etc/skill-order-mail/config.json').read_text())
    if config['mailbox'] != 'example@redacted.invalid' or config['approver'] != 'example@redacted.invalid':
        raise ValueError('unexpected_approval_identity')
    worker = Worker(config)
    lock = open(Path(config['state_db']).with_suffix('.lock'), 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    worker.settlement.initialize()
    run(worker)


if __name__ == '__main__':
    main()

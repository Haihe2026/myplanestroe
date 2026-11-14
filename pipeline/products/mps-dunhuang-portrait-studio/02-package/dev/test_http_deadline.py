"""Development checks for the HTTP helper. No real sockets or business calls."""
import ast
import argparse
import http.client
import io
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import threading
import time
import types
import unittest
from unittest import mock


_options = argparse.ArgumentParser(add_help=False)
_options.add_argument('--package')
_args, _unittest_args = _options.parse_known_args()
sys.argv[1:] = _unittest_args
PACKAGE_ROOT = (Path(_args.package).expanduser().resolve() if _args.package else
                Path(__file__).resolve().parents[1] / 'mps-dunhuang-portrait-studio')
MODULE_PATH = PACKAGE_ROOT / 'scripts' / 'http_bytes.py'
HTTP = types.ModuleType('http_deadline_development_module')
HTTP.__file__ = str(MODULE_PATH)
exec(compile(MODULE_PATH.read_text(encoding='utf-8'), str(MODULE_PATH), 'exec'), HTTP.__dict__)
REAL_POPEN = subprocess.Popen
URL = 'https://myplanestore.com/platform-api/gemini/health'
SECRET = 'synthetic-not-a-real-secret'


class CapturedPipe(io.BytesIO):
    captured = b''

    def close(self):
        if not self.closed:
            self.captured = self.getvalue()
        super().close()


class FakeProcess:
    def __init__(self, wire=None, timeout=False):
        self.wire = struct.pack('!I', 200) + b'ok' if wire is None else wire
        self.timeout = timeout
        self.returncode = None
        self.original_stdin = CapturedPipe()
        self.stdin = self.original_stdin
        self.stdout = io.BytesIO()
        self.stderr = None
        self.calls = []
        self.killed = False
        self.reaped = False

    def communicate(self, input=None, timeout=None):
        self.calls.append((input, timeout))
        if self.timeout and not self.killed:
            raise subprocess.TimeoutExpired('fixed-helper', timeout)
        self.returncode = -9 if self.killed else 0
        self.reaped = True
        return self.wire, None

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        self.reaped = True
        return self.returncode


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now


class HTTPDeadlineChecks(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'MPS_DUNHUANG_OFFLINE_TEST': '1'})
        self.env.start()
        self.addCleanup(self.env.stop)
        # Parent-side mocks must not accidentally perform even a DNS lookup.
        for target in ('socket.create_connection', 'socket.getaddrinfo',
                       'http.client.HTTPConnection.connect', 'http.client.HTTPSConnection.connect'):
            guard = mock.patch(target, side_effect=AssertionError('real network forbidden'))
            guard.start()
            self.addCleanup(guard.stop)

    def request(self, timeout=1.0, limit=32):
        return HTTP.request('POST', URL, {'note': SECRET}, {'Authorization': 'Bearer ' + SECRET}, timeout, limit)

    def test_command_is_fixed_credentials_stdin_only(self):
        process = FakeProcess()
        with mock.patch.object(HTTP.subprocess, 'Popen', return_value=process) as spawn:
            self.assertEqual(self.request(), (200, b'ok'))
        argv = spawn.call_args[0][0]
        options = spawn.call_args[1]
        self.assertEqual(argv, [sys.executable, '-I', '-S', str(MODULE_PATH), '--http-worker'])
        self.assertFalse(options['shell'])
        self.assertEqual(options['stderr'], subprocess.DEVNULL)
        self.assertNotIn(SECRET, ' '.join(argv))
        self.assertIn(SECRET.encode(), process.original_stdin.captured)
        self.assertIsNone(process.stdin)
        self.assertIsNone(process.calls[0][0])
        self.assertEqual(len(process.calls), 1)

    def test_timeout_kills_and_reaps_without_retry(self):
        process = FakeProcess(timeout=True)
        with mock.patch.object(HTTP.subprocess, 'Popen', return_value=process) as spawn:
            with self.assertRaises(OSError):
                self.request()
        self.assertEqual(spawn.call_count, 1)
        self.assertTrue(process.killed)
        self.assertTrue(process.reaped)
        self.assertEqual(len(process.calls), 2)
        self.assertIsNone(process.calls[1][0])

    def test_startup_time_reduces_remaining_budget(self):
        clock = Clock()
        process = FakeProcess()
        def spawn(*args, **kwargs):
            clock.now = 0.4
            return process
        with mock.patch.object(HTTP, 'time', clock), mock.patch.object(HTTP.subprocess, 'Popen', side_effect=spawn):
            self.request(timeout=1.0)
        self.assertAlmostEqual(process.calls[0][1], 0.6)

    def test_startup_over_deadline_kills_before_request_stdin(self):
        clock = Clock()
        process = FakeProcess()
        def spawn(*args, **kwargs):
            clock.now = 2.0
            return process
        with mock.patch.object(HTTP, 'time', clock), mock.patch.object(HTTP.subprocess, 'Popen', side_effect=spawn):
            with self.assertRaises(OSError):
                self.request(timeout=1.0)
        self.assertTrue(process.killed)
        self.assertTrue(process.reaped)
        self.assertTrue(all(body is None for body, _ in process.calls))

    def test_late_process_success_is_not_accepted(self):
        clock = Clock()
        process = FakeProcess()
        communicate = process.communicate
        def late(*args, **kwargs):
            result = communicate(*args, **kwargs)
            clock.now = 2.0
            return result
        process.communicate = late
        with mock.patch.object(HTTP, 'time', clock), mock.patch.object(HTTP.subprocess, 'Popen', return_value=process):
            with self.assertRaises(OSError):
                self.request(timeout=1.0)

    def test_bad_or_oversized_helper_protocol_rejected(self):
        wires = (b'', b'bad', struct.pack('!I', 0), struct.pack('!I', 999), struct.pack('!I', 200) + b'x' * 33)
        for wire in wires:
            with self.subTest(wire_length=len(wire)):
                with mock.patch.object(HTTP.subprocess, 'Popen', return_value=FakeProcess(wire=wire)):
                    with self.assertRaises(OSError):
                        self.request(limit=32)

    def test_non_success_http_status_preserved(self):
        with mock.patch.object(HTTP.subprocess, 'Popen', return_value=FakeProcess(wire=struct.pack('!I', 401))):
            self.assertEqual(self.request(), (401, b''))

    def test_destination_rejected_before_spawn(self):
        urls = ('http://myplanestore.com/platform-api/x', 'https://other.invalid/platform-api/x',
                'https://myplanestore.com/membership/', 'https://user@myplanestore.com/platform-api/x',
                'https://myplanestore.com/platform-api/../membership/',
                'https://myplanestore.com/platform-api/%252e%252e/membership/',
                'https://myplanestore.com/platform-api/x#fragment')
        with mock.patch.object(HTTP.subprocess, 'Popen') as spawn:
            for url in urls:
                with self.subTest(url=url), self.assertRaises(OSError):
                    HTTP.request('GET', url, None, {}, 1, 32)
            spawn.assert_not_called()

    def test_invalid_timeout_limit_headers_or_body_rejected(self):
        bad = [('GET', URL, None, {}, 0, 32), ('GET', URL, None, {}, float('nan'), 32),
               ('GET', URL, None, {}, 1, -1), ('GET', URL, None, {}, 1, HTTP.MAX_RESPONSE_BYTES + 1),
               ('GET', URL, None, {'X-Test': 'bad\r\nvalue'}, 1, 32),
               ('POST', URL, {'bad': float('nan')}, {}, 1, 32)]
        with mock.patch.object(HTTP.subprocess, 'Popen') as spawn:
            for args in bad:
                with self.subTest(args_kind=type(args[2]).__name__), self.assertRaises(OSError):
                    HTTP.request(*args)
            spawn.assert_not_called()

    def test_late_eof_rejected_after_read(self):
        clock = Clock()
        class LateEOF:
            def read(self, n=-1):
                clock.now = 2.0
                return b''
            read1 = read
        with mock.patch.object(HTTP, 'time', clock):
            with self.assertRaises(OSError):
                HTTP.read_response(LateEOF(), 32, 1.0)

    def test_real_httpresponse_chunked_trailers_late_return_rejected(self):
        clock = Clock()
        class FakeFile(io.BytesIO):
            advance = False
            def readline(self, n=-1):
                if self.advance:
                    clock.now += 0.4
                return super().readline(n)
        class FakeSocket:
            def __init__(self):
                self.fp = FakeFile(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'
                                   b'0\r\nX-A: 1\r\nX-B: 2\r\nX-C: 3\r\nX-D: 4\r\n\r\n')
            def makefile(self, *args, **kwargs):
                return self.fp
        sock = FakeSocket()
        response = http.client.HTTPResponse(sock)
        response.begin()
        sock.fp.advance = True
        with mock.patch.object(HTTP, 'time', clock):
            with self.assertRaises(OSError):
                HTTP.read_response(response, 32, 1.0)
        self.assertGreater(clock.now, 1.0)

    def test_response_limit_and_existing_expired_deadline(self):
        with self.assertRaises(OSError):
            HTTP.read_response(io.BytesIO(b'x' * 33), 32, time.monotonic() + 1)
        with self.assertRaises(OSError):
            HTTP.read_response(io.BytesIO(b''), 32, time.monotonic() - 1)

    def test_child_offline_gate_denies_before_network(self):
        # Exercise the child's gate in-process with socket guards too: a future
        # broken gate must fail this test without allowing a real child to connect.
        with mock.patch('urllib.request.build_opener') as opener:
            with self.assertRaises(OSError) as error:
                HTTP._perform_request(dict(method='POST', url=URL, body={'note': SECRET},
                                           headers={'Authorization': SECRET}, timeout=2, limit=32))
            opener.assert_not_called()
        self.assertIn('offline development check', str(error.exception))
        self.assertNotIn(SECRET, str(error.exception))

    def test_child_no_redirect_and_error_body_not_read(self):
        import urllib.error
        error = urllib.error.HTTPError(URL, 302, 'synthetic', {}, io.BytesIO(b'not-read'))
        with mock.patch.dict(os.environ, {'MPS_DUNHUANG_OFFLINE_TEST': '0'}):
            with mock.patch('urllib.request.build_opener') as build:
                build.return_value.open.side_effect = error
                result = HTTP._perform_request(dict(method='GET', url=URL, body=None, headers={}, timeout=1, limit=32))
        self.assertEqual(result, (302, b''))
        self.assertIsNone(build.call_args[0][0].redirect_request(None, None, None, None, None, None))

    def test_real_idle_helper_terminated_and_reaped(self):
        # An idle child represents work blocked in DNS, headers, or read1. No socket
        # is created; the identical parent boundary terminates every such stage.
        processes = []
        def idle(command, **options):
            process = REAL_POPEN([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(60)'], **options)
            processes.append(process)
            return process
        started = time.monotonic()
        with mock.patch.object(HTTP.subprocess, 'Popen', side_effect=idle):
            with self.assertRaises(OSError):
                self.request(timeout=0.2)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertLess(time.monotonic() - started, 5.0)

    def test_large_stdin_idle_child_deadline_and_writer_reaped(self):
        # Old Windows 3.12.10 implementation f5e7ada3... took 5.094 seconds:
        # communicate synchronously wrote 1MiB before reaching its timeout join.
        # This child never reads stdin, creates no socket, and lives at most 5s.
        processes = []
        before = set(threading.enumerate())
        def idle(command, **options):
            process = REAL_POPEN([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(5)'], **options)
            processes.append(process)
            return process
        started = time.monotonic()
        with mock.patch.object(HTTP.subprocess, 'Popen', side_effect=idle):
            with self.assertRaises(OSError):
                HTTP.request('POST', URL, {'synthetic_blob': 'x' * (1024 * 1024)}, {}, 0.2, 32)
        elapsed = time.monotonic() - started
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertLess(elapsed, 2.0)
        leaked = [thread for thread in threading.enumerate()
                  if thread not in before and thread.name == 'mps-http-stdin-writer']
        self.assertEqual(leaked, [])

    def test_failed_stdin_writer_rejects_successful_child(self):
        process = FakeProcess()
        process.original_stdin.write = mock.Mock(side_effect=OSError('synthetic pipe failure'))
        with mock.patch.object(HTTP.subprocess, 'Popen', return_value=process):
            with self.assertRaises(OSError):
                self.request()
        self.assertTrue(process.reaped)

    def test_active_reader_close_is_skipped(self):
        process = FakeProcess()
        process.stdout_thread = types.SimpleNamespace(is_alive=lambda: True)
        process.stderr_thread = types.SimpleNamespace(is_alive=lambda: True)
        process.stderr = io.BytesIO()
        HTTP._close_pipes(process)
        self.assertFalse(process.stdout.closed)
        self.assertFalse(process.stderr.closed)
        process.stdout_thread = process.stderr_thread = None
        HTTP._close_pipes(process)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)

    def test_runtime_python37_syntax(self):
        ast.parse(MODULE_PATH.read_text(encoding='utf-8'), feature_version=(3, 7))


if __name__ == '__main__':
    unittest.main()

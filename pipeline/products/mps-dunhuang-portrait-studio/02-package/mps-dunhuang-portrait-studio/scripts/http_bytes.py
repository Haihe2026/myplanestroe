"""Bounded one-shot HTTP transactions in a short-lived standard-library helper.

The parent deadline includes helper startup and DNS/headers/body work. OS process
creation, termination and reaping still have scheduling overhead; this is not a
hard real-time guarantee. No retries, shell, credential arguments or temp files.
"""
import json
import math
import os
import struct
import subprocess
import sys
import threading
import time
from urllib.parse import unquote, urlsplit


MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_REQUEST_BYTES = 32 * 1024 * 1024
REAP_TIMEOUT_S = 2.0
OFFLINE_SWITCH = 'MPS_DUNHUANG_OFFLINE_TEST'


def read_response(response, limit, deadline):
    chunks, total = [], 0
    reader = getattr(response, 'read1', response.read)
    sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OSError('response deadline reached')
        if sock is not None:
            sock.settimeout(remaining)
        block = reader(min(65536, limit + 1 - total))
        # read1 may itself consume multiple reads for chunk framing/trailers.
        # The parent process boundary supplies cancellation while it is blocked.
        if time.monotonic() >= deadline:
            raise OSError('response deadline reached')
        if not block:
            return b''.join(chunks)
        if not isinstance(block, bytes):
            raise OSError('invalid response bytes')
        total += len(block)
        if total > limit:
            raise OSError('response too large')
        chunks.append(block)


def _validate(method, url, headers, timeout, limit):
    if method not in ('GET', 'POST') or not isinstance(url, str):
        raise OSError('invalid request')
    if len(url) > 8192 or any(ord(ch) < 32 or ord(ch) == 127 for ch in url):
        raise OSError('invalid request')
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise OSError('invalid request') from None
    if (parsed.scheme != 'https' or parsed.netloc != 'myplanestore.com' or parsed.fragment or
            not parsed.path.startswith('/platform-api/')):
        raise OSError('request destination unavailable')
    decoded = parsed.path
    for _ in range(2):
        decoded = unquote(decoded)
        if '\\' in decoded or any(part in ('.', '..') for part in decoded.split('/')):
            raise OSError('invalid request path')
    if not isinstance(headers, dict) or len(headers) > 32:
        raise OSError('invalid request headers')
    for key, value in headers.items():
        if (not isinstance(key, str) or not isinstance(value, str) or
                len(key) > 128 or len(value) > 16384 or
                any(ord(ch) < 32 or ord(ch) == 127 for ch in key + value)):
            raise OSError('invalid request headers')
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or
            not math.isfinite(timeout) or timeout <= 0):
        raise OSError('invalid request timeout')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= MAX_RESPONSE_BYTES:
        raise OSError('invalid response limit')


def _kill_and_reap(process):
    """Terminate this helper only; bounded cleanup does not retry any request."""
    try:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=REAP_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        # A second bounded wait handles delayed exit notification without an
        # unbounded wait. An OS refusing termination cannot be solved by retrying.
        try:
            process.wait(timeout=REAP_TIMEOUT_S)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _close_pipes(process):
    for name in ('stdin', 'stdout', 'stderr'):
        reader = getattr(process, name + '_thread', None)
        if reader is not None and reader.is_alive():
            # Windows communicate readers own their BufferedReader lock. If OS
            # termination/reaping is delayed, close must not block this thread.
            continue
        stream = getattr(process, name, None)
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _write_stdin(stream, payload, done, result):
    """Own the stdin stream exclusively; never hold the deadline thread in write."""
    ok = False
    try:
        view = memoryview(payload)
        while view:
            written = stream.write(view)
            if not isinstance(written, int) or written <= 0 or written > len(view):
                raise OSError('request pipe unavailable')
            view = view[written:]
        stream.flush()
        ok = True
    except Exception:
        pass
    finally:
        try:
            stream.close()
        except Exception:
            ok = False
        result[0] = ok
        done.set()


def request(method, url, body, headers, timeout, limit):
    """Return (HTTP status, bounded bytes), or a sanitized OSError; never retry.

    Only the fixed helper command is visible in process arguments. Request
    credentials and response bytes stay in stdin/stdout memory pipes.
    """
    started = time.monotonic()
    _validate(method, url, headers, timeout, limit)
    deadline = started + timeout
    try:
        payload = json.dumps(dict(method=method, url=url, body=body, headers=headers,
                                  timeout=timeout, limit=limit), ensure_ascii=False,
                             allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError):
        raise OSError('invalid request data') from None
    if len(payload) > MAX_REQUEST_BYTES:
        raise OSError('request too large')
    if time.monotonic() >= deadline:
        raise OSError('request deadline reached')
    command = [sys.executable, '-I', '-S', os.path.abspath(__file__), '--http-worker']
    options = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                   shell=False)
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    process = None
    writer = None
    writer_started = False
    input_stream = None
    try:
        process = subprocess.Popen(command, **options)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OSError('request deadline reached')
        # Windows communicate(input=large_payload) writes stdin synchronously
        # before its timeout-controlled reader joins. Detach stdin first so that
        # communicate cannot flush, write or close a writer-owned buffered stream.
        input_stream = process.stdin
        if input_stream is None:
            raise OSError('request pipe unavailable')
        process.stdin = None
        written = threading.Event()
        write_result = [False]
        writer = threading.Thread(target=_write_stdin,
                                  args=(input_stream, payload, written, write_result), daemon=True,
                                  name='mps-http-stdin-writer')
        writer.start()
        writer_started = True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OSError('request deadline reached')
        try:
            wire, _ = process.communicate(input=None, timeout=remaining)
        except subprocess.TimeoutExpired:
            raise OSError('request deadline reached') from None
        writer.join(timeout=max(0.0, deadline - time.monotonic()))
        if not written.is_set() or not write_result[0]:
            raise OSError('request pipe unavailable')
        if time.monotonic() >= deadline:
            raise OSError('request deadline reached')
        if process.returncode != 0 or not isinstance(wire, bytes) or len(wire) < 4 or len(wire) > limit + 4:
            raise OSError('request unavailable')
        status = struct.unpack('!I', wire[:4])[0]
        if not 100 <= status <= 599:
            raise OSError('request unavailable')
        return status, wire[4:]
    except (OSError, RuntimeError):
        raise OSError('request unavailable') from None
    finally:
        if process is not None:
            if process.poll() is None:
                _kill_and_reap(process)
            if writer_started:
                # Killing the helper normally breaks the blocked write and lets
                # its owner close stdin. Never close that stream from this thread:
                # BufferedWriter.close could wait on the blocked writer's lock.
                writer.join(timeout=REAP_TIMEOUT_S)
            elif input_stream is not None:
                try:
                    input_stream.close()
                except OSError:
                    pass
            _close_pipes(process)


def _perform_request(data):
    # This gate is inherited even with -I, which ignores Python-specific env vars.
    # It is checked before constructing an opener or performing DNS/network work.
    if os.environ.get(OFFLINE_SWITCH) == '1':
        raise OSError('offline development check')
    import urllib.error
    import urllib.request

    method, url, headers = data['method'], data['url'], data['headers']
    timeout, limit = data['timeout'], data['limit']
    _validate(method, url, headers, timeout, limit)
    deadline = time.monotonic() + timeout
    raw_body = json.dumps(data['body'], ensure_ascii=False, allow_nan=False).encode('utf-8') if data['body'] is not None else None

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    req = urllib.request.Request(url, data=raw_body, headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            return response.status, read_response(response, limit, deadline)
    except urllib.error.HTTPError as error:
        # Redirects and non-success HTTP statuses preserve status, never follow or
        # read an unbounded error body, and never expose a credential-bearing error.
        try:
            return error.code, b''
        finally:
            error.close()


def _worker_main():
    wire = struct.pack('!I', 0)
    try:
        payload = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(payload) > MAX_REQUEST_BYTES:
            raise OSError('request too large')
        data = json.loads(payload)
        if not isinstance(data, dict) or set(data) != {'method', 'url', 'body', 'headers', 'timeout', 'limit'}:
            raise OSError('invalid request')
        _validate(data['method'], data['url'], data['headers'], data['timeout'], data['limit'])
        status, raw = _perform_request(data)
        if not isinstance(status, int) or not 100 <= status <= 599 or not isinstance(raw, bytes) or len(raw) > data['limit']:
            raise OSError('invalid response')
        wire = struct.pack('!I', status) + raw
    except Exception:
        # No repr, traceback, URL, header, request, response or secret on stderr.
        pass
    sys.stdout.buffer.write(wire)
    sys.stdout.buffer.flush()
    return 0


if __name__ == '__main__':
    if sys.argv[1:] != ['--http-worker']:
        sys.exit(2)
    sys.exit(_worker_main())

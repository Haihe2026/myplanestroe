"""Shared handoff transport. Does not implement any AI's product workflow."""
import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parent
ROUTES = {"brief_ready": "codex", "spec_ready": "claude", "test_failed": "claude",
          "package_ready": "codex", "test_passed": "codex", "listed": "codex"}
ROLES = {"codex", "claude", "muse"}
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")


def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_config():
    return json.loads((ROOT / "config.local.json").read_text(encoding="utf-8-sig"))


def child_env(cfg):
    env = dict(os.environ)
    if cfg.get("proxy"):
        env.update(HTTPS_PROXY=cfg["proxy"], HTTP_PROXY=cfg["proxy"])
    env["NO_PROXY"] = "localhost,127.0.0.1,::1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    env["PYTHONUTF8"] = "1"
    env["PATH"] = str(Path(cfg["node"]).parent) + os.pathsep + env.get("PATH", "")
    return env


def run(cfg, argv, cwd=None, timeout=45, payload=None):
    p = subprocess.run(argv, cwd=cwd, env=child_env(cfg), input=payload,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, creationflags=0x08000000 if os.name == "nt" else 0)
    if p.returncode:
        # Do not record credential-bearing stderr or command lines in public/local health.
        raise RuntimeError(f"{Path(argv[0]).name} failed (exit {p.returncode})")
    return p.stdout


def api(cfg, endpoint, method="GET", body=None):
    argv = [cfg["gh"], "api", endpoint, "--method", method]
    if body is not None:
        argv += ["--input", "-"]
    out = run(cfg, argv, payload=json.dumps(body) if body is not None else None)
    return json.loads(out) if out.strip() else {}


def remote_file(cfg, path):
    return api(cfg, f"repos/{cfg['repository']}/contents/{path}?ref={cfg['branch']}")


def publish_new(cfg, path, value):
    # Immutable path and Contents API create-only: competing writers cannot overwrite.
    body = {"message": "[relay] handoff metadata", "branch": cfg["branch"],
            "content": base64.b64encode((json.dumps(value, ensure_ascii=False, indent=2)+"\n").encode()).decode()}
    try:
        return api(cfg, f"repos/{cfg['repository']}/contents/{path}", "PUT", body)
    except RuntimeError:
        current = remote_file(cfg, path)
        stored = json.loads(base64.b64decode(current["content"]))
        if stored != value:
            raise RuntimeError("immutable event collision")
        return current


def valid_request(req, repository):
    allowed = {"request_id", "from", "to", "skill_id", "source_repo", "source_ref", "source_path", "kind"}
    if set(req) != allowed or req["from"] not in ROLES or req["to"] not in ROLES:
        raise ValueError("invalid role or request fields")
    if not SLUG.fullmatch(req["skill_id"]) or not SLUG.fullmatch(req["request_id"]):
        raise ValueError("invalid identifier")
    if req["source_repo"] != repository or not re.fullmatch(r"[a-f0-9]{40}", req["source_ref"]):
        raise ValueError("request repository/ref not allowed")
    path = PurePosixPath(req["source_path"])
    if path.is_absolute() or ".." in path.parts or not str(path).startswith("pipeline/products/" + req["skill_id"] + "/"):
        raise ValueError("request path outside product")
    if req["kind"] not in {"handoff", "question", "dependency", "retry"}:
        raise ValueError("invalid request kind")
    return req


def request_event(req):
    # Keep the v1 envelope compatible; preserve the sender's business type explicitly.
    return dict(req, schema_version=1, event_id="evt-" + digest(req),
                kind="request", request_kind=req["kind"])


def product_event(repo, ref, status_path, status, input_objects):
    skill = status_path.split("/")[2]
    if not SLUG.fullmatch(skill) or status.get("skill_id") != skill:
        raise ValueError("status skill identity mismatch")
    stage = status.get("stage")
    if stage not in ROUTES:
        return None
    fingerprint = digest({"status": status, "inputs": input_objects})
    return {"schema_version": 1, "event_id": "evt-" + fingerprint, "kind": "stage_ready",
            "to": ROUTES[stage], "skill_id": skill, "stage": stage,
            "source_repo": repo, "source_ref": ref, "source_path": status_path,
            "input_fingerprint": fingerprint}


class Relay:
    def __init__(self, cfg, root=ROOT):
        self.cfg, self.root = cfg, Path(root)
        self.state = self.root / "state"
        self.state.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.state / "relay.sqlite3", timeout=5)
        self.db.execute("CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, payload TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0)")
        self.db.execute("CREATE TABLE IF NOT EXISTS cursors(name TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.commit()

    def remember(self, event):
        before = self.db.total_changes
        self.db.execute("INSERT OR IGNORE INTO events(id,payload) VALUES(?,?)",
                        (event["event_id"], json.dumps(event, ensure_ascii=False)))
        inserted = self.db.total_changes > before
        # Upgrade unsent legacy payloads only. Published immutable events are never reissued.
        if not inserted and event.get("request_kind"):
            old = self.db.execute("SELECT payload,published FROM events WHERE id=?", (event["event_id"],)).fetchone()
            if old and old[1] == 0 and not json.loads(old[0]).get("request_kind"):
                self.db.execute("UPDATE events SET payload=? WHERE id=? AND published=0", (json.dumps(event, ensure_ascii=False),event["event_id"]))
        self.db.commit()
        return inserted

    def git(self, *args):
        proxy = ["-c", "http.proxy=" + self.cfg["proxy"]] if self.cfg.get("proxy") else []
        return run(self.cfg, [self.cfg["git"], *proxy, "-C", self.cfg["checkout"], *args])

    def sync(self):
        self.git("fetch", "--quiet", "origin", self.cfg["branch"])
        ref = self.git("rev-parse", "FETCH_HEAD").strip()
        entries = self.git("ls-tree", "-r", "--format=%(objectname) %(path)", ref, "pipeline/products", "pipeline/relay").splitlines()
        objects = dict((line.split(" ", 1)[1], line.split(" ", 1)[0]) for line in entries)
        added, rejected = 0, []
        for path in sorted(objects):
            if re.fullmatch(r"pipeline/products/[^/]+/status\.json", path):
                try:
                    status = json.loads(self.git("show", ref + ":" + path))
                    prefix = path.rsplit("/", 1)[0] + "/"
                    # Only business inputs cause a notification; relay/log/board updates don't.
                    inputs = {p: sha for p, sha in objects.items() if p.startswith(prefix) and
                              (p.endswith("00-brief.md") or p.endswith("01-dev-spec.md") or
                               p.endswith("01-dev-spec.json") or p.endswith("02-self-test.md") or
                               "/dist/" in p)}
                    event = product_event(self.cfg["repository"], ref, path, status, inputs)
                    if event:
                        added += int(self.remember(event))
                except (ValueError, KeyError):
                    rejected.append(path)
            elif re.fullmatch(r"pipeline/relay/requests/[^/]+\.json", path):
                try:
                    req = valid_request(json.loads(self.git("show", ref + ":" + path)), self.cfg["repository"])
                    event = request_event(req)
                    added += int(self.remember(event))
                except (ValueError, KeyError):
                    rejected.append(path)
        self.db.execute("INSERT OR REPLACE INTO cursors VALUES('last_commit',?)", (ref,))
        self.db.commit()
        return ref, added, rejected

    def flush(self):
        pending = self.db.execute("SELECT id,payload FROM events WHERE published=0 ORDER BY rowid LIMIT 10").fetchall()
        for event_id, payload in pending:
            event = json.loads(payload)
            write_json(self.root / "inbox" / event["to"] / (event_id + ".json"), event)
            if self.cfg.get("publish_events", False):
                publish_new(self.cfg, f"pipeline/relay/events/{event['to']}/{event_id}.json", event)
                self.db.execute("UPDATE events SET published=1 WHERE id=?", (event_id,))
                self.db.commit()
        return len(pending)

    def health(self, **values):
        counts = dict(self.db.execute("SELECT published,COUNT(*) FROM events GROUP BY published").fetchall())
        value = {"checked_at": now(), "pid": os.getpid(), "repository": self.cfg["repository"],
                 "branch": self.cfg["branch"], "interval_seconds": self.cfg["interval_seconds"],
                 "scope": "shared-handoff-only", "agent_workflows": "owned by each AI; not implemented here",
                 "pending_publication": counts.get(0, 0), "published_events": counts.get(1, 0), **values}
        write_json(self.state / "health.json", value)
        return value


@contextlib.contextmanager
def singleton(root):
    lockpath = Path(root) / "state" / "tick.lock"
    lockpath.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lockpath, "a+b")
    if os.name == "nt":
        import msvcrt
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            yield False
            return
    else:
        import fcntl
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            yield False
            return
    try:
        yield True
    finally:
        handle.close()


def tick():
    cfg = load_config()
    with singleton(ROOT) as acquired:
        if not acquired:
            return {"state": "already_running"}
        relay = Relay(cfg)
        try:
            if (ROOT / "PAUSED").exists():
                return relay.health(state="paused")
            ref, added, rejected = relay.sync()
            count = relay.flush()
            return relay.health(state="watching", last_success_at=now(), source_commit=ref,
                                new_events=added, delivered_or_pending=count, rejected_paths=rejected)
        except Exception as exc:
            # Error class is recorded; full network output may contain account/session data.
            return relay.health(state="connection_error", error_type=type(exc).__name__,
                                next_action="Check network and gh auth status; retained events will retry next tick")
        finally:
            relay.db.close()


def receipt(cfg, event_id, role, action, evidence, claim_id=None):
    if not re.fullmatch(r"evt-[a-f0-9]{64}", event_id) or role not in ROLES:
        raise ValueError("invalid event/role")
    event = remote_file(cfg, f"pipeline/relay/events/{role}/{event_id}.json")
    payload = json.loads(base64.b64decode(event["content"]))
    if payload.get("to") != role:
        raise ValueError("wrong event target")
    path = f"pipeline/relay/receipts/{role}/{event_id}.json"
    record = {"event_id": event_id, "role": role, "action": action, "at": now(), "evidence_ref": evidence,
              "claim_id": claim_id or str(uuid.uuid4())}
    if action == "claimed":
        # No existing sha: claim is a create-only compare-and-swap.
        api(cfg, f"repos/{cfg['repository']}/contents/{path}", "PUT",
            {"message": "[relay] claim handoff", "branch": cfg["branch"],
             "content": base64.b64encode(json.dumps(record).encode()).decode()})
    else:
        if not re.fullmatch(r"[a-f0-9]{40}:[A-Za-z0-9_./\-\u4e00-\u9fff]+", evidence or "") or ".." in evidence:
            raise ValueError("completion requires commit:path evidence")
        old = remote_file(cfg, path)
        previous = json.loads(base64.b64decode(old["content"]))
        if not claim_id or previous.get("claim_id") != claim_id or previous.get("role") != role:
            raise ValueError("claim ownership mismatch")
        if previous.get("action") == "acknowledged" and previous.get("evidence_ref") == evidence:
            return previous
        if previous.get("action") != "claimed":
            raise ValueError("only a claimed notification can be acknowledged")
        api(cfg, f"repos/{cfg['repository']}/contents/{path}", "PUT",
            {"message": "[relay] acknowledge handoff", "branch": cfg["branch"], "sha": old["sha"],
             "content": base64.b64encode(json.dumps(record).encode()).decode()})
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["tick", "status", "claim", "ack"])
    parser.add_argument("--event")
    parser.add_argument("--role", choices=sorted(ROLES))
    parser.add_argument("--evidence")
    parser.add_argument("--claim-id")
    args = parser.parse_args()
    if args.command == "tick":
        result = tick()
    elif args.command == "status":
        result = json.loads((ROOT / "state" / "health.json").read_text(encoding="utf-8"))
    else:
        result = receipt(load_config(), args.event or "", args.role, "claimed" if args.command == "claim" else "acknowledged", args.evidence, args.claim_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

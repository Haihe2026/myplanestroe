"""Keep the existing event-only Codex consumer available at user sign-in."""
import os
from pathlib import Path
import subprocess
import sys
import time
from relay import ROOT, now, singleton, write_json

BASE = ROOT / "codex-consumer"

def tick():
    health = {"pid": os.getpid(), "checked_at": now(), "state": "checking"}
    write_json(BASE / "state" / "supervisor-health.json", health)
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "codex_consumer.py"), "--once"],
            cwd=ROOT, timeout=240,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        health.update(state="watching" if result.returncode == 0 else "retrying",
                      consumer_exit=result.returncode)
    except Exception as exc:
        health.update(state="retrying", error_type=type(exc).__name__)
    health["checked_at"] = now()
    write_json(BASE / "state" / "supervisor-health.json", health)
    return health

def main():
    with singleton(BASE / "supervisor") as locked:
        if not locked:
            return
        while not (BASE / "STOP").exists():
            started = time.monotonic()
            tick()
            # Normal program polling only. No model call without a new event.
            while time.monotonic() - started < 60:
                if (BASE / "STOP").exists():
                    return
                time.sleep(1)

if __name__ == "__main__":
    main()

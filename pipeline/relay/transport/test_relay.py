import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from relay import Relay, product_event, valid_request, request_event, digest, singleton


class SharedRelayTests(unittest.TestCase):
    def sample(self, stage="brief_ready", name="mps-synthetic"):
        return product_event("owner/repo", "a"*40, f"pipeline/products/{name}/status.json",
                             {"skill_id": name, "stage": stage}, {"00-brief.md": "b"*40})

    def test_stage_routes(self):
        for stage, role in [("brief_ready", "codex"), ("spec_ready", "muse"),
                            ("test_failed", "codex"), ("package_ready", "codex"),
                            ("test_passed", "muse"), ("listed", "codex")]:
            self.assertEqual(self.sample(stage)["to"], role)

    def test_no_in_progress_or_blocked_retrigger(self):
        for stage in ["dev_in_progress", "blocked", "spec_in_progress"]:
            self.assertIsNone(self.sample(stage))

    def test_own_commit_does_not_retrigger(self):
        a = self.sample()
        b = product_event("owner/repo", "c"*40, a["source_path"],
                          {"skill_id": "mps-synthetic", "stage": "brief_ready"}, {"00-brief.md": "b"*40})
        self.assertEqual(a["event_id"], b["event_id"])

    def test_identity_and_path(self):
        with self.assertRaises(ValueError):
            self.sample(name="../bad")

    def test_ten_deliveries_once(self):
        with tempfile.TemporaryDirectory() as directory:
            r = Relay({}, directory)
            try:
                self.assertEqual(sum(r.remember(self.sample()) for _ in range(10)), 1)
            finally:
                r.db.close()

    def test_restart_retains_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            r = Relay({}, directory)
            r.remember(self.sample())
            r.db.close()
            r = Relay({}, directory)
            self.assertEqual(r.db.execute("SELECT COUNT(*) FROM events WHERE published=0").fetchone()[0], 1)
            r.db.close()

    def test_publish_failure_keeps_event(self):
        with tempfile.TemporaryDirectory() as directory:
            r = Relay({"publish_events": True}, directory)
            r.remember(self.sample())
            with patch("relay.publish_new", side_effect=RuntimeError("network failure")):
                with self.assertRaises(RuntimeError):
                    r.flush()
            self.assertEqual(r.db.execute("SELECT published FROM events").fetchone()[0], 0)
            r.db.close()

    def test_delivery_creates_correct_local_inbox(self):
        with tempfile.TemporaryDirectory() as directory:
            r = Relay({"publish_events": True}, directory)
            event = self.sample("spec_ready")
            r.remember(event)
            with patch("relay.publish_new") as publish:
                r.flush()
                r.flush()
                self.assertEqual(publish.call_count, 1)
            self.assertTrue((Path(directory)/"inbox"/"muse"/(event["event_id"]+".json")).exists())
            r.db.close()

    def test_request_rejects_commands_and_other_repo(self):
        req = {"request_id": "req-1", "skill_id": "mps-synthetic", "from": "muse", "to": "codex",
               "source_repo": "owner/repo", "source_ref": "a"*40,
               "source_path": "pipeline/products/mps-synthetic/00-brief.md", "kind": "handoff"}
        valid_request(req, "owner/repo")
        with self.assertRaises(ValueError):
            valid_request(dict(req, shell="do something"), "owner/repo")
        with self.assertRaises(ValueError):
            valid_request(dict(req, source_repo="other/repo"), "owner/repo")
        with self.assertRaises(ValueError):
            valid_request(dict(req, source_path="pipeline/products/mps-synthetic/../x"), "owner/repo")

    def test_all_request_types_survive_transport(self):
        for kind in ["handoff", "question", "dependency", "retry"]:
            req = {"request_id":"req-1", "skill_id":"mps-synthetic", "from":"muse", "to":"codex",
                   "source_repo":"owner/repo", "source_ref":"a"*40,
                   "source_path":"pipeline/products/mps-synthetic/00-brief.md", "kind":kind}
            event = request_event(valid_request(req, "owner/repo"))
            self.assertEqual(event["kind"], "request")
            self.assertEqual(event["request_kind"], kind)
            self.assertEqual(event["event_id"], "evt-"+digest(req))

    def test_request_type_survives_inbox_delivery_and_restart(self):
        req = {"kind":"question", "to":"codex"}
        event = request_event(req)
        with tempfile.TemporaryDirectory() as directory:
            r = Relay({}, directory);r.remember(event);r.db.close()
            r = Relay({}, directory);r.flush()
            saved=json.loads((Path(directory)/"inbox"/"codex"/(event["event_id"]+".json")).read_text(encoding="utf-8"))
            self.assertEqual(saved["request_kind"], "question")
            r.db.close()

    def test_pending_legacy_upgrades_without_reissuing_published(self):
        event=request_event({"kind":"question","to":"codex"})
        legacy={k:v for k,v in event.items() if k!="request_kind"}
        with tempfile.TemporaryDirectory() as directory:
            r=Relay({},directory);r.remember(legacy)
            self.assertFalse(r.remember(event))
            self.assertEqual(json.loads(r.db.execute("SELECT payload FROM events").fetchone()[0])["request_kind"],"question")
            r.db.execute("UPDATE events SET published=1,payload=?",(json.dumps(legacy),));r.db.commit()
            r.remember(event)
            self.assertNotIn("request_kind",json.loads(r.db.execute("SELECT payload FROM events").fetchone()[0]))
            r.db.close()

    def test_claim_collision_fails_not_treated_as_success(self):
        from relay import receipt
        event = self.sample()
        import base64
        value = {"content": base64.b64encode(json.dumps(event).encode()).decode()}
        with patch("relay.remote_file", return_value=value), patch("relay.api", side_effect=RuntimeError("conflict")):
            with self.assertRaises(RuntimeError):
                receipt({"repository":"owner/repo", "branch":"main"}, event["event_id"], "codex", "claimed", None)

    def test_singleton_prevents_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            with singleton(directory) as first:
                self.assertTrue(first)
                with singleton(directory) as second:
                    self.assertFalse(second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

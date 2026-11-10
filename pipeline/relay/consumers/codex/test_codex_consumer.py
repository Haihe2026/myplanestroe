import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from codex_consumer import Consumer,codex_executable,validate_event,worker_command


class ConsumerTests(unittest.TestCase):
    def test_unattended_worker_uses_review_without_disabling_sandbox(self):
        job=Path("isolated-job")
        argv=worker_command({"codex":"codex.exe"},job/"worktree",job)
        self.assertIn("--approve-for-me",argv)
        self.assertIn('apps._default.approvals_reviewer="auto_review"',argv)
        for conflicting in ["-a","never","--sandbox","--dangerously-bypass-approvals-and-sandbox"]:
            self.assertNotIn(conflicting,argv)
        self.assertEqual(argv[argv.index("--add-dir")+1],str(job))

    def test_windows_fallback_is_worker_local_and_cannot_disable_isolation(self):
        job=Path("isolated-job")
        argv=worker_command({"codex":"codex.exe","windows_sandbox":"unelevated"},job/"worktree",job)
        self.assertIn("windows.sandbox=unelevated",argv)
        self.assertIn("--approve-for-me",argv)
        with self.assertRaises(ValueError):
            worker_command({"codex":"codex.exe","windows_sandbox":"danger-full-access"},job/"worktree",job)

    def test_removed_desktop_binary_resolves_within_installation(self):
        import os

        with tempfile.TemporaryDirectory() as base:
            install_root = Path(base) / "OpenAI" / "Codex" / "bin"
            removed = install_root / "0123456789abcdef" / "codex.exe"
            current = install_root / "fedcba9876543210" / "codex.exe"
            current.parent.mkdir(parents=True)
            current.touch()
            with patch.dict(os.environ, {"LOCALAPPDATA": base}):
                self.assertEqual(codex_executable({"codex": str(removed)}), str(current))
                with self.assertRaises(FileNotFoundError):
                    codex_executable({"codex": str(Path(base) / "custom" / "codex.exe")})

    def test_all_product_stages_route_to_this_chat(self):
        import json

        with tempfile.TemporaryDirectory() as base:
            config = Path(base) / "worker.local.json"
            config.write_text(json.dumps({"muse_delivery": "chat_queue"}), encoding="utf-8")
            c = Consumer({"repository": "o/r"}, base)
            try:
                self.assertTrue(c.wants_chat_delivery({"kind": "stage_ready", "stage": "brief_ready"}))
                self.assertTrue(c.wants_chat_delivery({"kind": "stage_ready", "stage": "package_ready"}))
                self.assertTrue(c.wants_chat_delivery({"kind": "stage_ready", "stage": "test_passed"}))
                self.assertFalse(c.wants_chat_delivery({"kind": "transport_probe"}))
                self.assertFalse(c.wants_chat_delivery({"kind": "stage_ready", "is_test": True}))
                self.assertTrue(c.wants_chat_delivery({"kind": "request", "from": "muse"}))
            finally:
                c.db.close()

    def test_muse_notice_queues_once_without_starting_worker(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base);e=dict(self.event(),**{"from":"muse"})
            listings=[[{"name":e["event_id"]+".json","path":"event"}],[]]*2
            with patch("codex_consumer.api",side_effect=listings),patch.object(c,"get",return_value=({},json.dumps(e))),patch("codex_consumer.receipt",return_value={"claim_id":"x"}) as claim,patch.object(c,"wants_chat_delivery",return_value=True),patch.object(c,"queue_notice") as send,patch.object(c,"execute") as execute:
                c.poll();c.poll()
                self.assertEqual(send.call_count,1);self.assertEqual(claim.call_count,1);execute.assert_not_called()
            self.assertEqual(c.db.execute("SELECT state FROM events").fetchone()[0],"queued_to_chat")
            c.db.close()

    def test_queue_failure_is_not_blindly_resent(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base);e=dict(self.event(),**{"from":"muse"})
            with patch("codex_consumer.api",side_effect=[[{"name":e["event_id"]+".json","path":"event"}],[]]*2),patch.object(c,"get",return_value=({},json.dumps(e))),patch("codex_consumer.receipt",return_value={"claim_id":"x"}),patch.object(c,"wants_chat_delivery",return_value=True),patch.object(c,"queue_notice",side_effect=RuntimeError("unknown")) as send:
                c.poll();c.poll();self.assertEqual(send.call_count,1)
            c.db.close()

    def test_empty_poll_never_calls_ai_or_claim(self):
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base)
            with patch("codex_consumer.api",side_effect=[[],[]]),patch.object(c,"execute") as execute,patch.object(c,"codex_work") as work,patch("codex_consumer.receipt") as claim:
                c.poll()
                execute.assert_not_called();work.assert_not_called();claim.assert_not_called()
            c.db.close()

    def test_legacy_failed_stage_resumes_original_claim_in_chat(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c = Consumer({"repository":"o/r"}, base)
            e = dict(self.event(), kind="stage_ready", stage="package_ready")
            claim = dict(event_id=e["event_id"], role="codex", action="claimed", claim_id="same")
            (c.base/"state"/(e["event_id"]+".json")).write_text(json.dumps(claim))
            c.record(e["event_id"], "needs_followup", "same")
            with patch.object(c,"get",side_effect=[({},json.dumps(claim)),({},json.dumps(e))]), patch.object(c,"acknowledge_superseded_stage",return_value=False), patch.object(c,"wants_chat_delivery",return_value=True), patch.object(c,"queue_notice") as queue, patch.object(c,"execute") as execute:
                c.reconcile(e["event_id"], "needs_followup")
                queue.assert_called_once_with(e)
                execute.assert_not_called()
            self.assertEqual(c.db.execute("SELECT claim_id FROM events").fetchone()[0], "same")
            c.db.close()

    def test_acknowledgement_in_chat_is_reconciled_locally(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c = Consumer({"repository":"o/r"}, base)
            e = self.event()
            ack = dict(event_id=e["event_id"], role="codex", action="acknowledged", claim_id="same", evidence_ref="fixed:path")
            with patch.object(c,"get",return_value=({},json.dumps(ack))), patch.object(c,"queue_notice") as queue:
                c.reconcile(e["event_id"], "queued_to_chat")
                queue.assert_not_called()
            self.assertEqual(c.db.execute("SELECT state,evidence FROM events").fetchone(), ("acknowledged","fixed:path"))
            c.db.close()

    def test_unknown_queue_outcome_is_not_sent_twice(self):
        with tempfile.TemporaryDirectory() as base:
            c = Consumer({"repository":"o/r"}, base)
            e = self.event()
            with patch.object(c,"queue_notice",side_effect=TimeoutError) as queue:
                with self.assertRaises(TimeoutError):
                    c.deliver_to_chat(e,{"claim_id":"same"})
                c.deliver_to_chat(e,{"claim_id":"same"})
                self.assertEqual(queue.call_count,1)
            self.assertEqual(c.db.execute("SELECT state FROM events").fetchone()[0],"chat_delivery_unknown")
            c.db.close()

    def test_queue_requests_resume_in_configured_chat(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c = Consumer({"repository":"o/r"}, base)
            thread = "01a1b145-e321-72b1-836d-da9452de10e8"
            (c.base/"worker.local.json").write_text(json.dumps({"codex":"codex.exe","notification_thread":thread}))
            with patch("codex_consumer.run",return_value="Queued message") as run:
                c.queue_notice(self.event())
                args = run.call_args.args[1]
                self.assertIn("--resume",args)
                self.assertEqual(args[args.index("--thread")+1],thread)
            c.db.close()

    def test_unresolved_worker_is_not_restarted(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c = Consumer({"repository":"o/r"}, base)
            e = self.event()
            claim = dict(event_id=e["event_id"], role="codex", action="claimed", claim_id="same")
            (c.base/"state"/(e["event_id"]+".json")).write_text(json.dumps(claim))
            run = c.base/"runs"/e["event_id"]
            run.mkdir(parents=True)
            (run/"execution.json").write_text("{}")
            with patch.object(c,"get",side_effect=[({},json.dumps(claim)),({},json.dumps(e))]), patch.object(c,"queue_notice") as queue:
                c.reconcile(e["event_id"],"needs_followup")
                queue.assert_not_called()
            c.db.close()

    def test_superseded_stage_is_acknowledged_without_chat_delivery(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c = Consumer({"repository":"o/r"}, base)
            event = dict(self.event(), kind="stage_ready", stage="package_ready")
            ack = dict(event_id=event["event_id"],action="acknowledged",claim_id="same")
            with patch("codex_consumer.api",return_value={"object":{"sha":"c"*40}}), patch.object(c,"get",side_effect=[({},json.dumps({"stage":"package_ready","versions":{"package":"1"}})),({},json.dumps({"stage":"test_passed","versions":{"package":"2"}}))]), patch("codex_consumer.receipt",return_value=ack) as receipt, patch.object(c,"queue_notice") as queue:
                c.deliver_to_chat(event,{"claim_id":"same"})
                queue.assert_not_called()
                self.assertEqual(receipt.call_args.args[-1],"same")
            self.assertEqual(c.db.execute("SELECT state FROM events").fetchone()[0],"acknowledged")
            c.db.close()

    def event(self):
        return {"event_id":"evt-"+"a"*64,"to":"codex","source_repo":"o/r","source_ref":"b"*40,
                "source_path":"pipeline/products/mps-probe/README.md","skill_id":"mps-probe","kind":"request"}

    def test_receiver_and_source(self):
        e=self.event()
        validate_event(e,e["event_id"]+".json","o/r")
        for changes in [{"to":"claude"},{"source_repo":"other/repo"},{"source_ref":"main"},
                        {"source_path":"pipeline/products/mps-probe/../x"}]:
            with self.assertRaises(ValueError):validate_event(dict(e,**changes),e["event_id"]+".json","o/r")

    def test_reject_mismatched_filename(self):
        with self.assertRaises(ValueError):validate_event(self.event(),"evt-wrong.json","o/r")

    def test_legacy_kind_recovered_from_hashed_original(self):
        import json
        from relay import request_event
        req={"request_id":"req-probe","from":"claude","to":"codex","skill_id":"mps-relay-probe",
             "source_repo":"o/r","source_ref":"b"*40,"source_path":"pipeline/products/mps-relay-probe/README.md","kind":"question"}
        event=request_event(req);event.pop("request_kind")
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base)
            with patch.object(c,"get",side_effect=[({},json.dumps(req)),({},"���ǲ�Ʒ����")]):
                self.assertEqual(c.execute(event)[1],"transport_probe")
            c.db.close()

    def test_changed_legacy_original_is_rejected(self):
        import json
        from relay import request_event
        req={"request_id":"req-probe","from":"claude","to":"codex","skill_id":"mps-relay-probe",
             "source_repo":"o/r","source_ref":"b"*40,"source_path":"pipeline/products/mps-relay-probe/README.md","kind":"question"}
        event=request_event(req);event.pop("request_kind")
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base)
            with patch.object(c,"get",return_value=({},json.dumps(dict(req,kind="handoff")))):
                with self.assertRaises(ValueError):c.execute(event)
            c.db.close()

    def test_remote_claim_prevents_second_execution(self):
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base)
            e=self.event()
            responses=[[{"name":e["event_id"]+".json","path":"event"}], [{"name":e["event_id"]+".json"}]]
            with patch("codex_consumer.api",side_effect=responses),patch.object(c,"get",return_value=({},__import__('json').dumps(e))),patch.object(c,"execute") as execute:
                c.poll()
                execute.assert_not_called()
            c.db.close()

    def test_claim_then_ack_once_even_with_repeated_poll(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base);e=self.event()
            receipts=[{"claim_id":"claim-1"},{"action":"acknowledged"}]
            with patch("codex_consumer.api",side_effect=[[{"name":e["event_id"]+".json","path":"event"}],[],[{"name":e["event_id"]+".json","path":"event"}],[]]),patch.object(c,"get",return_value=({},json.dumps(e))),patch.object(c,"execute",return_value=("b"*40+":pipeline/products/mps-probe/README.md","probe")),patch("codex_consumer.receipt",side_effect=receipts) as call:
                c.poll();c.poll();self.assertEqual(call.call_count,2)
            c.db.close()

    def test_failure_keeps_claim_and_does_not_ack(self):
        import json
        with tempfile.TemporaryDirectory() as base:
            c=Consumer({"repository":"o/r"},base);e=self.event()
            with patch("codex_consumer.api",side_effect=[[{"name":e["event_id"]+".json","path":"event"}],[]]),patch.object(c,"get",return_value=({},json.dumps(e))),patch.object(c,"execute",side_effect=RuntimeError("error")),patch("codex_consumer.receipt",return_value={"claim_id":"x"}) as call:
                c.poll();self.assertEqual(call.call_count,1)
                self.assertEqual(c.db.execute("SELECT state FROM events").fetchone()[0],"needs_followup")
            c.db.close()


if __name__=="__main__":unittest.main(verbosity=2)

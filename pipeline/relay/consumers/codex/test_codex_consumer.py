import tempfile
import unittest
from unittest.mock import patch
from codex_consumer import Consumer,validate_event


class ConsumerTests(unittest.TestCase):
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
            with patch.object(c,"get",side_effect=[({},json.dumps(req)),({},"不是产品任务")]):
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

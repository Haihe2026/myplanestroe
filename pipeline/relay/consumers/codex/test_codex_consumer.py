import tempfile
import unittest
from unittest.mock import patch
from codex_consumer import Consumer,validate_event


class ConsumerTests(unittest.TestCase):
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

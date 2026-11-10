import subprocess
import unittest
from unittest.mock import patch
import watch_codex_consumer as guard


class SupervisorTests(unittest.TestCase):
    def test_failed_child_retries_on_next_cycle(self):
        with patch.object(guard, "write_json"), patch.object(guard.subprocess, "run", side_effect=[subprocess.CompletedProcess([],1), subprocess.CompletedProcess([],0)]) as run:
            self.assertEqual(guard.tick()["state"], "retrying")
            self.assertEqual(guard.tick()["state"], "watching")
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args.args[0][-1], "--once")

    def test_timeout_is_recorded_and_next_cycle_recovers(self):
        with patch.object(guard, "write_json"), patch.object(guard.subprocess, "run", side_effect=[subprocess.TimeoutExpired("consumer",240), subprocess.CompletedProcess([],0)]):
            self.assertEqual(guard.tick()["error_type"], "TimeoutExpired")
            self.assertEqual(guard.tick()["state"], "watching")


if __name__ == "__main__":
    unittest.main()
